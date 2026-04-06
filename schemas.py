from pydantic import BaseModel
from typing import List, Optional


class TweetCreate(BaseModel):
    tweet_data: str
    tweet_media_ids: Optional[List[int]] = []


class TweetResponse(BaseModel):
    id: int
    content: str
    attachments: List[str]
    author: dict
    likes: List[dict]


class UserResponse(BaseModel):
    id: int
    name: str
    followers: List[dict]
    following: List[dict]


class MediaResponse(BaseModel):
    result: bool
    media_id: int


class TweetIdResponse(BaseModel):
    result: bool
    tweet_id: int


class SimpleResponse(BaseModel):
    result: bool
