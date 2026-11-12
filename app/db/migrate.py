from pathlib import Path

from sqlalchemy import Connection, inspect, text

from app.config.config import setup
from app.db.database import database_from_config

TRACKING_TABLE = "schema_migrations"
LOCK_NAME = "comments_schema_migrations"
LOCK_TIMEOUT_SECONDS = 60
MISSING_SQL_FILES_FOUND_ERROR = "No .sql files found in directory"
MISSING_MIGRATION_LOCK_ERROR = "Could not acquire the migration lock"

class MigrationRunner:
    def __init__(self, connection: Connection, directory: Path, use_lock: bool) -> None:
        self._connection = connection
        self._directory = directory
        self._use_lock = use_lock

    def run(self) -> list[str]:
        files = sorted(self._directory.glob("*.sql"))
        if not files:
            raise FileNotFoundError(MISSING_SQL_FILES_FOUND_ERROR)

        if self._use_lock:
            self._acquire_lock()
        try:
            applied = self._applied()

            applied_list: list[str] = []

            for file in files:
                if file.name in applied:
                    continue

                self._apply(file)

                applied_list.append(file.name)

            return applied_list
        finally:
            if self._use_lock:
                self._connection.rollback()
                self._release_lock()

    def _applied(self) -> set[str]:
        applied: set[str] = set()

        if inspect(self._connection).has_table(TRACKING_TABLE):
            applied = {
                row[0]
                for row in self._connection.exec_driver_sql(
                    f"SELECT filename FROM {TRACKING_TABLE}"
                )
            }
        self._connection.commit()

        return applied

    def _apply(self, file: Path) -> None:
        for statement in self._statements(file.read_text(encoding="utf-8")):
            self._connection.exec_driver_sql(statement)

        self._connection.execute(text(f"INSERT INTO {TRACKING_TABLE} (filename) VALUES (:filename)"), {"filename": file.name})
        self._connection.commit()

    def _acquire_lock(self) -> None:
        acquired = self._connection.execute(text("SELECT GET_LOCK(:name, :timeout)"), {"name": LOCK_NAME, "timeout": LOCK_TIMEOUT_SECONDS}).scalar()

        if acquired != 1:
            raise RuntimeError(MISSING_MIGRATION_LOCK_ERROR)

    def _release_lock(self) -> None:
        self._connection.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": LOCK_NAME})

    @staticmethod
    def _statements(sql: str) -> list[str]:
        lines = [line for line in sql.splitlines() if not line.strip().startswith("--")]

        return [part.strip() for part in "\n".join(lines).split(";") if part.strip()]

if __name__ == "__main__":
    config = setup()
    database = database_from_config(config.db)

    try:
        with database.engine.connect() as connection:
            runner = MigrationRunner(connection, Path(config.migrator.path), use_lock=config.migrator.use_lock)
            for name in runner.run():
                print(f"applied {name}")
    finally:
        database.dispose()