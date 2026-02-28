from backend.src.feature.filter_and_show import filter_expenses
from backend.test.test_feature.globals import location
x =filter_expenses(location, category="Cloth",user_name='rakin')
print(x)