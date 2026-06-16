from backend.src.feature.initial import initial


def value_exist_check_id(database_url: str, id: int):
    """Returns the expense row with the given id, or None."""
    conn, cursor = initial(database_url)
    cursor.execute("SELECT * FROM expenses WHERE id = %s", (id,))
    value = cursor.fetchone()
    conn.close()
    return value


def value_exist_check_user_name(database_url: str, user_name: str):
    """Returns the first expense row for user_name, or None."""
    conn, cursor = initial(database_url)
    cursor.execute(
        "SELECT * FROM expenses WHERE user_name = %s",
        (user_name.lower(),),
    )
    value = cursor.fetchone()
    conn.close()
    return value