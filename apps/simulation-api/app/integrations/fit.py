from __future__ import annotations

import os
import re
from collections.abc import Mapping
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from jwt import InvalidTokenError, PyJWKClient
from jwt.exceptions import (
    DecodeError,
    ExpiredSignatureError,
    ImmatureSignatureError,
    MissingRequiredClaimError,
)

FIT_ISSUER = "forge/invocation-token"
UNREGISTERED_APP_ID = "ari:cloud:ecosystem::app/00000000-0000-4000-8000-000000000000"
REGISTERED_APP_ID = "ari:cloud:ecosystem::app/73670daa-a329-4491-8a96-89bf239b203b"
COMMERCIAL_JWKS_URL = "https://forge.cdn.prod.atlassian-dev.net/.well-known/jwks.json"
MAX_REMOTE_BYTES = 64 * 1024
ALLOWED_ALGORITHMS = ["RS256"]
APP_ARI = re.compile(
    r"^ari:cloud:ecosystem::app/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
INSTALLATION_ARI = re.compile(
    r"^ari:cloud:ecosystem::installation/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
IC_LABEL = re.compile(r"^[a-z0-9_-]{1,50}$")
ENVIRONMENT_TYPES = {"DEVELOPMENT", "STAGING", "PRODUCTION"}
REQUIRED_CLAIMS = ["exp", "nbf", "iat", "iss", "aud"]


class FitValidationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def trusted_app_id(configured: str | None = None) -> str:
    value = (
        configured
        if configured is not None
        else os.environ.get("OPSTWIN_FORGE_APP_ID", REGISTERED_APP_ID)
    )
    return value.strip() if isinstance(value, str) else ""


def jwks_url_for_label(ic_label: object) -> str:
    if ic_label in (None, ""):
        return COMMERCIAL_JWKS_URL
    if not isinstance(ic_label, str) or not IC_LABEL.fullmatch(ic_label):
        raise FitValidationError(
            "invalid_ic_label", "Isolated Cloud label is not a safe JWKS selector."
        )
    return f"https://forge.cdn.prod.atlassian-dev.net/.well-known/jwks-{ic_label}.json"


def extract_bearer_token(authorization_header: object) -> str:
    if not isinstance(authorization_header, str) or authorization_header.strip() == "":
        raise FitValidationError("missing_authorization", "Authorization header is required.")
    match = re.fullmatch(r"Bearer\s+(\S+)", authorization_header.strip(), flags=re.IGNORECASE)
    if not match:
        raise FitValidationError(
            "missing_authorization", "Authorization header must be a Bearer token."
        )
    return match.group(1)


def assert_payload_bounds(raw_body: bytes | str, limit: int = MAX_REMOTE_BYTES) -> int:
    if not isinstance(raw_body, bytes | str):
        raise FitValidationError("invalid_payload", "Remote body must be a string or buffer.")
    size = len(raw_body.encode("utf-8")) if isinstance(raw_body, str) else len(raw_body)
    if size > limit:
        raise FitValidationError(
            "payload_too_large", "Remote body exceeds the bounded payload limit."
        )
    return size


def sanitize_remote_log(value: object) -> str:
    if not isinstance(value, str):
        return "[redacted]"
    if re.search(r"bearer\s+", value, flags=re.IGNORECASE) or value.count(".") == 2:
        return "[redacted-token]"
    return value[:80]


def _require_app_identity(payload: Mapping[str, Any], expected: str) -> None:
    if not APP_ARI.fullmatch(expected):
        raise FitValidationError(
            "untrusted_app_id", "Trusted application identity is not configured."
        )
    if expected == UNREGISTERED_APP_ID:
        raise FitValidationError(
            "unregistered_app",
            "Placeholder Forge app identity cannot accept remote invocations.",
        )
    app = payload.get("app")
    app_id = app.get("id") if isinstance(app, Mapping) else None
    if app_id != expected:
        raise FitValidationError(
            "wrong_app_id", "Forge application identity does not match the trusted app ID."
        )


def _installation_id(payload: Mapping[str, Any]) -> str:
    app = payload.get("app")
    if not isinstance(app, Mapping):
        raise FitValidationError(
            "invalid_installation",
            "Installation identity is missing from the Forge Invocation Token.",
        )
    installation = app.get("installation")
    installation_id = app.get("installationId")
    if installation_id is None and isinstance(installation, Mapping):
        installation_id = installation.get("id")
    if not isinstance(installation_id, str) or not INSTALLATION_ARI.fullmatch(installation_id):
        raise FitValidationError(
            "invalid_installation",
            "Installation identity is missing from the Forge Invocation Token.",
        )
    return installation_id


def _assert_environment(payload: Mapping[str, Any]) -> None:
    app = payload.get("app")
    environment = app.get("environment") if isinstance(app, Mapping) else None
    env_type = environment.get("type") if isinstance(environment, Mapping) else None
    env_id = environment.get("id") if isinstance(environment, Mapping) else None
    if (
        env_type not in ENVIRONMENT_TYPES
        or not isinstance(env_id, str)
        or not env_id.startswith("ari:cloud:ecosystem::environment/")
    ):
        raise FitValidationError(
            "invalid_environment", "Forge environment context is missing or unsupported."
        )


def verify_forge_invocation_token(
    authorization_header: object,
    expected_app_id: str,
    *,
    key: RSAPublicKey | str | bytes | None = None,
    jwks_client: PyJWKClient | None = None,
) -> dict[str, Any]:
    token = extract_bearer_token(authorization_header)
    try:
        header = jwt.get_unverified_header(token)
    except DecodeError as error:
        raise FitValidationError(
            "invalid_token", "Forge Invocation Token could not be verified."
        ) from error
    if header.get("alg") not in ALLOWED_ALGORITHMS:
        raise FitValidationError(
            "unsupported_algorithm", "Forge Invocation Token signing algorithm is not allowed."
        )

    verification_key = key
    if verification_key is None:
        unverified = jwt.decode(
            token,
            options={
                "verify_signature": False,
                "verify_exp": False,
                "verify_nbf": False,
                "verify_aud": False,
            },
        )
        jwks_url = jwks_url_for_label(
            unverified.get("icLabel") if isinstance(unverified, Mapping) else None
        )
        client = jwks_client or PyJWKClient(jwks_url)
        try:
            verification_key = client.get_signing_key_from_jwt(token).key
        except Exception as error:
            raise FitValidationError(
                "jwks_unavailable", "Trusted JWKS could not be retrieved."
            ) from error

    try:
        payload = jwt.decode(
            token,
            verification_key,
            algorithms=ALLOWED_ALGORITHMS,
            audience=expected_app_id,
            issuer=FIT_ISSUER,
            leeway=5,
            options={"require": REQUIRED_CLAIMS},
        )
    except ExpiredSignatureError as error:
        raise FitValidationError("expired_token", "Forge Invocation Token has expired.") from error
    except ImmatureSignatureError as error:
        raise FitValidationError(
            "not_yet_valid", "Forge Invocation Token is not yet valid."
        ) from error
    except MissingRequiredClaimError as error:
        claim = getattr(error, "claim", "")
        if claim == "exp":
            raise FitValidationError(
                "missing_expiration", "Forge Invocation Token expiration is required."
            ) from error
        if claim == "aud":
            raise FitValidationError(
                "wrong_audience", "Forge Invocation Token audience does not match this app."
            ) from error
        if claim == "iss":
            raise FitValidationError(
                "invalid_issuer", "Forge Invocation Token issuer is not trusted."
            ) from error
        raise FitValidationError(
            "invalid_token", "Forge Invocation Token could not be verified."
        ) from error
    except InvalidTokenError as error:
        message = str(error).lower()
        if "audience" in message:
            raise FitValidationError(
                "wrong_audience", "Forge Invocation Token audience does not match this app."
            ) from error
        if "issuer" in message:
            raise FitValidationError(
                "invalid_issuer", "Forge Invocation Token issuer is not trusted."
            ) from error
        raise FitValidationError(
            "invalid_token", "Forge Invocation Token could not be verified."
        ) from error

    _require_app_identity(payload, expected_app_id)
    installation_id = _installation_id(payload)
    _assert_environment(payload)
    return {"payload": payload, "installationId": installation_id}
