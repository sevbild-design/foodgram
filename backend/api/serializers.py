from django.contrib.auth import get_user_model
from django.db import transaction
from djoser.serializers import \
    UserCreateSerializer as DjoserUserCreateSerializer
from djoser.serializers import UserSerializer as DjoserUserSerializer
from rest_framework import serializers

from api.fields import Base64ImageField
from recipes.constants import MIN_COOKING_TIME, MIN_INGREDIENT_AMOUNT
from recipes.models import Ingredient, IngredientInRecipe, Recipe, Tag

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
    """Сериализатор отображения пользователя."""

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

        return (
            request is not None
            and request.user.is_authenticated
            and request.user.subscriptions.filter(
                author=author
            ).exists()
        )


class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор загрузки аватара."""

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
    """Преобразует ингредиент и его единицу измерения в JSON."""

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
    """Расширяет профиль автора списком и количеством его рецептов."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + (
            'recipes',
            'recipes_count',
        )

    def get_recipes(self, author):
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
    """Возвращает полную информацию о рецепте."""

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

    def _is_in_user_list(self, recipe, relation_name):

        request = self.context.get('request')

        if request is None or not request.user.is_authenticated:
            return False

        relation_manager = getattr(recipe, relation_name)

        return relation_manager.filter(user=request.user).exists()

    def get_is_favorited(self, recipe):

        return self._is_in_user_list(recipe, 'favorites')

    def get_is_in_shopping_cart(self, recipe):

        return self._is_in_user_list(recipe, 'shopping_cart')


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Создание и обновление рецепта."""

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
