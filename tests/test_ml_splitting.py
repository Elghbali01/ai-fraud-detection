"""Mission 02 chronological split, leakage, and fold behavior."""

from __future__ import annotations

import json

import numpy as np
import pytest

from fraud_detection.ml.splitting import (
    create_temporal_split,
    make_expanding_time_folds,
    write_split_manifest,
)
from tests.ml_helpers import make_transaction_frame


def test_split_is_complete_chronological_tie_preserving_and_reproducible(tmp_path):
    frame = make_transaction_frame(200)
    split = create_temporal_split(frame, dataset_sha256="a" * 64)
    repeated = create_temporal_split(frame, dataset_sha256="a" * 64)

    positions = [split.train_positions, split.validation_positions, split.test_positions]
    assert sum(len(part) for part in positions) == len(frame)
    assert len(np.unique(np.concatenate(positions))) == len(frame)
    assert split.manifest["manifest_id"] == repeated.manifest["manifest_id"]
    time_ranges = [
        (frame.iloc[part]["Time"].min(), frame.iloc[part]["Time"].max()) for part in positions
    ]
    assert time_ranges[0][1] < time_ranges[1][0] <= time_ranges[1][1] < time_ranges[2][0]
    for time_value in frame["Time"].unique():
        memberships = [
            np.isin(np.flatnonzero(frame["Time"].to_numpy() == time_value), part).any()
            for part in positions
        ]
        assert sum(memberships) == 1
    assert split.manifest["excluded_rows"] == 0

    manifest_path = write_split_manifest(split, tmp_path / "manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["manifest_id"] == split.manifest["manifest_id"]
    assert manifest["row_positions_persisted"] is False


def test_duplicate_feature_vectors_are_kept_together_and_audited():
    frame = make_transaction_frame(200)
    frame = __import__("pandas").concat([frame.iloc[:2], frame.iloc[[1]], frame.iloc[2:]])
    frame = frame.reset_index(drop=True)
    split = create_temporal_split(frame, dataset_sha256="b" * 64)
    audit = split.manifest["duplicate_audit"]
    assert audit["exact_duplicate_copies_beyond_first"] == 1
    assert audit["rows_in_exact_duplicate_groups"] == 2
    assert audit["feature_vectors"]["cross_partition_signature_groups"] == 0
    assert audit["full_rows"]["cross_partition_signature_groups"] == 0


def test_expanding_folds_never_validate_on_an_earlier_timestamp():
    frame = make_transaction_frame(200)
    folds = make_expanding_time_folds(frame, n_splits=3)
    assert len(folds) == 3
    for fold in folds:
        fit_times = frame.iloc[fold.fit_positions]["Time"]
        validation_times = frame.iloc[fold.validation_positions]["Time"]
        assert fit_times.max() < validation_times.min()
        assert set(frame.iloc[fold.validation_positions]["Class"].unique()) == {0, 1}


def test_unsorted_time_is_rejected():
    frame = make_transaction_frame(120).iloc[::-1].reset_index(drop=True)
    with pytest.raises(ValueError, match="nondecreasing Time"):
        create_temporal_split(frame, dataset_sha256="c" * 64)
