from django.contrib.auth import get_user_model
from djoser.serializers import \
    UserCreateSerializer as DjoserUserCreateSerializer
from djoser.serializers import UserSerializer as DjoserUserSerializer
from rest_framework import serializers

from api.fields import Base64ImageField
from recipes.models import Recipe

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
    """Пользователь с кратким списком его рецептов."""

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
