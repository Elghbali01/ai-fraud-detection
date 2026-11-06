"""Reusable schema and data-quality profiling for transaction frames."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from fraud_detection.schema import TARGET_COLUMN, validate_ulb_frame


def profile_dataset(frame: pd.DataFrame, *, target_column: str = TARGET_COLUMN) -> dict[str, Any]:
    """Return deterministic row, column, missingness, class, and numeric summaries."""
    columns: list[dict[str, Any]] = []
    for name in frame.columns:
        series = frame[name]
        numeric = pd.api.types.is_numeric_dtype(series)
        item: dict[str, Any] = {
            "name": str(name),
            "dtype": str(series.dtype),
            "missing_count": int(series.isna().sum()),
            "missing_pct": float(series.isna().mean() * 100) if len(series) else 0.0,
            "unique_count": int(series.nunique(dropna=True)),
            "is_constant": bool(series.nunique(dropna=True) <= 1),
        }
        if numeric:
            values = series.dropna().astype("float64")
            finite = values[np.isfinite(values)]
            item["non_finite_count"] = int((~np.isfinite(values)).sum())
            item["zero_count"] = int((finite == 0).sum())
            item["statistics"] = {
                "min": _scalar(finite.min()) if not finite.empty else None,
                "q01": _scalar(finite.quantile(0.01)) if not finite.empty else None,
                "q25": _scalar(finite.quantile(0.25)) if not finite.empty else None,
                "median": _scalar(finite.median()) if not finite.empty else None,
                "mean": _scalar(finite.mean()) if not finite.empty else None,
                "q75": _scalar(finite.quantile(0.75)) if not finite.empty else None,
                "q99": _scalar(finite.quantile(0.99)) if not finite.empty else None,
                "max": _scalar(finite.max()) if not finite.empty else None,
                "std": _scalar(finite.std()) if len(finite) > 1 else None,
            }
        columns.append(item)

    class_counts: dict[str, int] = {}
    class_summary: dict[str, Any] | None = None
    if target_column in frame:
        counts = frame[target_column].value_counts(dropna=False, sort=False)
        class_counts = {
            str(_scalar(label) if not pd.isna(label) else "missing"): int(count)
            for label, count in counts.items()
        }
        non_missing_counts = frame[target_column].dropna().value_counts()
        if not non_missing_counts.empty:
            minority = int(non_missing_counts.min())
            majority = int(non_missing_counts.max())
            total = int(non_missing_counts.sum())
            fraud_count = int((frame[target_column] == 1).sum())
            class_summary = {
                "counts": class_counts,
                "legitimate_count": int((frame[target_column] == 0).sum()),
                "fraud_count": fraud_count,
                "fraud_pct_of_all_rows": float(100 * fraud_count / len(frame))
                if len(frame)
                else 0.0,
                "majority_minority_ratio": float(majority / minority) if minority else None,
                "majority_class_baseline_accuracy": float(majority / total) if total else None,
            }

    schema = validate_ulb_frame(frame)
    return {
        "schema_version": schema.schema_version,
        "row_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "memory_usage_bytes": int(frame.memory_usage(index=True, deep=True).sum()),
        "duplicate_row_count": int(frame.duplicated().sum()),
        "columns": columns,
        "class_summary": class_summary,
        "schema_validation": schema.to_dict(),
    }


def _scalar(value: Any) -> Any:
    """Convert NumPy scalars to built-in JSON-friendly scalar values."""
    return value.item() if isinstance(value, np.generic) else value
