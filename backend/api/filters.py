from django_filters import rest_framework as filters

from recipes.models import Ingredient, Recipe, Tag

BOOLEAN_FILTER_CHOICES = (
    ('0', 'Нет'),
    ('1', 'Да'),
)


class IngredientFilter(filters.FilterSet):
    """Фильтрует ингредиенты по началу названия без учёта регистра."""

    name = filters.CharFilter(
        field_name='name',
        lookup_expr='istartswith',
    )

    class Meta:
        model = Ingredient
        fields = ('name',)


class RecipeFilter(filters.FilterSet):
    """Фильтрует рецепты по автору, тегам и спискам пользователя."""

    author = filters.NumberFilter(
        field_name='author_id',
    )
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
        distinct=True,
    )
    is_favorited = filters.ChoiceFilter(
        choices=BOOLEAN_FILTER_CHOICES,
        method='filter_is_favorited',
    )
    is_in_shopping_cart = filters.ChoiceFilter(
        choices=BOOLEAN_FILTER_CHOICES,
        method='filter_is_in_shopping_cart',
    )

    class Meta:
        model = Recipe
        fields = (
            'author',
            'tags',
            'is_favorited',
            'is_in_shopping_cart',
        )

    def _filter_by_user_relation(
        self,
        queryset,
        value,
        relation_name,
    ):
        user = getattr(self.request, 'user', None)

        if user is None or not user.is_authenticated:
            if value == '1':
                return queryset.none()
            return queryset

        lookup = {
            f'{relation_name}__user': user,
        }
        if value == '1':
            return queryset.filter(**lookup).distinct()

        return queryset.exclude(**lookup).distinct()

    def filter_is_favorited(self, queryset, name, value):
        return self._filter_by_user_relation(
            queryset,
            value,
            'favorites',
        )

    def filter_is_in_shopping_cart(self, queryset, name, value):
        return self._filter_by_user_relation(
            queryset,
            value,
            'shopping_cart',
        )
