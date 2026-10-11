# Simple Search

Асинхронный HTTP-сервис поиска по публикациям: PostgreSQL — источник данных, Elasticsearch — поисковый индекс. Управление данными — только через API: загрузка исходного CSV — явной CLI-командой, удаление — по HTTP.

## Краткий старт

```bash
docker compose up --build
docker compose exec api python -m app.cli import-csv /data/posts.csv
```

Первая команда поднимает API, PostgreSQL и Elasticsearch и применяет миграции. Вторая загружает исходный CSV (1500 записей) в БД и индекс; повторный запуск безопасен и не создаёт дубликатов.

Сервис отвечает на `http://localhost:8000`:

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

## Поиск

`POST /search` с телом `{"query": "..."}` возвращает до 20 документов со всеми полями. Сортировка — по убыванию `created_date` (сначала свежие; направление в задании не зафиксировано, выбрано «сначала новые»):

```bash
curl -X POST http://localhost:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "WhatsApp"}'
```

## Удаление

`DELETE /posts/{id}` удаляет документ из БД и индекса; повтор безопасен:

```bash
curl -X DELETE http://localhost:8000/posts/1
```

## Переиндексация

Полная переиндексация Elasticsearch из PostgreSQL без повторного чтения CSV:

```bash
docker compose exec api python -m app.cli reindex
```

## API-документация

Контракт сервиса — в корневом файле `docs.json` (OpenAPI 3). Он воспроизводится из текущего кода командой:

```bash
docker compose exec -T api python -m app.cli export-openapi /dev/stdout > docs.json
```

## Переменные окружения

| Переменная | Назначение | Значение по умолчанию |
|---|---|---|
| `DATABASE_URL` | Асинхронный URL PostgreSQL | `postgresql+asyncpg://search:search@localhost:5432/search` |
| `ES_URL` | Адрес Elasticsearch | `http://localhost:9200` |
| `ES_INDEX_NAME` | Имя поискового индекса | `posts-v1` |

В Docker Compose значения задаются в `docker-compose.yml`; для локального запуска без Docker скопируйте `.env.example` в `.env`.

## Поведение ошибок

| Ситуация | Ответ |
|---|---|
| Пустой или нечитаемый поисковый запрос | `422` с описанием проблемы |
| PostgreSQL или Elasticsearch недоступны | `503` без внутренних трассировок |
| Нет совпадений | `200` с пустым `items` |
| Повторный `DELETE` | `204` (идемпотентно) |
| Ошибка в строке CSV при импорте | команда завершается с номером строки и причиной, без частичной загрузки |

Если `DELETE` вернул `503` из-за недоступного Elasticsearch, повторите запрос после восстановления — он доведёт очистку индекса.

## Elasticsearch в Compose

Локальный контур работает в режиме разработки: `discovery.type=single-node`, `xpack.security.enabled=false`, ограничение JVM 512 МБ. Для продакшена включите security и задайте ресурсы под нагрузку.

## Тесты

Функциональные тесты ходят в HTTP-контракт сервиса с настоящими PostgreSQL и Elasticsearch. Тестовый профиль поднимает **изолированные** контейнеры (`postgres-test`, `elasticsearch-test`) — отдельные от рабочего контура, — применяет миграции и прогоняет тесты, не трогая данные рабочего api:

```bash
docker compose --profile test run --rm tests
```

Команда работает и на чистом контуре (сразу после `docker compose down -v`).

## Как устроено

```
CSV ──CLI-импорт──> PostgreSQL (источник данных)
                        │                 │
                   удаление           поиск: ES находит id,
                        │             ответ собирается из БД
                        └──> Elasticsearch (только индекс)
```

PostgreSQL — источник истины, Elasticsearch — только поиск: `POST /search` ищет в индексе, возвращает id и даты, затем ответ гидратируется из БД в порядке сортировки. `DELETE` сначала удаляет строку в PostgreSQL, потом документ в индексе; после `reindex` индекс становится полной копией БД. Схема БД — миграции Alembic в `migrations/`, поисковый маппинг — `app/models/es.py`, маршруты — `app/api/routes/`, контракт — `docs.json`, тесты — `tests/` (18 сценариев по HTTP-контракту). Стек: Python 3.12, FastAPI, SQLAlchemy 2 (async), asyncpg, Elasticsearch 8.
