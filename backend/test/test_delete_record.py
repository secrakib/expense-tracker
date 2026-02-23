
from backend.src.delete_record import delete_record
from backend.test.globals import location

x = delete_record(location, user_name='rakib',category='cloth')
print(x)