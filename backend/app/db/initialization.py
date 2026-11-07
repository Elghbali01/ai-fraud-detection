"""Safely initialize the local API database at the current Alembic revision."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect

from backend.app.core.config import PROJECT_ROOT, Settings
from backend.app.db.models import Base
from backend.app.db.session import make_engine

_BASE_REVISION = "0001_initial_api_schema"
_KNOWN_ADDED_COLUMNS = {
    ("predictions", "probability_calibration_status"),
    ("predictions", "risk_policy_version"),
}


def _alembic_config(settings: Settings, config_path: Path) -> Config:
    config = Config(str(config_path))
    config.attributes["settings"] = settings
    config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
    return config


def _matches_unversioned_base_schema(table_names: set[str], differences: list[Any]) -> bool:
    """Recognize only the complete initial schema missing the two known later fields."""
    if table_names != set(Base.metadata.tables):
        return False
    added_columns = {
        (difference[2], difference[3].name)
        for difference in differences
        if len(difference) == 4 and difference[0] == "add_column"
    }
    return len(differences) == len(_KNOWN_ADDED_COLUMNS) and added_columns == _KNOWN_ADDED_COLUMNS


def initialize_database(
    settings: Settings | None = None, *, config_path: Path | None = None
) -> str:
    """Migrate a new or compatible legacy database without replacing existing data.

    An unversioned database is stamped only when its complete schema matches the
    current metadata or the known Mission 04 base schema. Any other unversioned
    schema is rejected before migration writes occur.
    """
    effective_settings = settings or Settings()
    effective_config_path = config_path or PROJECT_ROOT / "alembic.ini"
    config = _alembic_config(effective_settings, effective_config_path)
    script = ScriptDirectory.from_config(config)
    head = script.get_current_head()
    if head is None:
        raise RuntimeError("Alembic has no single current head revision")

    engine = make_engine(effective_settings.database_url)
    stamp_revision: str | None = None
    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            table_names = set(inspector.get_table_names()) - {"alembic_version"}
            migration_context = MigrationContext.configure(connection)
            current_revision = migration_context.get_current_revision()
            if current_revision is None and table_names:
                differences = compare_metadata(migration_context, Base.metadata)
                if not differences:
                    stamp_revision = head
                elif _matches_unversioned_base_schema(table_names, differences):
                    stamp_revision = _BASE_REVISION
                else:
                    raise RuntimeError(
                        "Existing unversioned database schema is not a recognized Mission 04 "
                        "layout; no schema changes were applied. Back up and inspect it before "
                        "migrating."
                    )

        if stamp_revision is not None:
            command.stamp(config, stamp_revision)
        command.upgrade(config, head)
        with engine.connect() as connection:
            final_context = MigrationContext.configure(connection)
            final_revision = final_context.get_current_revision()
            remaining_differences = compare_metadata(final_context, Base.metadata)
        if final_revision != head or remaining_differences:
            raise RuntimeError("Database migration did not produce the expected schema")
        return head
    finally:
        engine.dispose()


def main() -> int:
    """Initialize the configured local API database from PowerShell."""
    revision = initialize_database()
    print(f"Database schema is at Alembic revision {revision}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
