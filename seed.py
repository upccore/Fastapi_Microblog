from database import SessionLocal
from models import User

db = SessionLocal()

# Создаем тестовых пользователей
users = [
    User(name="Alice", api_key="alice123"),
    User(name="Bob", api_key="bob123"),
    User(name="Charlie", api_key="charlie123"),
    User(name="Test User", api_key="test"),
]

for user in users:
    existing = db.query(User).filter(User.api_key == user.api_key).first()
    if not existing:
        db.add(user)

db.commit()
db.close()
print("Тестовые пользователи созданы!")
print("api-key     Имя\nalice123    Alice\nbob123      Bob\ncharlie123  Charlie")
