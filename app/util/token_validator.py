from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import jwt

from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWTError

from app.errors import AuthenticationError, AuthenticationUnavailableError

bearer_scheme = HTTPBearer(auto_error=False)

MISSING_ACCESS_TOKEN = AuthenticationError("A bearer access token is required")
MISSING_AUTH_CONFIGURATION = AuthenticationUnavailableError(
    "Authentication is not configured"
)
MISSING_SIGNING_KEYS = AuthenticationUnavailableError("Signing keys are unavailable")
INVALID_BEARER_ACCESS_TOKEN = AuthenticationError("The bearer access token is invalid")


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    object_id: str

@dataclass(frozen=True)
class AuthConfig:
    disabled: bool = False
    disabled_principal: Principal = Principal(
        tenant_id="00000000-0000-0000-0000-000000000000",
        object_id="00000000-0000-0000-0000-000000000001",
    )
    tenant_id: str = ""
    audience: str = ""
    issuer_url: str = ""
    jwks_url: str = ""
    required_scope: str = ""
    algorithms: tuple[str, ...] = ("RS256",)


@lru_cache(maxsize=8)
def _jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url, cache_keys=True)

class TokenValidator:
    def __init__(self, config: AuthConfig) -> None:
        self._config = config

    def get_current_user(self, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]) -> Principal:
        if self._config.disabled:
            return self._config.disabled_principal

        self._verify_auth_setup(credentials)

        claims = self._decode_token(credentials.credentials)

        self._verify_claims(claims)

        return Principal(tenant_id=claims["tid"], object_id=claims["oid"])

    def _verify_auth_setup(self, credentials: HTTPAuthorizationCredentials | None):
        if credentials is None:
            raise MISSING_ACCESS_TOKEN

        config = self._config

        if not config.tenant_id or not config.audience or not config.jwks_url:
            raise MISSING_AUTH_CONFIGURATION

    def _decode_token(self, token: str) -> dict:
        config = self._config
        
        try:
            signing_key = _jwks_client(config.jwks_url).get_signing_key_from_jwt(token)
            
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=list(config.algorithms),
                audience=config.audience,
                issuer=config.issuer_url,
                options={"require": ["exp", "iat", "oid", "tid"]},
            )
        except PyJWKClientConnectionError as error:
            raise MISSING_SIGNING_KEYS from error
        except PyJWTError as error:
            raise INVALID_BEARER_ACCESS_TOKEN from error

    def _verify_claims(self, claims: dict) -> None:
        token_tenant = claims.get("tid")
        token_object = claims.get("oid")
        scopes = str(claims.get("scp", "")).split()

        if token_tenant != self._config.tenant_id:
            raise INVALID_BEARER_ACCESS_TOKEN

        if not isinstance(token_object, str) or not token_object:
            raise INVALID_BEARER_ACCESS_TOKEN

        if self._config.required_scope and self._config.required_scope not in scopes:
            raise INVALID_BEARER_ACCESS_TOKEN