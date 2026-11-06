from __future__ import annotations

import numpy as np
import pandas as pd

from fraud_detection.profiling import profile_dataset


def test_profile_counts_rows_missing_duplicates_classes_and_memory(transaction_frame):
    duplicated = pd.concat([transaction_frame, transaction_frame.iloc[[0]]], ignore_index=True)
    duplicated.loc[1, "V2"] = np.nan

    result = profile_dataset(duplicated)
    by_name = {column["name"]: column for column in result["columns"]}

    assert result["row_count"] == 13
    assert result["column_count"] == 31
    assert result["duplicate_row_count"] == 1
    assert result["memory_usage_bytes"] > 0
    assert by_name["V2"]["missing_count"] == 1
    assert by_name["Amount"]["zero_count"] == 2
    assert by_name["V3"]["is_constant"] is False
    assert result["class_summary"]["fraud_count"] == 1
    assert result["class_summary"]["legitimate_count"] == 12
    assert result["class_summary"]["majority_minority_ratio"] == 12.0


def test_profile_reports_numeric_summaries(transaction_frame):
    result = profile_dataset(transaction_frame)
    amount = next(column for column in result["columns"] if column["name"] == "Amount")

    assert amount["statistics"]["min"] == 0.0
    assert amount["statistics"]["max"] == 1_000.0
    assert amount["statistics"]["median"] == 55.0


def test_profile_handles_empty_frame_with_required_columns(transaction_frame):
    result = profile_dataset(transaction_frame.iloc[:0])

    assert result["row_count"] == 0
    assert result["duplicate_row_count"] == 0
    assert result["class_summary"] is None


def test_profile_separates_nulls_from_zeros(transaction_frame):
    frame = transaction_frame.copy()
    frame.loc[0, "Amount"] = 0
    frame.loc[1, "Amount"] = np.nan

    amount = next(
        column for column in profile_dataset(frame)["columns"] if column["name"] == "Amount"
    )

    assert amount["zero_count"] == 1
    assert amount["missing_count"] == 1
