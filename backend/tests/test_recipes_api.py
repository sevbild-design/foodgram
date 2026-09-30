import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status

from recipes.models import Favorite, IngredientInRecipe, Recipe, ShoppingCart
from tests.conftest import PNG_BYTES
from tests.constants import (INGREDIENT_AMOUNT, NEW_INGREDIENT_AMOUNT,
                             NEW_RECIPE_NAME)

pytestmark = pytest.mark.django_db


def create_recipe(author, tag, ingredient, name='Суп', amount=100):
    """Создать дополнительный рецепт для конкретного теста."""
    recipe = Recipe.objects.create(
        author=author,
        name=name,
        image=SimpleUploadedFile(
            f'{name}.png',
            PNG_BYTES,
            content_type='image/png',
        ),
        text='Приготовить.',
        cooking_time=15,
    )
    recipe.tags.add(tag)
    IngredientInRecipe.objects.create(
        recipe=recipe,
        ingredient=ingredient,
        amount=amount,
    )
    return recipe


def test_recipe_list_is_public(api_client, recipe):
    """Аноним получает список рецептов с пользовательскими флагами."""
    response = api_client.get('/api/recipes/')
    assert response.status_code == status.HTTP_200_OK, (
        'Публичный список рецептов должен возвращать статус 200 OK.'
    )
    item = response.data['results'][0]
    assert item['id'] == recipe.id, (
        'В выдаче должен присутствовать созданный рецепт.'
    )
    assert item['is_favorited'] is False, (
        'Для анонимного пользователя рецепт не должен быть отмечен как '
        'избранный.'
    )
    assert item['is_in_shopping_cart'] is False, (
        'Для анонимного пользователя рецепт не должен находиться в списке '
        'покупок.'
    )
    assert item['ingredients'][0]['amount'] == INGREDIENT_AMOUNT, (
        'В ответе должно возвращаться правильное количество ингредиента.'
    )


