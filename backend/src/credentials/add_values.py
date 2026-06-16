from backend.src.credentials.initial import initial
from psycopg2 import errors as pg_errors


def add_values(user_name: str, password: str, database_url: str) -> dict | None:
    """
    Inserts a new user into the credentials table.

    Params:
        user_name    - will be stored lowercase
        password     - pre-hashed password string
        database_url - PostgreSQL connection string

    Returns:
        None on success, or {'message': 'duplicate'} if user_name already exists.
    """
    conn, cursor = initial(database_url)

    try:
        cursor.execute(
            "INSERT INTO credentials (user_name, password) VALUES (%s, %s)",
            (user_name.lower(), password),
        )
        conn.commit()
    except pg_errors.UniqueViolation:
        conn.rollback()
        return {"message": "duplicate"}
    finally:
        conn.close()

    return None