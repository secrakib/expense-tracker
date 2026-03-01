from backend.src.feature.initial import initial

def delete_table(location: str, table_name: str) -> None:
    """
    Params:
        location: database file location
        table_name: name of table to delete

    Deletes the given table if it exists.
    """

    conn, cursor = initial(location)

    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

    conn.commit()
    conn.close()

    return None