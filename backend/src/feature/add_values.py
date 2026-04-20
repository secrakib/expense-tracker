from backend.src.feature.initial import initial
from sqlite3 import IntegrityError


def add_values(user_name: str, category: str, expense: float, date: str, location: str) -> dict:
    """
    Adds a new expense record for the given user.

    Params:
        user_name - the logged-in user
        category  - expense category (stored lowercase)
        expense   - expense amount
        date      - date string YYYY-MM-DD
        location  - path to the database

    Returns:
        dict with key: message (str)

    Raises:
        ValueError on integrity error (e.g. user does not exist in credentials)
    """
    conn, cursor = initial(location)

    try:
        cursor.execute(
            "INSERT INTO expenses (user_name, category, expense, date) VALUES (?,?,?,?)",
            (user_name.lower(), category.lower(), expense, date)
        )
    except IntegrityError as e:
        conn.close()
        raise ValueError(f"Could not add expense: {e}")

    conn.commit()
    conn.close()

    return {"message": "Expense added successfully."}