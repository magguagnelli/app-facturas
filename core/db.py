import os
import psycopg
from psycopg.rows import dict_row


DB_DSN = os.getenv("DB_DSN", "")

def get_conn() -> psycopg.Connection:
    if not DB_DSN:
        raise RuntimeError("DB_DSN no está configurado. Define la variable de entorno DB_DSN.")
    return psycopg.connect(DB_DSN, row_factory=dict_row)
