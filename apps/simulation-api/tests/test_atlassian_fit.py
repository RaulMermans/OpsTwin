from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey

from app.integrations.fit import (
    REGISTERED_APP_ID,
    UNREGISTERED_APP_ID,
    FitValidationError,
    assert_payload_bounds,
    extract_bearer_token,
    jwks_url_for_label,
    sanitize_remote_log,
    verify_forge_invocation_token,
)

TRUSTED_APP_ID = "ari:cloud:ecosystem::app/11111111-1111-4111-8111-111111111111"
INSTALLATION_ID = "ari:cloud:ecosystem::installation/22222222-2222-4222-8222-222222222222"


def _keys() -> tuple[RSAPrivateKey, RSAPublicKey]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def _token(
    private_key: RSAPrivateKey,
    *,
    app_id: str = TRUSTED_APP_ID,
    audience: str = TRUSTED_APP_ID,
    issuer: str = "forge/invocation-token",
    exp: datetime | None = None,
    nbf: datetime | None = None,
    installation_id: str = INSTALLATION_ID,
    environment_type: str = "DEVELOPMENT",
    algorithm: str = "RS256",
    include_exp: bool = True,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "app": {
            "id": app_id,
            "installationId": installation_id,
            "appVersion": "0.0.1",
            "environment": {
                "type": environment_type,
                "id": "ari:cloud:ecosystem::environment/dev",
            },
            "module": {"type": "core:endpoint", "key": "lab"},
        },
        "context": {"cloudId": "cloud-dev"},
        "iss": issuer,
        "aud": audience,
        "iat": int(now.timestamp()),
        "nbf": int((nbf or now - timedelta(seconds=1)).timestamp()),
    }
    if include_exp:
        payload["exp"] = int((exp or now + timedelta(minutes=2)).timestamp())
    return jwt.encode(payload, private_key, algorithm=algorithm)


def test_missing_bearer_is_rejected() -> None:
    with pytest.raises(FitValidationError) as error:
        extract_bearer_token("")
    assert error.value.code == "missing_authorization"


def test_valid_signed_token_is_accepted() -> None:
    private_key, public_key = _keys()
    token = _token(private_key)
    result = verify_forge_invocation_token(f"Bearer {token}", TRUSTED_APP_ID, key=public_key)
    assert result["installationId"] == INSTALLATION_ID


def test_expired_missing_exp_wrong_claims_and_placeholder_are_rejected() -> None:
    private_key, public_key = _keys()
    expired = _token(private_key, exp=datetime.now(UTC) - timedelta(minutes=1))
    with pytest.raises(FitValidationError) as error:
        verify_forge_invocation_token(f"Bearer {expired}", TRUSTED_APP_ID, key=public_key)
    assert error.value.code == "expired_token"

    future = _token(private_key, nbf=datetime.now(UTC) + timedelta(hours=1))
    with pytest.raises(FitValidationError) as error:
        verify_forge_invocation_token(f"Bearer {future}", TRUSTED_APP_ID, key=public_key)
    assert error.value.code == "not_yet_valid"

    now = datetime.now(UTC)
    payload = {
        "app": {
            "id": TRUSTED_APP_ID,
            "installationId": INSTALLATION_ID,
            "environment": {"type": "DEVELOPMENT", "id": "ari:cloud:ecosystem::environment/dev"},
        },
        "iss": "forge/invocation-token",
        "aud": TRUSTED_APP_ID,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
    }
    missing_exp = jwt.encode(payload, private_key, algorithm="RS256")
    with pytest.raises(FitValidationError) as error:
        verify_forge_invocation_token(f"Bearer {missing_exp}", TRUSTED_APP_ID, key=public_key)
    assert error.value.code in {"missing_expiration", "invalid_token"}

    wrong_aud = _token(private_key, audience=REGISTERED_APP_ID)
    with pytest.raises(FitValidationError) as error:
        verify_forge_invocation_token(f"Bearer {wrong_aud}", TRUSTED_APP_ID, key=public_key)
    assert error.value.code == "wrong_audience"

    placeholder = _token(private_key, app_id=UNREGISTERED_APP_ID, audience=UNREGISTERED_APP_ID)
    with pytest.raises(FitValidationError) as error:
        verify_forge_invocation_token(f"Bearer {placeholder}", UNREGISTERED_APP_ID, key=public_key)
    assert error.value.code == "unregistered_app"


def test_unsupported_algorithm_untrusted_key_and_logs_are_safe() -> None:
    private_key, public_key = _keys()
    hs_token = jwt.encode(
        {
            "app": {
                "id": TRUSTED_APP_ID,
                "installationId": INSTALLATION_ID,
                "environment": {
                    "type": "DEVELOPMENT",
                    "id": "ari:cloud:ecosystem::environment/dev",
                },
            },
            "iss": "forge/invocation-token",
            "aud": TRUSTED_APP_ID,
            "exp": int((datetime.now(UTC) + timedelta(minutes=2)).timestamp()),
            "nbf": int(datetime.now(UTC).timestamp()),
            "iat": int(datetime.now(UTC).timestamp()),
        },
        "secret",
        algorithm="HS256",
    )
    with pytest.raises(FitValidationError) as error:
        verify_forge_invocation_token(f"Bearer {hs_token}", TRUSTED_APP_ID, key=public_key)
    assert error.value.code == "unsupported_algorithm"

    other, _ = _keys()
    token = _token(other)
    with pytest.raises(FitValidationError) as error:
        verify_forge_invocation_token(f"Bearer {token}", TRUSTED_APP_ID, key=public_key)
    assert error.value.code == "invalid_token"

    with pytest.raises(FitValidationError) as error:
        assert_payload_bounds(b"x" * (193 * 1024))
    assert error.value.code == "payload_too_large"
    assert sanitize_remote_log("Bearer a.b.c") == "[redacted-token]"
    assert jwks_url_for_label(None).endswith("jwks.json")
