from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import Subscription, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Настройки отображения пользователей в админ-зоне."""

    list_display = (
        'username',
        'first_name',
        'last_name',
        'email',
        'avatar'
    )
    search_fields = (
        'username',
        'email',
    )

    fieldsets = UserAdmin.fieldsets + (
        (
            'Дополнительная информация',
            {
                'fields': (
                    'avatar',
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
