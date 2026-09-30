from api.fields import Base64ImageField
from django.contrib.auth import get_user_model
from django.db import transaction
from djoser.serializers import \
    UserCreateSerializer as DjoserUserCreateSerializer
from djoser.serializers import UserSerializer as DjoserUserSerializer
from recipes.constants import MIN_COOKING_TIME, MIN_INGREDIENT_AMOUNT
from recipes.models import Ingredient, IngredientInRecipe, Recipe, Tag
from rest_framework import serializers

User = get_user_model()


class UserCreateSerializer(DjoserUserCreateSerializer):
    """Сериализатор регистрации пользователя."""

    class Meta(DjoserUserCreateSerializer.Meta):
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password',
        )


class UserSerializer(DjoserUserSerializer):
    """
    Сериализатор отображения пользователя.

    Метод get_is_subscribed подписку на автора
    без повторных запросов к базе.
    При первом вызове получает одним запросом идентификаторы всех
    авторов подписок и сохраняет их в контексте сериализатора.
    Последующие вызовы используют кеш, предотвращая N+1-запросы.
    Для анонимного пользователя возвращает False.
    """

    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(read_only=True)

    class Meta(DjoserUserSerializer.Meta):
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        )

    def get_is_subscribed(self, author):

        request = self.context.get('request')

        if request is None or not request.user.is_authenticated:
            return False

        cache_key = '_subscribed_author_ids'
        subscribed_author_ids = self.context.get(cache_key)

        if subscribed_author_ids is None:
            subscribed_author_ids = set(
                request.user.subscriptions.values_list(
                    'author_id',
                    flat=True,
                )
            )
            self.context[cache_key] = subscribed_author_ids

        return author.id in subscribed_author_ids


class AvatarSerializer(serializers.ModelSerializer):
    """Проверяет и сохраняет аватар текущего пользователя."""

    avatar = Base64ImageField(
        required=True,
        allow_null=False,
    )

    class Meta:
        model = User
        fields = ('avatar',)


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор модели Tag."""

    class Meta:
        model = Tag
        fields = (
            'id',
            'name',
            'slug',
        )


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор модели Ingredient."""

    class Meta:
        model = Ingredient
        fields = (
            'id',
            'name',
            'measurement_unit',
        )


class RecipeShortSerializer(serializers.ModelSerializer):
    """Краткое представление рецепта."""

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time',
        )


class UserWithRecipesSerializer(UserSerializer):
    """
    Расширяет профиль автора списком и количеством его рецептов.

    Расширяет UserSerializer полями recipes и recipes_count. Поле recipes
    поддерживает ограничение количества объектов через query-параметр
    recipes_limit.
    При наличии предзагруженных и аннотированных данных сериализатор
    использует их без дополнительных запросов к базе. Запасные запросы
    выполняются при сериализации отдельного автора, например после
    создания подписки.
    Методы:
    get_recipes: Формирует краткий список рецептов автора.
    get_recipes_count: Возвращает общее количество рецептов автора.
    """

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + (
            'recipes',
            'recipes_count',
        )

    def get_recipes(self, author):

        recipes = getattr(
            author,
            'prefetched_recipes',
            None,
        )
        if recipes is None:
            recipes = author.recipes.all()
        request = self.context.get('request')

        if request is not None:
            recipes_limit = request.query_params.get('recipes_limit')
            if recipes_limit is not None:
                try:
                    recipes_limit = int(recipes_limit)
                except ValueError as error:
                    raise serializers.ValidationError(
                        'Параметр recipes_limit должен быть целым числом.'
                    ) from error
                if recipes_limit < 0:
                    raise serializers.ValidationError(
                        'Параметр recipes_limit не может быть отрицательным.'
                    )
                recipes = recipes[:recipes_limit]
        return RecipeShortSerializer(
            recipes,
            many=True,
            context=self.context,
        ).data

    def get_recipes_count(self, author):

        if hasattr(author, 'recipes_count_value'):
            return author.recipes_count_value

        return author.recipes.count()


class IngredientInRecipeReadSerializer(serializers.ModelSerializer):
    """Формирует полное представление ингредиента внутри рецепта."""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientInRecipe

        fields = (
            'id',
            'name',
            'measurement_unit',
            'amount',
        )


