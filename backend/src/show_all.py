from backend.src.initial import initial

def show_all(location:str,user_name:str):
    conn, cursor = initial(location)

    cursor.execute("SELECT * FROM expenses WHERE user_name = ?", (user_name,))

    value = cursor.fetchall()
    if not value:
        raise ValueError(f"User Name '{user_name}' not in database")
    return print(value)

    
