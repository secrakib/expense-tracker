from backend.src.feature.initial import initial
from backend.src.feature.value_exist_check import value_exist_check_user_name
from typing import Optional


def filter_expenses(
    database_url: str,
    user_name: str,
    category: Optional[str] = None,
    date: Optional[str] = None,
    min_expense: Optional[float] = None,
    max_expense: Optional[float] = None,
) -> list[dict]:
    """
    Returns matching expense records as a list of dicts.

    Params:
        database_url - PostgreSQL connection string
        user_name    - filter by user (matched lowercase)
        category     - optional category filter (matched lowercase)
        date         - optional exact date filter (YYYY-MM-DD)
        min_expense  - optional minimum amount (inclusive)
        max_expense  - optional maximum amount (inclusive)

    Returns:
        List of dicts with keys: id, user_name, category, expense, date
    """
    conn, cursor = initial(database_url)

    # Raise early if user has no expenses (preserves original behaviour)
    value_exist_check_user_name(database_url, user_name)

    query = "SELECT * FROM expenses WHERE user_name = %s"
    params: list = [user_name.lower()]

    if category:
        query += " AND category = %s"
        params.append(category.lower())

    if date:
        query += " AND date = %s"
        params.append(date)

    if min_expense is not None:
        query += " AND expense >= %s"
        params.append(min_expense)

    if max_expense is not None:
        query += " AND expense <= %s"
        params.append(max_expense)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    keys = ["id", "user_name", "category", "expense", "date"]
    return [dict(zip(keys, row)) for row in rows]