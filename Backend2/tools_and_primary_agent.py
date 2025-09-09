from langchain.tools import tool
from db_connection import with_sqlite_cursor
import json
from config import Config
from utils import llm_agent
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langgraph.prebuilt import tools_condition
from langgraph.graph import END


@tool(parse_docstring=True)
def get_database_info() -> str:
    """Return human-readable information about the SQLite database.

    Returns:
        str: Information about SQLite version, encoding, foreign keys,
             tables, views, and indexes in the database.
    """
    with with_sqlite_cursor() as (conn, cur):
        lines = []
        cur.execute("SELECT sqlite_version();")
        sqlite_version = cur.fetchone()[0]
        lines.append(f"SQLite version: {sqlite_version}")

        cur.execute("PRAGMA encoding;")
        encoding = cur.fetchone()[0]
        lines.append(f"Encoding: {encoding}")

        cur.execute("PRAGMA foreign_keys;")
        fk_enabled = "Enabled" if cur.fetchone()[0] else "Disabled"
        lines.append(f"Foreign Keys: {fk_enabled}")

        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [row[0] for row in cur.fetchall()]
        lines.append(f"\nTables ({len(tables)}):")
        lines.extend([f"  - {t}" for t in tables] or ["  (No tables found)"])

        cur.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name;")
        views = [row[0] for row in cur.fetchall()]
        lines.append(f"\nViews ({len(views)}):")
        lines.extend([f"  - {v}" for v in views] or ["  (No views found)"])

        cur.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' ORDER BY name;")
        indexes = cur.fetchall()
        lines.append(f"\nIndexes ({len(indexes)}):")
        lines.extend(
            [f"  - {idx} (on table: {tbl})" for idx, tbl in indexes] or ["  (No indexes found)"]
        )

        return "\n".join(lines)


@tool(parse_docstring=True)
def get_table_info(tables_str: str) -> str:
    """Return schema and sample values for one or more SQLite tables.

    Args:
        tables_str (str): Comma-separated list of table names.

    Returns:
        str: Human-readable schema details and 3 non-null example values per column.
    """
    tables = [t.strip() for t in tables_str.split(",") if t.strip()]
    if not tables:
        return "No valid table names provided."

    output = []
    with with_sqlite_cursor() as (conn, cur):
        for table in tables:
            output.append(f"\n=== Table: {table} ===")

            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table,))
            if not cur.fetchone():
                output.append(f"  ⚠️ Table '{table}' does not exist.\n")
                continue

            cur.execute(f'PRAGMA table_info("{table}");')
            schema = cur.fetchall()
            if not schema:
                output.append("  (No schema found)\n")
                continue

            output.append("Schema:")
            for col_id, name, col_type, notnull, default_val, pk in schema:
                constraints = []
                if pk:
                    constraints.append("PRIMARY KEY")
                if notnull:
                    constraints.append("NOT NULL")
                if default_val is not None:
                    constraints.append(f"DEFAULT {default_val}")
                constraints_str = " ".join(constraints) if constraints else ""
                output.append(f"  - {name} ({col_type}) {constraints_str}")

            output.append("\nExample values:")
            for col_id, name, col_type, notnull, default_val, pk in schema:
                try:
                    cur.execute(
                        f'SELECT "{name}" FROM "{table}" WHERE "{name}" IS NOT NULL LIMIT 3;'
                    )
                    values = [str(row[0]) for row in cur.fetchall()]
                    if values:
                        output.append(f"  - {name}: {', '.join(values)}")
                    else:
                        output.append(f"  - {name}: (no non-null values)")
                except Exception as e:
                    output.append(f"  - {name}: ⚠️ Error fetching values ({e})")

    return "\n".join(output)


@tool(parse_docstring=True)
def run_sqlite_query(query: str) -> str:
    """Execute a SQLite query and return results with safeguards.

    Args:
        query (str): The raw SQLite query to execute.

    Returns:
        str: Query results as pretty JSON, or an error/empty message if no data is found.
             If the result is too large (> ~6000 tokens), a message is returned asking
             to refine the query with smaller date ranges or filters.
    """
    with with_sqlite_cursor() as (conn, cur):
        try:
            cur.execute(query)
            rows = cur.fetchall()
            col_names = [desc[0] for desc in cur.description] if cur.description else []

            if not rows:
                return "No data found for that query. Please ask again with a more clear question."

            results = [dict(zip(col_names, row)) for row in rows]

            result_str = json.dumps(results, indent=2, ensure_ascii=False)

            if len(result_str) > Config.MAX_TOKENS * 4:  # rough char-to-token estimate
                return (
                    "Response is too long. Please ask the user refine your query by using "
                    "smaller date ranges or more filters."
                )
            print("this is the final response",result_str)

            return result_str

        except Exception as e:
            return f"Error executing query: {e}"


primary_agent_prompt = ChatPromptTemplate.from_messages(
    [
        (
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
        get_database_info,
        get_table_info,
        run_sqlite_query,
    ]

Primary_agent = primary_agent_prompt | llm_agent.bind_tools(get_primary_agent_tools())


def route_primary_assistant(state):
    route = tools_condition(state)
    if route==END:
        return "end"
    tool_calls = state["messages"][-1].tool_calls
    if tool_calls:
        return "primary_agent_tools"
