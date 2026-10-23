"""Table-driven tests for the comments API."""

import unittest
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.comments.router import get_pii_detector
from app.errors import (
    AuthenticationError,
    PiiDetectedError,
    PiiScreeningUnavailableError,
)
from app.main import create_app
from app.pii import PiiDetector
from app.security import EntraPrincipal, get_current_user
from app.users.models import UserRecord


COMMENT_DATA = {"content": "A useful comment"}
UPDATED_DATA = {"content": "An updated comment"}
PRINCIPAL = EntraPrincipal(
    tenant_id="11111111-1111-1111-1111-111111111111",
    object_id="22222222-2222-2222-2222-222222222222",
)


@dataclass(frozen=True)
class ApiCase:
    method: str
    path: str
    expected_status: int
    payload: dict[str, str] | None = None
    setup: tuple[tuple[str, str, dict[str, str]], ...] = ()
    expected_fields: dict[str, str] = field(default_factory=dict)
    expected_list_count: int | None = None
    confirm_deleted: bool = False
    expected_detail: str | None = None
    pii_result: str = "clean"


API_CASES: dict[str, ApiCase] = {
    "push comment": ApiCase(
        method="POST",
        path="/comments",
        payload=COMMENT_DATA,
        expected_status=201,
        expected_fields={**COMMENT_DATA, "user_id": 1},
    ),
    "list comments": ApiCase(
        method="GET",
        path="/comments",
        expected_status=200,
        setup=(("PUT", "/comments/list-seed", COMMENT_DATA),),
        expected_list_count=1,
    ),
    "get comment": ApiCase(
        method="GET",
        path="/comments/get-seed",
        expected_status=200,
        setup=(("PUT", "/comments/get-seed", COMMENT_DATA),),
        expected_fields=COMMENT_DATA,
    ),
    "replace comment": ApiCase(
        method="PUT",
        path="/comments/replace-seed",
        payload=UPDATED_DATA,
        expected_status=200,
        setup=(("PUT", "/comments/replace-seed", COMMENT_DATA),),
        expected_fields=UPDATED_DATA,
    ),
    "put creates missing comment": ApiCase(
        method="PUT",
        path="/comments/new-comment",
        payload=COMMENT_DATA,
        expected_status=200,
        expected_fields=COMMENT_DATA,
    ),
    "delete comment": ApiCase(
        method="DELETE",
        path="/comments/delete-seed",
        expected_status=204,
        setup=(("PUT", "/comments/delete-seed", COMMENT_DATA),),
        confirm_deleted=True,
    ),
    "get missing comment": ApiCase(
        method="GET",
        path="/comments/missing",
        expected_status=404,
        expected_detail="Comment 'missing' not found",
    ),
    "delete missing comment": ApiCase(
        method="DELETE",
        path="/comments/missing",
        expected_status=404,
        expected_detail="Comment 'missing' not found",
    ),
    "reject invalid comment": ApiCase(
        method="POST",
        path="/comments",
        payload={"content": ""},
        expected_status=422,
    ),
    "reject client-supplied author": ApiCase(
        method="POST",
        path="/comments",
        payload={"content": "A useful comment", "author": "Spoofed"},
        expected_status=422,
    ),
    "reject detected personal information": ApiCase(
        method="POST",
        path="/comments",
        payload=COMMENT_DATA,
        expected_status=422,
        expected_detail="Comment contains personal or sensitive information",
        pii_result="pii",
    ),
    "reject personal information on update": ApiCase(
        method="PUT",
        path="/comments/pii-update",
        payload=UPDATED_DATA,
        expected_status=422,
        expected_detail="Comment contains personal or sensitive information",
        pii_result="pii",
    ),
    "fail closed when PII screening is unavailable": ApiCase(
        method="PUT",
        path="/comments/unavailable-screening",
        payload=COMMENT_DATA,
        expected_status=503,
        expected_detail="Azure PII screening is unavailable",
        pii_result="unavailable",
    ),
}


class FakePiiDetector(PiiDetector):
    def __init__(self, result: str) -> None:
        self.result = result
        self.screened: list[str] = []

    def assert_clean(self, content: str) -> None:
        self.screened.append(content)
        if self.result == "pii":
            raise PiiDetectedError()
        if self.result == "unavailable":
            raise PiiScreeningUnavailableError("Azure PII screening is unavailable")


