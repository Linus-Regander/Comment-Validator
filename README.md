# Comment-Validator

## Tech Stack

| Category | Tools |
|---|---|
| Language | **Python 3.12** |
| Framework | **FastAPI**, Pydantic |
| Data Layer | SQLAlchemy, Alembic, **MariaDB**, SQLite (local development) |
| Identity & Access | **Microsoft Entra ID**, JWT bearer tokens |
| Privacy | **Azure AI Language** PII detection |
| Infrastructure | **Terraform**, Azure managed identity, private endpoint and DNS |
| Containers | **Docker**, Docker Compose |
| CI/CD (GitHub) | **GitHub Actions**, Copilot project agent |

## Comments API

Layered FastAPI service for creating, reading, replacing, and deleting comments.

- `GET /comments` lists comments; `GET /comments/{comment_id}` reads one.
- `POST /comments` creates a comment (push).
- `PUT /comments/{comment_id}` creates or replaces a comment.
- `DELETE /comments/{comment_id}` removes a comment.
- Expected application errors are centrally mapped to HTTP status codes; a missing comment returns `404`.
- All comment routes require an Entra v2 bearer token. The API stores the caller's tenant/object IDs and associates comments with that user; users can only update or delete their own comments.
- Create and update operations send the comment text to Azure AI Language PII detection before writing. Detected PII returns `422`; unavailable screening fails closed with `503`.

### Run Locally

Install dependencies and tests, then configure Entra and Azure Language before starting the service:

```bash
make install
make test
export ENTRA_TENANT_ID='<tenant-id>'
export ENTRA_CLIENT_ID='<api-client-id>'
export ENTRA_API_AUDIENCE='<api-client-id>'
export AZURE_LANGUAGE_ENDPOINT='https://<language-resource>.cognitiveservices.azure.com/'
make run
```

The API documentation is available at `http://localhost:8000/docs`.
Entra validation uses the tenant's published signing keys and validates issuer,
audience, signature, token lifetime, and the `access_as_user` delegated scope.
The client must request an access token for the Terraform-provisioned scope.
Azure SDK credentials use
`DefaultAzureCredential`; locally this can use Azure CLI login, while deployed
workloads should use the provisioned user-assigned managed identity.

Database changes run through Alembic at startup. The identity migration removes
the old client-provided `author` column and leaves existing comments unowned;
those legacy comments remain readable but cannot be updated or deleted through
the owner-only endpoints. New comments store only a foreign key to the minimal
Entra user record (tenant ID and object ID).

To use MariaDB outside Compose, set `DATABASE_URL`, for example:

```bash
export DATABASE_URL='mysql+pymysql://user:password@localhost:3306/comments'
make run
```

### Run With Docker

Docker Compose starts the API and a MariaDB database. The API is bound to
`127.0.0.1:8000`:

```bash
make up
make logs
make down
```

Local Compose credentials can be overridden using `MARIADB_DATABASE`,
`MARIADB_USER`, `MARIADB_PASSWORD`, and `MARIADB_ROOT_PASSWORD` environment
variables or a local `.env` file. Set `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`,
`ENTRA_API_AUDIENCE`, and `AZURE_LANGUAGE_ENDPOINT` there as well. The Azure
workload identity requires the container runtime to expose its federated/
managed identity credentials; do not pass client secrets in Compose.

### Azure Provisioning

Terraform provisions a single-tenant Entra API registration and `access_as_user`
scope, an Azure AI Language resource with local key authentication disabled, and
a user-assigned managed identity with the `Cognitive Services User` role. It
also provisions a VNet, private endpoint, and private DNS link for Language;
public network access is disabled by default. Deploy the API into a subnet with
access to this VNet and attach the managed identity before enabling production
traffic. Local Compose cannot access this private endpoint unless its host is
connected to the VNet, for example through a VPN.

```bash
export ARM_SUBSCRIPTION_ID='<subscription-id>'
az login
make terraform-init
make terraform-fmt
make terraform-validate
make terraform-plan
make terraform-apply
terraform -chdir=infra/terraform output
```

Terraform state contains Azure resource identifiers and must be stored in a
protected remote backend for team use; do not commit state or plan files. To
temporarily permit public access for development, explicitly set
`public_network_access_enabled=true`; do not use that setting for production.
PII detection is a preventive control, not a determination of
GDPR compliance. Provide a privacy notice and lawful basis, minimize retention,
and assess false positives and false negatives for your data and locales.

### CI/CD

GitHub Actions runs the test suite and builds the Docker image on pushes to
`main`, pull requests, and manual runs. Pushing a version tag such as `v1.0.0`
also publishes `ghcr.io/<owner>/<repository>:v1.0.0`.

The repository includes a Copilot project agent at
`.github/agents/comments-api.agent.md` for architecture, security, and validation
conventions.

### Disclaimer
This project is building using an agent of Visual Studio Code.

<div align="center">

**Developed by** Linus Regander
**Latest update:** 2026-10-23

</div>