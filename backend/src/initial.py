

def initial(location:str):
    '''
    Function needed for every query
    and connect to database

    Return : conn,cursor
    '''
    import sqlite3
    conn = sqlite3.connect(location)
    cursor = conn.cursor()

    return conn,cursor