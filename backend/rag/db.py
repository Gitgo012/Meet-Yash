import os
import psycopg
from pgvector.psycopg import register_vector

def get_connection():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")
    conn = psycopg.connect(database_url, connect_timeout=10)
    register_vector(conn)
    return conn
