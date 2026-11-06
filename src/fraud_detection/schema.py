"""Versioned schema contract and validation for the ULB transaction dataset."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

SCHEMA_VERSION = "ulb-credit-card-v1"
TARGET_COLUMN = "Class"
TIME_COLUMN = "Time"
AMOUNT_COLUMN = "Amount"
PCA_COLUMNS = tuple(f"V{i}" for i in range(1, 29))
EXPECTED_COLUMNS = (TIME_COLUMN, *PCA_COLUMNS, AMOUNT_COLUMN, TARGET_COLUMN)
FEATURE_COLUMNS = EXPECTED_COLUMNS[:-1]
NUMERIC_COLUMNS = EXPECTED_COLUMNS


@dataclass(frozen=True)
class SchemaValidation:
    """Deterministic results of checking a frame against the ULB schema."""

    schema_version: str
    row_count: int
    missing_columns: tuple[str, ...]
    unexpected_columns: tuple[str, ...]
    non_numeric_columns: tuple[str, ...]
    invalid_target_values: tuple[Any, ...]
    target_missing_count: int
    non_finite_counts: dict[str, int]
    strict_columns: bool = False

    @property
    def valid(self) -> bool:
        """Whether required fields and value types satisfy the contract."""
        return not (
            self.row_count == 0
            or self.missing_columns
            or self.non_numeric_columns
            or self.invalid_target_values
            or self.target_missing_count
            or self.non_finite_counts
            or (self.strict_columns and self.unexpected_columns)
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible validation result."""
        result = asdict(self)
        result["missing_columns"] = list(self.missing_columns)
        result["unexpected_columns"] = list(self.unexpected_columns)
        result["non_numeric_columns"] = list(self.non_numeric_columns)
        result["invalid_target_values"] = list(self.invalid_target_values)
        result["valid"] = self.valid
        return result


def validate_ulb_frame(frame: pd.DataFrame, *, strict_columns: bool = False) -> SchemaValidation:
    """Validate column presence, numeric types, labels, and finite numeric values.

    Extra columns are reported but allowed by default. No rows or values are changed.
    """
    columns = set(frame.columns)
    missing = tuple(column for column in EXPECTED_COLUMNS if column not in columns)
    unexpected = tuple(sorted(str(column) for column in columns - set(EXPECTED_COLUMNS)))
    present_numeric = [column for column in NUMERIC_COLUMNS if column in columns]
    non_numeric = tuple(
        column for column in present_numeric if not pd.api.types.is_numeric_dtype(frame[column])
    )
    invalid_labels: tuple[Any, ...] = ()
    target_missing = 0
    if TARGET_COLUMN in columns:
        target = frame[TARGET_COLUMN]
        target_missing = int(target.isna().sum())
        observed = target.dropna()
        invalid = observed.loc[~observed.isin([0, 1])].drop_duplicates().tolist()
        invalid_labels = tuple(
            sorted(invalid, key=lambda value: (type(value).__name__, str(value)))
        )

    non_finite: dict[str, int] = {}
    for column in present_numeric:
        if column in non_numeric:
            continue
        values = frame[column].to_numpy(dtype="float64", na_value=np.nan)
        count = int(np.isinf(values).sum())
        if count:
            non_finite[column] = count

    return SchemaValidation(
        schema_version=SCHEMA_VERSION,
        row_count=len(frame),
        missing_columns=missing,
        unexpected_columns=unexpected,
        non_numeric_columns=non_numeric,
        invalid_target_values=invalid_labels,
        target_missing_count=target_missing,
        non_finite_counts=non_finite,
        strict_columns=strict_columns,
    )


def require_valid_ulb_frame(
    frame: pd.DataFrame, *, strict_columns: bool = False
) -> SchemaValidation:
    """Validate a ULB frame and raise a readable exception if core checks fail."""
    from fraud_detection.exceptions import SchemaValidationError

    result = validate_ulb_frame(frame, strict_columns=strict_columns)
    if not result.valid:
        raise SchemaValidationError(f"Invalid {SCHEMA_VERSION} dataset: {result.to_dict()}")
    return result
