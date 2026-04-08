import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@db:5432/microblog"
)

# Движок SQLAlchemy
engine = create_engine(DATABASE_URL)
# Фабрика сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Базовый класс для всех моделей
Base = declarative_base()


def get_db():
    """
    Генератор сессии БД. Используется как зависимость FastAPI.

    Yields:
        Session: Сессия SQLAlchemy

    Ensures:
        Сессия всегда закрывается после использования
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
