# Кулинарная книга — API на FastAPI

Асинхронный сервис на `FastAPI` и асинхронной `SQLAlchemy 2.0` (`aiosqlite`)
с CI на GitHub Actions: линтеры и тесты запускаются на каждый пуш в любую ветку
и на каждый пулл-реквест.

| Путь | Что внутри |
|---|---|
| [`app/main.py`](app/main.py) | приложение и эндпоинты |
| [`app/models.py`](app/models.py) | ORM-модели `Recipe` и `Ingredient` |
| [`app/schemas.py`](app/schemas.py) | Pydantic-схемы запросов и ответов с описаниями для документации |
| [`app/database.py`](app/database.py) | движок, фабрика сессий, зависимость `get_session` |
| [`tests/`](tests) | тесты (`pytest` + `httpx.AsyncClient`) |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | CI |
| [`pyproject.toml`](pyproject.toml), [`.flake8`](.flake8) | настройки black, isort, mypy, pytest, coverage и flake8 |

## Запуск

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Документация: http://127.0.0.1:8000/docs (Swagger UI) и http://127.0.0.1:8000/redoc.
База по умолчанию — `cookbook.db` в текущей папке, другой путь задаётся переменной `DATABASE_URL`.

## Эндпоинты

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/recipes` | таблица рецептов: `id`, `title`, `views`, `cooking_time` |
| `GET` | `/recipes/{recipe_id}` | детальный рецепт: `title`, `cooking_time`, `ingredients`, `description`; увеличивает `views` на 1, `404` если не найден |
| `POST` | `/recipes` | создать рецепт, `201`; `422` при невалидных данных |

Список отсортирован по `views` по убыванию, при равенстве — по `cooking_time` по возрастанию.

## Проверки

```bash
pip install -r requirements-dev.txt

black --check --diff .
isort --check-only --diff .
flake8 .
mypy app tests
pytest --cov=app --cov-report=term-missing --cov-fail-under=90
```

В CI две джобы:

* **Linters** (Python 3.12) — `black`, `isort`, `flake8` (с плагинами `flake8-bugbear` и `flake8-pie`)
  и `mypy` в режиме `strict` с плагином pydantic.
* **Tests** (Python 3.9 и 3.12) — `pip check` на конфликты зависимостей и `pytest` с замером покрытия:
  джоба падает, если покрытие ниже 90%.

### Конфликт black и flake8

* Длина строки у обоих — 79 символов (`line-length` у black и `max-line-length` у flake8 совпадают).
* В flake8 отключены `E203`, `E701`, `E704`: black форматирует срезы (`a[x + 1 :]`) и заглушки
  (`def f(): ...`) так, что эти проверки срабатывают. `W503` и так игнорируется по умолчанию.
* isort работает с `profile = "black"`, иначе он и black по-разному переносят длинные импорты.

### Что исправлено по замечаниям линтеров

* `E501` — длинные строки в описаниях OpenAPI и тестах разбиты на части.
* `B008` (вызов функции в значении по умолчанию) — `= Depends(get_session)` и `= Path(...)`
  заменены на `Annotated[...]`, как рекомендует FastAPI.
* `PIE781` (присвоить и сразу вернуть) — лишние переменные убраны.
* isort — исправлен порядок импортов; модули собраны в пакет `app`, хак с `sys.path` в тестах убран.
* mypy — `rowcount` у результата `UPDATE` (нужен `CursorResult`), `session.get()` может вернуть `None`
  (добавлена обработка), недостающие аннотации в тестах.
