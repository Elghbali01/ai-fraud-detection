"""Opt-in API integration using verified Mission 02/03 artifacts and synthetic requests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from backend.app.core.config import Settings
from backend.app.db.session import make_engine
from backend.app.main import create_app
from backend.app.services.artifacts import load_runtime
from fastapi.testclient import TestClient

from fraud_detection.schema import FEATURE_COLUMNS


@pytest.mark.mission04_real_artifacts
def test_verified_artifacts_serve_synthetic_live_api_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify real artifact loading without opening or scoring any dataset rows."""
    if os.environ.get("RUN_MISSION04_ARTIFACT_TESTS") != "1":
        pytest.skip(
            "set RUN_MISSION04_ARTIFACT_TESTS=1 to load verified local Mission 02/03 artifacts"
        )
    root = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "mission04-real-artifacts.sqlite3"
    monkeypatch.setenv("FRAUD_API_DATABASE_PATH", str(database_path))
    config = Config(str(root / "alembic.ini"))
    command.upgrade(config, "head")
    settings = Settings(
        project_root=root,
        database_path=database_path,
        upload_directory=tmp_path / "uploads",
    )
    engine = make_engine(settings.database_url)
    runtime = load_runtime(settings)
    app = create_app(settings, runtime_override=runtime, engine_override=engine)
    with TestClient(app) as client:
        assert client.get("/api/v1/ready").status_code == 200
        values = {feature: 0.0 for feature in FEATURE_COLUMNS}
        local = client.post("/api/v1/predictions", json=values)
        assert local.status_code == 200
        assert local.json()["model_version"] == runtime.bundle.metadata["model_version"]
        shap = client.post(
            "/api/v1/explanations/local",
            json={"features": values, "method": "shap_interventional_log_odds", "top_n": 30},
        )
        assert shap.status_code == 200
        explanation = shap.json()["explanation"]
        assert explanation["output_space"] == "raw_log_odds"
        assert explanation["reconstruction_error"] < 1e-6
        assert explanation["background"]["partition"] == "training"
        assert client.get("/api/v1/explanations/global").status_code == 200
    engine.dispose()
