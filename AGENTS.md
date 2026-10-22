# Sheber Backend — правила для разработчиков и ИИ-агентов

Sheber — платформа заказа корпусной мебели. **Клиент** собирает мебель в онлайн 3D-конструкторе
(позже — по ссылке или фото с помощью ИИ) и публикует **заказ**. **Мастерские** проходят модерацию,
откликаются на заказы своего города ценой и сроком; клиент выбирает одну, и стороны видят контакты друг друга.
Оплаты на платформе пока нет.

Этот репозиторий — REST API. Фронтенд живёт в соседнем репозитории `../frontend` и получает
клиент API через Orval из нашей OpenAPI-схемы, поэтому **контракт API — часть кода** (см. «API-контракт»).

## Стек

Python 3.13 · FastAPI · SQLAlchemy 2 (async) + psycopg 3 · Pydantic 2 + pydantic-settings ·
Alembic · aioinject (DI) · PostgreSQL 18 · uv · ruff · mypy (strict) · pytest + pytest-asyncio.

Авторизация — Keycloak (JWT), см. раздел «Авторизация». Локальный Keycloak: `../keycloak-theme` (`make up`).

Локально проект запускается **без Docker**: PostgreSQL установлен на машине, API — `make dev`.
В Docker живёт только Keycloak.

## Команды

```bash
make install            # uv sync + git-хуки pre-commit
make db-create          # роль sheber и базы sheber, sheber_test в локальном PostgreSQL (пароль postgres)
# Keycloak: cd ../keycloak-theme && make up
make migrate            # применить миграции
make seed               # справочники (города) из scripts/seeds/*.json; можно запускать повторно
make dev                # API на http://localhost:8000, Swagger: /api/docs
make migration m="..."  # новая миграция из моделей (autogenerate)
make lint               # ruff + format --check + mypy
make format
make test               # pytest (тестам с маркером db нужна БД)
make openapi            # openapi.json без запуска сервера
```

Зависимости — только через `uv add <pkg>` / `uv add --dev <pkg>`. Не правьте `uv.lock` руками, не используйте pip.

## Структура

Код разложен **по слоям**, внутри слоя — **по доменам**. Один домен присутствует в нескольких слоях.

```
main.py                      точка входа (uvicorn main:app)
rest_api/
  start_app.py               фабрика приложения create_app()
  routers.py                 подключение всех роутеров к /api/v1
  error_handlers.py          AppError -> HTTP-ответ
  dependencies.py            CurrentUser, require_roles — авторизация
  <домен>/res_*.py           эндпоинты
services/
  <домен>/svc_*.py           бизнес-логика
  di/container.py            DI-контейнер aioinject
  di/providers/<домен>.py    регистрация сервисов и менеджеров домена
managers/
  mng_base.py                BaseManager[Model]
  <домен>/mng_*.py           запросы к БД
models/
  mdl_base.py                Base, UUIDMixin, TimestampMixin, naming convention
  <домен>/mdl_*.py           ORM-модели (подхватываются автоматически)
schemas/
  sch_base.py                BaseSchema, PageSchema, ErrorSchema
  <домен>/sch_*.py           Pydantic-схемы API
enums/<домен>_enum.py        перечисления
settings/                    *_settings.py — классы pydantic-settings, resolver.get_settings
common/                      инфраструктура: database.py, exceptions.py, security/ (проверка JWT), клиенты внешних систем
alembic/versions/            миграции (только autogenerate)
scripts/                     служебные скрипты: seed.py, create_db.sql, export_openapi.py
scripts/seeds/               данные справочников (JSON с переводами)
tests/                       тесты, зеркалят домены: tests/<домен>/test_*.py
```

### Домены

| Домен | Что внутри |
|---|---|
| `cities` | справочник городов: таблица с переводами названий, `GET /cities` в языке запроса, заполняется `make seed` |
| `users` | профиль поверх Keycloak: имя, телефон, город; создаётся при первом запросе (`UserService.sync_user`) |
| `workshops` | мастерские: анкета, модерация админом, выдача роли `contractor` через Admin API Keycloak |
| `designs` | проекты конструктора: документ мебели (`schemas/designs/sch_document.py`), источник (с нуля / ссылка / фото) |
| `orders` | опубликованный проект (снимок документа) и его статусы: `published → assigned → in_progress → completed`, `cancelled` |
| `offers` | отклики мастерских: цена, срок; принятие отклика назначает мастерскую на заказ |
| `imports` | *(позже)* разбор ссылки/фото с помощью ИИ в черновик документа. Сейчас ссылка сохраняется в `designs.source_url` и передаётся мастерской как референс |
| `files` | *(позже)* загрузка файлов (S3) |
| `system` | служебное: health и т.п. |

