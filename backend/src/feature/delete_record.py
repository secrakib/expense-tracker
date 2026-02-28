from backend.src.feature.initial import initial
from typing import Optional
from backend.src.feature.filter_and_show import filter_expenses

def delete_record(location: str,
    user_name: str,
    category: Optional[str] = None,
    date: Optional[str] = None,
    min_expense: Optional[float] = None,
    max_expense: Optional[float] = None,
) -> dict:
    """
    Function for deleting a record from expenses table based on id. 
    It first filters the records based on the given 
    criteria and then deletes the matching records.

    Params: 
        location   - path to the database
        user_name  - filter by user name
        category   - filter by category 
        date       - filter by date (e.g. '2024-01-15')
        min_expense - filter by minimum expense amount
        max_expense - filter by maximum expense amount

    Remember: user_name and category will be input as lowercase
    
    """
    conn, cursor = initial(location)
    id_list = []
    output = filter_expenses(location, user_name, category, date, min_expense, max_expense)
    for i in  output:
        id = i[0]
        id_list.append(id)
        cursor.execute("DELETE FROM expenses WHERE id = ?", (id,))
        conn.commit()
    conn.close()
    
    return {"message": f"{len(output)} record(s) deleted successfully.", "deleted_ids": id_list}