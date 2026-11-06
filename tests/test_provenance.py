from __future__ import annotations

import json

from fraud_detection.provenance import (
    KAGGLE_DATASET_ID,
    has_verified_kaggle_provenance,
    resolve_project_path,
    sha256_file,
)
from fraud_detection.schema import SCHEMA_VERSION


def test_kaggle_provenance_verifies_dataset_identity_and_checksum(tmp_path):
    dataset = tmp_path / "creditcard.csv"
    dataset.write_text("validated test fixture\n", encoding="utf-8")
    sidecar = tmp_path / "dataset-provenance.json"
    sidecar.write_text(
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

    assert has_verified_kaggle_provenance(dataset)
    dataset.write_text("changed bytes\n", encoding="utf-8")
    assert not has_verified_kaggle_provenance(dataset)


def test_unverified_or_malformed_metadata_is_not_trusted(tmp_path):
    dataset = tmp_path / "creditcard.csv"
    dataset.write_text("fixture\n", encoding="utf-8")
    assert not has_verified_kaggle_provenance(dataset)
    (tmp_path / "dataset-provenance.json").write_text("{", encoding="utf-8")
    assert not has_verified_kaggle_provenance(dataset)


def test_relative_paths_resolve_from_project_root(tmp_path):
    assert resolve_project_path("reports", project_root=tmp_path) == tmp_path / "reports"
    absolute = tmp_path / "data.csv"
    assert resolve_project_path(absolute, project_root=tmp_path) == absolute
