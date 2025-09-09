import pandas as pd
import sqlite3


df = pd.read_csv("TurnerAI.csv")


df.columns = df.columns.str.strip()

if "From_Date" in df.columns:
    df["From_Date"] = pd.to_datetime(df["From_Date"], errors='coerce').dt.strftime('%Y-%m-%d')

conn = sqlite3.connect("sales_data.db")
df.to_sql("sales", conn, if_exists="replace", index=False)
conn.close()

print("✅ Cleaned data and imported into SQLite successfully.")