from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from backend.app.core.config import PROJECT_ROOT, Settings
from backend.app.db.initialization import initialize_database
from backend.app.db.models import Base
from backend.app.db.session import make_engine
from sqlalchemy import inspect, text


def _settings(database_path: Path) -> Settings:
    return Settings(database_path=database_path, upload_directory=database_path.parent / "uploads")


def _config(settings: Settings) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.attributes["settings"] = settings
    config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
    return config


def test_initialize_migrates_a_new_database(tmp_path: Path) -> None:
    settings = _settings(tmp_path / "fresh.sqlite3")

    revision = initialize_database(settings)

    engine = make_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            assert revision == "0002_prediction_semantics"
            assert set(inspect(connection).get_table_names()) == set(Base.metadata.tables) | {
                "alembic_version"
            }
            prediction_columns = inspect(connection).get_columns("predictions")
            assert "probability_calibration_status" in {
                column["name"] for column in prediction_columns
            }
            assert "risk_policy_version" in {column["name"] for column in prediction_columns}
    finally:
        engine.dispose()


def test_initialize_adopts_known_legacy_schema_without_losing_rows(tmp_path: Path) -> None:
    settings = _settings(tmp_path / "legacy.sqlite3")
    command.upgrade(_config(settings), "0001_initial_api_schema")
    engine = make_engine(settings.database_url)
    prediction_id = "00000000-0000-0000-0000-000000000001"
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO predictions "
                    "(id, source, created_at, model_version, schema_version, "
                    "fraud_probability, risk_score, risk_tier, predicted_class, "
                    "decision_threshold, decision_status) VALUES "
                    "(:id, 'api', '2026-01-01 00:00:00', 'legacy-model', 'ulb-credit-card-v1', "
                    "0.1, 10.0, 'Low', 0, 0.5, 'not_flagged')"
                ),
                {"id": prediction_id},
            )
            connection.execute(text("DROP TABLE alembic_version"))
    finally:
        engine.dispose()

    revision = initialize_database(settings)

    engine = make_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            assert revision == "0002_prediction_semantics"
            assert connection.execute(text("SELECT COUNT(*) FROM predictions")).scalar_one() == 1
            provenance = connection.execute(
                text(
                    "SELECT probability_calibration_status, risk_policy_version "
                    "FROM predictions WHERE id = :id"
                ),
                {"id": prediction_id},
            ).one()
            assert provenance == ("unknown", "unknown")
    finally:
        engine.dispose()


def test_initialize_rejects_an_unrecognized_schema_before_writing(tmp_path: Path) -> None:
    settings = _settings(tmp_path / "custom.sqlite3")
    engine = make_engine(settings.database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE analyst_owned (id INTEGER PRIMARY KEY)"))
    finally:
        engine.dispose()

    with pytest.raises(RuntimeError, match="not a recognized Mission 04 layout"):
        initialize_database(settings)

    engine = make_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            tables = set(inspect(connection).get_table_names())
            assert tables == {"analyst_owned"}
    finally:
        engine.dispose()
