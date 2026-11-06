"""Chronological, duplicate-aware partitioning and development folds."""

from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from fraud_detection.schema import (
    EXPECTED_COLUMNS,
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    TIME_COLUMN,
    require_valid_ulb_frame,
)

SPLIT_PROTOCOL_VERSION = "mission02-chronological-v1"


@dataclass(frozen=True)
class TemporalFold:
    """One expanding-window development fold, indexed relative to its input frame."""

    fit_positions: np.ndarray
    validation_positions: np.ndarray
    metadata: dict[str, Any]


@dataclass(frozen=True)
class TemporalSplit:
    """Deterministic row positions and aggregate manifest for the primary split."""

    train_positions: np.ndarray
    validation_positions: np.ndarray
    test_positions: np.ndarray
    manifest: dict[str, Any]


def _class_summary(frame: pd.DataFrame) -> dict[str, Any]:
    counts = frame[TARGET_COLUMN].value_counts().reindex([0, 1], fill_value=0)
    total = len(frame)
    return {
        "rows": total,
        "class_counts": {str(label): int(counts[label]) for label in (0, 1)},
        "fraud_percentage": round(100 * int(counts[1]) / total, 8) if total else None,
        "time_min": float(frame[TIME_COLUMN].min()) if total else None,
        "time_max": float(frame[TIME_COLUMN].max()) if total else None,
    }


def _boundary_time(frame: pd.DataFrame, fraction: float) -> float:
    grouped = frame.groupby(TIME_COLUMN, sort=True).size()
    cumulative = grouped.cumsum().to_numpy(dtype=np.int64)
    target_rows = fraction * len(frame)
    position = int(np.argmin(np.abs(cumulative - target_rows)))
    return float(grouped.index[position])


def _row_balanced_time_blocks(
    frame: pd.DataFrame, block_count: int
) -> tuple[np.ndarray, list[float]]:
    """Assign complete time groups to approximately equal-row consecutive blocks."""
    grouped = frame.groupby(TIME_COLUMN, sort=True).size()
    cumulative = grouped.cumsum().to_numpy(dtype=np.int64)
    boundaries: list[float] = []
    for block in range(1, block_count):
        target = block * len(frame) / block_count
        position = int(np.argmin(np.abs(cumulative - target)))
        boundary = float(grouped.index[position])
        if boundaries and boundary <= boundaries[-1]:
            raise ValueError("Not enough distinct timestamps to construct temporal folds")
        boundaries.append(boundary)
    block_ids = np.searchsorted(
        np.asarray(boundaries, dtype=np.float64),
        frame[TIME_COLUMN].to_numpy(dtype=np.float64),
        side="left",
    )
    return block_ids, boundaries


def make_expanding_time_folds(
    frame: pd.DataFrame,
    *,
    n_splits: int = 3,
) -> list[TemporalFold]:
    """Make expanding folds from earlier to later training timestamps only.

    The training partition is divided into ``n_splits + 2`` row-balanced blocks.
    Each validation block is later than its fit window; complete equal-Time groups
    remain intact. Folds with one-class fit or validation data are rejected.
    """
    if n_splits < 1:
        raise ValueError("n_splits must be at least 1")
    require_valid_ulb_frame(frame, strict_columns=True)
    if not frame[TIME_COLUMN].is_monotonic_increasing:
        raise ValueError("Temporal folds require nondecreasing Time values")

    block_ids, boundaries = _row_balanced_time_blocks(frame, n_splits + 2)
    target = frame[TARGET_COLUMN].to_numpy(dtype=np.int8)
    folds: list[TemporalFold] = []
    for fold_index in range(n_splits):
        validation_block = fold_index + 2
        fit_positions = np.flatnonzero(block_ids < validation_block)
        validation_positions = np.flatnonzero(block_ids == validation_block)
        fit_y = target[fit_positions]
        validation_y = target[validation_positions]
        if np.unique(fit_y).size != 2 or np.unique(validation_y).size != 2:
            raise ValueError(
                f"Fold {fold_index + 1} must contain both labels in fit and validation data"
            )
        if (
            frame.iloc[fit_positions][TIME_COLUMN].max()
            >= frame.iloc[validation_positions][TIME_COLUMN].min()
        ):
            raise ValueError("Temporal fold timestamps overlap or are reversed")
        metadata = {
            "fold": fold_index + 1,
            "fit_rows": int(len(fit_positions)),
            "fit_fraud": int(fit_y.sum()),
            "fit_time_min": float(frame.iloc[fit_positions][TIME_COLUMN].min()),
            "fit_time_max": float(frame.iloc[fit_positions][TIME_COLUMN].max()),
            "validation_rows": int(len(validation_positions)),
            "validation_fraud": int(validation_y.sum()),
            "validation_time_min": float(frame.iloc[validation_positions][TIME_COLUMN].min()),
            "validation_time_max": float(frame.iloc[validation_positions][TIME_COLUMN].max()),
        }
        folds.append(TemporalFold(fit_positions, validation_positions, metadata))
    return folds


