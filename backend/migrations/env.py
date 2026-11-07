"""Alembic environment for the local SQLite database."""

from __future__ import annotations

from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.app.core.config import Settings
from backend.app.db.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = config.attributes.get("settings")
if not isinstance(settings, Settings):
    settings = Settings()
database_url = settings.database_url
database_file = Path(database_url.removeprefix("sqlite:///"))
database_file.parent.mkdir(parents=True, exist_ok=True)
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without an Engine, suitable for SQL rendering."""
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run ordered, explicit Alembic upgrades on the configured SQLite file."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"check_same_thread": False},
    )
    with connectable.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
