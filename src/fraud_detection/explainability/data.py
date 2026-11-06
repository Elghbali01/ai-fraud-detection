"""Load only the training and validation portions of the frozen Mission 02 data split."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from fraud_detection.exceptions import ArtifactError, SchemaValidationError
from fraud_detection.ml.persistence import sha256_file
from fraud_detection.provenance import MISSION01_ULB_SHA256
from fraud_detection.schema import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    TIME_COLUMN,
    require_valid_ulb_frame,
)


@dataclass(frozen=True)
class DevelopmentPartitions:
    """Verified train and validation frames; final-test rows are never parsed."""

    training: pd.DataFrame
    validation: pd.DataFrame
    dataset_sha256: str
    split_manifest_id: str
    split_manifest: dict[str, Any]
    source_path: Path


def load_development_partitions(
    dataset_path: str | Path,
    split_manifest_path: str | Path,
) -> DevelopmentPartitions:
    """Read only the frozen training and validation row prefix of the ordered CSV.

    The file checksum covers all bytes but only the first train+validation rows are
    parsed. The final-test labels and feature values are never loaded into a frame.
    """
    source = Path(dataset_path)
    manifest_path = Path(split_manifest_path)
    if not source.is_file():
        raise FileNotFoundError(f"Verified ULB data file was not found: {source}")
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Frozen Mission 02 split manifest was not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fingerprint = sha256_file(source)
    if fingerprint != MISSION01_ULB_SHA256 or fingerprint != manifest.get("dataset_sha256"):
        raise ArtifactError("Dataset checksum does not match the verified Mission 01 source")

    partitions = manifest.get("partitions", {})
    try:
        train_meta = partitions["train"]
        validation_meta = partitions["validation"]
        train_end = float(manifest["time_cutoffs"]["train_end_inclusive"])
        validation_end = float(manifest["time_cutoffs"]["validation_end_inclusive"])
        development_rows = int(train_meta["rows"]) + int(validation_meta["rows"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ArtifactError(
            "Split manifest is missing valid development partition metadata"
        ) from exc

    header = pd.read_csv(source, nrows=0).columns.tolist()
    expected = [
        TIME_COLUMN,
        *[name for name in FEATURE_COLUMNS if name != TIME_COLUMN],
        TARGET_COLUMN,
    ]
    if header != expected:
        raise SchemaValidationError("The verified ULB CSV header differs from its frozen schema")

    development = pd.read_csv(source, nrows=development_rows, low_memory=False)
    if len(development) != development_rows:
        raise ArtifactError("The CSV development prefix does not match the frozen partition sizes")
    validation_result = require_valid_ulb_frame(development, strict_columns=True)
    if not validation_result.valid:
        raise SchemaValidationError("Training/validation prefix failed the ULB schema contract")
    if not development[TIME_COLUMN].is_monotonic_increasing:
        raise ArtifactError("The source prefix is not monotonic in Time")

    training = development.loc[development[TIME_COLUMN].le(train_end)].copy()
    validation = development.loc[
        development[TIME_COLUMN].gt(train_end) & development[TIME_COLUMN].le(validation_end)
    ].copy()
    if len(training) != int(train_meta["rows"]) or len(validation) != int(validation_meta["rows"]):
        raise ArtifactError(
            "Observed training/validation boundaries differ from the frozen manifest"
        )
    if float(training[TIME_COLUMN].max()) != train_end:
        raise ArtifactError("Training Time boundary differs from the frozen manifest")
    if float(validation[TIME_COLUMN].max()) != validation_end:
        raise ArtifactError("Validation Time boundary differs from the frozen manifest")
    if TARGET_COLUMN not in training or TARGET_COLUMN not in validation:
        raise SchemaValidationError("Development partitions are missing the training target")

    training.index.name = "source_row_index"
    validation.index.name = "source_row_index"
    return DevelopmentPartitions(
        training=training,
        validation=validation,
        dataset_sha256=fingerprint,
        split_manifest_id=str(manifest["manifest_id"]),
        split_manifest=manifest,
        source_path=source.resolve(),
    )
