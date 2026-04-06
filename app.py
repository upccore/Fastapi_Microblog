from fastapi import FastAPI, Depends, HTTPException, Header, File, UploadFile, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import shutil
from datetime import datetime

from database import engine, get_db, Base
from models import User, Tweet, Like, Follow, Media
from schemas import *

# Создаем таблицы
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Microblog API", docs_url="/docs")

# Монтируем папки со статикой
app.mount("/css", StaticFiles(directory="static/css"), name="css")
app.mount("/js", StaticFiles(directory="static/js"), name="js")
app.mount("/static", StaticFiles(directory="static"), name="static")


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
        db: Session = Depends(get_db)
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
        tweet_id: int,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
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
        db: Session = Depends(get_db)
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
        tweet_id: int,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Поставить лайк"""
    existing = db.query(Like).filter(
        Like.user_id == user.id,
        Like.tweet_id == tweet_id
    ).first()

    if not existing:
        like = Like(user_id=user.id, tweet_id=tweet_id)
        db.add(like)
        db.commit()

    return {"result": True}


@app.delete("/api/tweets/{tweet_id}/likes", response_model=SimpleResponse)
def unlike_tweet(
        tweet_id: int,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Убрать лайк"""
    like = db.query(Like).filter(
        Like.user_id == user.id,
        Like.tweet_id == tweet_id
    ).first()

    if like:
        db.delete(like)
        db.commit()

    return {"result": True}


@app.post("/api/users/{user_id}/follow", response_model=SimpleResponse)
def follow_user(
        user_id: int,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Подписаться на пользователя"""
    if user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(Follow).filter(
        Follow.follower_id == user.id,
        Follow.following_id == user_id
    ).first()

    if not existing:
        follow = Follow(follower_id=user.id, following_id=user_id)
        db.add(follow)
        db.commit()

    return {"result": True}


@app.delete("/api/users/{user_id}/follow", response_model=SimpleResponse)
def unfollow_user(
        user_id: int,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Отписаться от пользователя"""
    follow = db.query(Follow).filter(
        Follow.follower_id == user.id,
        Follow.following_id == user_id
    ).first()

    if follow:
        db.delete(follow)
        db.commit()

    return {"result": True}


@app.get("/api/tweets")
def get_timeline(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """Получить ленту твитов"""
    following_ids = [f.following_id for f in db.query(Follow).filter(Follow.follower_id == user.id).all()]
    following_ids.append(user.id)

    tweets = db.query(Tweet).filter(Tweet.user_id.in_(following_ids)).all()

    tweets_with_likes = []
    for tweet in tweets:
        likes_count = db.query(Like).filter(Like.tweet_id == tweet.id).count()
        tweets_with_likes.append((tweet, likes_count))

    tweets_with_likes.sort(key=lambda x: x[1], reverse=True)

    result = []
    for tweet, _ in tweets_with_likes:
        author = db.query(User).filter(User.id == tweet.user_id).first()
        likes = db.query(Like).filter(Like.tweet_id == tweet.id).all()
        attachments = db.query(Media).filter(Media.tweet_id == tweet.id).all()

        result.append({
            "id": tweet.id,
            "content": tweet.content,
            "attachments": [f"/uploads/{m.file_path.split('/')[-1]}" for m in attachments],
            "author": {
                "id": author.id,
                "name": author.name
            },
            "likes": [
                {
                    "user_id": like.user_id,
                    "name": db.query(User).filter(User.id == like.user_id).first().name
                }
                for like in likes
            ]
        })

    return {"result": True, "tweets": result}


@app.get("/api/users/me")
def get_my_profile(
        request: Request,
        api_key: str = Header(None),
        db: Session = Depends(get_db)
):
    """Получить свой профиль (работает без api-key для теста)"""

    # Логируем все заголовки чтобы увидеть что приходит
    print("=== HEADERS RECEIVED ===")
    for key, value in request.headers.items():
        print(f"  {key}: {value}")
    print("========================")

    # Если api-key не передан, берем первого пользователя
    if not api_key:
        user = db.query(User).first()
        if not user:
            # Создаем тестового пользователя если нет ни одного
            user = User(name="Test", api_key="test123")
            db.add(user)
            db.commit()
        print(f"Using default user: {user.name}")
    else:
        user = db.query(User).filter(User.api_key == api_key).first()
        print(f"Looking for api_key '{api_key}', found: {user.name if user else 'Not found'}")

    if not user:
        raise HTTPException(status_code=401, detail="Invalid api-key")

    followers = [
        {
            "id": f.follower_id,
            "name": db.query(User).filter(User.id == f.follower_id).first().name
        }
        for f in db.query(Follow).filter(Follow.following_id == user.id).all()
    ]

    following = [
        {
            "id": f.following_id,
            "name": db.query(User).filter(User.id == f.following_id).first().name
        }
        for f in db.query(Follow).filter(Follow.follower_id == user.id).all()
    ]

    return {
        "result": True,
        "user": {
            "id": user.id,
            "name": user.name,
            "followers": followers,
            "following": following
        }
    }
