"""Synthetic Mission 04 API tests that never load the ULB dataset or model files."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from alembic import command
from alembic.config import Config
from backend.app.core.config import Settings
from backend.app.db.models import AnalysisJob, Upload, new_id, utcnow
from backend.app.db.session import make_engine, make_session_factory
from backend.app.main import create_app
from backend.app.services.artifacts import RuntimeServices
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import inspect, text

from fraud_detection.explainability.local_explanations import ExplainabilityService
from fraud_detection.ml.anomaly import anomaly_scores, fit_isolation_forest
from fraud_detection.ml.persistence import ModelBundle
from fraud_detection.ml.preprocessing import make_logistic_pipeline
from fraud_detection.risk.anomaly_intelligence import AnomalyScoreReference
from fraud_detection.risk.scoring import RiskScoringService
from fraud_detection.risk.service import RiskIntelligenceService
from fraud_detection.risk.tiers import RiskTierPolicy
from fraud_detection.schema import FEATURE_COLUMNS, SCHEMA_VERSION


def _runtime() -> RuntimeServices:
    """Fit small throwaway models on synthetic records for deterministic route tests."""
    rng = np.random.default_rng(41)
    values = rng.normal(size=(128, len(FEATURE_COLUMNS)))
    features = pd.DataFrame(values, columns=list(FEATURE_COLUMNS))
    labels = ((values[:, 1] - 0.5 * values[:, 2]) > 0).astype("int8")
    estimator = make_logistic_pipeline(c_value=1.0, class_weight="balanced")
    estimator.fit(features, labels)
    bundle = ModelBundle(
        estimator=estimator,
        calibrator=None,
        threshold=0.5,
        metadata={
            "model_version": "synthetic-api-test-v1",
            "schema_version": SCHEMA_VERSION,
            "feature_columns": list(FEATURE_COLUMNS),
            "probability_calibration_status": "synthetic test estimator output",
        },
    )
    training = features.copy()
    training["Class"] = labels
    anomaly = fit_isolation_forest(training, random_state=41)
    anomaly.metadata["model_version"] = "synthetic-anomaly-test-v1"
    scores = anomaly_scores(anomaly, features)
    reference = AnomalyScoreReference(
        sorted_scores=np.sort(scores),
        metadata={"source_partition": "synthetic test data", "reference_rows": len(scores)},
    )
    policy = RiskTierPolicy(
        policy_version="synthetic-risk-policy-v1",
        low_upper_exclusive=0.1,
        decision_threshold=0.5,
        critical_lower_inclusive=0.8,
        validation_quantile_low=0.95,
        validation_quantile_critical=0.75,
        validation_rows=100,
        validation_flagged_rows=20,
    )
    scoring = RiskScoringService(bundle, policy, max_batch_size=1_000)
    explanation = ExplainabilityService(bundle)
    intelligence = RiskIntelligenceService(
        scoring,
        explanation_service=explanation,
        anomaly_experiment=anomaly,
        anomaly_reference=reference,
    )
    return RuntimeServices(
        bundle=bundle,
        anomaly_experiment=anomaly,
        anomaly_reference=reference,
        policy=policy,
        scoring=scoring,
        explainability=explanation,
        intelligence=intelligence,
        global_summary=[
            {
                "feature": feature,
                "mean_abs_shap_log_odds": float(index + 1),
                "mean_shap_log_odds": 0.0,
            }
            for index, feature in enumerate(FEATURE_COLUMNS)
        ],
        artifact_metadata={"source": "synthetic test only"},
        shap_metadata={},
    )


@pytest.fixture
def api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    database_path = tmp_path / "api.sqlite3"
    monkeypatch.setenv("FRAUD_API_DATABASE_PATH", str(database_path))
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    settings = Settings(
        project_root=Path(__file__).resolve().parents[1],
        database_path=database_path,
        upload_directory=tmp_path / "uploads",
        max_upload_bytes=64 * 1024,
        max_csv_rows=10,
        csv_chunk_rows=2,
        max_batch_rows=10,
        max_explanation_batch=5,
        max_json_body_bytes=1_024,
    )
    engine = make_engine(settings.database_url)
    app = create_app(settings, runtime_override=_runtime(), engine_override=engine)
    with TestClient(app) as client:
        yield client, engine, settings
    engine.dispose()


def _features(value: float = 0.0) -> dict[str, float]:
    return {feature: value for feature in FEATURE_COLUMNS}


def _csv_bytes(rows: list[dict[str, float]] | None = None) -> bytes:
    records = rows or [_features(), _features(0.25)]
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(FEATURE_COLUMNS), lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return stream.getvalue().encode("utf-8")


def test_local_config_requires_loopback_and_explicit_cors_origins() -> None:
    with pytest.raises(ValidationError):
        Settings(host="0.0.0.0")
    with pytest.raises(ValidationError):
        Settings(cors_origins=("*",))
    assert Settings(host="127.0.0.1").host == "127.0.0.1"


def test_liveness_remains_available_when_database_schema_is_not_migrated(tmp_path: Path) -> None:
    settings = Settings(
        project_root=Path(__file__).resolve().parents[1],
        database_path=tmp_path / "unmigrated.sqlite3",
        upload_directory=tmp_path / "uploads",
    )
    engine = make_engine(settings.database_url)
    app = create_app(settings, runtime_override=_runtime(), engine_override=engine)
    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 200
        ready = client.get("/api/v1/ready")
        assert ready.status_code == 503
        assert ready.json()["error"] == "database_schema_unavailable"
    engine.dispose()


def test_alembic_migrations_commit_revision_and_are_repeatable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "migrated.sqlite3"
    monkeypatch.setenv("FRAUD_API_DATABASE_PATH", str(database_path))
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    engine = make_engine(Settings(database_path=database_path).database_url)
    try:
        with engine.connect() as connection:
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
        columns = {column["name"] for column in inspect(engine).get_columns("predictions")}
        assert revision == "0002_prediction_semantics"
        assert "probability_calibration_status" in columns
        assert "risk_policy_version" in columns
    finally:
        engine.dispose()


def test_startup_marks_interrupted_analysis_as_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "interrupted.sqlite3"
    monkeypatch.setenv("FRAUD_API_DATABASE_PATH", str(database_path))
    command.upgrade(Config(str(root / "alembic.ini")), "head")
    settings = Settings(
        project_root=root,
        database_path=database_path,
        upload_directory=tmp_path / "uploads",
    )
    engine = make_engine(settings.database_url)
    session = make_session_factory(engine)()
    upload_id = new_id()
    analysis_id = new_id()
    session.add(
        Upload(
            id=upload_id,
            storage_name=f"{upload_id}.csv",
            sha256="0" * 64,
            size_bytes=1,
            row_count=1,
            created_at=utcnow(),
        )
    )
    session.add(
        AnalysisJob(
            id=analysis_id,
            upload_id=upload_id,
            status="running",
            requested_rows=1,
            processed_rows=0,
            created_at=utcnow(),
        )
    )
    session.commit()
    session.close()
    app = create_app(settings, runtime_override=_runtime(), engine_override=engine)
    try:
        with TestClient(app) as client:
            analysis = client.get(f"/api/v1/analyses/{analysis_id}").json()
            assert analysis["status"] == "failed"
            assert analysis["failure_code"] == "analysis_interrupted_by_restart"
    finally:
        engine.dispose()


def test_prediction_explanation_risk_history_and_request_safety(api) -> None:
    client, engine, _settings = api
    feature_values = _features()
    response = client.post(
        "/api/v1/predictions",
        json=feature_values,
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["model_version"] == "synthetic-api-test-v1"
    assert result["probability_calibration_status"] == "synthetic test estimator output"
    assert result["risk_policy_version"] == "synthetic-risk-policy-v1"
    assert 0 <= result["fraud_probability"] <= 1
    assert result["anomaly"]["score_is_probability"] is False
    assert result["record_id"]
    assert result["timestamp"].endswith(("+00:00", "Z"))
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["x-request-id"]

    batch = client.post(
        "/api/v1/predictions/batch",
        json={"transactions": [feature_values, _features(0.1)]},
    )
    assert batch.status_code == 200
    assert batch.json()["count"] == 2

    explanation = client.post(
        "/api/v1/explanations/local",
        json={"features": feature_values, "method": "linear_log_odds", "top_n": 30},
    )
    assert explanation.status_code == 200
    assert explanation.json()["explanation"]["output_space"] == "raw_log_odds"
    assert explanation.json()["explanation"]["calibrated_probability_additivity_claim"] is False

    global_result = client.get("/api/v1/explanations/global")
    assert global_result.status_code == 200
    assert global_result.json()["output_space"] == "raw_log_odds"
    assert len(global_result.json()["features"]) == 30

    priority = client.post(
        "/api/v1/risk/prioritize",
        json={"transactions": [feature_values, _features(-0.25)], "top_k": 1},
    )
    assert priority.status_code == 200
    assert priority.json()["selected_count"] == 1
    assert priority.json()["priority_policy"]["budget"] == {"kind": "count", "requested": 1}
    percentage_priority = client.post(
        "/api/v1/risk/prioritize",
        json={"transactions": [feature_values, _features(-0.25)], "budget_percentage": 1},
    )
    assert percentage_priority.status_code == 200
    assert percentage_priority.json()["selected_count"] == 1

    anomaly = client.post("/api/v1/anomalies/score", json={"transactions": [feature_values]})
    assert anomaly.status_code == 200
    assert anomaly.json()["fraud_probability_included"] is False

    record_id = result["record_id"]
    history_item = client.get(f"/api/v1/history/{record_id}")
    assert history_item.status_code == 200
    assert history_item.json()["risk_policy_version"] == "synthetic-risk-policy-v1"
    history = client.get("/api/v1/history?limit=1&offset=0")
    assert history.status_code == 200
    assert history.json()["total"] >= 3
    history_filtered = client.get(
        "/api/v1/history?model_version=synthetic-api-test-v1&sort_order=asc"
    )
    assert history_filtered.status_code == 200
    assert history_filtered.json()["total"] == history.json()["total"]
    assert history_filtered.json()["sort_order"] == "asc"

    invalid = client.post("/api/v1/predictions", json={**feature_values, "Class": 0})
    assert invalid.status_code == 422
    assert "Class" not in invalid.text
    non_numeric = client.post("/api/v1/predictions", json={**feature_values, "V1": "1.2"})
    assert non_numeric.status_code == 422
    non_finite = client.post(
        "/api/v1/predictions",
        content=json.dumps({**feature_values, "V1": float("inf")}),
        headers={"Content-Type": "application/json"},
    )
    assert non_finite.status_code == 422
    not_found = client.get("/api/v1/history/not-a-record")
    assert not_found.status_code == 404
    assert "detail" not in not_found.json()
    assert len(inspect(engine).get_columns("predictions")) < len(FEATURE_COLUMNS)
    prediction_columns = {column["name"] for column in inspect(engine).get_columns("predictions")}
    assert not set(FEATURE_COLUMNS).intersection(prediction_columns)
    assert "Class" not in prediction_columns
    openapi = client.get("/openapi.json").json()
    error_schema = openapi["paths"]["/api/v1/predictions"]["post"]["responses"]["422"]
    assert "ApiErrorResponse" in error_schema["content"]["application/json"]["schema"]["$ref"]


def test_csv_upload_analysis_summary_history_and_investigation_workflow(api) -> None:
    client, _engine, settings = api
    upload_response = client.post(
        "/api/v1/uploads/csv",
        files={"file": (r"client path\creditcard.csv", _csv_bytes(), "text/csv")},
    )
    assert upload_response.status_code == 200
    upload = upload_response.json()
    assert upload["row_count"] == 2
    assert len(upload["sha256"]) == 64
    assert "client" not in str(list(settings.upload_directory.iterdir()))

    analysis_response = client.post("/api/v1/analyses", json={"upload_id": upload["upload_id"]})
    assert analysis_response.status_code == 200
    analysis = analysis_response.json()
    assert analysis["status"] == "completed"
    assert analysis["processed_rows"] == 2
    assert analysis["summary"]["labels_present"] is False
    assert analysis["summary"]["precision_recall_computed"] is False
    assert analysis["summary"]["flagged_percentage"] >= 0
    assert analysis["summary"]["created_at"].endswith(("+00:00", "Z"))
    assert analysis["summary"]["model_version"] == "synthetic-api-test-v1"
    assert "precision" not in analysis["summary"]

    assert client.get(f"/api/v1/analyses/{analysis['analysis_id']}").status_code == 200
    assert client.get("/api/v1/analyses?limit=5").json()["count"] == 1
    summary = client.get(f"/api/v1/analyses/{analysis['analysis_id']}/summary")
    assert summary.json()["summary"]["rows"] == 2
    results = client.get(f"/api/v1/analyses/{analysis['analysis_id']}/results?limit=1")
    assert results.status_code == 200
    assert results.json()["count"] == 1
    assert "features" not in results.json()["results"][0]

    history_response = client.get("/api/v1/history?limit=20")
    filtered_history = client.get(f"/api/v1/history?analysis_id={analysis['analysis_id']}")
    assert filtered_history.status_code == 200
    assert filtered_history.json()["total"] == 2
    analysis_record = next(
        item
        for item in history_response.json()["results"]
        if item["analysis_id"] == analysis["analysis_id"]
    )
    created = client.post(
        "/api/v1/investigations",
        json={
            "prediction_id": analysis_record["record_id"],
            "title": "Review synthetic model alert",
            "reason": "Synthetic API workflow test",
        },
    )
    assert created.status_code == 200
    investigation_id = created.json()["investigation_id"]
    updated = client.patch(
        f"/api/v1/investigations/{investigation_id}",
        json={"status": "In Review", "outcome": "Unconfirmed"},
    )
    assert updated.status_code == 200
    assert updated.json()["outcome_is_ground_truth"] is False
    note = client.post(
        f"/api/v1/investigations/{investigation_id}/notes",
        json={"body": "Manually checked the synthetic example."},
    )
    assert note.status_code == 200
    detail = client.get(f"/api/v1/investigations/{investigation_id}")
    assert detail.status_code == 200
    assert len(detail.json()["notes"]) == 1
    assert len(detail.json()["events"]) == 4
    assert client.get("/api/v1/investigations?status=In%20Review").json()["count"] == 1

    closed = client.patch(f"/api/v1/investigations/{investigation_id}", json={"status": "Closed"})
    assert closed.status_code == 200
    reopened = client.patch(f"/api/v1/investigations/{investigation_id}", json={"status": "Open"})
    assert reopened.status_code == 409

    deleted = client.delete(f"/api/v1/analyses/{analysis['analysis_id']}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
    assert not (settings.upload_directory / f"{upload['upload_id']}.csv").exists()
    assert client.get(f"/api/v1/analyses/{analysis['analysis_id']}").status_code == 404


@pytest.mark.parametrize(
    ("content", "expected_code"),
    [
        (b"\n", "feature_schema_mismatch"),
        (_csv_bytes().replace(b"Amount", b"Class"), "target_column_forbidden"),
        (_csv_bytes().replace(b"Amount", b"V1"), "duplicate_headers"),
        (_csv_bytes().replace(b"Amount", b"extra"), "feature_schema_mismatch"),
        (_csv_bytes([_features(float("nan"))]), "non_finite_value"),
        (_csv_bytes([_features(float("inf"))]), "non_finite_value"),
        (b",".join(name.encode() for name in FEATURE_COLUMNS) + b'\n"broken', "malformed_csv"),
    ],
)
def test_csv_rejects_invalid_or_target_bearing_files(
    api, content: bytes, expected_code: str
) -> None:
    client, _engine, _settings = api
    response = client.post(
        "/api/v1/uploads/csv",
        files={"file": ("unsafe.csv", content, "text/csv")},
    )
    assert response.status_code == 422
    assert response.json()["error"] == expected_code
    assert "unsafe.csv" not in response.text


def test_csv_byte_and_row_limits_are_enforced(api) -> None:
    client, _engine, _settings = api
    oversized_json_body = client.request(
        "GET",
        "/api/v1/health",
        content=b"x" * 1_025,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert oversized_json_body.status_code == 413
    assert oversized_json_body.headers["x-request-id"]

    too_large = client.post(
        "/api/v1/uploads/csv",
        files={"file": ("large.csv", b"x" * (64 * 1024 + 1), "text/csv")},
    )
    assert too_large.status_code == 413
    assert too_large.json()["error"] == "upload_limit_exceeded"

    row_limited = client.post(
        "/api/v1/uploads/csv",
        files={
            "file": (
                "too-many.csv",
                _csv_bytes([_features() for _ in range(11)]),
                "text/csv",
            )
        },
    )
    assert row_limited.status_code == 422
    assert row_limited.json()["error"] == "row_limit_exceeded"


def test_csv_upload_rejects_unsupported_media_type(api) -> None:
    client, _engine, settings = api
    response = client.post(
        "/api/v1/uploads/csv",
        files={"file": ("payload.txt", _csv_bytes(), "text/plain")},
    )
    assert response.status_code == 415
    assert response.json()["error"] == "unsupported_media_type"
    assert response.json()["timestamp"]
    assert list(settings.upload_directory.iterdir()) == []
