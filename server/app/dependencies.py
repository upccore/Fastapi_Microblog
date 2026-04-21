from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db import models
from app.db.database import get_db


async def get_current_user(
    api_key: str = Header(..., alias="api-key"), db: Session = Depends(get_db)
):
    """
    Для проверки api-key и получения текущего пользователя.

    Args:
        api_key: Ключ из заголовка api-key.
        db: Сессия БД.

    Returns:
        models.User: Объект пользователя.

    Raises:
        HTTPException: 401 если ключ не найден.
    """
    user = db.query(models.User).filter(models.User.api_key == api_key).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return user
