import os

# Tests use their own database; must be set before settings are read
os.environ.setdefault("DB_NAME", "sheber_test")
# Uploaded files of a test run go to a throwaway directory
os.environ.setdefault("FILES_STORAGE_DIR", __import__("tempfile").mkdtemp(prefix="sheber-files-"))

import time
import uuid
from collections.abc import AsyncIterator, Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import jwt
import psycopg
import pytest
from aioinject import Object
from aioinject.testing import TestContainer
from alembic import command
from alembic.config import Config
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from common.database import engine, session_maker
from common.security.keycloak import KeycloakTokenVerifier
from common.security.keycloak_admin import RoleGranter
from enums.auth_enum import UserRoleEnum
from models import Base
from models.cities.mdl_city import City
from rest_api.dependencies import get_token_verifier
from rest_api.start_app import create_app
from services.di.container import create_container
from settings.db_settings import DBSettings
from settings.keycloak_settings import KeycloakSettings
from settings.resolver import get_settings

type MakeToken = Callable[..., str]

SETTINGS = KeycloakSettings(url="http://keycloak.test", realm="sheber", audience="sheber-backend")
USER_ID = "4f0c8a52-0d4e-4c55-9b1e-1f6b2f5d6c11"


class StaticKeyResolver:
    def __init__(self, public_key: rsa.RSAPublicKey) -> None:
        self._key = jwt.PyJWK.from_dict(jwt.algorithms.RSAAlgorithm.to_jwk(public_key, as_dict=True))

    def get_signing_key_from_jwt(self, token: str) -> jwt.PyJWK:
        return self._key


@pytest.fixture(scope="session")
def private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="session")
def verifier(private_key: rsa.RSAPrivateKey) -> KeycloakTokenVerifier:
    return KeycloakTokenVerifier(SETTINGS, key_resolver=StaticKeyResolver(private_key.public_key()))


@pytest.fixture(scope="session")
def make_token(private_key: rsa.RSAPrivateKey) -> MakeToken:
    def _make_token(**overrides: Any) -> str:
        now = int(time.time())
        claims: dict[str, Any] = {
            "iss": SETTINGS.issuer,
            "aud": ["sheber-backend", "account"],
            "sub": USER_ID,
            "iat": now,
            "exp": now + 300,
            "email": "client@sheber.local",
            "given_name": "Айгерим",
            "family_name": "Клиентова",
            "realm_access": {"roles": ["client", "offline_access", "default-roles-sheber"]},
        }
        claims.update(overrides)
        return jwt.encode(claims, private_key, algorithm="RS256")

    return _make_token


@pytest.fixture
def auth_app(app: FastAPI, verifier: KeycloakTokenVerifier) -> Iterator[FastAPI]:
    app.dependency_overrides[get_token_verifier] = lambda: verifier
    yield app
    app.dependency_overrides.pop(get_token_verifier)


type AuthHeaders = Callable[..., dict[str, str]]


@pytest.fixture(scope="session")
def app() -> FastAPI:
    return create_app()


@pytest.fixture(scope="session")
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client


@pytest.fixture
def auth_headers(auth_app: FastAPI, make_token: MakeToken) -> AuthHeaders:
    """Bearer headers for a user: auth_headers(user_id, roles=[...])."""

    def _headers(
        user_id: uuid.UUID, roles: tuple[UserRoleEnum, ...] = (UserRoleEnum.CLIENT,), **claims: Any
    ) -> dict[str, str]:
        token = make_token(
            sub=str(user_id),
            email=claims.pop("email", f"{user_id.hex[:8]}@sheber.local"),
            realm_access={"roles": [role.value for role in roles]},
            **claims,
        )
        return {"Authorization": f"Bearer {token}"}

    return _headers


class FakeRoleGranter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, uuid.UUID, UserRoleEnum]] = []

    async def grant_role(self, user_id: uuid.UUID, role: UserRoleEnum) -> None:
        self.calls.append(("grant", user_id, role))

    async def revoke_role(self, user_id: uuid.UUID, role: UserRoleEnum) -> None:
        self.calls.append(("revoke", user_id, role))


@pytest.fixture
def role_granter() -> Iterator[FakeRoleGranter]:
    fake = FakeRoleGranter()
    with TestContainer(create_container()).override(Object(fake, interface=RoleGranter)):
        yield fake


@pytest.fixture(scope="session")
def _test_database() -> None:
    settings = get_settings(DBSettings)
    admin_url = settings.url.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False)
    with psycopg.connect(admin_url, autocommit=True) as connection:
        exists = connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", (settings.name,)).fetchone()
        if not exists:
            connection.execute(f'CREATE DATABASE "{settings.name}"')
    # alembic env.py calls asyncio.run, which cannot nest in the test event loop
    with ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(command.upgrade, Config("alembic.ini"), "head").result()


@pytest.fixture(autouse=True)
async def _clean_database(request: pytest.FixtureRequest) -> AsyncIterator[None]:
    if request.node.get_closest_marker("db") is None:
        yield
        return
    request.getfixturevalue("_test_database")
    yield
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    async with engine.begin() as connection:
        await connection.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture
async def cities(_clean_database: None) -> dict[str, uuid.UUID]:
    """Two active cities and one hidden: slug -> id."""
    rows = [
        City(slug="almaty", name={"ru": "Алматы", "kk": "Алматы", "en": "Almaty"}, sort_order=2),
        City(slug="oskemen", name={"ru": "Усть-Каменогорск", "kk": "Өскемен", "en": "Oskemen"}),
        City(slug="hidden", name={"ru": "Скрытый"}, is_active=False),
    ]
    async with session_maker() as session:
        session.add_all(rows)
        await session.commit()
    return {city.slug: city.id for city in rows}


@pytest.fixture
def workshop_body(cities: dict[str, uuid.UUID]) -> dict[str, Any]:
    return {
        "name": "Ағаш Шебер",
        "cityId": str(cities["almaty"]),
        "phone": "+7 701 000 00 01",
        "taxId": "123456789012",
        "description": "Корпусная мебель на заказ",
        "furnitureTypes": ["wardrobe", "dresser"],
    }
