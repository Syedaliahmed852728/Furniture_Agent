import os
import pandas as pd
from sqlalchemy import create_engine, text
import re
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

def get_engine():
    import urllib.parse
    server = os.getenv('DB_SERVER')
    database = os.getenv('DB_NAME')
    username = urllib.parse.quote_plus(os.getenv('DB_USER'))
    password = urllib.parse.quote_plus(os.getenv('DB_PASSWORD'))
    driver = 'ODBC Driver 17 for SQL Server'

    connection_string = (
        f"mssql+pyodbc://{username}:{password}@{server},1433/{database}"
        f"?driver={driver.replace(' ', '+')}&TrustServerCertificate=yes"
    )

    return create_engine(connection_string)

def run_sql_query(sql):
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn)
    return df

def extract_schema():
    engine = get_engine()
    query = """
    SELECT TABLE_NAME, COLUMN_NAME
    FROM INFORMATION_SCHEMA.COLUMNS
    ORDER BY TABLE_NAME, ORDINAL_POSITION;
    """

    with engine.connect() as conn:
        result = conn.execute(text(query))
        rows = result.fetchall()

    schema = {}
    for table, column in rows:
        if table not in schema:
            schema[table] = []
        schema[table].append(column)

    schema_text = ""
    for table, columns in schema.items():
        column_str = ", ".join(columns)
        schema_text += f"TABLE {table} ({column_str})\n"

    return schema_text.strip()


FORBIDDEN_STMTS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|BACKUP|RESTORE|EXECUTE|EXEC|RECONFIGURE)\b",
    re.IGNORECASE,
)

class ReadOnlyCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def _ensure_read_only_sql(self, sql):
        if isinstance(sql, str):
            stripped = sql.lstrip()
            if FORBIDDEN_STMTS.search(stripped):
                raise PermissionError(
                    "Query blocked: only read-only queries (SELECT/CTE) are permitted in this context."
                )

    def execute(self, sql, *params, **kwargs):
        self._ensure_read_only_sql(sql)
        return self._cursor.execute(sql, *params, **kwargs)

    def executemany(self, sql, seq_of_params):
        self._ensure_read_only_sql(sql)
        return self._cursor.executemany(sql, seq_of_params)

    def callproc(self, procname, *args, **kwargs):
        raise PermissionError("Calling stored procedures is not allowed in read-only mode.")

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchmany(self, size=None):
        return self._cursor.fetchmany(size) if size else self._cursor.fetchmany()

    def fetchall(self):
        return self._cursor.fetchall()

    def close(self):
        return self._cursor.close()

    @property
    def description(self):
        return self._cursor.description

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def __iter__(self):
        return iter(self._cursor)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


@contextmanager
def with_sqlserver_cursor():
    """
    Context manager that yields a DB-API (pyodbc) connection and a read-only cursor proxy.

    Usage:
        with with_sqlserver_cursor() as (conn, cur):
            cur.execute("SELECT ...")
            rows = cur.fetchall()

    Characteristics:
    - Any SQL containing write/DDL keywords (INSERT/UPDATE/DELETE/CREATE/DROP/etc.)
      will raise PermissionError before being executed.
    - Stored procedure calls are blocked.
    - The manager will ALWAYS rollback (so no accidental writes persist).
    - Resources are properly closed and the engine disposed.
    """
    engine = get_engine()
    dbapi_conn = None
    raw_cur = None
    ro_cur = None

    try:
        dbapi_conn = engine.raw_connection()
        raw_cur = dbapi_conn.cursor()
        ro_cur = ReadOnlyCursor(raw_cur)
        yield dbapi_conn, ro_cur

        try:
            dbapi_conn.rollback()
        except Exception:
            pass

    except SQLAlchemyError:
        if dbapi_conn:
            try:
                dbapi_conn.rollback()
            except Exception:
                pass
        raise
    except PermissionError:
        raise
    except Exception:
        if dbapi_conn:
            try:
                dbapi_conn.rollback()
            except Exception:
                pass
        raise
    finally:
        if ro_cur:
            try:
                ro_cur.close()
            except Exception:
                pass
        elif raw_cur:
            try:
                raw_cur.close()
            except Exception:
                pass

        if dbapi_conn:
            try:
                dbapi_conn.close()
            except Exception:
                pass
        try:
            engine.dispose()
        except Exception:
            pass

# with with_sqlserver_cursor() as (con, cur):
#     cur.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE';")
#     result = cur.fetchall()
#     print(result)