### Справочники и перечисления

Два вида «списков значений», выбор между ними — по тому, кто и как часто их меняет:

| | Перечисление в коде | Таблица-справочник |
|---|---|---|
| Примеры | статусы заказа и отклика, типы мебели, материалы, роли | города |
| Где живёт | `enums/<домен>_enum.py` (`StrEnum`) | своя таблица + `scripts/seeds/<что>.json` |
| В БД | колонка `String(32)` без ограничений (не `Enum`, не CHECK) | строки таблицы, связь по `id` (FK) |
| Валидация | Pydantic-схемы API (поле типа `XxxEnum`) | сервис: `require_active(id)` перед записью |
| Новое значение | правка enum в коде, **без миграции** | `make seed` (или админка), без деплоя кода |
| Переводы | на фронте (`i18n`), бэкенд отдаёт код | в БД, бэкенд отдаёт текст на языке запроса |
| Фронт | тип и константы генерирует Orval из OpenAPI | список — запросом к API |

- В моделях enum-поле объявляется как `Mapped[str] = mapped_column(String(32), default=XxxEnum.VALUE)` с комментарием,
  какой enum в нём хранится. Тип `Enum` SQLAlchemy запрещён — проверяет `tests/test_models.py`.
- Справочник: `id` (UUID), стабильный `slug` для сидов, `name` (JSONB с переводами), `sort_order`, `is_active`.
  Удалять строки нельзя (на них ссылаются) — скрывайте через `is_active`.

Новый домен — новая подпапка в каждом нужном слое с тем же именем (`snake_case`, мн. число для коллекций).

## Нейминг

**Файлы** — `snake_case` с префиксом слоя:

| Слой | Префикс | Пример |
|---|---|---|
| роутеры | `res_` | `rest_api/listings/res_listings.py` |
| сервисы | `svc_` | `services/listings/svc_listings.py` |
| менеджеры | `mng_` | `managers/listings/mng_listings.py` |
| модели | `mdl_` | `models/listings/mdl_listing.py` |
| схемы | `sch_` | `schemas/listings/sch_listing.py` |
| перечисления | `<домен>_enum.py` | `enums/listings_enum.py` |
| настройки | `<что>_settings.py` | `settings/db_settings.py` |

**Классы** — `PascalCase`:
- модели — единственное число без суффикса: `Listing(Base, UUIDMixin, TimestampMixin)`; таблица — мн. число `snake_case`: `__tablename__ = "listings"`;
- менеджеры — `<Model>Manager(BaseManager[Model])`: `ListingManager`;
- сервисы — `<Домен>Service`: `ListingService`, `ListingPublishService`;
- схемы — всегда суффикс `Schema`: `ListingSchema` (ответ), `ListingCreateSchema`, `ListingUpdateSchema`, `ListingFilterSchema`; списки — `PageSchema[ListingSchema]`;
- перечисления — `<Что>Enum(StrEnum)`, значения в `snake_case`: `ListingStatusEnum.PUBLISHED = "published"`;
- исключения — суффикс `Error`, наследник `AppError`: `ListingAlreadyPublishedError`.

**Функции и методы** — `snake_case`, I/O всегда `async def`. Приватные — с `_`.
Эндпоинты называются `<глагол>_<сущность>`: `list_listings`, `get_listing`, `create_listing`,
`update_listing`, `delete_listing`, `publish_listing`. Имя эндпоинта **уникально на всё приложение**
(из него получается имя хука на фронте, см. ниже).

## Слои и правила

Поток вызова строго сверху вниз: `rest_api → services → managers → models`. Схемы — на границе API.

**rest_api** — тонкий слой: принимает схему, вызывает **один** метод сервиса, возвращает схему.
Никакого SQLAlchemy, никакой бизнес-логики, никакого `HTTPException` (кроме редких случаев протокола).
Тип ответа указывается аннотацией возврата функции — `response_model` не дублируем.

