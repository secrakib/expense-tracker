from backend.src.feature.initial import initial
from psycopg2 import errors as pg_errors


def add_values(
    user_name: str,
    category: str,
    expense: float,
    date: str,
    database_url: str,
) -> dict:
    """
    Adds a new expense record for the given user.

    Params:
        user_name    - the logged-in user (stored lowercase)
        category     - expense category (stored lowercase)
        expense      - expense amount
        date         - date string YYYY-MM-DD
        database_url - PostgreSQL connection string

    Returns:
        dict with key 'message'

    Raises:
        ValueError on integrity error (e.g. user_name not in credentials)
    """
    conn, cursor = initial(database_url)

    try:
        cursor.execute(
            "INSERT INTO expenses (user_name, category, expense, date) VALUES (%s, %s, %s, %s)",
            (user_name.lower(), category.lower(), expense, date),
        )
        conn.commit()
    except pg_errors.ForeignKeyViolation as e:
        conn.rollback()
        raise ValueError(f"Could not add expense: {e}")
    finally:
        conn.close()

    return {"message": "Expense added successfully."}