import pytest
from django.db import IntegrityError, transaction
from recipes.models import Favorite, Ingredient, ShoppingCart
from users.models import Subscription

pytestmark = pytest.mark.django_db


def test_ingredient_name_and_unit_pair_is_unique(ingredient):
    """Одинаковую пару названия и единицы нельзя сохранить дважды."""
    with pytest.raises(IntegrityError), transaction.atomic():
        Ingredient.objects.create(
            name=ingredient.name,
            measurement_unit=ingredient.measurement_unit,
        )


@pytest.mark.parametrize('model', (Favorite, ShoppingCart))
def test_user_recipe_relation_is_unique(model, user, recipe):
    """Рецепт нельзя дважды добавить в один пользовательский список."""
    model.objects.create(user=user, recipe=recipe)
    with pytest.raises(IntegrityError), transaction.atomic():
        model.objects.create(user=user, recipe=recipe)


def test_subscription_pair_is_unique(user, author):
    """Повторная подписка ограничена на уровне базы данных."""
    Subscription.objects.create(user=user, author=author)
    with pytest.raises(IntegrityError), transaction.atomic():
        Subscription.objects.create(user=user, author=author)


def test_self_subscription_is_forbidden_by_database(user):
    """Ограничение базы данных запрещает подписку на себя."""
    with pytest.raises(IntegrityError), transaction.atomic():
        Subscription.objects.create(user=user, author=user)
