import duckdb

from .config import DB_PATH, DB_SCHEMA


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    if DB_SCHEMA != "main":
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}")
    return con
