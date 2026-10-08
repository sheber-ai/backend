import time
from collections.abc import Callable, Iterator
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI

from common.security.keycloak import KeycloakTokenVerifier
from rest_api.dependencies import get_token_verifier
from settings.keycloak_settings import KeycloakSettings

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
