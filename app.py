import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Follow, Like, Media, Tweet, User
from schemas import MediaResponse, SimpleResponse, TweetCreate, TweetIdResponse

MEDIA_DIR = Path("media")
MEDIA_DIR.mkdir(exist_ok=True)


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


@app.get("/media/{filename}")
async def get_media_file(filename: str):
    """
    Возвращает медиа-файл по имени.
    В production запросы обрабатывает Nginx.

    Args:
        filename (str): Имя файла в папке media/

    Returns:
        FileResponse: Файл

    Raises:
        HTTPException: 404 если файл не найден
    """
    file_path = MEDIA_DIR / filename
    if file_path.exists():
        return FileResponse(str(file_path))
    raise HTTPException(status_code=404, detail="File not found")


@app.get("/")
async def index():
    """Отдаёт главную HTML страницу (интерфейс микроблога)."""
    return FileResponse("static/index.html")


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


@app.post("/api/tweets", response_model=TweetIdResponse)
def create_tweet(
        tweet: TweetCreate,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    """
    Создаёт новый твит.

    Args:
        tweet (TweetCreate): Данные твита (текст и ID медиа)
        user (User): Текущий пользователь
        db (Session): Сессия БД

    Returns:
        dict: {"result": True, "tweet_id": ID_твита}
    """
    new_tweet = Tweet(content=tweet.tweet_data, user_id=user.id)
    db.add(new_tweet)
    db.flush()

    if tweet.tweet_media_ids:
        for media_id in tweet.tweet_media_ids:
            media = db.query(Media).filter(Media.id == media_id).first()
            if media:
                media.tweet_id = new_tweet.id

    db.commit()
    return {"result": True, "tweet_id": new_tweet.id}


@app.delete("/api/tweets/{tweet_id}", response_model=SimpleResponse)
def delete_tweet(
        tweet_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Удаляет твит текущего пользователя.

    Args:
        tweet_id (int): ID твита для удаления
        user (User): Текущий пользователь
        db (Session): Сессия БД

    Returns:
        dict: {"result": True}

    Raises:
        HTTPException: 404 если твит не найден
        HTTPException: 403 если попытка удалить чужой твит
    """
    tweet = db.query(Tweet).filter(Tweet.id == tweet_id).first()
    if not tweet:
        raise HTTPException(status_code=404, detail="Tweet not found")
    if tweet.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your tweet")

    db.delete(tweet)
    db.commit()
    return {"result": True}


@app.post("/api/medias", response_model=MediaResponse)
async def upload_media(
        file: UploadFile = File(...),
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    """
    Загружает изображение на сервер и сохраняет запись в БД.

    Args:
        file (UploadFile): Загружаемый файл (только изображения)
        user (User): Текущий пользователь
        db (Session): Сессия БД

    Returns:
        dict: {"result": True, "media_id": ID_медиа}

    Raises:
        HTTPException: 400 если файл не изображение или нет имени
        HTTPException: 500 если ошибка сохранения файла
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only images are allowed")

    if not file.filename:
        raise HTTPException(status_code=400, detail="File has no filename")

    # Безопасное имя файла
    original_filename = file.filename.replace(" ", "_")
    timestamp = datetime.now().timestamp()
    filename = f"{timestamp}_{original_filename}"
    filepath = MEDIA_DIR / filename

    # Сохранение файла
    try:
        with open(filepath, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Сохранение в БД
    media = Media(file_path=str(filepath))
    db.add(media)
    db.commit()
    db.refresh(media)

    return {"result": True, "media_id": media.id}


@app.post("/api/tweets/{tweet_id}/likes", response_model=SimpleResponse)
def like_tweet(
        tweet_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Ставит лайк твиту.

    Args:
        tweet_id (int): ID твита
        user (User): Текущий пользователь
        db (Session): Сессия БД

    Returns:
        dict: {"result": True}
    """
    existing = (
        db.query(Like)
        .filter(Like.user_id == user.id, Like.tweet_id == tweet_id)
        .first()
    )

    if not existing:
        like = Like(user_id=user.id, tweet_id=tweet_id)
        db.add(like)
        db.commit()

    return {"result": True}


@app.delete("/api/tweets/{tweet_id}/likes", response_model=SimpleResponse)
def unlike_tweet(
        tweet_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Убирает лайк с твита.

    Args:
        tweet_id (int): ID твита
        user (User): Текущий пользователь
        db (Session): Сессия БД

    Returns:
        dict: {"result": True}
    """
    like = (
        db.query(Like)
        .filter(Like.user_id == user.id, Like.tweet_id == tweet_id)
        .first()
    )

    if like:
        db.delete(like)
        db.commit()

    return {"result": True}


@app.post("/api/users/{user_id}/follow", response_model=SimpleResponse)
def follow_user(
        user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Подписывается на пользователя.

    Args:
        user_id (int): ID пользователя на которого подписаться
        user (User): Текущий пользователь
        db (Session): Сессия БД

    Returns:
        dict: {"result": True}

    Raises:
        HTTPException: 400 если попытка подписаться на себя
        HTTPException: 404 если пользователь не найден
    """
    if user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    existing = (
        db.query(Follow)
        .filter(Follow.follower_id == user.id, Follow.following_id == user_id)
        .first()
    )

    if not existing:
        follow = Follow(follower_id=user.id, following_id=user_id)
        db.add(follow)
        db.commit()

    return {"result": True}


@app.delete("/api/users/{user_id}/follow", response_model=SimpleResponse)
def unfollow_user(
        user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Отписывается от пользователя.

    Args:
        user_id (int): ID пользователя от которого отписаться
        user (User): Текущий пользователь
        db (Session): Сессия БД

    Returns:
        dict: {"result": True}
    """
    follow = (
        db.query(Follow)
        .filter(Follow.follower_id == user.id, Follow.following_id == user_id)
        .first()
    )

    if follow:
        db.delete(follow)
        db.commit()

    return {"result": True}


@app.get("/api/tweets")
def get_timeline(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Получает ленту твитов, отсортированных по лайкам от подписок.

    Args:
        user (User): Текущий пользователь
        db (Session): Сессия БД

    Returns:
        dict: {"result": True, "tweets": list}
    """

    # Получаем ID подписок
    following_ids = {f.following_id for f in user.following}

    # Получаем все твиты
    all_tweets = db.query(Tweet).all()

    # Сортируем
    all_tweets.sort(
        key=lambda tweet: sum(
            1 for like in tweet.likes if like.user_id in following_ids
        ),
        reverse=True,
    )

    # Формируем результат
    return {
        "result": True,
        "tweets": [
            {
                "id": tweet.id,
                "content": tweet.content,
                "attachments": [
                    f"/media/{Path(m.file_path).name}" for m in tweet.attachments
                ],
                "author": {"id": tweet.author.id, "name": tweet.author.name},
                "likes": [
                    {"user_id": like.user.id, "name": like.user.name}
                    for like in tweet.likes
                ],
            }
            for tweet in all_tweets
        ],
    }


@app.get("/api/users/me")
def get_my_profile(
        user: User = Depends(get_current_user),
):
    """
    Получает информацию о своём профиле (подписчики, подписки).

    Args:
        user (User): Текущий пользователь

    Returns:
        dict: {"result": True, "user": dict}
    """

    followers = [{"id": f.follower.id, "name": f.follower.name} for f in user.followers]

    following = [
        {"id": f.following.id, "name": f.following.name} for f in user.following
    ]

    return {
        "result": True,
        "user": {
            "id": user.id,
            "name": user.name,
            "followers": followers,
            "following": following,
        },
    }


@app.get("/api/users/{user_id}")
def get_user_profile(
        user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Получает информацию о профиле другого пользователя по ID.

    Args:
        user_id (int): ID пользователя
        user (User): Текущий пользователь
        db (Session): Сессия БД

    Returns:
        dict: {"result": True, "user": dict}

    Raises:
        HTTPException: 404 если пользователь не найден
    """

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    followers = [
        {"id": f.follower.id, "name": f.follower.name} for f in target_user.followers
    ]

    following = [
        {"id": f.following.id, "name": f.following.name} for f in target_user.following
    ]

    return {
        "result": True,
        "user": {
            "id": target_user.id,
            "name": target_user.name,
            "followers": followers,
            "following": following,
        },
    }
