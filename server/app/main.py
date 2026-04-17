import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from db.database import Base, engine, get_db
from db.models import User

from server.app.api.tweets.endpoints import router as tweets_router
from server.app.api.users.endpoints import router as users_router

Base.metadata.create_all(bind=engine)

MEDIA_DIR = Path("/app/media")
MEDIA_DIR.mkdir(exist_ok=True, parents=True)


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


@app.get("/")
async def index():
    """Отдаёт главную HTML страницу (интерфейс микроблога)."""
    return FileResponse("client/static/index.html")


def get_current_user(api_key: str = Header(...), db: Session = Depends(get_db)):
    """
    Получает текущего пользователя по api-key из заголовка запроса.

    Args:
        api_key (str): API ключ из заголовка запроса
        db (Session): Сессия БД

    Returns:
        User: Объект пользователя

    Raises:
        HTTPException: 401 если api-key неверный или отсутствует
    """
    user = db.query(User).filter(User.api_key == api_key).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid api-key")
    return user
