from backend.src.feature.initial import initial
from typing import Optional
from backend.src.feature.filter_and_show import filter_expenses


def delete_record(
    location: str,
    user_name: str,
    category: Optional[str] = None,
    date: Optional[str] = None,
    min_expense: Optional[float] = None,
    max_expense: Optional[float] = None,
) -> dict:
    """
    Deletes expense records matching the given filters for the user.
    Filters first, then deletes matching ids.

    Params:
        location    - path to the database
        user_name   - filter by user name
        category    - filter by category
        date        - filter by date (e.g. '2024-01-15')
        min_expense - filter by minimum expense amount
        max_expense - filter by maximum expense amount

    Returns:
        dict with keys: message (str), deleted_ids (list[int])

    Raises:
        ValueError if no filters are provided
    """
    if not any([category, date, min_expense is not None, max_expense is not None]):
        raise ValueError("At least one filter must be provided.")

    conn, cursor = initial(location)

    matching = filter_expenses(location, user_name, category, date, min_expense, max_expense)
    deleted_ids = []

    for record in matching:
        record_id = record["id"]
        cursor.execute("DELETE FROM expenses WHERE id = ?", (record_id,))
        deleted_ids.append(record_id)

    conn.commit()
    conn.close()

    return {
        "message": f"{len(deleted_ids)} record(s) deleted successfully.",
        "deleted_ids": deleted_ids,
    }