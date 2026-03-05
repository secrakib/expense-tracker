from backend.src.feature.initial import initial
from typing import Optional
from backend.src.feature.value_exist_check import value_exist_check_user_name

def filter_expenses(
    location: str,
    user_name: str,
    category: Optional[str] = None,
    date: Optional[str] = None,
    min_expense: Optional[float] = None,
    max_expense: Optional[float] = None,
) -> list[tuple]:
    """
    Params: 
        location   - path to the database
        user_name  - filter by user name
        category   - filter by category 
        date       - filter by date (e.g. '2024-01-15')
        min_expense - filter by minimum expense amount
        max_expense - filter by maximum expense amount

    Remember: user_name and category will be input as lowercase
    
    Returns a list of matching expense records as dicts.
    """
    conn, cursor = initial(location)

    query = "SELECT * FROM expenses WHERE 1=1"
    params = []

    value_exist_check_user_name(location,user_name)

    query += " AND user_name = ?"
    params.append(user_name.lower())


    if category:
        query += " AND category = ?"
        params.append(category.lower())

    if date:
        query += " AND date = ?"
        params.append(date)

    if min_expense is not None:
        query += " AND expense >= ?"
        params.append(min_expense)

    if max_expense is not None:
        query += " AND expense <= ?"
        params.append(max_expense)

    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return rows



