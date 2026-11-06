"""Opt-in end-to-end checks for trusted real artifacts and development data only."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pytest

from fraud_detection.explainability.data import load_development_partitions
from fraud_detection.explainability.linear import exact_linear_attributions
from fraud_detection.explainability.shap_engine import (
    build_linear_explainer,
    explain_with_shap,
    make_training_background,
)
from fraud_detection.ml.persistence import load_anomaly_artifact, load_model_bundle, sha256_file
from fraud_detection.risk.anomaly_intelligence import load_anomaly_reference
from fraud_detection.schema import FEATURE_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
RUN_REAL = os.environ.get("RUN_MISSION03_REAL_DATA") == "1"


pytestmark = [
    pytest.mark.real_data,
    pytest.mark.mission03_real_data,
    pytest.mark.skipif(not RUN_REAL, reason="set RUN_MISSION03_REAL_DATA=1 to opt in"),
]


def _verified_manifest(path: Path) -> tuple[dict, Path]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    artifact = (ROOT / manifest["artifact_path"]).resolve()
    assert artifact.is_file()
    assert sha256_file(artifact) == manifest["artifact_sha256"]
    return manifest, artifact


def test_real_artifact_explanations_use_development_partitions_only():
    data = load_development_partitions(
        ROOT / "data/raw/creditcard.csv",
        ROOT / "reports/ml/split_manifest.json",
    )
    assert len(data.training) == 199_364
    assert len(data.validation) == 42_722
    assert data.dataset_sha256 == "76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89"
    assert data.training.index.max() < data.validation.index.min()
    assert data.validation.index.max() == 242_085

    model_manifest, classifier_path = _verified_manifest(ROOT / "reports/ml/artifact_manifest.json")
    anomaly_manifest, anomaly_path = _verified_manifest(
        ROOT / "reports/ml/anomaly_artifact_manifest.json"
    )
    bundle = load_model_bundle(classifier_path, expected_sha256=model_manifest["artifact_sha256"])
    anomaly = load_anomaly_artifact(
        anomaly_path, expected_sha256=anomaly_manifest["artifact_sha256"]
    )
    assert bundle.threshold == model_manifest["threshold"] == 0.1835921396957453

    validation_features = data.validation.loc[
        : data.validation.index.min() + 15, list(FEATURE_COLUMNS)
    ]
    linear = exact_linear_attributions(bundle, validation_features)
    assert np.max(linear.reconstruction_error) < 1e-10
    background, metadata = make_training_background(
        data.training.loc[:, list(FEATURE_COLUMNS)],
        sample_size=512,
        random_state=17,
        dataset_sha256=data.dataset_sha256,
        split_manifest_id=data.split_manifest_id,
    )
    explainer, _ = build_linear_explainer(bundle, background, random_state=17)
    shap_result = explain_with_shap(
        bundle,
        explainer,
        validation_features.iloc[:8],
        background_metadata=metadata,
    )
    assert shap_result.additivity["passed"]
    assert shap_result.additivity["maximum_absolute_error"] < 1e-7

    local_reference = load_anomaly_reference(ROOT / "reports/risk/anomaly_reference_manifest.json")
    assert local_reference.metadata["source_partition"] == "training"
    assert local_reference.metadata["dataset_sha256"] == data.dataset_sha256
    assert anomaly.metadata.get("feature_columns", list(FEATURE_COLUMNS)) == list(FEATURE_COLUMNS)

    results_path = ROOT / "reports/risk/mission03_results.json"
    results = json.loads(results_path.read_text(encoding="utf-8"))
    assert results["dataset_sha256"] == data.dataset_sha256
    assert results["partitions"]["final_test_rows_loaded"] == 0
    assert results["partitions"]["final_test_labels_loaded"] == 0
    assert results["shap"]["validation_additivity"]["passed"] is True
    assert results["supervised_anomaly_comparison"]["partition"] == "validation"
    assert (ROOT / "reports/explainability/GLOBAL_EXPLAINABILITY.md").is_file()
