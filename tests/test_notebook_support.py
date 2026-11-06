from __future__ import annotations

import json

from fraud_detection.notebook_support import load_notebook_frame
from fraud_detection.provenance import KAGGLE_DATASET_ID, sha256_file
from fraud_detection.schema import SCHEMA_VERSION


def test_missing_notebook_dataset_uses_labeled_synthetic_fixture(tmp_path):
    frame, status = load_notebook_frame(tmp_path / "missing.csv")

    assert status == "synthetic_fixture"
    assert len(frame) == 200


def test_notebook_source_status_distinguishes_unverified_and_verified_files(
    transaction_frame, tmp_path
):
    dataset = tmp_path / "creditcard.csv"
    transaction_frame.to_csv(dataset, index=False)

    unverified_frame, unverified_status = load_notebook_frame(dataset)

    assert len(unverified_frame) == len(transaction_frame)
    assert unverified_status == "unverified_local_file"
    (tmp_path / "dataset-provenance.json").write_text(
        json.dumps(
            {
                "dataset_id": KAGGLE_DATASET_ID,
                "file_name": dataset.name,
                "sha256": sha256_file(dataset),
                "schema_validation": {"schema_version": SCHEMA_VERSION},
            }
        ),
        encoding="utf-8",
    )

    _, verified_status = load_notebook_frame(dataset)

    assert verified_status == "source_verified_file"
