import pytest
from rest_framework import status

from tests.conftest import BASE64_IMAGE
from users.models import Subscription

pytestmark = pytest.mark.django_db


def test_user_registration(api_client, django_user_model):
    """Новый пользователь может зарегистрироваться без авторизации."""
    payload = {
        'email': 'new@example.com',
        'username': 'new_user',
        'first_name': 'Новый',
        'last_name': 'Пользователь',
        'password': 'StrongPass123',
    }
    response = api_client.post('/api/users/', payload)
    assert response.status_code == status.HTTP_201_CREATED, (
        'Корректная регистрация пользователя должна вернуть статус 201 '
        'Created.'
    )
    assert django_user_model.objects.filter(email=payload['email']).exists(), (
        'После регистрации пользователь должен быть сохранён в базе данных.'
    )
    assert 'password' not in response.data, (
        'Пароль не должен возвращаться в ответе API.'
    )


def test_public_user_list(api_client, user):
    """Список пользователей доступен без токена."""
    response = api_client.get('/api/users/')
    assert response.status_code == status.HTTP_200_OK, (
        'Публичный список пользователей должен возвращать статус 200 OK.'
    )
    assert response.data['results'][0]['id'] == user.id, (
        'В списке пользователей должен присутствовать созданный пользователь.'
    )


def test_current_user_requires_authentication(api_client):
    """Профиль текущего пользователя закрыт для анонимов."""
    response = api_client.get('/api/users/me/')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED, (
        'Профиль текущего пользователя должен быть закрыт для анонимов.'
    )


def test_current_user_profile(auth_client, user):
    """Авторизованный пользователь получает собственный профиль."""
    response = auth_client.get('/api/users/me/')
    assert response.status_code == status.HTTP_200_OK, (
        'Авторизованный пользователь должен получить собственный профиль.'
    )
    assert response.data['email'] == user.email, (
        'В профиле должен возвращаться email текущего пользователя.'
    )
    assert response.data['is_subscribed'] is False, (
        'Пользователь не должен считаться подписанным на самого себя.'
    )


def test_token_login(api_client, user):
    """Djoser выдаёт токен по email и паролю."""
    response = api_client.post(
        '/api/auth/token/login/',
        {
            'email': user.email,
            'password': 'StrongPass123',
        },
    )
    assert response.status_code == status.HTTP_200_OK, (
        'Корректные учётные данные должны возвращать статус 200 OK.'
    )
    assert response.data.get('auth_token'), (
        'После успешной авторизации API должен вернуть токен.'
    )


def test_avatar_can_be_set_and_deleted(auth_client, user):
    """Текущий пользователь может установить и удалить аватар."""
    put_response = auth_client.put(
        '/api/users/me/avatar/',
        {'avatar': BASE64_IMAGE},
        format='json',
    )
    assert put_response.status_code == status.HTTP_200_OK, (
        'Установка корректного аватара должна вернуть статус 200 OK.'
    )
    user.refresh_from_db()
    assert user.avatar, (
        'После PUT-запроса путь к аватару должен сохраниться у пользователя.'
    )
    delete_response = auth_client.delete('/api/users/me/avatar/')
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT, (
        'Удаление аватара должно вернуть статус 204 No Content.'
    )
    user.refresh_from_db()
    assert not user.avatar, (
        'После DELETE-запроса поле avatar должно быть очищено.'
    )


def test_subscribe_and_unsubscribe(auth_client, user, author):
    """Пользователь может создать и удалить подписку."""
    url = f'/api/users/{author.id}/subscribe/'
    post_response = auth_client.post(url)
    assert post_response.status_code == status.HTTP_201_CREATED, (
        'Создание подписки должно вернуть статус 201 Created.'
    )
    assert Subscription.objects.filter(user=user, author=author).exists(), (
        'После POST-запроса подписка должна быть сохранена в базе данных.'
    )
    assert post_response.data['is_subscribed'] is True, (
        'После создания подписки поле is_subscribed должно быть True.'
    )
    duplicate_response = auth_client.post(url)
    assert duplicate_response.status_code == status.HTTP_400_BAD_REQUEST, (
        'Повторная подписка на того же автора должна быть отклонена.'
    )
    delete_response = auth_client.delete(url)
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT, (
        'Удаление существующей подписки должно вернуть статус 204 No Content.'
    )
    assert (
        not Subscription.objects.filter(user=user, author=author).exists()
    ), (
        'После DELETE-запроса подписка должна быть удалена из базы данных.'
    )


def test_user_cannot_subscribe_to_self(auth_client, user):
    """API отклоняет попытку подписаться на себя."""
    response = auth_client.post(f'/api/users/{user.id}/subscribe/')
    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        'Пользователь не должен иметь возможность подписаться на себя.'
    )


def test_subscriptions_respect_recipes_limit(
    auth_client,
    user,
    author,
    recipe,
):
    """Список подписок поддерживает параметр recipes_limit."""
    Subscription.objects.create(user=user, author=author)
    response = auth_client.get('/api/users/subscriptions/?recipes_limit=0')
    assert response.status_code == status.HTTP_200_OK, (
        'Получение списка подписок должно вернуть статус 200 OK.'
    )
    assert response.data['count'] == 1, (
        'В списке подписок должен присутствовать один автор.'
    )
    assert response.data['results'][0]['recipes'] == [], (
        'Параметр recipes_limit=0 должен вернуть пустой список рецептов.'
    )
    assert response.data['results'][0]['recipes_count'] == 1, (
        'Поле recipes_count должно содержать общее число рецептов автора.'
    )
