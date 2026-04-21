import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.tweets.endpoints import router as tweets_router
from app.api.users.endpoints import router as users_router
from app.db.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Контекст жизненного цикла приложения.

    Создаёт таблицы БД при старте (вне тестового режима).

    Args:
        app: Экземпляр FastAPI.

    Yields:
        None
    """
    if not os.environ.get("TESTING"):
        Base.metadata.create_all(bind=engine)
        print("Database tables created")
    yield
    print("Shutting down...")


app = FastAPI(title="Microblog API", docs_url="/docs", lifespan=lifespan)
app.include_router(tweets_router)
app.include_router(users_router)
