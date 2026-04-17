import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app

# Устанавливаем переменную окружения для тестов
os.environ["TESTING"] = "true"



# Тестовая БД - SQLite в памяти
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """
    Создаёт таблицы один раз для всех тестов.

    Scope: session - выполняется один раз за сессию тестирования
    """
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db():
    """
    Фикстура сессии БД с изоляцией транзакций.

    Scope: function - новая сессия для каждого теста

    Yields:
        Session: Сессия SQLAlchemy
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db):
    """
    Фикстура тестового клиента с переопределённой БД.

    Args:
        db (Session): Сессия БД из фикстуры

    Yields:
        TestClient: Клиент FastAPI для тестирования эндпоинтов
    """

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
