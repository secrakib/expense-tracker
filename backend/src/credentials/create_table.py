from backend.src.credentials.initial import initial


def create_table(database_url: str) -> None:
    """
    Creates the credentials table if it does not already exist.

    Schema:
        user_name  TEXT  PRIMARY KEY
        password   TEXT  NOT NULL
    """
    conn, cursor = initial(database_url)

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS credentials (
            user_name TEXT PRIMARY KEY,
            password  TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()