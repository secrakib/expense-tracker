import psycopg2
from psycopg2.extensions import connection, cursor as Cursor
from typing import Tuple


def initial(database_url: str) -> Tuple[connection, Cursor]:
    """
    Connect to a PostgreSQL database.

    Params:
        database_url - libpq connection string, e.g.
                       "postgresql://user:pass@host:5432/dbname"

    Returns:
        (conn, cursor) — caller is responsible for commit/close.
    """
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    return conn, cursor