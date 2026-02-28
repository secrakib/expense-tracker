
from backend.src.feature.delete_record import delete_record
from backend.test.test_feature.globals import location

x = delete_record(location, user_name='rakin',category='cloth')
print(x)