# Foodgram

Foodgram — веб-приложение для публикации рецептов и формирования списка
покупок.

Пользователи могут создавать рецепты, добавлять к ним изображения, теги и
ингредиенты, подписываться на авторов, сохранять рецепты в избранное и
формировать список необходимых продуктов. Список покупок можно скачать в виде
текстового файла, в котором количество одинаковых ингредиентов суммируется.

Проект состоит из Django REST API и React-фронтенда. Приложение работает в
Docker-контейнерах, а сборка образов и production-деплой автоматизированы с
помощью GitHub Actions.

## Возможности проекта

- регистрация и токен-аутентификация пользователей;
- просмотр профилей пользователей;
- установка и удаление аватара;
- подписка и отписка от авторов рецептов;
- просмотр ленты подписок;
- создание, редактирование и удаление собственных рецептов;
- добавление изображения рецепта в формате Base64;
- фильтрация рецептов по автору, тегам, избранному и списку покупок;
- поиск ингредиентов по началу названия без учёта регистра;
- добавление рецептов в избранное;
- добавление рецептов в список покупок;
- скачивание списка покупок с суммированием ингредиентов;
- административное управление пользователями, рецептами, тегами и
  ингредиентами;
- автоматическое наполнение базы исходным списком ингредиентов;
- хранение данных в PostgreSQL;
- раздача frontend, статики и медиафайлов через Nginx;
- автоматическая сборка и публикация Docker-образов;
- автоматический production-деплой через GitHub Actions;
- отправка уведомления в Telegram после успешного деплоя.

## Технологии

### Backend

- Python 3.12
- Django
- Django REST Framework
- Djoser
- django-filter
- PostgreSQL
- Gunicorn

### Frontend

- React
- JavaScript
- Node.js

### Infrastructure

- Docker
- Docker Compose
- Nginx
- GitHub Actions
- Docker Hub

## Архитектура

Production-окружение состоит из четырёх сервисов:

- `db` — база данных PostgreSQL;
- `backend` — Django REST API, запущенный через Gunicorn;
- `frontend` — контейнер для подготовки собранных файлов React-приложения;
- `gateway` — Nginx, который раздаёт frontend, статические и медиафайлы и
  проксирует API-запросы к backend.

Данные PostgreSQL, статические и медиафайлы сохраняются в Docker volumes.

На сервере дополнительно используется внешний Nginx. Он принимает запросы к
домену проекта, обеспечивает работу HTTPS и перенаправляет запросы на контейнер
`gateway`.

## Переменные окружения

Конфиденциальные настройки проекта хранятся в файле `.env`. Этот файл нельзя
добавлять в Git.

Пример конфигурации:

```env
POSTGRES_DB=foodgram
POSTGRES_USER=foodgram_user
POSTGRES_PASSWORD=change_me
DB_HOST=db
DB_PORT=5432

SECRET_KEY=change_me
DEBUG=False
ALLOWED_HOSTS=foodgram.example.com,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://foodgram.example.com

DOCKER_USERNAME=wantedpa
```

| Переменная | Назначение |
| --- | --- |
| `POSTGRES_DB` | имя базы данных PostgreSQL |
| `POSTGRES_USER` | пользователь PostgreSQL |
| `POSTGRES_PASSWORD` | пароль пользователя PostgreSQL |
| `DB_HOST` | имя сервиса PostgreSQL в Docker Compose |
| `DB_PORT` | порт PostgreSQL |
| `SECRET_KEY` | секретный ключ Django |
| `DEBUG` | режим отладки Django |
| `ALLOWED_HOSTS` | список разрешённых хостов Django |
| `CSRF_TRUSTED_ORIGINS` | доверенные HTTPS-адреса для CSRF-проверки |
| `DOCKER_USERNAME` | имя пользователя на Docker Hub |

Названия переменных должны совпадать с настройками Django и
`docker-compose.production.yml`.

## Локальный запуск через Docker Compose

Клонируйте репозиторий и перейдите в каталог `infra`:

```bash
git clone https://github.com/sevbild-design/foodgram.git
cd foodgram/infra
```

