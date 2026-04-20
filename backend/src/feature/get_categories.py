from backend.src.feature.initial import initial


def get_categories(location: str, user_name: str) -> list[str]:
    """
    Returns a list of distinct expense categories for the given user.
    Returns an empty list if the user has no expenses yet.

    Params:
        location  - path to the database
        user_name - the logged-in user
    """
    conn, cursor = initial(location)

    cursor.execute(
        "SELECT DISTINCT category FROM expenses WHERE user_name = ?",
        (user_name.lower(),)
    )
    rows = cursor.fetchall()
    conn.close()

    return [row[0] for row in rows]