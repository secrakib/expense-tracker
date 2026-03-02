from backend.src.credentials.initial import initial
from sqlite3 import IntegrityError
def add_values(user_name:str, password:str,location:str)->None:
    '''
    Params: user name , hashed password 
    Function to add values to table
    '''
    conn,cursor = initial(location)

    try:
        cursor.execute(
            '''
        INSERT INTO CREDENTIALS (user_name, password) VALUES (?,?)
            ''',
            (user_name.lower(), password)
        )
    except IntegrityError as e:
        if 'UNIQUE' in str(e):
            print(f"Duplicate key Detected ")
        else:
            print(f"Error {e} Occured ")
        return None

    conn.commit()
    conn.close()

