from backend.src.initial import initial

def value_exist_check(location:str,id:int):
    conn, cursor = initial(location)

    cursor.execute("SELECT * FROM expenses WHERE id = ?", (id,))

    value = cursor.fetchone()
    if not value:
        raise ValueError(f"id '{id}' not in database")

    
