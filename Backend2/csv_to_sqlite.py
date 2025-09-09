import pandas as pd
from config import Config
from db_connection import with_sqlite_cursor

df = pd.read_csv("TurnerAI.csv", header=0)

df.columns = df.columns.str.strip()

def ensure_table_and_insert(conn, cursor, dataframe: pd.DataFrame):
    columns = []
    for col, dtype in zip(dataframe.columns, dataframe.dtypes):
        if "int" in str(dtype):
            sql_type = "INTEGER"
        elif "float" in str(dtype):
            sql_type = "REAL"
        else:
            sql_type = "TEXT"
        # column names now clean, no extra spaces
        columns.append(f'"{col}" {sql_type}')

    columns_sql = ", ".join(columns)
    create_table_sql = f'CREATE TABLE IF NOT EXISTS "{Config.TABLE_NAME}" ({columns_sql});'
    cursor.execute(create_table_sql)

    dataframe.to_sql(Config.TABLE_NAME, conn, if_exists="append", index=False)


with with_sqlite_cursor() as (con, cur):
    ensure_table_and_insert(conn=con, cursor=cur, dataframe=df)