class IngredientInRecipeWriteSerializer(serializers.Serializer):
    """Проверяет ингредиент, переданный при создании рецепта."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient',
    )
    amount = serializers.IntegerField(
        min_value=MIN_INGREDIENT_AMOUNT,
    )


class RecipeReadSerializer(serializers.ModelSerializer):
    """
    Формирует полное представление рецепта.

    Методы:
    _is_in_user_list:
    Выполняет общую проверку нахождения рецепта в пользовательском
    списке. Сначала использует указанную аннотацию, а при её
    отсутствии проверяет связь через менеджер модели.
    get_is_favorited:
    Передаёт общей проверке аннотацию is_favorited_by_user
    и обратную связь favorites для определения наличия рецепта
    в избранном.
    get_is_in_shopping_cart:
    Передаёт общей проверке аннотацию
    is_in_shopping_cart_by_user и обратную связь shopping_cart
    для определения наличия рецепта в списке покупок.
    """

    tags = TagSerializer(
        many=True,
        read_only=True,
    )
    author = UserSerializer(
        read_only=True,
    )
    ingredients = IngredientInRecipeReadSerializer(
        source='recipe_ingredients',
        many=True,
        read_only=True,
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def _is_in_user_list(
        self,
        recipe,
        annotation_name,
        relation_name,
    ):

        request = self.context.get('request')
        if request is None or not request.user.is_authenticated:
            return False

        if hasattr(recipe, annotation_name):
            return getattr(recipe, annotation_name)

        relation_manager = getattr(recipe, relation_name)

        return relation_manager.filter(
            user=request.user,
        ).exists()

    def get_is_favorited(self, recipe):

        return self._is_in_user_list(
            recipe=recipe,
            annotation_name='is_favorited_by_user',
            relation_name='favorites',
        )

    def get_is_in_shopping_cart(self, recipe):

        return self._is_in_user_list(
            recipe=recipe,
            annotation_name='is_in_shopping_cart_by_user',
            relation_name='shopping_cart',
        )


class RecipeWriteSerializer(serializers.ModelSerializer):
    """
    Проверка данных и создание или обновление рецепта.

    Изображение принимается как строка Base64 и преобразуется в
    файл с помощью Base64ImageField.
    Минимальное время приготовления ограничено константой MIN_COOKING_TIME.
    Поля ingredients и tags обязательны как при создании,
    так и при частичном обновлении рецепта.
    Создание и обновление выполняются внутри атомарных транзакций.
    Поэтому при ошибке сохранения тегов или ингредиентов все изменения
    текущей операции откатываются.
    При обновлении старые связи с тегами и ингредиентами полностью
    заменяются данными из запроса. После сохранения результат передаётся
    RecipeReadSerializer, чтобы API вернул полное представление рецепта,
    а не входной формат с идентификаторами.
    Методы:
    validate_ingredients:
    Проверяет, что один ингредиент не указан в рецепте несколько раз.
    При обнаружении повторяющихся идентификаторов возвращает
    ошибку валидации поля ingredients.
    validate_tags:
    Проверяет уникальность тегов внутри одного рецепта.
    Повторяющиеся идентификаторы вызывают ошибку валидации.
    validate:
    Выполняет общую проверку запроса и требует присутствия полей
    ingredients и tags, включая запросы PATCH.
    _create_recipe_ingredients:
    Формирует объекты промежуточной модели IngredientInRecipe
    и сохраняет все связи одним вызовом bulk_create.
    create:
    Извлекает данные тегов и ингредиентов, создаёт основной объект Recipe,
    устанавливает теги и сохраняет состав рецепта.
    Поле author передаётся представлением при вызове save().
    update:
    Обновляет основные поля рецепта, заменяет набор тегов, удаляет
    прежний состав и создаёт новые связи с ингредиентами.
    to_representation:
    Передаёт сохранённый объект в RecipeReadSerializer и возвращает
    полную структуру рецепта для ответа API.
    """

    ingredients = IngredientInRecipeWriteSerializer(
        many=True,
        allow_empty=False,
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        allow_empty=False,
    )
    image = Base64ImageField()
    cooking_time = serializers.IntegerField(
        min_value=MIN_COOKING_TIME,
    )

    class Meta:
        model = Recipe
        fields = (
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time',
        )

    def validate_ingredients(self, ingredients):

        ingredient_ids = [
            item['ingredient'].id
            for item in ingredients
        ]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты в рецепте не должны повторяться.'
            )
        return ingredients

    def validate_tags(self, tags):

        tag_ids = [tag.id for tag in tags]
        if len(tag_ids) != len(set(tag_ids)):
            raise serializers.ValidationError(
                'Теги в рецепте не должны повторяться.'
            )
        return tags

    def validate(self, attrs):

        errors = {}
        if 'ingredients' not in self.initial_data:
            errors['ingredients'] = 'Обязательное поле.'
        if 'tags' not in self.initial_data:
            errors['tags'] = 'Обязательное поле.'
        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    @staticmethod
    def _create_recipe_ingredients(recipe, ingredients):

        ingredient_relations = [
            IngredientInRecipe(
                recipe=recipe,
                ingredient=item['ingredient'],
                amount=item['amount'],
            )
            for item in ingredients
        ]
        IngredientInRecipe.objects.bulk_create(ingredient_relations)

    @transaction.atomic
    def create(self, validated_data):

        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self._create_recipe_ingredients(recipe, ingredients)

        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):

        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        instance = super().update(instance, validated_data)
        instance.tags.set(tags)
        IngredientInRecipe.objects.filter(recipe=instance).delete()
        self._create_recipe_ingredients(instance, ingredients)

        return instance

    def to_representation(self, instance):

        return RecipeReadSerializer(
            instance,
            context=self.context,
        ).data
