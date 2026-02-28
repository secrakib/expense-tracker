from backend.src.feature.initial import initial

def create_table(location:str)->None:

    '''
    Params: Take location of database

    Function for Creating table with
    user_name text
    category text
    expense real
    data text
    id integer and primary key
    '''
    
    conn,cursor = initial(location)
    cursor.execute("PRAGMA foreign_keys = ON")

    cursor.execute(
    """
CREATE TABLE IF NOT EXISTS credentials(
        user_name TEXT PRIMARY KEY,
        password TEXT NOT NULL
    )
    """
)

    cursor.execute(
    """
CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT NOT NULL,
        category TEXT NOT NULL,
        expense REAL NOT NULL,
        date TEXT NOT NULL,
        FOREIGN KEY (user_name) REFERENCES credentials(user_name)
            ON DELETE CASCADE
    )
    """
)

    conn.commit()
    conn.close()

    

    return None
 

