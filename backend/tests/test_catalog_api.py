import pytest
from rest_framework import status

pytestmark = pytest.mark.django_db


def test_tags_are_public_and_not_paginated(api_client, tag):
    """Справочник тегов доступен всем и возвращается списком."""
    response = api_client.get('/api/tags/')
    assert response.status_code == status.HTTP_200_OK, (
        'Публичный список тегов должен возвращать статус 200 OK.'
    )
    assert response.data == [
        {
            'id': tag.id,
            'name': tag.name,
            'slug': tag.slug,
        }
    ], (
        'API должен возвращать непагинированный список со всеми данными тега.'
    )


def test_tag_creation_is_not_allowed(api_client):
    """Пользовательский API не позволяет создавать теги."""
    response = api_client.post(
        '/api/tags/',
        {'name': 'Обед', 'slug': 'lunch'},
    )
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED, (
        'Создание тегов через пользовательский API должно быть запрещено.'
    )


def test_ingredients_are_public_and_not_paginated(api_client, ingredient):
    """Справочник ингредиентов доступен без авторизации."""
    response = api_client.get('/api/ingredients/')
    assert response.status_code == status.HTTP_200_OK, (
        'Публичный список ингредиентов должен возвращать статус 200 OK.'
    )
    assert response.data[0]['id'] == ingredient.id, (
        'В ответе должен присутствовать созданный ингредиент.'
    )


def test_ingredient_name_filter_uses_case_insensitive_prefix(
    api_client,
    ingredient,
    second_ingredient,
):
    """Параметр name ищет ингредиенты по началу названия."""
    response = api_client.get('/api/ingredients/?name=Мол')
    assert response.status_code == status.HTTP_200_OK, (
        'Фильтрация ингредиентов должна возвращать статус 200 OK.'
    )
    assert [item['id'] for item in response.data] == [ingredient.id], (
        'Фильтр name должен оставлять ингредиенты, название которых '
        'начинается с указанной строки.'
    )
