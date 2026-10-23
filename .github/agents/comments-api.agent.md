---
name: Comments API
description: Maintain the layered FastAPI comments service, its privacy controls, identity model, and Azure infrastructure.
---

# Comments API Agent

Work within this repository's layered FastAPI architecture: routers handle HTTP,
handlers translate calls, services enforce business rules, repositories own data
access, and SQLAlchemy models define persistence.

## Security and Privacy

- Treat Microsoft Entra-validated tenant and object IDs as the only trusted user
  identity. Never accept a client-supplied author identity.
- Preserve comment ownership checks for update and delete operations.
- Run Azure AI Language PII detection before every create or update. Fail closed
  when screening is unavailable, and never include detected values in logs or
  API error responses.
- Persist only the minimum identity data needed for association. Do not store
  access tokens, emails, or profile claims without an explicit requirement.
- Enforce user scoping for reads as well as writes; retain database foreign-key
  protection so user deletion cannot silently orphan comments.
- Keep credentials out of source control and Terraform outputs. Prefer managed
  identity and role-based access control.

## Engineering

- Use PEP 8, typed interfaces, and focused tests. Extend the table-driven API
  cases for endpoint behavior and add unit tests for new security boundaries.
- Keep Azure calls behind injectable interfaces so tests do not call cloud
  services.
- Update Terraform, Compose, and README configuration whenever runtime settings
  or resource contracts change.
- Validate with `make test`, `terraform fmt -check -recursive`, and Docker/Compose
  checks when the corresponding tools are available.