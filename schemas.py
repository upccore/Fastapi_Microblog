from typing import List, Optional

from pydantic import BaseModel


class TweetCreate(BaseModel):
    """
    Pydantic схема для создания нового твита.

    Attributes:
        tweet_data (str): Текст твита
        tweet_media_ids (Optional[List[int]]): Список ID прикреплённых изображений
    """
    tweet_data: str
    tweet_media_ids: Optional[List[int]] = []


class TweetResponse(BaseModel):
    """
    Pydantic схема ответа с данными твита.

    Attributes:
        id (int): ID твита
        content (str): Текст твита
        attachments (List[str]): Список URL ссылок на картинки
        author (dict): Информация об авторе (id, name)
        likes (List[dict]): Список лайков с информацией о пользователях
    """
    id: int
    content: str
    attachments: List[str]
    author: dict
    likes: List[dict]


class UserResponse(BaseModel):
    """
    Pydantic схема ответа с данными пользователя.

    Attributes:
        id (int): ID пользователя
        name (str): Имя пользователя
        followers (List[dict]): Список подписчиков
        following (List[dict]): Список подписок
    """
    id: int
    name: str
    followers: List[dict]
    following: List[dict]


class MediaResponse(BaseModel):
    """
    Pydantic схема ответа после загрузки изображения.

    Attributes:
        result (bool): Статус операции (True/False)
        media_id (int): ID загруженного медиафайла
    """
    result: bool
    media_id: int


class TweetIdResponse(BaseModel):
    """
    Pydantic схема ответа после создания твита.

    Attributes:
        result (bool): Статус операции (True/False)
        tweet_id (int): ID созданного твита
    """
    result: bool
    tweet_id: int


class SimpleResponse(BaseModel):
    """
    Базовая Pydantic схема ответа.

    Attributes:
        result (bool): Статус операции (True/False)
    """
    result: bool
