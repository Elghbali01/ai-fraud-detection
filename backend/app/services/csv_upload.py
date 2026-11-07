"""Strict streaming CSV validation for user supplied feature-only data."""

from __future__ import annotations

import csv
import math
from collections.abc import Iterator
from pathlib import Path

import pandas as pd

from fraud_detection.schema import FEATURE_COLUMNS


class CSVValidationError(ValueError):
    """A bounded CSV failed the exact feature-only input contract."""

    def __init__(self, code: str, public_message: str) -> None:
        super().__init__(public_message)
        self.code = code


def _read_header(reader: csv.reader) -> list[str]:
    try:
        header = next(reader)
    except StopIteration as exc:
        raise CSVValidationError(
            "empty_csv", "CSV must contain a header and at least one row"
        ) from exc
    except (csv.Error, UnicodeDecodeError) as exc:
        raise CSVValidationError("malformed_csv", "CSV encoding or header is malformed") from exc
    if len(header) != len(set(header)):
        raise CSVValidationError("duplicate_headers", "CSV header contains duplicate columns")
    if "Class" in header:
        raise CSVValidationError(
            "target_column_forbidden", "Class is not accepted in prediction uploads"
        )
    if header != list(FEATURE_COLUMNS):
        raise CSVValidationError(
            "feature_schema_mismatch",
            "CSV header must match the 30 feature names in the documented order",
        )
    return header


def _parse_row(row: list[str], row_number: int) -> list[float]:
    if len(row) != len(FEATURE_COLUMNS):
        raise CSVValidationError(
            "malformed_row", f"CSV row {row_number} has an invalid number of fields"
        )
    values: list[float] = []
    for text in row:
        try:
            value = float(text)
        except (TypeError, ValueError) as exc:
            raise CSVValidationError(
                "invalid_numeric_value", f"CSV row {row_number} contains a non-numeric value"
            ) from exc
        if not math.isfinite(value):
            raise CSVValidationError(
                "non_finite_value", f"CSV row {row_number} contains a non-finite value"
            )
        values.append(value)
    return values


def validate_csv_file(path: str | Path, *, max_rows: int) -> int:
    """Stream the file once, checking exact headers, strict quotes, rows, and finite values."""
    rows = 0
    try:
        with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, strict=True)
            _read_header(reader)
            for source_row, row in enumerate(reader, start=2):
                if not row:
                    raise CSVValidationError("blank_row", f"CSV row {source_row} is blank")
                _parse_row(row, source_row)
                rows += 1
                if rows > max_rows:
                    raise CSVValidationError(
                        "row_limit_exceeded", "CSV exceeds the configured row limit"
                    )
    except CSVValidationError:
        raise
    except (csv.Error, UnicodeDecodeError, OSError) as exc:
        raise CSVValidationError(
            "malformed_csv", "CSV encoding, quoting, or structure is malformed"
        ) from exc
    if rows == 0:
        raise CSVValidationError("empty_csv", "CSV must contain a header and at least one data row")
    return rows


def iter_csv_batches(
    path: str | Path,
    *,
    chunk_rows: int,
    max_rows: int,
) -> Iterator[tuple[int, pd.DataFrame]]:
    """Yield validated feature chunks and their first one-based source row number."""
    buffered: list[list[float]] = []
    count = 0
    try:
        with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, strict=True)
            _read_header(reader)
            for source_row, row in enumerate(reader, start=2):
                if not row:
                    raise CSVValidationError("blank_row", f"CSV row {source_row} is blank")
                buffered.append(_parse_row(row, source_row))
                count += 1
                if count > max_rows:
                    raise CSVValidationError(
                        "row_limit_exceeded", "CSV exceeds the configured row limit"
                    )
                if len(buffered) == chunk_rows:
                    first_row = source_row - len(buffered) + 1
                    yield first_row, pd.DataFrame(buffered, columns=list(FEATURE_COLUMNS))
                    buffered = []
            if buffered:
                first_row = count - len(buffered) + 2
                yield first_row, pd.DataFrame(buffered, columns=list(FEATURE_COLUMNS))
    except CSVValidationError:
        raise
    except (csv.Error, UnicodeDecodeError, OSError) as exc:
        raise CSVValidationError(
            "malformed_csv", "CSV encoding, quoting, or structure is malformed"
        ) from exc