**services** — бизнес-логика и права доступа. Получают менеджеры и другие сервисы через конструктор (DI).
**Сервис владеет транзакцией**: после изменений сам вызывает `await self._session.commit()`.
Менеджеры и роутеры `commit` не делают никогда. Ошибки — подклассы `AppError` из `common/exceptions.py`.

**managers** — только запросы к БД, возвращают ORM-модели. Можно `flush`, нельзя `commit`.
Без бизнес-правил и без схем. Общие CRUD-операции — в `BaseManager`, своё — методами наследника.

**models** — только описание таблиц. Наследуйте `Base` и миксины из `models/mdl_base.py`.
- Типы — через `Mapped[...]`; `datetime` всегда с таймзоной (уже настроено в `Base`).
- Перечисления — колонка `String(32)`, не `Enum` (см. «Справочники и перечисления»).
- JSON-поля: `Mapped[dict[str, Any]]` / `Mapped[list[Any]]` → JSONB.
- Внешние ключи с явным `ondelete`. Индексы — на всё, по чему фильтруем.
- Регистрировать модель нигде не нужно: `import_all_models()` подхватывает все `models/**/mdl_*.py`.

**schemas** — наследуйте `BaseSchema`. В JSON поля автоматически в `camelCase`, в Python — `snake_case`.
Валидацию входа делайте в схеме (`Field(min_length=..., gt=...)`), а не в сервисе.
`model_dump()` по умолчанию отдаёт `camelCase` — для ORM-моделей используйте `model_dump(by_alias=False)`.
Телефоны — тип `Phone` из `sch_base.py` (нормализует в `+7XXXXXXXXXX`), пагинация — `PaginationSchema` через
`Annotated[PaginationSchema, Query()]`.

**settings** — только классы `BaseSettings` с `env_prefix`. Получать через DI (`settings: AppSettings`
в конструкторе) или `get_settings(Cls)`. `os.environ` в коде не читаем. Новую переменную — в `.env.example`.

**DI** — каждый домен регистрирует свои сервисы и менеджеры в `services/di/providers/<домен>.py`
(`Scoped(...)`); модуль подхватывается автоматически. В эндпоинте: `@inject` и `Injected[Service]`.

### Пример нового домена

```python
# models/listings/mdl_listing.py
class Listing(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "listings"
    title: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(32), default=ListingStatusEnum.DRAFT, index=True)  # ListingStatusEnum


# managers/listings/mng_listings.py
class ListingManager(BaseManager[Listing]):
    model = Listing


# services/listings/svc_listings.py
class ListingService:
    def __init__(self, session: AsyncSession, mng_listings: ListingManager) -> None:
        self._session = session
        self._mng_listings = mng_listings

    async def create_listing(self, data: ListingCreateSchema) -> ListingSchema:
        listing = await self._mng_listings.add(Listing(**data.model_dump(by_alias=False)))
        await self._session.commit()
        return ListingSchema.model_validate(listing)


# services/di/providers/listings.py
providers: Providers = [Scoped(ListingManager), Scoped(ListingService)]

# rest_api/listings/res_listings.py
router = APIRouter(prefix="/listings", tags=["listings"])


@router.post("", status_code=status.HTTP_201_CREATED)
@inject
async def create_listing(body: ListingCreateSchema, svc_listings: Injected[ListingService]) -> ListingSchema:
    return await svc_listings.create_listing(body)


# rest_api/routers.py
api_v1_router.include_router(res_listings.router)
```

## Авторизация

Пользователи, пароли, регистрация и роли живут в Keycloak. Бэкенд только **проверяет access token**:
подпись по JWKS realm'а (ключи кэшируются), срок, `iss` и `aud = sheber-backend`. Запросов к Keycloak
на каждый запрос нет. Код: `common/security/keycloak.py`, `rest_api/dependencies.py`.

```python
from rest_api.dependencies import AdminUser, ContractorUser, CurrentUser

@router.get("/mine")
@inject
async def list_my_listings(user: CurrentUser, svc_listings: Injected[ListingService]) -> PageSchema[ListingSchema]:
    return await svc_listings.list_for_owner(user.id)

@router.post("/{listing_id}/offers")
@inject
async def create_offer(listing_id: UUID, user: ContractorUser, ...) -> OfferSchema: ...
```

