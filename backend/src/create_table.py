from backend.src.initial import initial

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

    cursor.execute(
        """
CREATE TABLE IF NOT EXISTS expenses(
    user_name TEXT NOT NULL,
    category TEXT NOT NULL,
    expense REAL NOT NULL,
    date TEXT NOT NULL,
    id INTEGER PRIMARY KEY)
        """
    )

    conn.commit()
    conn.close()

    

    return None
 

