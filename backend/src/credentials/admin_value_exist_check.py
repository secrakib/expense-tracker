from backend.src.credentials.initial import initial

def admin_user_name_exist_check(location:str,user_name:str):
    conn, cursor = initial(location)
    user_name = user_name.lower()
    cursor.execute("SELECT * FROM credentials WHERE user_name = ?", (user_name,))

    value = cursor.fetchone()
    return value 