- `CurrentUser` — любой вошедший; `ContractorUser`, `AdminUser` — с ролью; свой набор ролей —
  `Annotated[CurrentUserSchema, Depends(require_roles(UserRoleEnum.CLIENT, UserRoleEnum.ADMIN))]`.
- Эндпоинт без этих зависимостей — публичный. Публичным делайте осознанно.
- `user.id` — `sub` пользователя в Keycloak (UUID). Им связываем данные с пользователем (`owner_id` и т.п.).
- Пользователь передаётся в сервис аргументом метода. Сервис проверяет права на конкретный объект
  (своё объявление и т.п.) и бросает `PermissionDeniedError`; роли проверяются на уровне эндпоинта.
- Роли — `enums/auth_enum.py` (`client`, `contractor`, `admin`) и realm-роли Keycloak с теми же именами.
  Новая роль — в обоих местах. Роли из токена, которых нет в enum, отбрасываются.
- Ошибки: нет/плохой токен → 401 `unauthorized`, нет роли → 403 `permission_denied`, Keycloak недоступен → 503.
- Swagger (`/api/docs`): кнопка **Authorize** → вход через Keycloak (client `sheber-frontend`, PKCE), токен подставится сам.
- Тесты: фикстуры `make_token` и `auth_app` из `tests/auth/conftest.py` подписывают токены локальным RSA-ключом —
  Keycloak для тестов не нужен.

## Мультиязычность

Языки — `LanguageEnum` (`ru`, `kk`, `en`) в `enums/i18n_enum.py`, по умолчанию `ru`.

- Клиент передаёт язык заголовком `Accept-Language` (фронтенд ставит его в каждый запрос).
  Эндпоинт получает его зависимостью `language: Language` и передаёт в сервис аргументом.
- Переводимые данные в БД — JSONB `{"ru": ..., "kk": ..., "en": ...}`; `ru` обязателен, это запасной язык.
  Вход — `LocalizedTextSchema`, выход — поле типа `LocalizedStr`: схема сама выбирает перевод, если
  валидировать её с контекстом языка:
  ```python
  CitySchema.model_validate(city, context=language_context(language))
  ```
  Контекст передаётся вложенным схемам: `OrderSchema` с полем `city: CityBriefSchema` локализует и город.
- Тексты интерфейса и подписи enum-значений переводит фронтенд; ошибки API — по `code`.
- Новый язык: значение в `LanguageEnum`, переводы в сидах и в локалях фронтенда. Миграция не нужна.

## Миграции (Alembic)

**Миграции создаются только автогенерацией из моделей.** Одна миграция — один модуль (таблица или
тесно связанная группа таблиц одного домена). Не смешивайте в одной миграции изменения разных доменов:
меняете две модели из разных доменов — сделайте два шага `make migration`. Порядок:

1. Изменить модель в `models/`.
2. `make migration m="add listings table"` — описание на английском, в нижнем регистре.
3. Прочитать сгенерированный файл (`alembic/versions/YYYYMMDDHHMMSS_<rev>_<slug>.py`) и убедиться, что он делает ровно то, что нужно.
4. `make migrate`, затем `make check-migrations`.

Это enforced:
- `alembic revision` без `--autogenerate` падает (`alembic/env.py`); пустые миграции не создаются;
- pre-commit отклоняет файл миграции без маркера autogenerate;
- Claude Code не даёт создать файл в `alembic/versions` (`.claude/hooks`), а правку — только с подтверждения;
- `tests/test_migrations.py` падает, если модели разошлись с миграциями.

Данные справочников в миграции не пишутся — они в `scripts/seeds/` и загружаются `make seed`.

Правка сгенерированной миграции допустима **только** для того, чего autogenerate не умеет:
переименование колонки/таблицы (иначе он сделает drop + add и потеряет данные), перенос данных,
`CREATE EXTENSION`. Такую правку согласуйте с пользователем. Никогда не редактируйте миграцию,
которая уже применена где-либо кроме вашей локальной БД — создайте новую.

## API-контракт (для Orval на фронте)

