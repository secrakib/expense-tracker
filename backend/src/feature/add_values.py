from backend.src.feature.initial import initial

def add_values(user_name:str, category:str, expense:str, date:str,location:str)->None:
    '''
    Params: date format YYYY-MM-DD
    Function to add values to table
    '''
    conn,cursor = initial(location)

    cursor.execute(
        '''
    INSERT INTO expenses (user_name, category, expense, date) VALUES (?,?,?,?)
        ''',
        (user_name.lower(), category.lower(), expense, date)
    )

    conn.commit()
    conn.close()

    return None

