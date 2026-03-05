from backend.src.credentials.initial import initial
from typing import Optional
from backend.src.credentials.admin_filter_and_show import admin_filter_expenses
from backend.src.credentials.admin_value_exist_check import admin_user_name_exist_check

def delete_user(location: str,
    user_name: str
) -> dict:
    """
    Function for deleting a record from expenses table based on id. 
    It first filters the records based on the given 
    criteria and then deletes the matching records.

    Params: 
        location   - path to the database
        user_name  - filter by user name
        
    Remember: user_name will be input as lowercase
    
    """
    conn, cursor = initial(location)
    id_list = []
    
    if not admin_user_name_exist_check(location,user_name):
        raise ValueError(f"User Name {user_name} not found")

    output = admin_filter_expenses(location, user_name)
    for i in  output:
        id = i[0]
        id_list.append(id)
        cursor.execute("DELETE FROM credentials WHERE user_name = ?", (user_name,))
        conn.commit()
    conn.close()
    
    return {"message": f"User {user_name} deleted succesfully"}