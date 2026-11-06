from __future__ import annotations

import pandas as pd
import pytest

from fraud_detection.exceptions import DatasetLoadError, EmptyDatasetError, SchemaValidationError
from fraud_detection.loading import load_csv, load_ulb_csv


def test_load_ulb_csv_validates_and_preserves_values(transaction_frame, tmp_path):
    path = tmp_path / "transactions.csv"
    transaction_frame.to_csv(path, index=False)

    loaded = load_ulb_csv(path)

    pd.testing.assert_frame_equal(loaded, transaction_frame)


def test_missing_file_is_reported(tmp_path):
    with pytest.raises(DatasetLoadError, match="does not exist"):
        load_csv(tmp_path / "missing.csv")


def test_empty_file_and_header_only_file_are_reported(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_bytes(b"")
    with pytest.raises(EmptyDatasetError, match="empty"):
        load_csv(empty)

    header_only = tmp_path / "header.csv"
    header_only.write_text("Time,Class\n", encoding="utf-8")
    with pytest.raises(EmptyDatasetError, match="no data rows"):
        load_csv(header_only)


def test_invalid_schema_is_rejected_by_ulb_loader(tmp_path):
    path = tmp_path / "wrong.csv"
    path.write_text("Time,Class\n1,0\n", encoding="utf-8")

    with pytest.raises(SchemaValidationError, match="missing_columns"):
        load_ulb_csv(path)


def test_malformed_csv_is_reported(tmp_path):
    path = tmp_path / "malformed.csv"
    path.write_text("a,b\n1,2\n3,4,5\n", encoding="utf-8")

    with pytest.raises(DatasetLoadError, match="Could not read CSV"):
        load_csv(path)


def test_invalid_utf8_is_reported(tmp_path):
    path = tmp_path / "invalid.csv"
    path.write_bytes(b"a,b\n1,\xff\n")

    with pytest.raises(DatasetLoadError, match="Could not read CSV"):
        load_csv(path)


def test_bounded_read_is_documented_head_sample(transaction_frame, tmp_path):
    path = tmp_path / "transactions.csv"
    transaction_frame.to_csv(path, index=False)

    sample = load_csv(path, sample_rows=3)

    assert len(sample) == 3
    assert sample.iloc[0]["Time"] == transaction_frame.iloc[0]["Time"]
    with pytest.raises(ValueError, match="positive"):
        load_csv(path, sample_rows=0)
