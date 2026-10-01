from django_filters import rest_framework as filters

from recipes.models import Ingredient, Recipe

BOOLEAN_FILTER_CHOICES = (
    ('0', 'Нет'),
    ('1', 'Да'),
)


class IngredientFilter(filters.FilterSet):
    """
    Фильтр ингредиентов.

    Фильтрует ингредиенты по началу названия без учёта регистра.
    """

    name = filters.CharFilter(
        field_name='name',
        lookup_expr='istartswith',
    )

    class Meta:
        model = Ingredient
        fields = ('name',)


class RecipeFilter(filters.FilterSet):
    """
    Фильтрует список рецептов.

    Позволяет выбрать рецепты определённого автора, отфильтровать их
    по одному или нескольким тегам, а также учитывать пользовательские
    списки: избранное и список покупок.
    Для фильтров is_favorited и is_in_shopping_cart используются
    значения 1 и 0:
    - 1 — оставить рецепты, находящиеся в списке пользователя;
    - 0 — исключить рецепты, находящиеся в списке пользователя.
    Для анонимного пользователя значение 1 возвращает пустой QuerySet.
    При значении 0 исходный QuerySet возвращается без изменений.
    distinct=True предотвращает появление одинаковых рецептов в результате
    SQL-объединения таблиц тегов, избранного или списка покупок.

    Методы:
    _filter_by_user_relation(...):
    Выполняет общую фильтрацию по связи рецепта с текущим пользователем.
    Название обратной связи получает через аргумент relation_name.

    filter_is_favorited(queryset, name, value):
    Передаёт общей функции параметр favorites и фильтрует
    рецепты по избранному.

    filter_is_in_shopping_cart(queryset, name, value):
    Передаёт общей функции параметр shopping_cart и фильтрует
    рецепты по корзине.
    """

    tags = filters.AllValuesMultipleFilter(
        field_name='tags__slug',
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
