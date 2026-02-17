from backend.src.initial import initial

conn, cursor = initial('backend/test/test_database/database.db')

cursor.execute("SELECT * FROM expenses")

print(cursor.fetchall())
