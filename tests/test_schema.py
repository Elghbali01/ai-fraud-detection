from __future__ import annotations

import numpy as np

from fraud_detection.schema import EXPECTED_COLUMNS, SCHEMA_VERSION, validate_ulb_frame


def test_expected_ulb_schema_is_valid(transaction_frame):
    result = validate_ulb_frame(transaction_frame)

    assert result.valid
    assert result.schema_version == SCHEMA_VERSION
    assert result.row_count == len(transaction_frame)
    assert len(EXPECTED_COLUMNS) == 31


def test_missing_and_unexpected_columns_are_reported(transaction_frame):
    frame = transaction_frame.drop(columns=["V1"]).assign(custom_metadata=1)

    result = validate_ulb_frame(frame)

    assert "V1" in result.missing_columns
    assert result.unexpected_columns == ("custom_metadata",)
    assert not result.valid


def test_extra_columns_are_allowed_unless_strict(transaction_frame):
    frame = transaction_frame.assign(custom_metadata=1)

    assert validate_ulb_frame(frame).valid
    assert not validate_ulb_frame(frame, strict_columns=True).valid


def test_invalid_labels_missing_labels_and_nonnumeric_columns_are_reported(transaction_frame):
    frame = transaction_frame.copy()
    frame.loc[0, "Class"] = 2
    frame.loc[1, "Class"] = np.nan
    frame["V1"] = frame["V1"].astype("object")
    frame.loc[2, "V1"] = "not numeric"

    result = validate_ulb_frame(frame)

    assert result.invalid_target_values == (2.0,)
    assert result.target_missing_count == 1
    assert "V1" in result.non_numeric_columns
    assert not result.valid


def test_nonfinite_values_are_reported_but_zero_is_valid(transaction_frame):
    frame = transaction_frame.copy()
    frame.loc[0, "Amount"] = 0
    frame.loc[1, "V2"] = np.inf

    result = validate_ulb_frame(frame)

    assert result.non_finite_counts == {"V2": 1}
    assert not result.valid
    assert frame.loc[0, "Amount"] == 0


def test_empty_frame_is_invalid(transaction_frame):
    result = validate_ulb_frame(transaction_frame.iloc[:0])

    assert result.row_count == 0
    assert not result.valid


def test_to_dict_has_machine_readable_fields(transaction_frame):
    result = validate_ulb_frame(transaction_frame).to_dict()

    assert result["valid"] is True
    assert result["schema_version"] == SCHEMA_VERSION
    assert isinstance(result["unexpected_columns"], list)
