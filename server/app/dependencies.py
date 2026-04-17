from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db import models

async def get_current_user(
    api_key: str = Header(..., alias="api-key"),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.api_key == api_key).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return user