- Все роуты под `/api/v1`, схема — `/api/v1/openapi.json`.
- `operationId` = имя функции-эндпоинта: `get_listing` → на фронте хук `useGetListing`. Поэтому имена уникальны (проверяет `tests/test_openapi.py`).
- `tags=["<домен>"]` на каждом роутере — Orval раскладывает код по папкам тегов. Без тега тест упадёт.
- Каждый эндпоинт возвращает Pydantic-схему (аннотация возврата), не `dict` и не ORM-модель.
- Списки — `PageSchema[ItemSchema]` с `offset`/`limit` в query.
- Ошибки — `ErrorSchema {code, detail}` через `AppError`. `code` — стабильный ключ для перевода на фронте, `detail` — на английском для разработчика.
- После изменения контракта сообщите, что фронтенду нужен `npm run generate:api`.

## Тесты

- `pytest` + `pytest-asyncio` (режим auto). HTTP — через фикстуру `client` (`httpx.AsyncClient`).
- Файлы `tests/<домен>/test_*.py`, функции `test_<что>_<ожидание>`.
- Тесты, которым нужна БД, помечаются `@pytest.mark.db`. Они работают в отдельной базе `sheber_test`
  (создаётся `make db-create`, мигрируется автоматически), таблицы очищаются после каждого теста.
- Справочники в тестах — фикстуры (`cities` в `tests/conftest.py`), а не сиды.
- Пользователи в тестах — фикстура `auth_headers(user_id, roles=(...))`; вызовы Keycloak Admin API —
  фикстура `role_granter` (подменяет `RoleGranter` в DI и записывает вызовы).
- Новая бизнес-логика — с тестом.

## Git

Коммиты — **Conventional Commits** (проверяется хуком `commit-msg`):

```
<type>(<scope>): <описание>

[тело: зачем, а не что]

[BREAKING CHANGE: ...]
```

| type | когда |
|---|---|
| `feat` | новая функциональность |
| `fix` | исправление бага |
| `refactor` | изменение кода без изменения поведения |
| `perf` | производительность |
| `test` | только тесты |
| `docs` | только документация (в т.ч. AGENTS.md) |
| `style` | форматирование без изменения логики |
| `build` | зависимости, Dockerfile, uv |
| `ci` | CI/CD |
| `chore` | прочее обслуживание |
| `revert` | откат коммита |

- `scope` — домен (`listings`, `imports`, `db`, `di`), необязателен.
- Описание — **на английском**, в повелительном наклонении («add», а не «added»/«adds»), с маленькой буквы, без точки, заголовок до 72 символов. Тело коммита (зачем) — тоже на английском.
- Ломающее API изменение — `feat!:` / `fix!:` и футер `BREAKING CHANGE:`.
- Один коммит — одно логическое изменение. Миграция коммитится вместе с изменением модели.
- Примеры: `feat(listings): add listing publishing`, `fix(imports): handle links without og:image`, `build: bump fastapi to 0.143`.
- Ветки: `<type>/<кратко-через-дефис>` — `feat/listing-publish`.

## Комментарии и язык кода

- Комментарии и докстринги — **только на английском**, коротко и **только когда без них непонятно**:
  неочевидное «почему», ограничение, обход бага. Не пересказывайте код, не дублируйте имя функции.
  ```python
  # PyJWKClient does blocking I/O
  signing_key = await asyncio.to_thread(...)
  ```
- Всё, что видит только разработчик, — тоже на английском: `detail` ошибок API, сообщения CLI, `## help` в Makefile,
  названия тестов и `id` параметров. Фронтенд показывает пользователю перевод по `code` ошибки, а не `detail`.
- Русский/казахский — только в данных (тестовые имена и т.п.).

## Чек-лист перед завершением задачи

1. `make format && make lint` — без ошибок.
2. `make test` — зелёные.
3. Если менялись модели — миграция (по одной на модуль) создана через `make migration` и проверена `make check-migrations`.
4. Если менялся API — тег, уникальное имя эндпоинта, схемы ответа на месте.
5. Новые переменные окружения — в `.env.example`.

## Для ИИ-агентов

- Не коммитьте и не пушьте без явной просьбы пользователя.
- Не добавляйте зависимости без необходимости; если добавили — объясните зачем.
- Не создавайте файлы вне описанной структуры и не вводите новые слои/префиксы без согласования.
- Комментарии — на английском и только по необходимости (см. «Комментарии и язык кода»).
- Если правило мешает решить задачу — остановитесь и спросите, а не обходите его.
