from backend.src.feature.initial import initial


def create_table(database_url: str) -> None:
    """
    Creates the expenses table if it does not already exist.

    Schema:
        id        SERIAL  PRIMARY KEY
        user_name TEXT    NOT NULL  (FK → credentials.user_name, CASCADE DELETE)
        category  TEXT    NOT NULL
        expense   REAL    NOT NULL
        date      TEXT    NOT NULL
    """
    conn, cursor = initial(database_url)

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id        SERIAL  PRIMARY KEY,
            user_name TEXT    NOT NULL,
            category  TEXT    NOT NULL,
            expense   REAL    NOT NULL,
            date      TEXT    NOT NULL,
            FOREIGN KEY (user_name)
                REFERENCES credentials (user_name)
                ON DELETE CASCADE
        )
        """
    )

    conn.commit()
    conn.close()