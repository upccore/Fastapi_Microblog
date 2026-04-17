from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import User, Follow
from app.db.schemas import SimpleResponse
from app.main import get_current_user, app

router = APIRouter(prefix="/users", tags=["users"])


# Перенесите сюда эндпоинты пользователей (профиль, подписки)
@router.get("/users/me")
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


@router.get("/users/{user_id}")
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

@router.post("/users/{user_id}/follow", response_model=SimpleResponse)
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

@router.delete("/users/{user_id}/follow", response_model=SimpleResponse)
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