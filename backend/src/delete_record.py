from backend.src.initial import initial
from backend.src.value_exist_check import value_exist_check
def delete_record(location: str, id: int) -> None:
    '''
    Params: Take location of database and id of record to delete
    
    Function for deleting a record from expenses table based on id
    '''
    value_exist_check(location, id)
    conn, cursor = initial(location)
    
    cursor.execute("DELETE FROM expenses WHERE id = ?", (id,))
    
    conn.commit()
    conn.close()
    
    return None