Создайте файл `.env` и заполните переменные окружения. Затем соберите и
запустите контейнеры:

```bash
docker compose up -d --build
```

Проверьте состояние сервисов:

```bash
docker compose ps
```

Выполните миграции:

```bash
docker compose exec backend python manage.py migrate
```

Создайте суперпользователя:

```bash
docker compose exec backend python manage.py createsuperuser
```

После запуска приложение будет доступно по адресам:

- frontend — <http://localhost/>;
- API — <http://localhost/api/>;
- документация API — <http://localhost/api/docs/>;
- административная панель — <http://localhost/admin/>.

Посмотреть логи backend:

```bash
docker compose logs -f --tail=100 backend
```

Остановить и удалить контейнеры, сохранив volumes:

```bash
docker compose down
```

## Наполнение базы ингредиентами

Исходный список ингредиентов находится в файле:

```text
data/ingredients.json
```

При сборке backend-образа файл копируется внутрь контейнера:

```text
/data/ingredients.json
```

После выполнения миграций workflow запускает management-команду:

```bash
python manage.py import_ingredients
```

Команда читает JSON-файл и создаёт отсутствующие ингредиенты. Импорт сделан
идемпотентным: повторный запуск не создаёт дубликаты, а уже существующие записи
учитываются отдельно. Поэтому команда может безопасно выполняться при каждом
деплое.

Пример результата первого запуска:

```text
Импорт завершён. Создано: 2186. Уже существовало: 0.
```

Результат повторного запуска:

```text
Импорт завершён. Создано: 0. Уже существовало: 2186.
```

При необходимости импорт можно выполнить вручную:

```bash
docker compose exec backend python manage.py import_ingredients
```

В production-окружении:

```bash
sudo docker compose -f docker-compose.production.yml exec backend \
  python manage.py import_ingredients
```

Ингредиенты сохраняются в PostgreSQL volume и не удаляются при обычном
перезапуске или пересоздании контейнеров.

## Production-деплой

Production-деплой выполняется автоматически с помощью GitHub Actions.

Workflow расположен в:

```text
.github/workflows/main.yml
```

Перед первым деплоем необходимо:

- установить Docker на сервер;
- установить и настроить внешний Nginx;
- настроить домен и HTTPS;
- создать каталог проекта на сервере;
- создать production-файл `.env`;
- добавить необходимые Secrets в настройках GitHub Actions.

После отправки изменений в ветку `main` GitHub Actions автоматически:

1. собирает backend-образ вместе с исходным файлом ингредиентов;
2. собирает frontend-образ;
3. собирает gateway-образ;
4. публикует образы на Docker Hub;
5. копирует на сервер `docker-compose.production.yml`;
6. подключается к серверу по SSH;
7. загружает актуальные Docker-образы;
8. запускает или пересоздаёт production-контейнеры;
9. ожидает готовности PostgreSQL;
10. выполняет миграции Django;
11. автоматически загружает ингредиенты в базу данных;
12. собирает и копирует статические файлы;
13. отправляет уведомление в Telegram после успешного деплоя.

Имена Docker-образов:

```text
wantedpa/foodgram_backend:latest
wantedpa/foodgram_frontend:latest
wantedpa/foodgram_gateway:latest
```

Для повторного ручного запуска production-контейнеров:

```bash
cd ~/foodgram
sudo docker compose -f docker-compose.production.yml pull
sudo docker compose -f docker-compose.production.yml up -d
```

Проверка состояния:

```bash
sudo docker compose -f docker-compose.production.yml ps
```

## API

Основные группы эндпоинтов:

```text
/api/users/
/api/users/me/
/api/users/subscriptions/
/api/tags/
/api/ingredients/
/api/recipes/
/api/auth/token/login/
/api/auth/token/logout/
```

Полная спецификация доступна после запуска проекта:

```text
/api/docs/
```

## Развёрнутый проект

```text
https://sevbild.ru
```

## Автор

Милютиков Павел — [GitHub](https://github.com/sevbild-design)
