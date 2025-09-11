from langchain.tools import tool
import re
from typing import List
from db import with_sqlserver_cursor 
import pandas as pd
from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from utils import llm_agent
from langgraph.prebuilt import tools_condition
from langgraph.graph import END


Table_name = "ConsolidateData_PBI"



IDENT_RE = re.compile(r'^[A-Za-z0-9_\$\#]+(?:\.[A-Za-z0-9_\$\#]+)?$') 
IDENT_PART_RE = re.compile(r'^[A-Za-z0-9_\$\#]+$')


def _split_schema_table(name: str):
    parts = name.split('.', 1)
    if len(parts) == 1:
        return 'dbo', parts[0]
    return parts[0], parts[1]


def _quote_ident(identifier: str) -> str:
    return f"[{identifier.replace(']', ']]')}]"


def _normalize_table_list(tables_str: str) -> List[str]:
    return [t.strip() for t in tables_str.split(',') if t.strip()]


@tool(parse_docstring=True)
def get_table_info() -> str:
    """
    Return schema and up to max_samples non-null sample values per column for one or more SQL Server tables.

    Returns:
        str: Human-readable schema + sample values for each requested table.
    """
    tables = _normalize_table_list(Table_name)
    if not tables:
        return "No valid table names provided."

    for t in tables:
        if not IDENT_RE.match(t):
            return f"Invalid table identifier: '{t}'. Allowed characters: letters, numbers, _, $, # and optional schema prefix."

    output_lines = []

    with with_sqlserver_cursor() as (dbapi_conn, cur):
        for raw_name in tables:
            schema, table = _split_schema_table(raw_name)

            if not (IDENT_PART_RE.match(schema) and IDENT_PART_RE.match(table)):
                output_lines.append(f"⚠ Skipping invalid identifier: {raw_name}")
                continue

            output_lines.append(f"\n=== Table: {schema}.{table} ===")

            exists_q = """
                SELECT 1
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND TABLE_TYPE = 'BASE TABLE';
            """
            cur.execute(exists_q, (schema, table))
            if not cur.fetchone():
                output_lines.append(f"table '{schema}.{table}' does not exist.\n")
                continue

            cols_q = """
                SELECT
                    c.COLUMN_NAME,
                    c.ORDINAL_POSITION,
                    c.DATA_TYPE,
                    COALESCE(c.CHARACTER_MAXIMUM_LENGTH, c.NUMERIC_PRECISION, c.DATETIME_PRECISION) AS length_or_precision,
                    c.IS_NULLABLE,
                    c.COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS c
                WHERE c.TABLE_SCHEMA = ? AND c.TABLE_NAME = ?
                ORDER BY c.ORDINAL_POSITION
            """
            cur.execute(cols_q, (schema, table))
            cols = cur.fetchall()
            if not cols:
                output_lines.append("  (No schema found)\n")
                continue

            pk_q = """
                SELECT kcu.COLUMN_NAME
                FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                  ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                 AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
                 AND tc.TABLE_NAME = kcu.TABLE_NAME
                WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                  AND tc.TABLE_SCHEMA = ?
                  AND tc.TABLE_NAME = ?
                ORDER BY kcu.ORDINAL_POSITION
            """
            cur.execute(pk_q, (schema, table))
            pk_rows = cur.fetchall()
            pk_cols = {r[0] for r in pk_rows} if pk_rows else set()

            # Append schema description
            output_lines.append("Schema:")
            for column_name, ordinal, data_type, length_or_precision, is_nullable, column_default in cols:
                constraints = []
                if column_name in pk_cols:
                    constraints.append("PRIMARY KEY")
                if is_nullable and is_nullable.upper() == "NO":
                    constraints.append("NOT NULL")
                if column_default is not None:
                    constraints.append(f"DEFAULT {column_default}")
                length_info = f"({length_or_precision})" if length_or_precision is not None else ""
                constraints_str = " ".join(constraints) if constraints else ""
                output_lines.append(f"  - {column_name} {data_type}{length_info} {constraints_str}".rstrip())

            # Example values (up to max_samples distinct non-null samples per column)
            output_lines.append("\nExample values (up to {} non-null samples):".format(3))
            quoted_schema = _quote_ident(schema)
            quoted_table = _quote_ident(table)

            for column_name, ordinal, data_type, length_or_precision, is_nullable, column_default in cols:
                if not IDENT_PART_RE.match(column_name):
                    output_lines.append(f"  - {column_name}: (skipped invalid column name)")
                    continue

                quoted_col = _quote_ident(column_name)
                # We must embed identifiers directly (safe because validated & quoted), but values are selected with no params
                sample_q = f"SELECT DISTINCT TOP 3 {quoted_col} FROM {quoted_schema}.{quoted_table} WHERE {quoted_col} IS NOT NULL;"
                try:
                    cur.execute(sample_q)
                    sample_rows = cur.fetchall()
                    values = []
                    for r in sample_rows:
                        v = r[0]
                        if v is None:
                            continue
                        s = str(v)
                        # keep output readable
                        if len(s) > 200:
                            s = s[:197] + "..."
                        values.append(s)
                    if values:
                        output_lines.append(f"  - {column_name}: {', '.join(values)}")
                    else:
                        output_lines.append(f"  - {column_name}: (no non-null values)")
                except Exception as e:
                    output_lines.append(f"  - {column_name}: ⚠ Error fetching values ({e})")

    return "\n".join(output_lines)

@tool(parse_docstring=True)
def run_sql_query(query: str) -> pd.DataFrame:
    """
    Execute a SQL Server query in read-only mode and return results as a Pandas DataFrame.

    Args:
        query (str): The raw SQL query (must be read-only, e.g., SELECT).

    Returns:
        pd.DataFrame: Query results as a DataFrame.
    """
    with with_sqlserver_cursor() as (conn, cur):
        cur.execute(query)
        rows = cur.fetchall()

        # If no rows, return empty DataFrame
        if not rows:
            return pd.DataFrame()

        # Extract column names from cursor.description
        columns = [col[0] for col in cur.description]

        # Build DataFrame
        df = pd.DataFrame.from_records(rows, columns=columns)

    return df


primary_agent_prompt = ChatPromptTemplate.from_messages(
    [
        (""
            "system",
            "You are a helpful assistant for a furniture business. "
            "Your primary role is to answer customer queries by routing them through the provided tools. "
            "Don't Directly execute the query without having the information about tables and database schema"
            "If the user asks about furniture sales, customers, prices, profits, or other business-related details, "
            "use the tools to fetch the relevant information from the database. "
            "Do not mention database names, tables, or technical details to the user. "
            "If the question is casual or unrelated to the data, respond directly without using tools. "
            "If the query is unclear, ask for clarification first. "
            "When processing queries, you may run multiple intermediate queries (e.g., fetching distinct values, checking for closest matches, etc.) before forming the final query that provides the correct result. "
            "If a query with filters returns no result, check distinct values of the relevant column(s), find the closest matches, and suggest them to the user before finalizing the response. "
            "Always provide clear, human-readable responses after tool use. "
            "\nCurrent time: {time}.",
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=datetime.now)


def get_primary_agent_tools():
    return [
        # get_database_info,
        get_table_info,
        run_sql_query,
    ]

Primary_agent = primary_agent_prompt | llm_agent.bind_tools(get_primary_agent_tools())


def route_primary_assistant(state):
    route = tools_condition(state)
    if route==END:
        return "end"
    tool_calls = state["messages"][-1].tool_calls
    if tool_calls:
        return "primary_agent_tools"


# ans =get_table_info()
# print(ans)