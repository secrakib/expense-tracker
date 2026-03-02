from backend.src.feature.initial import initial
from typing import Optional
from backend.src.feature.value_exist_check import value_exist_check_id,value_exist_check_user_name

def update_values(location: str, id: int, user_name: str , category: Optional[str] = None, expense: Optional[str] = None, date: Optional[str] = None):
    conn, cursor = initial(location)
    
    if not value_exist_check_user_name(location,user_name) or not value_exist_check_id(location,id):
        raise ValueError(f'id {id} or user name {user_name} not found')
    
    if category is None and expense is None and date is None:
        raise ValueError("At least one value should be given.")

    if category is not None:
        cursor.execute("UPDATE expenses SET category = ? WHERE id = ?", (category, id))

    if expense is not None:
        cursor.execute("UPDATE expenses SET expense = ? WHERE id = ?", (expense, id))

    if date is not None:
        cursor.execute("UPDATE expenses SET date = ? WHERE id = ?", (date, id))

    conn.commit()

    return None

