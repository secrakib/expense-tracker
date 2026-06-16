from backend.src.credentials.initial import initial


def delete_table(database_url: str, table_name: str) -> None:
    """
    Drops the given table if it exists.

    WARNING: table_name is interpolated directly — only pass trusted values.

    Params:
        database_url - PostgreSQL connection string
        table_name   - name of the table to drop
    """
    conn, cursor = initial(database_url)

    # CASCADE drops dependent objects (e.g. FK references) automatically.
    cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")

    conn.commit()
    conn.close()