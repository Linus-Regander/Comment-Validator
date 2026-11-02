from pathlib import Path

from sqlalchemy import Connection
from app.config.config import setup
from app.db.database import Database, DatabaseConfig


def _statements(sql: str) -> list[str]:
    lines = [line for line in sql.splitlines() if not line.strip().startswith("--")]

    return [part.strip() for part in "\n".join(lines).split(";") if part.strip()]

def apply_migrations(connection: Connection, directory: Path) -> list[str]:
    files = sorted(directory.glob("*.sql"))
    if not files:
        raise FileNotFoundError(f"No .sql files found in {directory}")

    for file in files:
        for statement in _statements(file.read_text(encoding="utf-8")):
            connection.exec_driver_sql(statement)

    return [file.name for file in files]


if __name__ == "__main__":
    config = setup()
    database = Database(DatabaseConfig(url=config.db.url, echo=config.db.echo))
    try:
        with database.engine.begin() as connection:
            for name in apply_migrations(connection, Path(config.migrator.path)):
                print(f"applied {name}")
    finally:
        database.dispose()