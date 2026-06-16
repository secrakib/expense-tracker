from backend.src.feature.initial import initial


def get_categories(database_url: str, user_name: str) -> list[str]:
    """
    Returns a list of distinct expense categories for the given user.

    Params:
        database_url - PostgreSQL connection string
        user_name    - the logged-in user
    """
    conn, cursor = initial(database_url)

    cursor.execute(
        "SELECT DISTINCT category FROM expenses WHERE user_name = %s",
        (user_name.lower(),),
    )
    rows = cursor.fetchall()
    conn.close()

    return [row[0] for row in rows]