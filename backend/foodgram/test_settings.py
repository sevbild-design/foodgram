"""Настройки, используемые только при запуске автоматических тестов."""

from foodgram.settings import *  # noqa: F401, F403

# Тестам не требуется запущенный контейнер PostgreSQL. Django создаёт
# временную SQLite-базу перед прогоном и удаляет её после завершения.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'test_db.sqlite3',  # noqa: F405
    },
}

# Ускоряем создание пользователей: криптографическая стойкость хеширования
# паролей здесь не проверяется, поэтому достаточно быстрого MD5-хешера.
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)
