from django.contrib import admin
from django.utils.html import format_html

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
    min_num = 1
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
        'author__first_name',
        'author__last_name',
        'author__email',
    )
    list_filter = (
        'tags',
    )
    readonly_fields = (
        'favorite_count',
        'image_preview',
    )
    inlines = (
        IngredientInRecipeInline,
    )
    list_select_related = (
        'author',
    )
    fieldsets = (
        (None, {
            'fields': [
                'name',
                'author',
                ('text', 'cooking_time', 'tags')]
        }),
        ('Изображение рецепта', {
            'fields': [
                'image',
                'image_preview'
            ],
        })
    )

    @admin.display(description='Фото')
    def image_preview(self, recipe):
        return format_html(
            '<img src="{}" width="120" '
            'style="max-height: 200px; object-fit: cover; '
            'border-radius: 6px;" />',
            recipe.image.url,
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
        'user__first_name',
        'user__last_name',
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
        'user__first_name',
        'user__last_name',
        'recipe__name',
    )
