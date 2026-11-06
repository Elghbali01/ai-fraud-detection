"""Memory-conscious CSV loading with explicit error handling."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from fraud_detection.exceptions import DatasetLoadError, EmptyDatasetError
from fraud_detection.schema import require_valid_ulb_frame


def load_csv(
    path: str | Path,
    *,
    sample_rows: int | None = None,
    encoding: str = "utf-8",
) -> pd.DataFrame:
    """Load a CSV without modifying its values.

    sample_rows reads the first N rows for a bounded diagnostic; it is not a
    random sample and should not be used for final dataset statistics.
    """
    source = Path(path)
    if not source.is_file():
        raise DatasetLoadError(f"Dataset file does not exist: {source}")
    if source.stat().st_size == 0:
        raise EmptyDatasetError(f"Dataset file is empty: {source}")
    if sample_rows is not None and sample_rows <= 0:
        raise ValueError("sample_rows must be a positive integer when supplied")
    try:
        frame = pd.read_csv(
            source,
            encoding=encoding,
            nrows=sample_rows,
            low_memory=False,
            on_bad_lines="error",
        )
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError, OSError) as exc:
        raise DatasetLoadError(f"Could not read CSV at {source}: {exc}") from exc
    if frame.empty:
        raise EmptyDatasetError(f"CSV contains a header but no data rows: {source}")
    return frame


def load_ulb_csv(
    path: str | Path,
    *,
    sample_rows: int | None = None,
    encoding: str = "utf-8",
    strict_columns: bool = False,
) -> pd.DataFrame:
    """Load a CSV and validate it against the versioned ULB schema."""
    frame = load_csv(path, sample_rows=sample_rows, encoding=encoding)
    require_valid_ulb_frame(frame, strict_columns=strict_columns)
    return frame
