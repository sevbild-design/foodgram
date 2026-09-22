from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import User


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
    list_filter = (
        'username',
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
