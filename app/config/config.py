import os

from collections.abc import Mapping
from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any, TypeVar, get_origin, get_type_hints

from sqlalchemy.engine import URL

T = TypeVar("T")

class ConfigError(Exception):
    """Raised when environment variables are missing or invalid."""

def env(name: str, *, optional: bool = False, secret: bool = False) -> Any:
    return field(repr=not secret, metadata={"env": name, "optional": optional})

@dataclass(frozen=True)
class DB:
    driver: str = env("DB_DRIVER")
    host: str = env("DB_HOST")
    port: int = env("DB_PORT")
    username: str = env("DB_USERNAME")
    password: str = env("DB_PASSWORD", secret=True)
    database: str = env("DB_DATABASE")
    echo: bool = env("DB_ECHO", optional=True)

    @property
    def url(self) -> str:
        return URL.create(
            drivername=self.driver,
            username=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        ).render_as_string(hide_password=False)

@dataclass(frozen=True)
class Migrator:
    path: str = env("DB_MIGRATIONS_PATH")
    run: bool = env("DB_RUN_MIGRATIONS", optional=True)

@dataclass(frozen=True)
class Service:
    host: str = env("SERVICE_HOST")
    port: int = env("SERVICE_PORT")


@dataclass(frozen=True)
class API:
    prefix: str = env("API_URL_PREFIX")
    tags: list[str] = env("API_TAGS")


@dataclass(frozen=True)
class Auth:
    auth_disabled: str = env("APPLICATION_AUTH_DISABLED", optional=True)
    authority: str = env("APPLICATION_AUTHORITY")
    tenant_id: str = env("APPLICATION_TENANT_ID")
    client_id: str = env("APPLICATION_CLIENT_ID", optional=True)
    audience: str = env("APPLICATION_API_AUDIENCE", optional=True)
    scope: str = env("APPLICATION_API_SCOPE")

    @property
    def disabled(self) -> bool:
        return str(self.auth_disabled or "").strip().lower() in ("true", "1", "yes")

    @property
    def token_audience(self) -> str:
        return self.audience or self.client_id

    @property
    def issuer_url(self) -> str:
        return f"{self.authority.rstrip('/')}/{self.tenant_id}/v2.0"

    @property
    def jwks_url(self) -> str:
        return f"{self.authority.rstrip('/')}/{self.tenant_id}/discovery/v2.0/keys"


@dataclass(frozen=True)
class Azure:
    language_endpoint: str = env("AZURE_LANGUAGE_ENDPOINT")
    disabled_pii: str = env("APPLICATION_PII_DISABLED", optional=True)

    @property
    def pii_disabled(self) -> bool:
        return str(self.disabled_pii or "").strip().lower() in ("true", "1", "yes")

@dataclass(frozen=True)
class Config:
    db: DB
    migrator: Migrator
    service: Service
    api: API
    auth: Auth
    azure: Azure

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off", ""}

def setup(environ: Mapping[str, str] | None = None) -> Config:
    source = os.environ if environ is None else environ
    errors: list[str] = []

    config = _load(Config, source, errors)
    if not errors:
        errors.extend(_validate(config))
    if errors:
        raise ConfigError("invalid configuration:\n- " + "\n- ".join(errors))

    return config

def _load(cls: type[T], environ: Mapping[str, str], errors: list[str]) -> T:
    hints = get_type_hints(cls)
    values: dict[str, Any] = {}

    for item in fields(cls):
        tp = hints[item.name]

        if is_dataclass(tp):
            values[item.name] = _load(tp, environ, errors)
            continue

        name = item.metadata.get("env")
        if not name:
            continue

        raw = environ.get(name)
        if raw is None:
            if item.metadata.get("optional"):
                values[item.name] = _zero(tp)
            else:
                errors.append(f"missing environment variable: {name}")
                values[item.name] = None
            continue

        try:
            values[item.name] = _convert(raw.strip(), tp, name)
        except ValueError as error:
            errors.append(str(error))
            values[item.name] = None

    return cls(**values)

def _zero(tp: Any) -> Any:
    return [] if get_origin(tp) is list else tp()

def _convert(raw: str, tp: Any, name: str) -> Any:
    if get_origin(tp) is list:
        return [part.strip() for part in raw.split(",") if part.strip()]

    if tp is bool:
        value = raw.lower()
        if value in _TRUE:
            return True
        if value in _FALSE:
            return False
        raise ValueError(f"{name} must be a boolean")

    if tp is int:
        try:
            return int(raw)
        except ValueError:
            raise ValueError(f"{name} must be an integer") from None

    if tp is str:
        return raw

    raise TypeError(f"unsupported config type for {name}: {tp}")

def _validate(config: Config) -> list[str]:
    errors: list[str] = []

    for name, port in (("SERVICE_PORT", config.service.port), ("DB_PORT", config.db.port)):
        if not 0 < port < 65536:
            errors.append(f"{name} must be between 1 and 65535")

    prefix = config.api.prefix
    if not prefix.startswith("/") or prefix.endswith("/"):
        errors.append("API_URL_PREFIX must start with '/' and not end with '/'")
    if not config.api.tags:
        errors.append("API_TAGS must contain at least one tag")

    required = {
        "DB_DRIVER": config.db.driver,
        "DB_HOST": config.db.host,
        "DB_USERNAME": config.db.username,
        "DB_DATABASE": config.db.database,
        "DB_MIGRATIONS_PATH": config.migrator.path,
        "SERVICE_HOST": config.service.host,
        "APPLICATION_AUTHORITY": config.auth.authority,
        "APPLICATION_TENANT_ID": config.auth.tenant_id,
        "APPLICATION_API_SCOPE": config.auth.scope,
        "APPLICATION_API_AUDIENCE or APPLICATION_CLIENT_ID": config.auth.token_audience,
        "AZURE_LANGUAGE_ENDPOINT": config.azure.language_endpoint,
    }
    errors.extend(f"{name} must not be empty" for name, value in required.items() if not value)

    return errors