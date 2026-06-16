from backend.src.feature.initial import initial
from backend.src.feature.value_exist_check import value_exist_check_id, value_exist_check_user_name
from typing import Optional


def update_values(
    database_url: str,
    id: int,
    user_name: str,
    category: Optional[str] = None,
    expense: Optional[float] = None,
    date: Optional[str] = None,
) -> dict:
    """
    Updates an expense record by id for the given user.

    Params:
        database_url - PostgreSQL connection string
        id           - the expense record id to update
        user_name    - must match the owner of the record
        category     - new category value (optional, stored lowercase)
        expense      - new expense amount (optional)
        date         - new date string YYYY-MM-DD (optional)

    Returns:
        dict with keys: updated_id (int), changes (dict of updated fields)

    Raises:
        ValueError if id or user_name not found, or if no fields are provided.
    """
    if not value_exist_check_user_name(database_url, user_name) or not value_exist_check_id(database_url, id):
        raise ValueError(f"id {id} or user_name '{user_name}' not found")

    if category is None and expense is None and date is None:
        raise ValueError("At least one value must be provided.")

    conn, cursor = initial(database_url)
    changes: dict = {}

    if category is not None:
        cursor.execute(
            "UPDATE expenses SET category = %s WHERE id = %s",
            (category.lower(), id),
        )
        changes["category"] = category.lower()

    if expense is not None:
        cursor.execute(
            "UPDATE expenses SET expense = %s WHERE id = %s",
            (expense, id),
        )
        changes["expense"] = expense

    if date is not None:
        cursor.execute(
            "UPDATE expenses SET date = %s WHERE id = %s",
            (date, id),
        )
        changes["date"] = date

    conn.commit()
    conn.close()

    return {"updated_id": id, "changes": changes}