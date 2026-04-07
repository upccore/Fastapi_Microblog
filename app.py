import os
import shutil
from datetime import datetime

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Follow, Like, Media, Tweet, User
from schemas import *

os.makedirs("uploads", exist_ok=True)

# Создаем таблицы
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Microblog API", docs_url="/docs")

# Монтируем папки со статикой
app.mount("/css", StaticFiles(directory="static/css"), name="css")
app.mount("/js", StaticFiles(directory="static/js"), name="js")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/uploads/{filename}")
async def get_uploaded_file(filename: str):
    """Получить загруженный файл"""
    file_path = f"uploads/{filename}"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


def get_current_user(api_key: str = Header(...), db: Session = Depends(get_db)):
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
    """Создать новый твит"""
    new_tweet = Tweet(content=tweet.tweet_data, user_id=user.id)
    db.add(new_tweet)
    db.flush()

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
    """Удалить свой твит"""
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
    """Загрузить картинку"""
    filename = f"{datetime.now().timestamp()}_{file.filename}"
    filepath = f"uploads/{filename}"

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    media = Media(file_path=filepath)
    db.add(media)
    db.commit()

    return {"result": True, "media_id": media.id}


@app.post("/api/tweets/{tweet_id}/likes", response_model=SimpleResponse)
def like_tweet(
    tweet_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Поставить лайк"""
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
    """Убрать лайк"""
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
    """Подписаться на пользователя"""
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
    """Отписаться от пользователя"""
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
    """Получить ленту твитов, отсортированных по лайкам от подписок"""

    # Получаем ID подписок
    following_ids = {
        f.following_id for f in user.following
    }  # используем set для быстрого поиска

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
                    f"/uploads/{m.file_path.split('/')[-1]}" for m in tweet.attachments
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
    """Получить информацию о своем профиле"""

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
    """Получить информацию о профиле другого пользователя по id"""

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
