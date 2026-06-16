from backend.src.credentials.initial import initial


def admin_filter_expenses(database_url: str, user_name: str) -> list[tuple]:
    """
    Returns all credential rows matching the given user_name.

    Params:
        database_url - PostgreSQL connection string
        user_name    - looked up as lowercase
    """
    conn, cursor = initial(database_url)

    cursor.execute(
        "SELECT * FROM credentials WHERE user_name = %s",
        (user_name.lower(),),
    )
    rows = cursor.fetchall()
    conn.close()

    return rows