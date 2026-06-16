from backend.src.credentials.initial import initial
from backend.src.credentials.admin_filter_and_show import admin_filter_expenses
from backend.src.credentials.admin_value_exist_check import admin_user_name_exist_check


def delete_user(database_url: str, user_name: str) -> dict:
    """
    Deletes a user from the credentials table.
    The expenses rows are removed automatically via ON DELETE CASCADE.

    Params:
        database_url - PostgreSQL connection string
        user_name    - will be matched as lowercase

    Returns:
        dict with key 'message'

    Raises:
        ValueError if the user does not exist.
    """
    if not admin_user_name_exist_check(database_url, user_name):
        raise ValueError(f"User '{user_name}' not found")

    conn, cursor = initial(database_url)

    cursor.execute(
        "DELETE FROM credentials WHERE user_name = %s",
        (user_name.lower(),),
    )
    conn.commit()
    conn.close()

    return {"message": f"User '{user_name}' deleted successfully"}