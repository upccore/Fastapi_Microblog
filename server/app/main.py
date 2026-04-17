import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.database import Base, engine, get_db
from app.db.models import User

from app.api.tweets.endpoints import router as tweets_router
from app.api.users.endpoints import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управляет жизненным циклом приложения.

    Args:
        app (FastAPI): Экземпляр FastAPI приложения
    """
    if not os.environ.get("TESTING"):
        Base.metadata.create_all(bind=engine)
        print("Database tables created")
    yield
    print("Shutting down...")


app = FastAPI(title="Microblog API", docs_url="/docs", lifespan=lifespan)
app.include_router(tweets_router)
app.include_router(users_router)
