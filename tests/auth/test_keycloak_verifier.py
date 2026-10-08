import time

import pytest

from common.exceptions import UnauthorizedError
from common.security.keycloak import KeycloakTokenVerifier
from tests.auth.conftest import USER_ID, MakeToken


async def test_verify_returns_claims_for_valid_token(verifier: KeycloakTokenVerifier, make_token: MakeToken) -> None:
    claims = await verifier.verify(make_token())

    assert claims["sub"] == USER_ID


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"aud": "account"}, id="wrong-audience"),
        pytest.param({"iss": "http://evil.test/realms/sheber"}, id="wrong-issuer"),
        pytest.param({"exp": int(time.time()) - 60}, id="expired"),
    ],
)
async def test_verify_rejects_invalid_token(
    verifier: KeycloakTokenVerifier, make_token: MakeToken, overrides: dict[str, object]
) -> None:
    with pytest.raises(UnauthorizedError):
        await verifier.verify(make_token(**overrides))


async def test_verify_rejects_garbage(verifier: KeycloakTokenVerifier) -> None:
    with pytest.raises(UnauthorizedError):
        await verifier.verify("not-a-jwt")
