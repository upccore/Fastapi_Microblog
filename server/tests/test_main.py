from app.db.models import User, Tweet


def test_create_tweet(db, client):
    """Тест создания твита."""
    # Создаем тестового пользователя
    test_user = User(name="Test User", api_key="test-key-123")
    db.add(test_user)
    db.commit()
    db.refresh(test_user)

    # Тестируем создание твита
    response = client.post(
        "/tweets",
        headers={"api-key": "test-key-123"},
        json={"tweet_data": "Hello World!"},
    )

    assert response.status_code == 200
    assert response.json()["result"]
    assert "tweet_id" in response.json()


def test_get_timeline(db, client):
    """Тест получения ленты твитов."""
    test_user = User(name="Test User", api_key="test-key-123")
    db.add(test_user)
    db.commit()
    db.refresh(test_user)

    # Создаем твит
    tweet = Tweet(content="Test tweet", user_id=test_user.id)
    db.add(tweet)
    db.commit()

    response = client.get("/tweets", headers={"api-key": "test-key-123"})

    assert response.status_code == 200
    assert response.json()["result"]
    assert len(response.json()["tweets"]) > 0


def test_follow_user(db, client):
    """Тест подписки на пользователя."""
    # Создаем пользователей
    user1 = User(name="User 1", api_key="key1")
    user2 = User(name="User 2", api_key="key2")
    db.add_all([user1, user2])
    db.commit()
    db.refresh(user1)
    db.refresh(user2)

    response = client.post(
        f"/users/{user2.id}/follow", headers={"api-key": user1.api_key}
    )

    assert response.status_code == 200
    assert response.json()["result"]


def test_like_tweet(db, client):
    """Тест лайка твита."""
    user = User(name="Liker", api_key="like-key")
    db.add(user)
    db.commit()
    db.refresh(user)

    # Создаем tweet
    tweet = Tweet(content="Like me", user_id=user.id)
    db.add(tweet)
    db.commit()
    db.refresh(tweet)

    response = client.post(
        f"/tweets/{tweet.id}/likes", headers={"api-key": user.api_key}
    )

    assert response.status_code == 200
    assert response.json()["result"]


def test_delete_tweet(db, client):
    """Тест удаления своего твита."""
    # Создаем пользователя и твит
    user = User(name="Deleter", api_key="delete-key")
    db.add(user)
    db.commit()
    db.refresh(user)

    tweet = Tweet(content="To be deleted", user_id=user.id)
    db.add(tweet)
    db.commit()
    db.refresh(tweet)

    # Удаляем твит
    response = client.delete(
        f"/tweets/{tweet.id}", headers={"api-key": user.api_key}
    )

    assert response.status_code == 200
    assert response.json()["result"]


def test_get_user_profile(db, client):
    """Тест получения своего профиля."""
    user = User(name="Profile User", api_key="profile-key")
    db.add(user)
    db.commit()
    db.refresh(user)

    response = client.get("/users/me", headers={"api-key": user.api_key})

    assert response.status_code == 200
    assert response.json()["result"]
    assert "user" in response.json()
    assert response.json()["user"]["name"] == "Profile User"


def test_unfollow_user(db, client):
    """Тест отписки от пользователя."""
    user1 = User(name="User A", api_key="key_a")
    user2 = User(name="User B", api_key="key_b")
    db.add_all([user1, user2])
    db.commit()
    db.refresh(user1)
    db.refresh(user2)

    # Сначала подписываемся
    client.post(f"/users/{user2.id}/follow", headers={"api-key": user1.api_key})

    # Затем отписываемся
    response = client.delete(
        f"/users/{user2.id}/follow", headers={"api-key": user1.api_key}
    )

    assert response.status_code == 200
    assert response.json()["result"]


def test_unlike_tweet(db, client):
    """Тест снятия лайка с твита."""
    user = User(name="Unliker", api_key="unlike-key")
    db.add(user)
    db.commit()
    db.refresh(user)

    tweet = Tweet(content="To be unliked", user_id=user.id)
    db.add(tweet)
    db.commit()
    db.refresh(tweet)

    # Сначала ставим лайк
    client.post(f"/tweets/{tweet.id}/likes", headers={"api-key": user.api_key})

    # Затем удаляем лайк
    response = client.delete(
        f"/tweets/{tweet.id}/likes", headers={"api-key": user.api_key}
    )

    assert response.status_code == 200
    assert response.json()["result"]


def test_invalid_api_key(db, client):
    """Тест доступа с невалидным api-key."""
    response = client.get("/tweets", headers={"api-key": "invalid-key-12345"})

    assert response.status_code == 401

    response_json = response.json()
    assert "detail" in response_json
    assert response_json["detail"] == "Invalid API Key"


def test_tweet_not_found(db, client):
    """Тест удаления несуществующего твита."""
    user = User(name="Test User", api_key="test-key")
    db.add(user)
    db.commit()

    response = client.delete("/tweets/99999", headers={"api-key": user.api_key})

    assert response.status_code == 404
    response_json = response.json()
    assert "detail" in response_json
    assert response_json["detail"] == "Tweet not found"


