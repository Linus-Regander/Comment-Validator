"""API tests for the current comments service contract."""

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.config.config import API, Auth, Azure, Config, DB, Migrator, Service
from app.db.database import Base, Database, DatabaseConfig
from app.errors import PiiDetectedError
from app.main import create_app
from app.util.token_validator import AuthConfig, Principal


COMMENT_DATA = {"content": "A useful comment"}
PRINCIPAL = Principal(
    tenant_id="11111111-1111-1111-1111-111111111111",
    object_id="22222222-2222-2222-2222-222222222222",
)


class FakePiiDetector:
    def __init__(self) -> None:
        self.reject = False
        self.screened: list[str] = []

    def assert_clean(self, content: str) -> None:
        self.screened.append(content)
        if self.reject:
            raise PiiDetectedError()

    def close(self) -> None:
        pass


def build_test_config() -> Config:
    return Config(
        db=DB(
            driver="sqlite",
            host="",
            port=1,
            username="",
            password="",
            database="",
            echo=False,
        ),
        migrator=Migrator(path="", run=False, use_lock=False),
        service=Service(host="127.0.0.1", port=8000),
        api=API(prefix="/comments", tags=["Comments"]),
        auth=Auth(
            auth_disabled="true",
            authority="https://login.microsoftonline.com",
            tenant_id=PRINCIPAL.tenant_id,
            client_id="comments-api",
            audience="comments-api",
            scope="access_as_user",
        ),
        azure=Azure(
            language_endpoint="https://language.example.test",
            disabled_pii="true",
        ),
    )


class CommentsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)

        database_path = Path(self.temporary_directory.name) / "comments.db"
        self.database = Database(
            DatabaseConfig(
                url=f"sqlite:///{database_path}",
                connect_args={"check_same_thread": False},
            )
        )
        self.addCleanup(self.database.dispose)
        Base.metadata.create_all(self.database.engine)

        self.principal = {"value": PRINCIPAL}
        self.detector = FakePiiDetector()
        self.application = create_app(
            config=build_test_config(),
            database=self.database,
            auth_config=AuthConfig(
                disabled=True,
                disabled_principal=PRINCIPAL,
            ),
        )
        self.application.dependency_overrides[
            self.application.state.user_dependency
        ] = lambda: self.principal["value"]
        self.application.dependency_overrides[
            self.application.state.pii_dependency
        ] = lambda: self.detector

    def test_create_comment_returns_current_response_shape(self) -> None:
        with TestClient(self.application) as client:
            response = client.post("/comments", json=COMMENT_DATA)

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["content"], COMMENT_DATA["content"])
        self.assertEqual(body["user_id"], PRINCIPAL.object_id)
        self.assertTrue(body["id"])
        self.assertIn("created_at", body)
        self.assertIn("updated_at", body)
        self.assertEqual(self.detector.screened, [COMMENT_DATA["content"]])

    def test_list_and_get_are_scoped_to_the_tenant(self) -> None:
        with TestClient(self.application) as client:
            created = client.post("/comments", json=COMMENT_DATA)
            comment_id = created.json()["id"]

            listed = client.get("/comments")
            fetched = client.get(f"/comments/{comment_id}")
            self.principal["value"] = Principal(
                tenant_id="33333333-3333-3333-3333-333333333333",
                object_id="44444444-4444-4444-4444-444444444444",
            )
            other_tenant_list = client.get("/comments")
            other_tenant_fetch = client.get(f"/comments/{comment_id}")

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["id"], comment_id)
        self.assertEqual(other_tenant_list.status_code, 200)
        self.assertEqual(other_tenant_list.json(), [])
        self.assertEqual(other_tenant_fetch.status_code, 404)

    def test_missing_comment_returns_not_found(self) -> None:
        with TestClient(self.application) as client:
            response = client.get("/comments/missing")

        self.assertEqual(response.status_code, 404)
        self.assertIn("detail", response.json())

    def test_write_schema_rejects_empty_oversized_and_extra_fields(self) -> None:
        invalid_payloads = (
            {"content": ""},
            {"content": "x" * 5001},
            {"content": "A useful comment", "author": "Client supplied"},
        )
        with TestClient(self.application) as client:
            responses = [
                client.post("/comments", json=payload)
                for payload in invalid_payloads
            ]

        self.assertEqual([response.status_code for response in responses], [422] * 3)
        self.assertEqual(self.detector.screened, [])

    def test_detected_pii_rejects_creation(self) -> None:
        self.detector.reject = True
        with TestClient(self.application) as client:
            response = client.post("/comments", json=COMMENT_DATA)
            listed = client.get("/comments")

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"],
            "Comment contains personal or sensitive information",
        )
        self.assertEqual(listed.json(), [])

    def test_owner_can_update_and_delete_comment(self) -> None:
        updated_content = "Updated comment"
        with TestClient(self.application) as client:
            created = client.post("/comments", json=COMMENT_DATA)
            comment_id = created.json()["id"]
            updated = client.put(
                f"/comments/{comment_id}",
                json={"content": updated_content},
            )
            deleted = client.delete(f"/comments/{comment_id}")
            fetched_after_delete = client.get(f"/comments/{comment_id}")

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["content"], updated_content)
        self.assertEqual(updated.json()["user_id"], PRINCIPAL.object_id)
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(fetched_after_delete.status_code, 404)

    def test_update_and_delete_are_limited_to_comment_owner(self) -> None:
        with TestClient(self.application) as client:
            created = client.post("/comments", json=COMMENT_DATA)
            comment_id = created.json()["id"]
            self.principal["value"] = Principal(
                tenant_id=PRINCIPAL.tenant_id,
                object_id="44444444-4444-4444-4444-444444444444",
            )
            forbidden_update = client.put(
                f"/comments/{comment_id}",
                json={"content": "Not the owner"},
            )
            forbidden_delete = client.delete(f"/comments/{comment_id}")
            still_present = client.get(f"/comments/{comment_id}")

            self.principal["value"] = Principal(
                tenant_id="55555555-5555-5555-5555-555555555555",
                object_id=PRINCIPAL.object_id,
            )
            other_tenant_update = client.put(
                f"/comments/{comment_id}",
                json={"content": "Other tenant"},
            )
            other_tenant_delete = client.delete(f"/comments/{comment_id}")

        self.assertEqual(forbidden_update.status_code, 403)
        self.assertEqual(forbidden_delete.status_code, 403)
        self.assertEqual(still_present.status_code, 200)
        self.assertEqual(still_present.json()["content"], COMMENT_DATA["content"])
        self.assertEqual(other_tenant_update.status_code, 404)
        self.assertEqual(other_tenant_delete.status_code, 404)

    def test_comments_require_a_bearer_token_when_auth_is_enabled(self) -> None:
        application = create_app(
            config=build_test_config(),
            database=self.database,
            auth_config=AuthConfig(),
        )
        with TestClient(application) as client:
            response = client.get("/comments")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["www-authenticate"], "Bearer")

    def test_update_and_delete_routes_are_registered(self) -> None:
        with TestClient(self.application) as client:
            paths = client.get("/openapi.json").json()["paths"]

        self.assertIn("put", paths["/comments/{comment_id}"])
        self.assertIn("delete", paths["/comments/{comment_id}"])


if __name__ == "__main__":
    unittest.main()
