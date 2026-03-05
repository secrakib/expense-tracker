from backend.src.credentials.initial import initial
from typing import Optional


def admin_filter_expenses(
    location: str,
    user_name: str
) -> list[tuple]:
    """
    Params: 
        location   - path to the database
        user_name  - filter by user name
        

    Remember: user_name will be input as lowercase
    
    Returns a list of matching expense records as dicts.
    """
    conn, cursor = initial(location)

    query = "SELECT * FROM credentials WHERE 1=1"
    params = []


    query += " AND user_name = ?"
    params.append(user_name.lower())

    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return rows