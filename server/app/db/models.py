from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.database import Base


class User(Base):
    """
    Модель пользователя микроблога.

    Attributes:
        id (int): Уникальный идентификатор пользователя
        name (str): Имя пользователя
        api_key (str): API ключ для авторизации
        tweets (List[Tweet]): Список твитов пользователя
        likes (List[Like]): Список лайков пользователя
        following (List[Follow]): Список подписок (на кого подписан)
        followers (List[Follow]): Список подписчиков (кто подписан)
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    api_key = Column(String, unique=True, nullable=False, index=True)

    tweets = relationship("Tweet", back_populates="author")
    likes = relationship("Like", back_populates="user")
    following = relationship(
        "Follow", foreign_keys="Follow.follower_id", back_populates="follower"
    )
    followers = relationship(
        "Follow", foreign_keys="Follow.following_id", back_populates="following"
    )


class Tweet(Base):
    """
    Модель твита (сообщения).

    Attributes:
        id (int): Уникальный идентификатор твита
        content (str): Текст твита
        created_at (datetime): Дата и время создания
        user_id (int): ID автора твита
        author (User): Объект автора (связь с User)
        likes (List[Like]): Список лайков твита
        attachments (List[Media]): Список прикреплённых медиафайлов
    """

    __tablename__ = "tweets"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    user_id = Column(Integer, ForeignKey("users.id"))

    author = relationship("User", back_populates="tweets")
    likes = relationship("Like", back_populates="tweet", cascade="all, delete-orphan")
    attachments = relationship("Media", back_populates="tweet")


class Like(Base):
    """
    Модель лайка (связь пользователя и твита).

    Attributes:
        id (int): Уникальный идентификатор лайка
        user_id (int): ID пользователя который лайкнул
        tweet_id (int): ID твита который лайкнули
        user (User): Объект пользователя (связь)
        tweet (Tweet): Объект твита (связь)
    """

    __tablename__ = "likes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    tweet_id = Column(Integer, ForeignKey("tweets.id"))

    user = relationship("User", back_populates="likes")
    tweet = relationship("Tweet", back_populates="likes")


class Follow(Base):
    """
    Модель подписки (связь пользователей).

    Attributes:
        id (int): Уникальный идентификатор подписки
        follower_id (int): ID пользователя который подписывается
        following_id (int): ID пользователя на которого подписываются
        follower (User): Объект подписчика (связь)
        following (User): Объект цели подписки (связь)
    """

    __tablename__ = "follows"

    id = Column(Integer, primary_key=True)
    follower_id = Column(Integer, ForeignKey("users.id"))
    following_id = Column(Integer, ForeignKey("users.id"))

    follower = relationship(
        "User", foreign_keys=[follower_id], back_populates="following"
    )
    following = relationship(
        "User", foreign_keys=[following_id], back_populates="followers"
    )


class Media(Base):
    """
    Модель медиафайла (изображения).

    Attributes:
        id (int): Уникальный идентификатор медиа
        file_path (str): Путь к файлу на диске
        tweet_id (int|None): ID твита к которому прикреплён (может быть None)
        tweet (Tweet|None): Объект твита (связь)
    """

    __tablename__ = "media"

    id = Column(Integer, primary_key=True)
    file_path = Column(String, nullable=False)
    tweet_id = Column(Integer, ForeignKey("tweets.id"), nullable=True)

    tweet = relationship("Tweet", back_populates="attachments")
