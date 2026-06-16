from backend.src.feature.initial import initial
from backend.src.feature.filter_and_show import filter_expenses
from typing import Optional


def delete_record(
    database_url: str,
    user_name: str,
    category: Optional[str] = None,
    date: Optional[str] = None,
    min_expense: Optional[float] = None,
    max_expense: Optional[float] = None,
) -> dict:
    """
    Deletes expense records matching the given filters for the user.

    Params:
        database_url - PostgreSQL connection string
        user_name    - filter by user name
        category     - optional category filter
        date         - optional exact date filter (YYYY-MM-DD)
        min_expense  - optional minimum amount (inclusive)
        max_expense  - optional maximum amount (inclusive)

    Returns:
        dict with keys: message (str), deleted_ids (list[int])

    Raises:
        ValueError if no filters are provided.
    """
    if not any([category, date, min_expense is not None, max_expense is not None]):
        raise ValueError("At least one filter must be provided.")

    matching = filter_expenses(database_url, user_name, category, date, min_expense, max_expense)

    conn, cursor = initial(database_url)
    deleted_ids: list[int] = []

    for record in matching:
        cursor.execute("DELETE FROM expenses WHERE id = %s", (record["id"],))
        deleted_ids.append(record["id"])

    conn.commit()
    conn.close()

    return {
        "message": f"{len(deleted_ids)} record(s) deleted successfully.",
        "deleted_ids": deleted_ids,
    }