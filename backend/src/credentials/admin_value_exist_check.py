from backend.src.credentials.initial import initial


def admin_user_name_exist_check(database_url: str, user_name: str):
    """
    Returns the credentials row for user_name, or None if not found.
    """
    conn, cursor = initial(database_url)

    cursor.execute(
        "SELECT * FROM credentials WHERE user_name = %s",
        (user_name.lower(),),
    )
    value = cursor.fetchone()
    conn.close()

    return value