from backend.src.feature.initial import initial
def value_exist_check_id(location:str,id:int):
    conn, cursor = initial(location)

    cursor.execute("SELECT * FROM expenses WHERE id = ?", (id,))

    value = cursor.fetchone()
    return value 

    
def value_exist_check_user_name(location:str,user_name:str):
    conn, cursor = initial(location)
    user_name = user_name.lower()
    cursor.execute("SELECT * FROM expenses WHERE user_name = ?", (user_name,))

    value = cursor.fetchone()
    return value 


