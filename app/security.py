"""Microsoft Entra access-token validation for API callers."""

import os
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWTError

from app.errors import AuthenticationError, AuthenticationUnavailableError


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class EntraPrincipal:
    """Verified, tenant-scoped Entra user identity."""

    tenant_id: str
    object_id: str


@lru_cache(maxsize=8)
def _jwks_client(tenant_id: str) -> PyJWKClient:
    return PyJWKClient(
        f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
        cache_keys=True,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> EntraPrincipal:
    """Validate an Entra JWT and return its stable tenant/object identifiers."""
    if credentials is None:
        raise AuthenticationError("A bearer access token is required")

    tenant_id = os.getenv("ENTRA_TENANT_ID")
    audience = os.getenv("ENTRA_API_AUDIENCE") or os.getenv("ENTRA_CLIENT_ID")
    if not tenant_id or not audience:
        raise AuthenticationUnavailableError(
            "Entra authentication is not configured"
        )

    issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
    try:
        signing_key = _jwks_client(tenant_id).get_signing_key_from_jwt(
            credentials.credentials
        )
        claims = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
            options={"require": ["exp", "iat", "oid", "tid"]},
        )
    except PyJWKClientConnectionError as error:
        raise AuthenticationUnavailableError(
            "Entra signing keys are unavailable"
        ) from error
    except PyJWTError as error:
        raise AuthenticationError("The bearer access token is invalid") from error

    token_tenant = claims.get("tid")
    object_id = claims.get("oid")
    scopes = claims.get("scp", "").split()
    required_scope = os.getenv("ENTRA_REQUIRED_SCOPE", "access_as_user")
    if (
        token_tenant != tenant_id
        or not isinstance(object_id, str)
        or not object_id
        or required_scope not in scopes
    ):
        raise AuthenticationError("The bearer access token is invalid")

    return EntraPrincipal(tenant_id=tenant_id, object_id=object_id)