import base64
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from recipes.models import Ingredient, IngredientInRecipe, Recipe, Tag
from tests.constants import INGREDIENT_AMOUNT


def make_png_bytes():
    """Создание PNG-изображения для тестов."""
    image_buffer = BytesIO()
    Image.new('RGB', (10, 10), color='red').save(
        image_buffer,
        format='PNG',
    )
    return image_buffer.getvalue()


PNG_BYTES = make_png_bytes()
BASE64_IMAGE = (
    'data:image/png;base64,'
    + base64.b64encode(PNG_BYTES).decode()
)


@pytest.fixture(autouse=True)
def use_temporary_media_root(settings, tmp_path):
    """Сохранение тестовых изображений во временном каталоге."""
    settings.MEDIA_ROOT = tmp_path / 'media'


@pytest.fixture
def api_client():
    """Возвращает неавторизованный DRF-клиент."""
    return APIClient()


@pytest.fixture
def user(django_user_model):
    """Создание обычного пользователя."""
    return django_user_model.objects.create_user(
        email='reader@example.com',
        username='reader',
        first_name='Иван',
        last_name='Иванов',
        password='StrongPass123',
    )


@pytest.fixture
def author(django_user_model):
    """Создание автора рецептов."""
    return django_user_model.objects.create_user(
        email='author@example.com',
        username='author',
        first_name='Анна',
        last_name='Иванова',
        password='StrongPass123',
    )


@pytest.fixture
def another_user(django_user_model):
    """Создание дополнительного пользователя."""
    return django_user_model.objects.create_user(
        email='other@example.com',
        username='other',
        first_name='Пётр',
        last_name='Петров',
        password='StrongPass123',
    )


@pytest.fixture
def auth_client(user):
    """Возвращает клиент, авторизованный через force_authenticate."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def author_client(author):
    """Возвращает клиент, авторизованный как автор рецепта."""
    client = APIClient()
    client.force_authenticate(user=author)
    return client


@pytest.fixture
def tag():
    """Создать тег."""
    return Tag.objects.create(name='Завтрак', slug='breakfast')


@pytest.fixture
def second_tag():
    """Создать второй тег."""
    return Tag.objects.create(name='Ужин', slug='dinner')


@pytest.fixture
def ingredient():
    """Создать ингредиент."""
    return Ingredient.objects.create(name='Молоко', measurement_unit='мл')


@pytest.fixture
def second_ingredient():
    """Создать второй ингредиент."""
    return Ingredient.objects.create(name='Сахар', measurement_unit='г')


@pytest.fixture
def recipe(author, tag, ingredient):
    """Создать рецепт с тегом и ингредиентом."""
    recipe = Recipe.objects.create(
        author=author,
        name='Каша',
        image=SimpleUploadedFile(
            'recipe.png',
            PNG_BYTES,
            content_type='image/png',
        ),
        text='Смешать и приготовить.',
        cooking_time=10,
    )
    recipe.tags.add(tag)
    IngredientInRecipe.objects.create(
        recipe=recipe,
        ingredient=ingredient,
        amount=INGREDIENT_AMOUNT,
    )
    return recipe


@pytest.fixture
def recipe_payload(tag, ingredient):
    """Возвращает корректные данные для записи рецепта через API."""
    return {
        'name': 'Омлет',
        'text': 'Всё смешать и пожарить.',
        'cooking_time': 7,
        'image': BASE64_IMAGE,
        'tags': [tag.id],
        'ingredients': [
            {
                'id': ingredient.id,
                'amount': 2,
            },
        ],
    }
