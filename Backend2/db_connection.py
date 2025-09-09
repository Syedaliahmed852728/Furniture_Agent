from contextlib import contextmanager
import sqlite3
from config import Config
from sqlite3 import Error

@contextmanager
def with_sqlite_cursor():
    conn = None
    cur = None
    try:
        conn = sqlite3.connect(Config.DB_NAME)
        cur = conn.cursor()
        yield conn, cur
        conn.commit()
    except Error:
        if conn:
            conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


