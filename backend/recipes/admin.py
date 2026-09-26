from django.contrib import admin

from recipes.models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                            ShoppingCart, Tag)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """
    Отображение тегов в админ панели.

    Поиск по полям name и slug.
    """

    list_display = (
        'name',
        'slug',
    )
    search_fields = (
        'name',
        'slug',
    )


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """
    Отображение ингредиентов в админ панели.

    Поиск по полю name.
    """

    list_display = (
        'name',
        'measurement_unit',
    )
    search_fields = (
        'name',
    )


class IngredientInRecipeInline(admin.TabularInline):
    """Позволяет редактировать состав прямо в форме рецепта."""

    model = IngredientInRecipe
    extra = 1


@admin.register(IngredientInRecipe)
class IngredientInRecipeAdmin(admin.ModelAdmin):
    """Отдельный раздел для просмотра связей рецепт–ингредиент."""

    list_display = (
        'recipe',
        'ingredient',
        'amount',
    )
    search_fields = (
        'recipe__name',
        'ingredient__name',
    )


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """
    Отображение рецептов в админ панели.

    Поиск по названию, username или email автора.
    Добавлен фильтр по тегам.
    Состав рецепта отображается внутри основной формы.
    """

    list_display = (
        'name',
        'author',
    )
    search_fields = (
        'name',
        'author__username',
        'author__email',
    )
    list_filter = (
        'tags',
    )
    readonly_fields = (
        'favorite_count',
    )
    inlines = (
        IngredientInRecipeInline,
    )
    list_select_related = (
        'author',
    )

    @admin.display(description='Добавлений в избранное')
    def favorite_count(self, obj):
        return obj.favorites.count() if obj else 0


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    """Показывает связи пользователей с избранными рецептами."""

    list_display = (
        'user',
        'recipe',
    )
    search_fields = (
        'user__username',
        'recipe__name',
    )


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    """Показывает содержимое пользовательских списков покупок."""

    list_display = (
        'user',
        'recipe',
    )
    search_fields = (
        'user__username',
        'recipe__name',
    )
