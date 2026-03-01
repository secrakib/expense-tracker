from backend.src.credentials.initial import initial

def add_values(user_name:str, password:str,location:str)->None:
    '''
    Params: user name , hashed password 
    Function to add values to table
    '''
    conn,cursor = initial(location)

    cursor.execute(
        '''
    INSERT INTO CREDENTIALS (user_name, password) VALUES (?,?)
        ''',
        (user_name.lower(), password)
    )

    conn.commit()
    conn.close()

    return None

