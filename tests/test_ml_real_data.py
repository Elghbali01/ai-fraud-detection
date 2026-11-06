"""Opt-in full-data ML workflow integration against verified local ULB records."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from fraud_detection.loading import load_ulb_csv
from fraud_detection.ml.baselines import make_candidates
from fraud_detection.ml.preprocessing import validate_features
from fraud_detection.ml.splitting import create_temporal_split
from fraud_detection.provenance import has_verified_kaggle_provenance, sha256_file
from fraud_detection.schema import FEATURE_COLUMNS, TARGET_COLUMN

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REAL_DATASET = PROJECT_ROOT / "data" / "raw" / "creditcard.csv"


@pytest.mark.real_data
def test_real_data_models_artifacts_and_reports(tmp_path):
    """Smoke-test full real-data splitting and training without opening the final-test labels."""
    if os.environ.get("RUN_REAL_DATA_TESTS") != "1":
        pytest.skip("set RUN_REAL_DATA_TESTS=1 to run the full local ULB ML integration check")
    if not has_verified_kaggle_provenance(REAL_DATASET):
        pytest.skip("verified local ULB CSV and provenance are unavailable")

    frame = load_ulb_csv(REAL_DATASET, strict_columns=True)
    split = create_temporal_split(frame, dataset_sha256=sha256_file(REAL_DATASET))
    train = frame.iloc[split.train_positions]
    validation = frame.iloc[split.validation_positions]
    estimator = next(
        item.estimator for item in make_candidates() if item.name == "logistic_balanced_c1"
    )
    estimator.fit(
        train.loc[:, list(FEATURE_COLUMNS)],
        train[TARGET_COLUMN],
    )
    probabilities = estimator.predict_proba(
        validate_features(validation.loc[:, list(FEATURE_COLUMNS)])
    )[:, 1]
    assert split.manifest["row_count"] == 284_807
    assert len(validation) == 42_722
    assert split.manifest["partitions"]["test"]["class_counts"]["1"] == 52
    assert (
        split.manifest["duplicate_audit"]["feature_vectors"]["cross_partition_signature_groups"]
        == 0
    )
    assert len(probabilities) == len(validation)
    assert probabilities.min() >= 0
    assert probabilities.max() <= 1