class CommentsApiTests(unittest.TestCase):
    def test_comment_endpoints_table_driven(self) -> None:
        for case_name, case in API_CASES.items():
            with self.subTest(case=case_name):
                engine = create_engine(
                    "sqlite://",
                    connect_args={"check_same_thread": False},
                    poolclass=StaticPool,
                )
                session_factory = sessionmaker(
                    bind=engine,
                    autoflush=False,
                    autocommit=False,
                )

                detector = FakePiiDetector(case.pii_result)
                application = create_app(session_factory)
                application.dependency_overrides[get_current_user] = lambda: PRINCIPAL
                application.dependency_overrides[get_pii_detector] = lambda: detector

                with TestClient(application) as client:
                    for method, path, payload in case.setup:
                        setup_response = client.request(method, path, json=payload)
                        self.assertLess(setup_response.status_code, 300)

                    response = client.request(
                        case.method,
                        case.path,
                        json=case.payload,
                    )
                    self.assertEqual(response.status_code, case.expected_status)

                    if case.expected_detail is not None:
                        self.assertEqual(response.json()["detail"], case.expected_detail)

                    if case.expected_fields:
                        response_body: dict[str, Any] = response.json()
                        for field_name, expected_value in case.expected_fields.items():
                            self.assertEqual(response_body[field_name], expected_value)

                    if case.expected_list_count is not None:
                        self.assertEqual(len(response.json()), case.expected_list_count)

                    if case.confirm_deleted:
                        self.assertEqual(client.get(case.path).status_code, 404)

                engine.dispose()

    def test_only_comment_owner_can_update_or_delete(self) -> None:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        session_factory = sessionmaker(bind=engine)
        detector = FakePiiDetector("clean")
        application = create_app(session_factory)
        current_principal = {"value": PRINCIPAL}
        application.dependency_overrides[get_current_user] = (
            lambda: current_principal["value"]
        )
        application.dependency_overrides[get_pii_detector] = lambda: detector

        with TestClient(application) as client:
            created = client.post("/comments", json=COMMENT_DATA)
            comment_id = created.json()["id"]
            current_principal["value"] = EntraPrincipal(
                tenant_id=PRINCIPAL.tenant_id,
                object_id="33333333-3333-3333-3333-333333333333",
            )

            update_response = client.put(
                f"/comments/{comment_id}",
                json=UPDATED_DATA,
            )
            delete_response = client.delete(f"/comments/{comment_id}")

            self.assertEqual(update_response.status_code, 403)
            self.assertEqual(delete_response.status_code, 403)
            self.assertEqual(detector.screened, [COMMENT_DATA["content"]])

        engine.dispose()

    def test_comment_routes_require_bearer_identity(self) -> None:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        session_factory = sessionmaker(bind=engine)
        with TestClient(create_app(session_factory)) as client:
            response = client.get("/comments")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["www-authenticate"], "Bearer")
        engine.dispose()

    def test_update_rejects_pii_without_changing_existing_comment(self) -> None:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        session_factory = sessionmaker(bind=engine)
        detector = FakePiiDetector("clean")
        application = create_app(session_factory)
        application.dependency_overrides[get_current_user] = lambda: PRINCIPAL
        application.dependency_overrides[get_pii_detector] = lambda: detector

        with TestClient(application) as client:
            created = client.put("/comments/pii-update", json=COMMENT_DATA)
            self.assertEqual(created.status_code, 200)
            detector.result = "pii"

            updated = client.put("/comments/pii-update", json=UPDATED_DATA)
            current = client.get("/comments/pii-update")

            self.assertEqual(updated.status_code, 422)
            self.assertEqual(current.json()["content"], COMMENT_DATA["content"])

        engine.dispose()

    def test_migration_preserves_legacy_comments_without_assigning_owner(self) -> None:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE comments ("
                "id VARCHAR(36) PRIMARY KEY, author VARCHAR(120) NOT NULL, "
                "content TEXT NOT NULL, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            connection.exec_driver_sql(
                "INSERT INTO comments (id, author, content) VALUES (?, ?, ?)",
                ("legacy-comment", "Unverified author", "Legacy content"),
            )

        session_factory = sessionmaker(bind=engine)
        application = create_app(session_factory)
        application.dependency_overrides[get_current_user] = lambda: PRINCIPAL
        application.dependency_overrides[get_pii_detector] = lambda: FakePiiDetector(
            "clean"
        )

        with TestClient(application) as client:
            fetched = client.get("/comments/legacy-comment")
            update = client.put("/comments/legacy-comment", json=UPDATED_DATA)
            legacy_columns = {
                column["name"] for column in inspect(engine).get_columns("comments")
            }

            self.assertEqual(fetched.status_code, 404)
            self.assertEqual(update.status_code, 403)
            self.assertNotIn("author", legacy_columns)

        engine.dispose()

    def test_reads_are_scoped_to_the_authenticated_user(self) -> None:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        session_factory = sessionmaker(bind=engine)
        application = create_app(session_factory)
        detector = FakePiiDetector("clean")
        principal = {"value": PRINCIPAL}
        application.dependency_overrides[get_current_user] = lambda: principal["value"]
        application.dependency_overrides[get_pii_detector] = lambda: detector

        with TestClient(application) as client:
            created = client.post("/comments", json=COMMENT_DATA)
            comment_id = created.json()["id"]
            principal["value"] = EntraPrincipal(
                tenant_id=PRINCIPAL.tenant_id,
                object_id="33333333-3333-3333-3333-333333333333",
            )

            self.assertEqual(client.get(f"/comments/{comment_id}").status_code, 403)
            self.assertEqual(client.get("/comments").json(), [])

        engine.dispose()

    def test_database_restricts_deleting_a_user_with_comments(self) -> None:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        session_factory = sessionmaker(bind=engine)
        application = create_app(session_factory)
        application.dependency_overrides[get_current_user] = lambda: PRINCIPAL
        application.dependency_overrides[get_pii_detector] = lambda: FakePiiDetector(
            "clean"
        )

        with TestClient(application) as client:
            created = client.post("/comments", json=COMMENT_DATA)
            self.assertEqual(created.status_code, 201)

        with session_factory() as session:
            user = session.query(UserRecord).one()
            session.delete(user)
            with self.assertRaises(IntegrityError):
                session.commit()
            session.rollback()

        engine.dispose()

    def test_entra_token_requires_valid_claims_and_delegated_scope(self) -> None:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        token = jwt.encode(
            {
                "aud": "comments-api-client",
                "iss": "https://login.microsoftonline.com/test-tenant/v2.0",
                "tid": "test-tenant",
                "oid": "test-user",
                "scp": "access_as_user",
                "iat": 1_750_000_000,
                "exp": 2_000_000_000,
            },
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key"},
        )

        class FakeSigningKey:
            key = public_key

        class FakeJwksClient:
            def get_signing_key_from_jwt(self, _: str) -> FakeSigningKey:
                return FakeSigningKey()

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token,
        )
        with (
            patch.dict(
                "os.environ",
                {
                    "ENTRA_TENANT_ID": "test-tenant",
                    "ENTRA_CLIENT_ID": "comments-api-client",
                    "ENTRA_REQUIRED_SCOPE": "access_as_user",
                },
            ),
            patch("app.security._jwks_client", return_value=FakeJwksClient()),
        ):
            principal = get_current_user(credentials)

        self.assertEqual(principal, EntraPrincipal("test-tenant", "test-user"))

        token_without_scope = jwt.encode(
            {
                "aud": "comments-api-client",
                "iss": "https://login.microsoftonline.com/test-tenant/v2.0",
                "tid": "test-tenant",
                "oid": "test-user",
                "scp": "other_scope",
                "iat": 1_750_000_000,
                "exp": 2_000_000_000,
            },
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key"},
        )
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token_without_scope,
        )
        with (
            patch.dict(
                "os.environ",
                {
                    "ENTRA_TENANT_ID": "test-tenant",
                    "ENTRA_CLIENT_ID": "comments-api-client",
                    "ENTRA_REQUIRED_SCOPE": "access_as_user",
                },
            ),
            patch("app.security._jwks_client", return_value=FakeJwksClient()),
        ):
            with self.assertRaises(AuthenticationError):
                get_current_user(credentials)


if __name__ == "__main__":
    unittest.main()