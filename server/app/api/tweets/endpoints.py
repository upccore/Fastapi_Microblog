from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import User, Tweet, Media, Like
from app.db.schemas import TweetIdResponse, TweetCreate, SimpleResponse, MediaResponse
from fastapi.responses import FileResponse
from app.dependencies import get_current_user
from app.config import MEDIA_DIR
from fastapi import File

router = APIRouter(prefix="/tweets", tags=["tweets"])


@router.post("", response_model=TweetIdResponse)
def create_tweet(
        tweet: TweetCreate,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    """
    Создание нового твита.

    Args:
        tweet: Данные твита.
        user: Автор твита.
        db: Сессия БД.

    Returns:
        dict: {"result": True, "tweet_id": int}.
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


@router.delete("/{tweet_id}", response_model=SimpleResponse)
def delete_tweet(
        tweet_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Удаление своего твита.

    Args:
        tweet_id: ID твита.
        user: Текущий пользователь.
        db: Сессия БД.

    Returns:
        dict: {"result": True}.

    Raises:
        HTTPException: 404 если твит не найден.
        HTTPException: 403 если твит чужой.
    """
    tweet = db.query(Tweet).filter(Tweet.id == tweet_id).first()
    if not tweet:
        raise HTTPException(status_code=404, detail="Tweet not found")
    if tweet.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your tweet")

    db.delete(tweet)
    db.commit()
    return {"result": True}


@router.post("/{tweet_id}/likes", response_model=SimpleResponse)
def like_tweet(
        tweet_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Лайк твита (идемпотентный).

    Args:
        tweet_id: ID твита.
        user: Текущий пользователь.
        db: Сессия БД.

    Returns:
        dict: {"result": True}.
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


@router.delete("/{tweet_id}/likes", response_model=SimpleResponse)
def unlike_tweet(
        tweet_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Снятие лайка с твита.

    Args:
        tweet_id: ID твита.
        user: Текущий пользователь.
        db: Сессия БД.

    Returns:
        dict: {"result": True}.
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


@router.get("")
def get_timeline(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Получение ленты твитов.

    Сортировка:
    1. Твиты подписок, отсортированные по убыванию лайков от подписок.
    2. Остальные твиты подписок (новые сверху).
    3. Твиты остальных пользователей (новые сверху).

    Args:
        user: Текущий пользователь.
        db: Сессия БД.

    Returns:
        dict: {"result": True, "tweets": list}.
    """
    following_ids = {f.following_id for f in user.following}
    all_tweets = db.query(Tweet).all()

    # Три группы
    liked_by_following = []  # Твиты от подписок с лайками от подписок
    other_from_following = []  # Твиты от подписок без лайков
    from_others = []  # Твиты от остальных

    for tweet in all_tweets:
        likes_from_following = sum(
            1 for like in tweet.likes if like.user_id in following_ids
        )

        if tweet.author.id in following_ids:
            if likes_from_following > 0:
                liked_by_following.append((tweet, likes_from_following))
            else:
                other_from_following.append((tweet, likes_from_following))
        else:
            from_others.append((tweet, likes_from_following))

    # ВАЖНО: сортировка по убыванию (больше лайков = выше)
    liked_by_following.sort(key=lambda x: x[1], reverse=True)

    # Остальные от подписок: новые сверху
    other_from_following.sort(key=lambda x: x[0].id, reverse=True)

    # От остальных: новые сверху
    from_others.sort(key=lambda x: x[0].id, reverse=True)

    # ПОРЯДОК ОБЪЕДИНЕНИЯ:
    # 1. Самые залайканные от подписок (liked_by_following)
    # 2. Остальные от подписок (other_from_following)
    # 3. От остальных (from_others)
    sorted_tweets = (
            [t[0] for t in liked_by_following] +  # ← ВВЕРХУ
            [t[0] for t in other_from_following] +  # ← ПОСЕРЕДИНЕ
            [t[0] for t in from_others]  # ← ВНИЗУ
    )

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
            for tweet in sorted_tweets
        ],
    }


@router.get("/{filename}")
async def get_media_file(filename: str):
    """
    Отдача медиафайла по имени.

    Args:
        filename: Имя файла в папке media.

    Returns:
        FileResponse: Файл изображения.

    Raises:
        HTTPException: 404 если файл не найден.
    """
    file_path = MEDIA_DIR / filename
    if file_path.exists():
        return FileResponse(str(file_path))
    raise HTTPException(status_code=404, detail="File not found")


@router.post("/medias", response_model=MediaResponse)
async def upload_media(
        file: UploadFile = File(...),
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
):
    """
    Загрузка изображения для последующей привязки к твиту.

    Args:
        file: Загружаемый файл (только изображения).
        user: Текущий пользователь.
        db: Сессия БД.

    Returns:
        dict: {"result": True, "media_id": int}.

    Raises:
        HTTPException: 400 если файл не изображение или без имени.
        HTTPException: 500 при ошибке сохранения.
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
