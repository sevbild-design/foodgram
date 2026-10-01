from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from users.models import Subscription

User = get_user_model()


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Настройки отображения пользователей в админ-зоне."""

    list_display = (
        'username',
        'first_name',
        'last_name',
        'email',
        'avatar',
        'date_joined',
    )

    search_fields = (
        'username',
        'email',
    )
    readonly_fields = (
        'avatar_preview',
    )

    fieldsets = UserAdmin.fieldsets + (
        (
            'Дополнительная информация',
            {
                'fields': (
                    'avatar',
                    'avatar_preview',
                )
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            'Дополнительная информация',
            {
                'fields': (
                    'email',
                    'first_name',
                    'last_name',
                    'avatar',
                )
            },
        ),
    )

    @admin.display(description='Аватар')
    def avatar_preview(self, user):
        if user is None or not user.avatar:
            return 'Аватар отсутствует'
        return format_html(
            '<img src="{}" width="100" height="100" '
            'style="object-fit: cover; border-radius: 50%;" />',
            user.avatar.url,
        )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Управление подписками."""

    list_display = (
        'user',
        'author',
    )
    search_fields = (
        'user__username',
        'user__email',
        'author__username',
        'author__email',
    )
