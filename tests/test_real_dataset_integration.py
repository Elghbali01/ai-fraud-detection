"""Opt-in checks against the locally acquired ULB CSV."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pytest

from fraud_detection.loading import load_ulb_csv
from fraud_detection.provenance import (
    KAGGLE_DATASET_ID,
    has_verified_kaggle_provenance,
    sha256_file,
)
from fraud_detection.reporting import generate_eda_artifacts
from fraud_detection.schema import EXPECTED_COLUMNS, SCHEMA_VERSION, validate_ulb_frame

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REAL_DATASET = PROJECT_ROOT / "data" / "raw" / "creditcard.csv"
PROVENANCE_PATH = REAL_DATASET.parent / "dataset-provenance.json"


@pytest.mark.real_data
def test_real_ulb_dataset_integrity_and_report(tmp_path):
    """Validate provenance, scientific invariants, and report artifacts for ULB data."""
    if os.environ.get("RUN_REAL_DATA_TESTS") != "1":
        pytest.skip("set RUN_REAL_DATA_TESTS=1 to run the optional local ULB integration check")
    if not REAL_DATASET.is_file():
        pytest.skip(f"real ULB dataset is unavailable at {REAL_DATASET}")
    if not PROVENANCE_PATH.is_file():
        pytest.skip(f"verified dataset provenance is unavailable at {PROVENANCE_PATH}")

    provenance = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
    frame = load_ulb_csv(REAL_DATASET)

    assert has_verified_kaggle_provenance(REAL_DATASET)
    assert provenance["dataset_id"] == KAGGLE_DATASET_ID
    assert provenance["file_name"] == REAL_DATASET.name
    assert provenance["sha256"] == sha256_file(REAL_DATASET)
    assert provenance["schema_validation"]["schema_version"] == SCHEMA_VERSION
    assert frame.shape == (284_807, 31)
    assert tuple(frame.columns) == EXPECTED_COLUMNS
    assert all(np.issubdtype(dtype, np.number) for dtype in frame.dtypes)
    assert not frame.isna().any().any()
    assert np.isfinite(frame.to_numpy(dtype="float64")).all()
    assert set(frame["Class"].unique()) == {0, 1}
    assert frame["Class"].value_counts().to_dict() == {0: 284_315, 1: 492}
    assert frame.duplicated().sum() == 1_081
    assert validate_ulb_frame(frame).valid

    summary = generate_eda_artifacts(
        frame,
        tmp_path,
        data_classification="source_verified_file",
        dataset_name=REAL_DATASET.name,
        provenance=provenance,
    )
    report = (tmp_path / "EDA_REPORT.md").read_text(encoding="utf-8")
    status = json.loads((tmp_path / "summaries" / "eda_status.json").read_text(encoding="utf-8"))
    assert summary["data_classification"] == "source_verified_file"
    assert summary["profile"]["class_summary"]["fraud_count"] == 492
    assert summary["dataset_diagnostics"]["duplicate_rows_in_groups"] == 1_854
    assert status["real_data_eda_status"] == "complete"
    assert status["publisher_counts_verified_locally"]
    assert (tmp_path / "tables" / "class_conditional_summaries.csv").is_file()
    assert (tmp_path / "figures" / "class_distribution.png").is_file()
    assert "SOURCE_VERIFIED_FILE" in report
    assert provenance["sha256"] in report
    assert "validation_candidate" in report
