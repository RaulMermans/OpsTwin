from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from collections.abc import Mapping
from typing import Any

from app.interventions.execute import MultiExperimentEvidence

TOKEN_VERSION = "ev1"
MAX_CLAIMS_BYTES = 48 * 1024
DEFAULT_TTL_SECONDS = 6 * 60 * 60
# Existing ev1 tokens without project/principal fail bind_context after CG-7.1; TTL is 6 hours.
DEV_FALLBACK_KEY = "opstwin-dev-evidence-hmac-not-for-production"
SHARED_PRINCIPAL = "scope:installation-user-context"


class EvidenceTokenError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def signing_key() -> bytes:
    configured = os.environ.get("OPSTWIN_EVIDENCE_HMAC_KEY", "").strip()
    if configured:
        return configured.encode("utf-8")
    if os.environ.get("OPSTWIN_ALLOW_DEV_EVIDENCE_KEY") == "1":
        return DEV_FALLBACK_KEY.encode("utf-8")
    raise EvidenceTokenError(
        "signing_key_unavailable",
        "Evidence signing is not configured for this environment.",
    )


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64url(text: str) -> bytes:
    padding = "=" * ((4 - len(text) % 4) % 4)
    try:
        return base64.urlsafe_b64decode(text + padding)
    except (ValueError, OSError) as error:
        raise EvidenceTokenError("malformed_token", "The evidence token is malformed.") from error


def canonical_dumps(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def compact_operational_evidence(evidence: MultiExperimentEvidence) -> dict[str, Any]:
    payload = json.loads(evidence.model_dump_json(by_alias=True, exclude_none=True))
    if not isinstance(payload, dict):
        raise EvidenceTokenError("malformed_token", "Operational evidence could not be compacted.")
    return payload


def sign_claims(claims: dict[str, Any], *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    now = int(time.time())
    payload = {
        **claims,
        "tokenVersion": TOKEN_VERSION,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    body = canonical_dumps(payload)
    if len(body) > MAX_CLAIMS_BYTES:
        raise EvidenceTokenError("payload_too_large", "Signed evidence exceeds the token size limit.")  # noqa: E501
    digest = hmac.new(signing_key(), body, hashlib.sha256).hexdigest()
    return f"{TOKEN_VERSION}.{_b64url(body)}.{digest}"


def verify_claims(token: object) -> dict[str, Any]:
    if not isinstance(token, str) or token.count(".") != 2:
        raise EvidenceTokenError("malformed_token", "The evidence token is malformed.")
    version, encoded, digest = token.split(".", 2)
    if version != TOKEN_VERSION or not digest:
        raise EvidenceTokenError("unsupported_token", "Unsupported evidence token version.")
    body = _unb64url(encoded)
    if len(body) > MAX_CLAIMS_BYTES:
        raise EvidenceTokenError("payload_too_large", "Signed evidence exceeds the token size limit.")  # noqa: E501
    expected = hmac.new(signing_key(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, digest):
        raise EvidenceTokenError("invalid_signature", "The evidence token signature is invalid.")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EvidenceTokenError("malformed_token", "The evidence token is malformed.") from error
    if not isinstance(payload, dict):
        raise EvidenceTokenError("malformed_token", "The evidence token is malformed.")
    exp = payload.get("exp")
    if not isinstance(exp, int) or exp < int(time.time()) - 5:
        raise EvidenceTokenError("expired_token", "The evidence token has expired.")
    if payload.get("tokenVersion") != TOKEN_VERSION:
        raise EvidenceTokenError("unsupported_token", "Unsupported evidence token version.")
    return payload


def bind_context(
    claims: dict[str, Any],
    *,
    app_id: str,
    installation_id: str,
    environment_type: str,
    project_key: str | None = None,
    principal_id: str | None = None,
    kind: str | None = None,
    purpose: str | None = None,
) -> None:
    if claims.get("appId") != app_id:
        raise EvidenceTokenError("scope_mismatch", "Evidence was issued for a different application.")  # noqa: E501
    if claims.get("installationId") != installation_id:
        raise EvidenceTokenError(
            "scope_mismatch",
            "Evidence cannot be reused across Forge installations.",
        )
    if claims.get("environmentType") != environment_type:
        raise EvidenceTokenError("scope_mismatch", "Evidence was issued for a different environment.")  # noqa: E501
    expected_project = claims.get("projectKey")
    if not expected_project:
        raise EvidenceTokenError("scope_mismatch", "Evidence is missing project authorization scope.")  # noqa: E501
    if expected_project != project_key:
        raise EvidenceTokenError("scope_mismatch", "Evidence cannot be reused across Jira projects.")  # noqa: E501
    expected_principal = claims.get("principalId")
    if not expected_principal:
        raise EvidenceTokenError("scope_mismatch", "Evidence is missing principal authorization scope.")  # noqa: E501
    if expected_principal != principal_id:
        raise EvidenceTokenError(
            "scope_mismatch",
            "Evidence cannot be reused by an unauthorized principal.",
        )
    if kind is not None and claims.get("kind") != kind:
        raise EvidenceTokenError("unsupported_token", "The token is not the required artifact type.")  # noqa: E501
    if purpose is not None and claims.get("purpose") != purpose:
        raise EvidenceTokenError("unsupported_token", "The token cannot be reused for this purpose.")  # noqa: E501


def principal_from_verified(verified: Mapping[str, Any] | None) -> str | None:
    if not isinstance(verified, Mapping):
        return None
    payload = verified.get("payload")
    if not isinstance(payload, Mapping):
        return None
    principal = payload.get("principal")
    if not isinstance(principal, Mapping):
        return None
    account = principal.get("accountId")
    if not isinstance(account, str) or not account.strip():
        return None
    return account.strip()


def bind_request_principal(verified: Mapping[str, Any] | None, principal_id: str) -> str:
    if not principal_id or principal_id == SHARED_PRINCIPAL:
        raise EvidenceTokenError(
            "scope_mismatch",
            "A verified user identity is required for signed evidence.",
        )
    fit_principal = principal_from_verified(verified)
    if fit_principal and fit_principal != principal_id:
        raise EvidenceTokenError(
            "scope_mismatch",
            "Authorized principal does not match the Forge invocation identity.",
        )
    return principal_id


def authorized_scope_from_payload(payload: dict[str, Any]) -> tuple[str, str]:
    project = payload.get("authorizedProjectKey")
    principal = payload.get("authorizedPrincipal")
    if not isinstance(project, str) or not project.strip():
        raise EvidenceTokenError("scope_mismatch", "Authorized project context is required.")
    if not isinstance(principal, str) or not principal.strip():
        raise EvidenceTokenError("scope_mismatch", "Authorized principal context is required.")
    if principal.strip() == SHARED_PRINCIPAL:
        raise EvidenceTokenError(
            "scope_mismatch",
            "Shared installation principal context cannot authorize signed evidence.",
        )
    return project.strip(), principal.strip()


def artifact_claims(
    *,
    kind: str,
    purpose: str,
    app_id: str,
    installation_id: str,
    environment_type: str,
    project_key: str | None,
    principal_id: str | None,
    extra: dict[str, Any],
) -> dict[str, Any]:
    if not project_key or not principal_id:
        raise EvidenceTokenError(
            "scope_mismatch",
            "Signed evidence requires authorized project and principal scope.",
        )
    return {
        "kind": kind,
        "purpose": purpose,
        "artifactType": kind,
        "contractVersion": extra.get("contractVersion", "cg7.v1"),
        "appId": app_id,
        "installationId": installation_id,
        "environmentType": environment_type,
        "projectKey": project_key,
        "principalId": principal_id,
        **extra,
    }
