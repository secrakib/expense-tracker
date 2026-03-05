from backend.src.credentials.delete_user import delete_user
from backend.test.test_feature.globals import location
x =delete_user(location,user_name='rakin')
print(x)