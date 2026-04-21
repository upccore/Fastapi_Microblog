from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import User, Follow
from app.db.schemas import SimpleResponse
from app.dependencies import get_current_user
from app.config import MEDIA_DIR

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
def get_my_profile(
        user: User = Depends(get_current_user),
):
    """
    Получение профиля текущего пользователя.

    Args:
        user: Текущий пользователь.

    Returns:
        dict: Профиль с подписчиками и подписками.
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


@router.get("/{user_id}")
def get_user_profile(
        user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Получение профиля другого пользователя по ID.

    Args:
        user_id: ID целевого пользователя.
        user: Текущий пользователь.
        db: Сессия БД.

    Returns:
        dict: Профиль пользователя.

    Raises:
        HTTPException: 404 если пользователь не найден.
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


@router.post("/{user_id}/follow", response_model=SimpleResponse)
def follow_user(
        user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Подписка на пользователя.

    Args:
        user_id: ID целевого пользователя.
        user: Текущий пользователь.
        db: Сессия БД.

    Returns:
        dict: {"result": True}.

    Raises:
        HTTPException: 400 при попытке подписаться на себя.
        HTTPException: 404 если пользователь не найден.
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


@router.delete("/{user_id}/follow", response_model=SimpleResponse)
def unfollow_user(
        user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Отписка от пользователя.

    Args:
        user_id: ID целевого пользователя.
        user: Текущий пользователь.
        db: Сессия БД.

    Returns:
        dict: {"result": True}.
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
