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

## Configuration

Create a local `.env` file (do not commit it) with the following values:

```dotenv
DB_DRIVER=mysql+pymysql
DB_HOST=db
DB_PORT=3306
DB_USERNAME=comments
DB_PASSWORD=<database-password>
DB_DATABASE=comments
DB_ECHO=false
DB_MIGRATIONS_PATH=/app/app/sql
DB_RUN_MIGRATIONS=true

SERVICE_HOST=0.0.0.0
SERVICE_PORT=8000
API_URL_PREFIX=/comments
API_TAGS=Comments

APPLICATION_AUTH_DISABLED=true
APPLICATION_AUTHORITY=https://login.microsoftonline.com
APPLICATION_TENANT_ID=<tenant-id>
APPLICATION_CLIENT_ID=<api-client-id>
APPLICATION_API_AUDIENCE=<api-audience>
APPLICATION_API_SCOPE=access_as_user

APPLICATION_PII_DISABLED=true
AZURE_LANGUAGE_ENDPOINT=https://<language-resource>.cognitiveservices.azure.com/

MARIADB_ROOT_PASSWORD=<database-root-password>
```

`DB_HOST`, `DB_PORT`, `DB_MIGRATIONS_PATH`, and `SERVICE_HOST` are set for the
API container by Docker Compose. The API configuration still requires their
values to be present in its environment, so set them in `.env` as shown.
Authentication and PII disable flags should be `false` in a deployment, once
the corresponding service configuration is ready.

## Run and Test

Start the API and MariaDB with Docker Compose:

```bash
make run
```

This builds the API image and starts both services. The API listens at
`http://localhost:8000`; interactive API documentation is at
`http://localhost:8000/docs`. Stop the services with `make down` and view logs
with `make logs`.

Install the development dependencies and run the test suite with:

```bash
make install
make test
```

The API tests use an isolated SQLite database and inject test identity and PII
screening dependencies. Database schema changes are plain SQL files in
`app/sql`; startup applies them when `DB_RUN_MIGRATIONS=true`.

## CI

GitHub Actions runs the Python tests, validates the Terraform configuration,
and builds/publishes the container image for the configured branches and
version tags.

<div align="center">

**Developed by** Linus Regander

**Latest update:** 2026-11-02

</div>
