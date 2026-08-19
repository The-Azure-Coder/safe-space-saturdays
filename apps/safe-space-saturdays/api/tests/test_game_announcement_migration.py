from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_game_announcements_repair_the_pre_media_production_schema() -> None:
    migration_path = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "20260818_0024_game_announcements.py"
    )
    spec = spec_from_file_location("game_announcement_migration", migration_path)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, role VARCHAR(30) NOT NULL)"
        )
        connection.exec_driver_sql(
            """
            CREATE TABLE announcements (
                id INTEGER PRIMARY KEY,
                title VARCHAR(160) NOT NULL,
                body TEXT NOT NULL,
                is_published BOOLEAN NOT NULL DEFAULT true,
                author_id INTEGER NOT NULL
            )
            """
        )
        connection.exec_driver_sql("INSERT INTO users (id, role) VALUES (1, 'admin')")
        migration.op = Operations(MigrationContext.configure(connection))

        migration.upgrade()

        columns = {column["name"] for column in sa.inspect(connection).get_columns("announcements")}
        assert {"image_url", "cta_label", "cta_path"}.issubset(columns)
        announcements = connection.execute(
            sa.text(
                "SELECT title, image_url, cta_label, cta_path FROM announcements ORDER BY title"
            )
        ).all()
        assert announcements == [
            (
                "ABC Fast or Slow is here",
                "/assets/game-abc-fast-slow.png",
                "Play ABC Fast or Slow",
                "/games",
            ),
            (
                "Checkers has arrived",
                "/assets/game-checkers.png",
                "Play Checkers",
                "/games",
            ),
        ]