def test_anonymous_user_cannot_create_recipe(api_client, recipe_payload):
    """Для создания рецепта требуется токен."""
    response = api_client.post(
        '/api/recipes/',
        recipe_payload,
        format='json',
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED, (
        'Анонимный пользователь не должен иметь возможность создать рецепт.'
    )


def test_authenticated_user_can_create_recipe(
    auth_client,
    user,
    recipe_payload,
    ingredient,
    tag,
):
    """Корректный запрос создаёт рецепт и промежуточные связи."""
    response = auth_client.post(
        '/api/recipes/',
        recipe_payload,
        format='json',
    )
    assert response.status_code == status.HTTP_201_CREATED, (
        'Корректный запрос авторизованного пользователя должен создать '
        'рецепт.'
    )
    recipe = Recipe.objects.get(id=response.data['id'])
    assert recipe.author == user, (
        'Автором созданного рецепта должен быть текущий пользователь.'
    )
    assert list(recipe.tags.all()) == [tag], (
        'К созданному рецепту должен быть привязан переданный тег.'
    )
    relation = recipe.recipe_ingredients.get(ingredient=ingredient)
    assert relation.amount == 2, (
        'В промежуточной модели должно сохраниться переданное количество '
        'ингредиента.'
    )


@pytest.mark.parametrize('field', ('tags', 'ingredients'))
def test_recipe_requires_tags_and_ingredients(
    auth_client,
    recipe_payload,
    field,
):
    """Теги и ингредиенты обязательны при создании рецепта."""
    recipe_payload.pop(field)
    response = auth_client.post(
        '/api/recipes/',
        recipe_payload,
        format='json',
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        'Рецепт без обязательного поля должен возвращать статус 400 Bad '
        'Request.'
    )
    assert field in response.data, (
        'Ответ должен содержать ошибку отсутствующего обязательного поля.'
    )


def test_duplicate_tags_are_rejected(auth_client, recipe_payload, tag):
    """Один тег нельзя дважды указать в одном рецепте."""
    recipe_payload['tags'] = [tag.id, tag.id]
    response = auth_client.post(
        '/api/recipes/',
        recipe_payload,
        format='json',
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        'Повторяющиеся теги должны вызывать ошибку 400 Bad Request.'
    )
    assert 'tags' in response.data, (
        'Ошибка повторяющихся тегов должна относиться к полю tags.'
    )


def test_duplicate_ingredients_are_rejected(
    auth_client,
    recipe_payload,
    ingredient,
):
    """Один ингредиент нельзя дважды указать в одном рецепте."""
    recipe_payload['ingredients'] = [
        {'id': ingredient.id, 'amount': 1},
        {'id': ingredient.id, 'amount': 2},
    ]
    response = auth_client.post(
        '/api/recipes/',
        recipe_payload,
        format='json',
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        'Повторяющиеся ингредиенты должны вызывать ошибку 400 Bad Request.'
    )
    assert 'ingredients' in response.data, (
        'Ошибка повторяющихся ингредиентов должна относиться к полю '
        'ingredients.'
    )


def test_only_author_can_update_recipe(auth_client, recipe, recipe_payload):
    """Чужой рецепт нельзя изменять."""
    response = auth_client.patch(
        f'/api/recipes/{recipe.id}/',
        recipe_payload,
        format='json',
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN, (
        'Пользователь не должен иметь возможность изменить чужой рецепт.'
    )


def test_author_can_update_recipe(
    author_client,
    recipe,
    recipe_payload,
    ingredient,
):
    """Автор может заменить данные и состав рецепта."""
    recipe_payload['name'] = NEW_RECIPE_NAME
    recipe_payload['ingredients'] = [
        {'id': ingredient.id, 'amount': NEW_INGREDIENT_AMOUNT},
    ]
    response = author_client.patch(
        f'/api/recipes/{recipe.id}/',
        recipe_payload,
        format='json',
    )
    assert response.status_code == status.HTTP_200_OK, (
        'Автор должен иметь возможность обновить собственный рецепт.'
    )
    recipe.refresh_from_db()
    assert recipe.name == NEW_RECIPE_NAME, (
        'После обновления должно сохраниться новое название рецепта.'
    )
    assert recipe.recipe_ingredients.get().amount == NEW_INGREDIENT_AMOUNT, (
        'После обновления должно сохраниться новое количество ингредиента.'
    )


@pytest.mark.parametrize(
    ('path', 'model'),
    (
        ('favorite', Favorite),
        ('shopping_cart', ShoppingCart),
    ),
)
def test_add_and_remove_recipe_from_user_list(
    auth_client,
    user,
    recipe,
    path,
    model,
):
    """Избранное и корзина поддерживают POST и DELETE."""
    url = f'/api/recipes/{recipe.id}/{path}/'
    post_response = auth_client.post(url)
    assert post_response.status_code == status.HTTP_201_CREATED, (
        'Добавление рецепта в пользовательский список должно вернуть статус '
        '201 Created.'
    )
    assert model.objects.filter(user=user, recipe=recipe).exists(), (
        'После POST-запроса связь пользователя с рецептом должна быть '
        'создана.'
    )
    assert auth_client.post(url).status_code == status.HTTP_400_BAD_REQUEST, (
        'Повторное добавление рецепта в тот же список должно быть отклонено.'
    )
    delete_response = auth_client.delete(url)
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT, (
        'Удаление рецепта из пользовательского списка должно вернуть статус '
        '204 No Content.'
    )
    assert not model.objects.filter(user=user, recipe=recipe).exists()
    assert (
        auth_client.delete(url).status_code == status.HTTP_400_BAD_REQUEST
    ), (
        'Удаление отсутствующей связи должно возвращать статус 400 Bad '
        'Request.'
    )


def test_recipe_filters_by_author_and_tag(
    api_client,
    author,
    recipe,
    tag,
):
    """Выдачу можно фильтровать по автору и slug тега."""
    response = api_client.get(
        f'/api/recipes/?author={author.id}&tags={tag.slug}'
    )
    assert response.status_code == status.HTTP_200_OK, (
        'Фильтрация рецептов по автору и тегу должна вернуть статус 200 OK.'
    )
    assert [item['id'] for item in response.data['results']] == [recipe.id], (
        'Фильтры author и tags должны оставить только подходящий рецепт.'
    )


def test_recipe_filters_by_favorite(auth_client, user, recipe):
    """Фильтр is_favorited учитывает текущего пользователя."""
    Favorite.objects.create(user=user, recipe=recipe)
    response = auth_client.get('/api/recipes/?is_favorited=1')
    assert response.status_code == status.HTTP_200_OK, (
        'Фильтрация рецептов по избранному должна вернуть статус 200 OK.'
    )
    assert [item['id'] for item in response.data['results']] == [recipe.id], (
        'Фильтр is_favorited должен оставить только избранный рецепт '
        'пользователя.'
    )
    assert response.data['results'][0]['is_favorited'] is True, (
        'Избранный рецепт должен возвращаться с признаком is_favorited=true.'
    )


def test_get_recipe_link(api_client, recipe):
    """Специальный endpoint возвращает ссылку на страницу рецепта."""
    response = api_client.get(f'/api/recipes/{recipe.id}/get-link/')
    assert response.status_code == status.HTTP_200_OK, (
        'Получение ссылки на рецепт должно вернуть статус 200 OK.'
    )
    assert response.data['short-link'].endswith(f'/recipes/{recipe.id}'), (
        'Ссылка должна вести на страницу выбранного рецепта.'
    )


def test_download_shopping_cart_sums_ingredients(
    auth_client,
    user,
    author,
    recipe,
    tag,
    ingredient,
):
    """Список покупок суммирует одинаковые ингредиенты рецептов."""
    second_recipe = create_recipe(
        author,
        tag,
        ingredient,
        name='Второй рецепт',
        amount=NEW_INGREDIENT_AMOUNT,
    )
    ShoppingCart.objects.create(user=user, recipe=recipe)
    ShoppingCart.objects.create(user=user, recipe=second_recipe)
    response = auth_client.get('/api/recipes/download_shopping_cart/')
    assert response.status_code == status.HTTP_200_OK
    assert response['Content-Type'].startswith('text/plain')
    assert (
        'Молоко (мл) — '
        f'{INGREDIENT_AMOUNT + NEW_INGREDIENT_AMOUNT}'
    ) in response.content.decode(), (
        'Количество одинакового ингредиента из разных рецептов должно '
        'суммироваться.'
    )
