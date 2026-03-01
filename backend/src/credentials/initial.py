

def initial(location:str):
    '''
    Function needed for every query
    and connect to database

    Return : conn,cursor
    '''
    import sqlite3
    conn = sqlite3.connect(location)
    conn.execute("PRAGMA foreign_keys = ON")
    
    cursor = conn.cursor()

    return conn,cursor