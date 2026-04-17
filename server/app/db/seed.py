from app.db.models import User
from app.db.database import SessionLocal

def seed_users():
    db = SessionLocal()
    try:
        # Проверяем, есть ли уже пользователи
        if db.query(User).count() == 0:
            users = [
                User(name="Alice", api_key="alice123"),
                User(name="Bob", api_key="bob123"),
                User(name="Charlie", api_key="charlie123"),
                User(name="Test User", api_key="test"),
            ]
            db.add_all(users)
            db.commit()
            print(f"✅ Added {len(users)} users")
        else:
            print("ℹ️ Users already exist, skipping seed")
    finally:
        db.close()

if __name__ == "__main__":
    seed_users()