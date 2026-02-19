from backend.src.initial import initial
from typing import Optional
from backend.src.value_exist_check import value_exist_check

def update_values(location: str, id: int, user_name: Optional[str] = None, category: Optional[str] = None, expense: Optional[str] = None, date: Optional[str] = None):
    conn, cursor = initial(location)
    
    value_exist_check(location,id)

    if user_name is None and category is None and expense is None and date is None:
        raise ValueError("At least one value should be given.")

    if user_name is not None:
        cursor.execute("UPDATE expenses SET user_name = ? WHERE id = ?", (user_name, id))

    if category is not None:
        cursor.execute("UPDATE expenses SET category = ? WHERE id = ?", (category, id))

    if expense is not None:
        cursor.execute("UPDATE expenses SET expense = ? WHERE id = ?", (expense, id))

    if date is not None:
        cursor.execute("UPDATE expenses SET date = ? WHERE id = ?", (date, id))

    conn.commit()

    return None

