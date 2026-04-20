from backend.src.feature.initial import initial
from typing import Optional
from backend.src.feature.value_exist_check import value_exist_check_id, value_exist_check_user_name


def update_values(
    location: str,
    id: int,
    user_name: str,
    category: Optional[str] = None,
    expense: Optional[float] = None,
    date: Optional[str] = None,
) -> dict:
    """
    Updates an expense record by id for the given user.

    Params:
        location  - path to the database
        id        - the expense record id to update
        user_name - must match the owner of the record
        category  - new category value (optional)
        expense   - new expense amount (optional)
        date      - new date string YYYY-MM-DD (optional)

    Returns:
        dict with keys: updated_id, changes (dict of fields that were updated)

    Raises:
        ValueError if id or user_name not found, or if no fields provided
    """
    conn, cursor = initial(location)

    if not value_exist_check_user_name(location, user_name) or not value_exist_check_id(location, id):
        raise ValueError(f"id {id} or user name {user_name} not found")

    if category is None and expense is None and date is None:
        raise ValueError("At least one value should be given.")

    changes = {}

    if category is not None:
        cursor.execute("UPDATE expenses SET category = ? WHERE id = ?", (category.lower(), id))
        changes["category"] = category.lower()

    if expense is not None:
        cursor.execute("UPDATE expenses SET expense = ? WHERE id = ?", (expense, id))
        changes["expense"] = expense

    if date is not None:
        cursor.execute("UPDATE expenses SET date = ? WHERE id = ?", (date, id))
        changes["date"] = date

    conn.commit()
    conn.close()

    return {"updated_id": id, "changes": changes}