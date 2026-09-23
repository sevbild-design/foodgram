import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from recipes.models import Ingredient

DEFAULT_DATA_PATH = (
    settings.BASE_DIR.parent / 'data' / 'ingredients.json'
)


class Command(BaseCommand):
    """Загружает ингредиенты из JSON-файла."""

    help = 'Загружает ингредиенты из data/ingredients.json'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            type=Path,
            default=DEFAULT_DATA_PATH,
            help='Путь до JSON-файла с ингредиентами',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        file_path = options['path']

        if not file_path.exists():
            raise CommandError(
                f'Файл с ингредиентами не найден: {file_path}'
            )

        try:
            with file_path.open(encoding='utf-8') as file:
                ingredients_data = json.load(file)
        except json.JSONDecodeError as error:
            raise CommandError(
                f'Некорректный JSON: {error}'
            ) from error
        except (OSError, UnicodeDecodeError) as error:
            raise CommandError(
                f'Не удалось прочитать файл: {error}'
            ) from error

        if not isinstance(ingredients_data, list):
            raise CommandError(
                'Корневой элемент JSON должен быть списком.'
            )

        created_count = 0
        existing_count = 0

        for number, item in enumerate(ingredients_data, start=1):
            try:
                name = item['name'].strip()
                measurement_unit = item['measurement_unit'].strip()
            except (KeyError, TypeError, AttributeError) as error:
                raise CommandError(
                    f'Некорректная запись №{number}: {item}'
                ) from error

            if not name or not measurement_unit:
                raise CommandError(
                    f'Пустое поле в записи №{number}: {item}'
                )

            _, created = Ingredient.objects.get_or_create(
                name=name,
                measurement_unit=measurement_unit,
            )

            if created:
                created_count += 1
            else:
                existing_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                'Импорт завершён. '
                f'Создано: {created_count}. '
                f'Уже существовало: {existing_count}.'
            )
        )
