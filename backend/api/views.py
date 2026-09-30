from api.filters import IngredientFilter, RecipeFilter
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (AvatarSerializer, IngredientSerializer,
                             RecipeReadSerializer, RecipeShortSerializer,
                             RecipeWriteSerializer, TagSerializer,
                             UserWithRecipesSerializer)
from django.contrib.auth import get_user_model
from django.db.models import Count, Exists, OuterRef, Prefetch, Sum
from django.http import HttpResponse
from djoser.views import UserViewSet as DjoserUserViewSet
from recipes.models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                            ShoppingCart, Tag)
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from users.models import Subscription

User = get_user_model()


class UserViewSet(DjoserUserViewSet):
    """
    Расширяет стандартный Djoser API пользователей.

    Сохраняет встроенные возможности Djoser: регистрацию, получение профиля,
    работу с текущим пользователем и смену пароля. Дополнительно открывает
    публичное чтение списка пользователей и отдельных профилей, позволяет
    управлять аватаром, подписываться на авторов и получать список подписок.

    Методы:
    get_permissions(): Выбирает разрешения для текущего действия и делает
    список пользователей и отдельные профили общедоступными.

    avatar(request):
    PUT - устанавливает или заменяет аватар текущего пользователя,
    DELETE - удаляет его.

    subscriptions(request):
    Возвращает пагинированный список авторов, на которых подписан
    текущий пользователь, вместе с их рецептами.

    subscribe(request, *args, **kwargs):
    POST - создаёт подписку на указанного автора,
    DELETE - удаляет существующую подписку.
    """

    def get_permissions(self):

        if self.action in ('list', 'retrieve'):
            return [AllowAny()]

        return super().get_permissions()

    @action(
        detail=False,
        methods=('put', 'delete'),
        url_path='me/avatar',
        permission_classes=(IsAuthenticated,),
    )
    def avatar(self, request):
        user = request.user
        if request.method == 'PUT':
            serializer = AvatarSerializer(
                user,
                data=request.data,
                context={'request': request},
            )
            serializer.is_valid(raise_exception=True)
            old_avatar = user.avatar if user.avatar else None
            serializer.save()

            if old_avatar:
                old_avatar.delete(save=False)

            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )
        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save(update_fields=('avatar',))

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,),
    )
    def subscriptions(self, request):

        authors = (
            User.objects.filter(
                subscribers__user=request.user,
            ).annotate(
                recipes_count_value=Count(
                    'recipes',
                    distinct=True,
                )
            ).prefetch_related(
                Prefetch(
                    'recipes',
                    queryset=Recipe.objects.all(),
                    to_attr='prefetched_recipes',
                )
            ).order_by('id')
        )

        page = self.paginate_queryset(authors)

        serializer = UserWithRecipesSerializer(
            page,
            many=True,
            context=self.get_serializer_context(),
        )

        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,),
    )
    def subscribe(self, request, *args, **kwargs):
        author = self.get_object()

        if request.method == 'POST':
            if author == request.user:
                return Response(
                    {'errors': 'Нельзя подписаться на самого себя.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            _, created = Subscription.objects.get_or_create(
                user=request.user,
                author=author,
            )

            if not created:
                return Response(
                    {'errors': 'Вы уже подписаны на этого пользователя.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = UserWithRecipesSerializer(
                author,
                context=self.get_serializer_context(),
            )
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )
        deleted_count, _ = Subscription.objects.filter(
            user=request.user,
            author=author,
        ).delete()

        if deleted_count == 0:
            return Response(
                {'errors': 'Вы не подписаны на этого пользователя.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(ReadOnlyModelViewSet):
    """
    Предоставляет публичный API справочника тегов только для чтения.

    Доступ разрешён без авторизации. Пагинация отключена.
    """

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None


class IngredientViewSet(ReadOnlyModelViewSet):
    """
    Предоставляет публичный API ингредиентов только для чтения.

    Создавать, изменять и удалять ингредиенты через
    пользовательский API нельзя.
    Список доступен без авторизации и возвращается без пагинации.
    """

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)
    filterset_class = IngredientFilter
    pagination_class = None


class RecipeViewSet(ModelViewSet):
    """
    Реализует полный пользовательский API рецептов.

    Анонимным пользователям разрешено только чтение.
    Изменять или удалять рецепт может только его автор.
    RecipeFilter фильтрует выдачу по автору, тегам,
    избранному и списку покупок.

    Методы:
    get_queryset():
    Возвращает оптимизированный QuerySet и добавляет признаки избранного и
    списка покупок текущего пользователя.

    get_serializer_class():
    Выбирает сериализатор записи для создания и изменения,
    а сериализатор чтения — для остальных действий.

    perform_create(serializer):
    Передаёт текущего пользователя в качестве автора создаваемого рецепта.

    get_link(request, *args, **kwargs):
    Возвращает абсолютную ссылку на страницу выбранного рецепта.

    _manage_recipe_relation(...):
    Содержит общую логику добавления рецепта в пользовательский
    список и удаления из него.

    favorite(request, *args, **kwargs):
    Управляет связью рецепта с избранным текущего пользователя.

    shopping_cart(request, *args, **kwargs):
    Управляет связью рецепта со списком покупок текущего пользователя.

    download_shopping_cart(request):
    Суммирует одинаковые ингредиенты во всех рецептах корзины и
    возвращает результат текстовым файлом.
    """

    queryset = Recipe.objects.select_related(
        'author',
    ).prefetch_related(
        'tags',
        'recipe_ingredients__ingredient',
    )
    permission_classes = (
        IsAuthenticatedOrReadOnly,
        IsAuthorOrReadOnly,
    )
    filterset_class = RecipeFilter

    def get_queryset(self):

        queryset = super().get_queryset()
        user = self.request.user

        if not user.is_authenticated:
            return queryset

        return queryset.annotate(
            is_favorited_by_user=Exists(
                Favorite.objects.filter(
                    user=user,
                    recipe_id=OuterRef('pk'),
                )
            ),
            is_in_shopping_cart_by_user=Exists(
                ShoppingCart.objects.filter(
                    user=user,
                    recipe_id=OuterRef('pk'),
                )
            ),
        )

    def get_serializer_class(self):

        if self.action in (
            'create',
            'update',
            'partial_update',
        ):
            return RecipeWriteSerializer

        return RecipeReadSerializer

    def perform_create(self, serializer):

        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=('get',),
        url_path='get-link',
        permission_classes=(AllowAny,),
    )
    def get_link(self, request, *args, **kwargs):

        recipe = self.get_object()
        recipe_link = request.build_absolute_uri(
            f'/recipes/{recipe.id}'
        )
        return Response(
            {'short-link': recipe_link},
            status=status.HTTP_200_OK,
        )

    def _manage_recipe_relation(
        self,
        request,
        relation_model,
        already_exists_message,
        does_not_exist_message,
    ):
        recipe = self.get_object()

        if request.method == 'POST':
            _, created = relation_model.objects.get_or_create(
                user=request.user,
                recipe=recipe,
            )

            if not created:
                return Response(
                    {'errors': already_exists_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = RecipeShortSerializer(
                recipe,
                context=self.get_serializer_context(),
            )

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )
        deleted_count, _ = relation_model.objects.filter(
            user=request.user,
            recipe=recipe,
        ).delete()

        if deleted_count == 0:
            return Response(
                {'errors': does_not_exist_message},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=('post', 'delete'),
        url_path='favorite',
        permission_classes=(IsAuthenticated,),
    )
    def favorite(self, request, *args, **kwargs):

        return self._manage_recipe_relation(
            request=request,
            relation_model=Favorite,
            already_exists_message=(
                'Рецепт уже добавлен в избранное.'
            ),
            does_not_exist_message=(
                'Рецепта нет в избранном.'
            ),
        )

    @action(
        detail=True,
        methods=('post', 'delete'),
        url_path='shopping_cart',
        permission_classes=(IsAuthenticated,),
    )
    def shopping_cart(self, request, *args, **kwargs):

        return self._manage_recipe_relation(
            request=request,
            relation_model=ShoppingCart,
            already_exists_message=(
                'Рецепт уже добавлен в список покупок.'
            ),
            does_not_exist_message=(
                'Рецепта нет в списке покупок.'
            ),
        )

    @action(
        detail=False,
        methods=('get',),
        url_path='download_shopping_cart',
        permission_classes=(IsAuthenticated,),
    )
    def download_shopping_cart(self, request):
        ingredients = (
            IngredientInRecipe.objects
            .filter(
                recipe__shopping_cart__user=request.user,
            )
            .values(
                'ingredient__name',
                'ingredient__measurement_unit',
            )
            .annotate(
                total_amount=Sum('amount'),
            )
            .order_by('ingredient__name')
        )
        shopping_list = [
            'Список покупок',
            '',
        ]

        for ingredient in ingredients:
            name = ingredient['ingredient__name']
            measurement_unit = (
                ingredient['ingredient__measurement_unit']
            )
            total_amount = ingredient['total_amount']

            shopping_list.append(
                f'{name} ({measurement_unit}) — {total_amount}'
            )
        file_content = '\n'.join(shopping_list)
        response = HttpResponse(
            file_content,
            content_type='text/plain; charset=utf-8',
        )
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response
