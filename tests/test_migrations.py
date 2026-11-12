import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine, inspect

from app.db.migrate import MigrationRunner


class MigrationRunnerTests(unittest.TestCase):
    def test_run_applies_migrations_once_in_filename_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            (directory / "001_create_records.sql").write_text(
                "CREATE TABLE records (id INTEGER PRIMARY KEY);",
                encoding="utf-8",
            )
            (directory / "000_create_migration_table.sql").write_text(
                "CREATE TABLE schema_migrations (filename TEXT PRIMARY KEY);",
                encoding="utf-8",
            )

            engine = create_engine(f"sqlite:///{directory / 'test.db'}")
            try:
                with engine.connect() as connection:
                    runner = MigrationRunner(connection, directory, use_lock=False)

                    first_run = runner.run()
                    second_run = runner.run()
                    tables = set(inspect(connection).get_table_names())
                    applied = {
                        row[0]
                        for row in connection.exec_driver_sql(
                            "SELECT filename FROM schema_migrations"
                        )
                    }

                self.assertEqual(
                    first_run,
                    ["000_create_migration_table.sql", "001_create_records.sql"],
                )
                self.assertEqual(second_run, [])
                self.assertTrue({"schema_migrations", "records"} <= tables)
                self.assertEqual(applied, set(first_run))
            finally:
                engine.dispose()

    def test_run_requires_at_least_one_sql_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            engine = create_engine(f"sqlite:///{directory / 'test.db'}")
            try:
                with engine.connect() as connection:
                    runner = MigrationRunner(connection, directory, use_lock=False)

                    with self.assertRaisesRegex(
                        FileNotFoundError,
                        "No \\.sql files found in directory",
                    ):
                        runner.run()
            finally:
                engine.dispose()


if __name__ == "__main__":
    unittest.main()