def test_delete_others_tweet(db, client):
    """Тест попытки удаления чужого твита."""
    # Создаем двух пользователей
    user1 = User(name="Author", api_key="author-key")
    user2 = User(name="Hacker", api_key="hacker-key")
    db.add_all([user1, user2])
    db.commit()
    db.refresh(user1)
    db.refresh(user2)

    # user1 создает твит
    tweet = Tweet(content="Author's tweet", user_id=user1.id)
    db.add(tweet)
    db.commit()
    db.refresh(tweet)

    # user2 пытается удалить чужой твит
    response = client.delete(
        f"/tweets/{tweet.id}", headers={"api-key": user2.api_key}
    )

    assert response.status_code == 403  # Forbidden


def test_follow_self(db, client):
    """Тест попытки подписаться на самого себя."""
    user = User(name="Lonely", api_key="lonely-key")
    db.add(user)
    db.commit()
    db.refresh(user)

    response = client.post(
        f"/users/{user.id}/follow", headers={"api-key": user.api_key}
    )

    assert response.status_code == 400
    response_json = response.json()
    assert "detail" in response_json
    assert response_json["detail"] == "Cannot follow yourself"


def test_upload_media(db, client):
    """Тест загрузки изображения."""
    user = User(name="Media User", api_key="media-key")
    db.add(user)
    db.commit()
    db.refresh(user)

    # Создаем тестовый файл
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(b"fake image content")
        f.flush()

        with open(f.name, "rb") as img:
            response = client.post(
                "/tweets/medias",
                headers={"api-key": user.api_key},
                files={"file": ("test.jpg", img, "image/jpeg")},
            )

    assert response.status_code == 200
    assert response.json()["result"]
    assert "media_id" in response.json()


def test_create_tweet_with_media(db, client):
    """Тест создания твита с прикреплённым изображением."""
    user = User(name="Media Tweet User", api_key="media-tweet-key")
    db.add(user)
    db.commit()
    db.refresh(user)

    # Сначала загружаем медиа
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(b"fake image")
        f.flush()

        with open(f.name, "rb") as img:
            media_response = client.post(
                "/tweets/medias",
                headers={"api-key": user.api_key},
                files={"file": ("test.jpg", img, "image/jpeg")},
            )

    media_id = media_response.json()["media_id"]

    # Создаем твит с медиа
    response = client.post(
        "/tweets",
        headers={"api-key": user.api_key},
        json={"tweet_data": "Tweet with image!", "tweet_media_ids": [media_id]},
    )

    assert response.status_code == 200
    assert response.json()["result"]


def test_like_tweet_already_liked(db, client):
    """Тест идемпотентности лайка (повторный лайк)."""
    user = User(name="Double Liker", api_key="double-key")
    db.add(user)
    db.commit()
    db.refresh(user)

    tweet = Tweet(content="Double like", user_id=user.id)
    db.add(tweet)
    db.commit()
    db.refresh(tweet)

    # Ставим лайк первый раз
    response1 = client.post(
        f"/tweets/{tweet.id}/likes", headers={"api-key": user.api_key}
    )

    # Ставим лайк второй раз
    response2 = client.post(
        f"/tweets/{tweet.id}/likes", headers={"api-key": user.api_key}
    )

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json()["result"]
    assert response2.json()["result"]


def test_unlike_tweet_not_liked(db, client):
    """Тест идемпотентности дизлайка (снятие без лайка)."""
    user = User(name="Unlike without like", api_key="unlike-key")
    db.add(user)
    db.commit()
    db.refresh(user)

    tweet = Tweet(content="No likes", user_id=user.id)
    db.add(tweet)
    db.commit()
    db.refresh(tweet)

    response = client.delete(
        f"/tweets/{tweet.id}/likes", headers={"api-key": user.api_key}
    )

    assert response.status_code == 200
    assert response.json()["result"]


def test_follow_user_twice(db, client):
    """Тест идемпотентности подписки (повторная подписка)."""
    user1 = User(name="Follow A", api_key="follow-a")
    user2 = User(name="Follow B", api_key="follow-b")
    db.add_all([user1, user2])
    db.commit()
    db.refresh(user1)
    db.refresh(user2)

    # Подписываемся первый раз
    response1 = client.post(
        f"/users/{user2.id}/follow", headers={"api-key": user1.api_key}
    )

    # Подписываемся второй раз
    response2 = client.post(
        f"/users/{user2.id}/follow", headers={"api-key": user1.api_key}
    )

    assert response1.status_code == 200
    assert response2.status_code == 200


def test_unfollow_not_following(db, client):
    """Тест идемпотентности отписки (отписка без подписки)."""
    user1 = User(name="Not Following", api_key="not-follow")
    user2 = User(name="Target", api_key="target")
    db.add_all([user1, user2])
    db.commit()
    db.refresh(user1)
    db.refresh(user2)

    response = client.delete(
        f"/users/{user2.id}/follow", headers={"api-key": user1.api_key}
    )

    assert response.status_code == 200
    assert response.json()["result"]
