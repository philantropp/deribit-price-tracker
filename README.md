# Deribit Price Tracker

Тестовое задание. Раз в минуту забираю с Deribit индексную цену `btc_usd` и `eth_usd`,
сохраняю в PostgreSQL (тикер, цена, UNIX-время) и отдаю через FastAPI.

Стек: Python 3.12, FastAPI, Celery + beat, Redis, PostgreSQL, SQLAlchemy (async), Alembic, aiohttp, pytest.

## Запуск

```bash
cp .env.example .env
docker compose up -d --build
```

Поднимаются `db`, `redis`, `migrate` (прогоняет миграции и выходит), `api`, `worker`, `beat`.
API на `http://localhost:8000`, документация на `/docs`.

Первая запись появляется примерно через минуту. Проверить, что сбор идёт:

```bash
docker compose logs -f worker
```

## API

Во всех методах обязателен параметр `ticker` (`btc_usd` или `eth_usd`).

- `GET /api/v1/prices?ticker=btc_usd` — все записи по тикеру. Есть необязательные `limit` и `offset`.
- `GET /api/v1/prices/latest?ticker=btc_usd` — последняя цена (404, если данных ещё нет).
- `GET /api/v1/prices/by-date?ticker=btc_usd&date_from=...&date_to=...` — цены за период.
  Нужна хотя бы одна граница. Дата в ISO (`2026-10-15`, `2026-10-15T12:00:00+03:00`)
  или UNIX-время. Без часового пояса считается UTC.

Пример ответа:

```json
{"ticker": "btc_usd", "price": 80918.93, "timestamp": 1792061819}
```

## Тесты

```bash
docker compose --profile test run --rm tests
```

Юнит-тесты работают на фейках, без сети и БД. Интеграционные тесты репозитория запускаются на
настоящем Postgres, если задан `TEST_DATABASE_URL` (в контейнере `tests` он задан).

Линтер: `ruff check app tests migrations`.

## Без Docker

Нужны запущенные Postgres и Redis, адреса прописываются в `.env`.

```bash
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.api.main:create_app --factory --reload
celery -A app.worker.celery_app worker --loglevel=INFO   # на Windows добавить --pool=solo
celery -A app.worker.celery_app beat --loglevel=INFO
```

## Немного о решениях

- Код разбит на слои: клиент Deribit, сервисы, репозиторий. API и Celery-задача только вызывают
  сервисы, поэтому логику можно тестировать без инфраструктуры.
- Глобальных объектов нет: настройки, приложение и Celery собираются через фабрики, зависимости
  передаются через `Depends`/конструкторы. Исключение — `celery_app` на уровне модуля,
  без него не работает `celery -A`.
- Задача Celery синхронная и внутри вызывает `asyncio.run`. Engine БД создаётся на каждый запуск,
  потому что asyncpg-соединения нельзя переносить между event loop'ами.
- Оба тикера запрашиваются параллельно, и у записей одного запуска одинаковый timestamp.
  Если один тикер не получен, второй всё равно сохраняется, а задача помечается упавшей.
  Ретраев нет: цена с опозданием уже не цена той минуты.
- Цена хранится как `NUMERIC`, время как `BIGINT`, индекс на `(ticker, timestamp)`.
- Redis добавлен, потому что Celery нужен брокер. Beat вынесен в отдельный контейнер,
  чтобы при нескольких воркерах задачи не дублировались.

## Что бы доделал

- unique на `(ticker, timestamp)`, чтобы не было дублей;
- курсорную пагинацию вместо `offset`;
- CI с ruff и pytest.