def _duplicate_audit(
    frame: pd.DataFrame,
    partition_ids: np.ndarray,
) -> dict[str, Any]:
    feature_hashes = pd.util.hash_pandas_object(
        frame.loc[:, list(FEATURE_COLUMNS)], index=False
    ).to_numpy(dtype=np.uint64)
    full_hashes = pd.util.hash_pandas_object(frame.loc[:, EXPECTED_COLUMNS], index=False).to_numpy(
        dtype=np.uint64
    )

    def crossing_summary(hashes: np.ndarray) -> dict[str, int]:
        unique_pairs = pd.DataFrame(
            {"signature": hashes, "partition": partition_ids}
        ).drop_duplicates()
        partition_counts = unique_pairs.groupby("signature", sort=False)["partition"].nunique()
        cross_signatures = partition_counts[partition_counts > 1].index.to_numpy(dtype=np.uint64)
        return {
            "cross_partition_signature_groups": int(len(cross_signatures)),
            "rows_in_cross_partition_groups": int(np.isin(hashes, cross_signatures).sum()),
        }

    feature_counts = pd.Series(feature_hashes).value_counts()
    full_counts = pd.Series(full_hashes).value_counts()
    conflicting_labels = (
        pd.DataFrame({"signature": feature_hashes, "label": frame[TARGET_COLUMN].to_numpy()})
        .groupby("signature", sort=False)["label"]
        .nunique()
    )
    duplicate_mask = frame.duplicated(keep=False).to_numpy()
    return {
        "exact_duplicate_copies_beyond_first": int(frame.duplicated().sum()),
        "rows_in_exact_duplicate_groups": int(duplicate_mask.sum()),
        "exact_duplicate_groups": int((full_counts > 1).sum()),
        "repeated_feature_vector_groups": int((feature_counts > 1).sum()),
        "rows_in_repeated_feature_vector_groups": int(feature_counts[feature_counts > 1].sum()),
        "feature_vectors_with_conflicting_labels": int((conflicting_labels > 1).sum()),
        "feature_vectors": crossing_summary(feature_hashes),
        "full_rows": crossing_summary(full_hashes),
        "signature_method": "pandas.util.hash_pandas_object; deterministic row signatures",
    }


def create_temporal_split(
    frame: pd.DataFrame,
    *,
    dataset_sha256: str,
    train_fraction: float = 0.70,
    validation_fraction: float = 0.15,
    seed: int = 17,
    cv_splits: int = 3,
) -> TemporalSplit:
    """Create a tie-preserving 70/15/15 forward-in-time split and audit it."""
    require_valid_ulb_frame(frame, strict_columns=True)
    if tuple(frame.columns) != EXPECTED_COLUMNS:
        raise ValueError("Input columns do not match the canonical ULB feature order")
    if not frame[TIME_COLUMN].is_monotonic_increasing:
        raise ValueError("Chronological splitting requires nondecreasing Time values")
    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1:
        raise ValueError("Split fractions must be between zero and one")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("Training and validation fractions must leave a nonempty test set")
    if len(dataset_sha256) != 64 or any(
        c not in "0123456789abcdef" for c in dataset_sha256.lower()
    ):
        raise ValueError("dataset_sha256 must be a 64-character hexadecimal SHA-256")

    train_end = _boundary_time(frame, train_fraction)
    validation_end = _boundary_time(frame, train_fraction + validation_fraction)
    if validation_end <= train_end:
        raise ValueError("Time quantiles did not produce three distinct partitions")
    times = frame[TIME_COLUMN].to_numpy(dtype=np.float64)
    positions = np.arange(len(frame), dtype=np.int64)
    train_positions = positions[times <= train_end]
    validation_positions = positions[(times > train_end) & (times <= validation_end)]
    test_positions = positions[times > validation_end]
    if min(len(train_positions), len(validation_positions), len(test_positions)) == 0:
        raise ValueError("Chronological split produced an empty partition")
    if len(
        np.unique(np.concatenate([train_positions, validation_positions, test_positions]))
    ) != len(frame):
        raise ValueError("Split positions overlap or do not cover the input rows")

    partition_ids = np.full(len(frame), -1, dtype=np.int8)
    partition_ids[train_positions] = 0
    partition_ids[validation_positions] = 1
    partition_ids[test_positions] = 2
    if np.any(partition_ids < 0):
        raise ValueError("Some input rows were not assigned to a partition")
    duplicate_audit = _duplicate_audit(frame, partition_ids)
    if duplicate_audit["feature_vectors"]["cross_partition_signature_groups"]:
        raise ValueError("Identical feature vectors cross primary partitions")
    if duplicate_audit["full_rows"]["cross_partition_signature_groups"]:
        raise ValueError("Exact duplicate rows cross primary partitions")

    train_frame = frame.iloc[train_positions]
    folds = make_expanding_time_folds(train_frame, n_splits=cv_splits)
    fold_metadata = [fold.metadata for fold in folds]
    manifest_body: dict[str, Any] = {
        "protocol_version": SPLIT_PROTOCOL_VERSION,
        "dataset_sha256": dataset_sha256.lower(),
        "schema_version": "ulb-credit-card-v1",
        "feature_columns": list(FEATURE_COLUMNS),
        "target_column": TARGET_COLUMN,
        "strategy": "chronological grouped-time row quantiles",
        "nominal_fractions": {
            "train": train_fraction,
            "validation": validation_fraction,
            "test": round(1 - train_fraction - validation_fraction, 8),
        },
        "time_tie_policy": "all rows with equal Time stay in one partition",
        "seed": seed,
        "row_count": int(len(frame)),
        "time_cutoffs": {
            "train_end_inclusive": train_end,
            "validation_end_inclusive": validation_end,
        },
        "partitions": {
            "train": _class_summary(train_frame),
            "validation": _class_summary(frame.iloc[validation_positions]),
            "test": _class_summary(frame.iloc[test_positions]),
        },
        "excluded_rows": 0,
        "duplicate_audit": duplicate_audit,
        "development_folds": fold_metadata,
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "row_positions_persisted": False,
    }
    canonical = json.dumps(manifest_body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest = {"manifest_id": hashlib.sha256(canonical).hexdigest(), **manifest_body}
    return TemporalSplit(train_positions, validation_positions, test_positions, manifest)


def write_split_manifest(split: TemporalSplit, path: str | Path) -> Path:
    """Write an aggregate-only JSON manifest and return its path."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(split.manifest, indent=2) + "\n", encoding="utf-8")
    return destination
