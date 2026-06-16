from backend.src.feature.initial import initial


def show_all(database_url: str, user_name: str):
    conn, cursor = initial(database_url)

    cursor.execute(
        "SELECT * FROM expenses WHERE user_name = %s",
        (user_name,),
    )
    value = cursor.fetchall()
    conn.close()

    if not value:
        raise ValueError(f"User '{user_name}' not in database")
    return print(value)