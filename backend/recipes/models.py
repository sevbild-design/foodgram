from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from recipes.constants import (INGREDIENT_NAME_MAX_LENGTH,
                               MEASUREMENT_UNIT_MAX_LENGTH, MIN_COOKING_TIME,
                               MIN_INGREDIENT_AMOUNT, RECIPE_NAME_MAX_LENGTH,
                               SLUG_MAX_LENGTH, TAG_MAX_LENGTH)


class Tag(models.Model):
    """
    Модель тегов.

    Категория рецепта, например «Завтрак» или «Ужин».
    Название тега уникально. Сортировка по алфавиту.
    """

    name = models.CharField(
        verbose_name='Название',
        max_length=TAG_MAX_LENGTH,
        unique=True
    )
    slug = models.SlugField(
        verbose_name='Идентификатор',
        max_length=SLUG_MAX_LENGTH,
        unique=True,
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """
    Модель ингредиента.

    Продукт и единица, в которой измеряется его количество.
    Пара продукт-единица измерения уникальна.
    """

    name = models.CharField(
        verbose_name='Наименование',
        max_length=INGREDIENT_NAME_MAX_LENGTH,
    )
    measurement_unit = models.CharField(
        verbose_name='Единицы измерения',
        max_length=MEASUREMENT_UNIT_MAX_LENGTH,
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        constraints = (
            models.UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='unique_ingredient_measurement_unit',
            ),
        )

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}'


class Recipe(models.Model):
    """
    Модель рецепта.

    При удалении автора удаляются и его рецепты.
    Файл изображения сохраняется в MEDIA_ROOT/recipes/images/.
    Минимальное время приготовления задано константой MIN_COOKING_TIME.
    Ингредиенты описаны через промежуточную модель IngredientInRecipe.
    В IngredientInRecipe добавлено кол-во ингредиента.
    Время создания заполняется один раз при первой записи объекта в базу.
    """

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Автор',
    )
    name = models.CharField(
        verbose_name='Название',
        max_length=RECIPE_NAME_MAX_LENGTH,
    )
    image = models.ImageField(
        verbose_name='Изображение',
        upload_to='recipes/images/',
    )
    text = models.TextField(
        verbose_name='Рецепт приготовления',
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления (в минутах)',
        validators=(MinValueValidator(MIN_COOKING_TIME),),
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientInRecipe',
        verbose_name='Ингредиенты',
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Теги',
    )
    created_at = models.DateTimeField(
        verbose_name='Дата создания',
        auto_now_add=True,
    )

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        default_related_name = 'recipes'

    def __str__(self):
        return self.name


class IngredientInRecipe(models.Model):
    """
    Промежуточная модель с количеством ингредиента в рецепте.

    Удаление ингредиента удаляет его вхождения в состав рецептов.
    Кол-во ингредиента - целое положительное число,
    минимальное кол-во в константе MIN_INGREDIENT_AMOUNT.
    Один ингредиент нельзя дважды добавить в один рецепт.
    """

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент',
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество',
        validators=(MinValueValidator(MIN_INGREDIENT_AMOUNT),),
    )

    class Meta:
        default_related_name = 'recipe_ingredients'
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_recipe_ingredient',
            ),
        )

    def __str__(self):
        return (
            f'{self.ingredient.name} — '
            f'{self.amount} {self.ingredient.measurement_unit}'
        )


class Favorite(models.Model):
    """
    Модель избранное.

    Рецепт, добавленный пользователем в избранное.
    Пара пользователь-рецепт уникальна.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )

    class Meta:
        default_related_name = 'favorites'
        verbose_name = 'Избранное'
        verbose_name_plural = 'избранное'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_user_favorite_recipe',
            ),
        )

    def __str__(self):
        return f'{self.user}: {self.recipe.name}'


class ShoppingCart(models.Model):
    """
    Список покупок.

    Рецепт, добавленный пользователем в список покупок.
    При удалении пользователя или рецепта связанная запись тоже удаляется.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )

    class Meta:
        default_related_name = 'shopping_cart'
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_user_shopping_cart_recipe',
            ),
        )

    def __str__(self):
        return f'{self.user}: {self.recipe.name}'
