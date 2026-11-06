"""Schema-validated inference and trusted local artifact round trips."""

from __future__ import annotations

import json

import pytest
import sklearn

from fraud_detection.exceptions import ArtifactError, InferenceInputError
from fraud_detection.ml.baselines import make_candidates
from fraud_detection.ml.inference import predict_batch, predict_one
from fraud_detection.ml.persistence import (
    ModelBundle,
    load_model_bundle,
    save_model_bundle,
    verify_artifact_manifest,
)
from fraud_detection.ml.preprocessing import validate_features
from fraud_detection.schema import FEATURE_COLUMNS
from tests.ml_helpers import make_transaction_frame


def _fitted_bundle():
    frame = make_transaction_frame(120)
    candidate = make_candidates()[1]
    candidate.estimator.fit(frame.loc[:, list(FEATURE_COLUMNS)], frame["Class"])
    return ModelBundle(
        estimator=candidate.estimator,
        calibrator=None,
        threshold=0.25,
        metadata={
            "model_version": "synthetic-test-v1",
            "schema_version": "ulb-credit-card-v1",
            "feature_columns": list(FEATURE_COLUMNS),
            "scikit_learn_version": sklearn.__version__,
            "probability_calibration_status": "uncalibrated estimator output",
        },
    ), frame


def test_feature_validation_orders_columns_and_rejects_invalid_schema():
    bundle, frame = _fitted_bundle()
    del bundle
    reversed_features = frame.loc[:, list(reversed(FEATURE_COLUMNS))]
    assert tuple(validate_features(reversed_features).columns) == FEATURE_COLUMNS
    with pytest.raises(InferenceInputError, match="missing"):
        validate_features(reversed_features.drop(columns=[FEATURE_COLUMNS[0]]))
    with pytest.raises(InferenceInputError, match="unexpected"):
        validate_features(reversed_features.assign(extra=1.0))
    with pytest.raises(InferenceInputError, match="Target column"):
        validate_features(frame.loc[:, list(FEATURE_COLUMNS) + ["Class"]])
    with pytest.raises(InferenceInputError, match="non-finite"):
        validate_features(frame.loc[:, list(FEATURE_COLUMNS)].assign(Time=float("nan")))


def test_batch_and_single_inference_are_stable_and_thresholded(tmp_path):
    bundle, frame = _fitted_bundle()
    features = frame.loc[:4, list(reversed(FEATURE_COLUMNS))]
    before = predict_batch(bundle, features)
    artifact_path = tmp_path / "model.joblib"
    manifest = save_model_bundle(bundle, artifact_path)
    assert verify_artifact_manifest(manifest)
    loaded = load_model_bundle(artifact_path, expected_sha256=manifest["artifact_sha256"])
    after = predict_batch(loaded, features)
    assert before["fraud_probability"].tolist() == after["fraud_probability"].tolist()
    assert after["predicted_class"].isin([0, 1]).all()
    assert after["decision_threshold"].eq(0.25).all()
    response = predict_one(loaded, features.iloc[0].to_dict())
    assert 0 <= response["fraud_probability"] <= 1
    assert response["model_version"] == "synthetic-test-v1"
    with pytest.raises(ValueError, match="exactly one"):
        predict_one(loaded, features)

    artifact_path.write_bytes(artifact_path.read_bytes() + b"tamper")
    assert not verify_artifact_manifest(manifest)
    with pytest.raises(ArtifactError, match="checksum"):
        load_model_bundle(artifact_path, expected_sha256=manifest["artifact_sha256"])


def test_artifact_manifest_records_schema_and_versions(tmp_path):
    bundle, _ = _fitted_bundle()
    manifest = save_model_bundle(bundle, tmp_path / "model.joblib")
    sidecar = json.loads((tmp_path / "model.manifest.json").read_text(encoding="utf-8"))
    assert manifest["artifact_sha256"] == sidecar["artifact_sha256"]
    assert manifest["feature_columns"] == list(FEATURE_COLUMNS)
    assert manifest["scikit_learn_version"] == sklearn.__version__


def test_registry_is_append_only(tmp_path):
    from fraud_detection.ml.registry import append_experiment

    path = tmp_path / "registry.json"
    record = {"experiment_id": "unique-1", "model_family": "test"}
    append_experiment(path, record)
    with pytest.raises(ValueError, match="already exists"):
        append_experiment(path, record)
