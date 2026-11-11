# Comment-Validator

A Python 3.12 FastAPI service for storing comments in MariaDB. The API uses
SQLAlchemy, validates Entra bearer tokens, and is configured through
environment variables.

## Comments API

The API is mounted at the configured `API_URL_PREFIX`, set to `/comments` in
the configuration example below. Its request body for create and replace
operations is:

```json
{"content": "A useful comment"}
```

`content` must contain 1–5000 characters. Additional request fields are
rejected. Successful comment responses contain `id`, `content`, `user_id`,
`created_at`, and `updated_at`. `user_id` is the caller's Entra object ID;
the database also stores the tenant ID for tenant isolation.

| Method | Path | Purpose | Declared success |
|---|---|---|---|
| `GET` | `/comments` | List comments in the caller's tenant | `200` |
| `GET` | `/comments/{comment_id}` | Get a comment in the caller's tenant | `200` |
| `POST` | `/comments` | Create a comment | `201` |
| `PUT` | `/comments/{comment_id}` | Replace an existing comment | `200` |
| `DELETE` | `/comments/{comment_id}` | Delete a comment | `204` |

Reads are scoped to the caller's tenant. Update and delete are intended to
require both the caller's tenant ID and object ID to match the comment owner.
The current service calls the repository's `get` method without its required
tenant ID for both operations, so `PUT` and `DELETE` currently fail at runtime.
Those endpoints are listed in the OpenAPI schema but are not yet usable.

Expected API errors are returned as `{"detail": "..."}` responses. Missing
comments return `404`; invalid request bodies and detected PII return `422`;
unauthenticated requests return `401`; and access denials return `403`.

Authentication is enabled by default. The API validates the token signature,
issuer, audience, lifetime, tenant, object ID, and configured delegated scope.
Set `APPLICATION_AUTH_DISABLED=true` only for local development or tests; this
mode uses a fixed development identity and is not suitable for deployment.

PII screening is enabled by default and is intended to use Azure AI Language.
The current Azure detector configuration is incomplete, so enabled screening
fails closed with `503`. Set `APPLICATION_PII_DISABLED=true` only for local
development or tests. The Azure endpoint remains a required configuration
value even when screening is disabled.

GitHub Actions runs the Python tests, validates the Terraform configuration,
and builds/publishes the container image for the configured branches and
version tags.

<div align="center">

**Developed by** Linus Regander

**Latest update:** 2026-11-11

</div>
