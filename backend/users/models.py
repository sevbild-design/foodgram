from django.contrib.auth.models import AbstractUser
from django.db import models

from users.constants import EMAIL_MAX_LENGTH, USERNAME_MAX_LENGTH


class User(AbstractUser):
    """
    Кастомная модель пользователя.

    Поля 'Имя' и 'Фамилия' обязательные.
    Стандартная модель расширена добавлением аватара.
    Для входа используется email вместо username.
    """

    first_name = models.CharField(
        verbose_name='Имя',
        max_length=USERNAME_MAX_LENGTH,
    )
    last_name = models.CharField(
        verbose_name='Фамилия',
        max_length=USERNAME_MAX_LENGTH,
    )
    email = models.EmailField(
        verbose_name='Адрес электронной почты',
        max_length=EMAIL_MAX_LENGTH,
        unique=True,
    )
    avatar = models.ImageField(
        verbose_name='Ссылка на аватар',
        upload_to='users/avatars/',
        blank=True,
        null=True,
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = (
        'username',
        'first_name',
        'last_name',
    )

    class Meta:
        ordering = ('username',)
        verbose_name = 'Пользователь'
        verbose_name_plural = 'пользователи'

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class Subscription(models.Model):
    """
    Модель подписки одного пользователя на другого.

    Одна и та же пара подписчик–автор может существовать только раз.
    При удалении автора или подписчика удаляются и связанные подписки.
    Невозможна подписка на самого себя.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Подписчик',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscribers',
        verbose_name='Автор',
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'подписки'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'author'),
                name='unique_user_author_subscription',
            ),
            models.CheckConstraint(
                condition=~models.Q(user=models.F('author')),
                name='prevent_self_subscription',
            ),
        )

    def __str__(self):
        return f'{self.user} → {self.author}'
