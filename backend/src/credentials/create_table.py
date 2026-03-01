from backend.src.feature.initial import initial

def create_table(location:str)->None:

    '''
    Params: Take location of database

    Function for Creating table with
    user_name text Primary key
    password text
    '''
    
    conn,cursor = initial(location)

    cursor.execute(
    """
CREATE TABLE IF NOT EXISTS credentials(
        user_name TEXT PRIMARY KEY,
        password TEXT NOT NULL
    )
    """
)

    conn.commit()
    conn.close()

    

    return None
 

