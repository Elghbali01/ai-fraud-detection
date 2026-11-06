"""Statistical summaries used by the Mission 01 EDA."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from fraud_detection.schema import AMOUNT_COLUMN, TARGET_COLUMN, TIME_COLUMN


def class_imbalance(frame: pd.DataFrame, *, target_column: str = TARGET_COLUMN) -> dict[str, Any]:
    """Summarize the binary label distribution and majority-class baseline."""
    if target_column not in frame:
        raise ValueError(f"Target column {target_column!r} is required")
    counts = frame[target_column].value_counts(dropna=False, sort=False)
    labeled = frame[target_column].dropna()
    clean_counts = labeled.value_counts()
    total = int(clean_counts.sum())
    positives = int((labeled == 1).sum())
    majority = int(clean_counts.max()) if not clean_counts.empty else 0
    minority = int(clean_counts.min()) if not clean_counts.empty else 0
    return {
        "row_count": int(len(frame)),
        "labeled_row_count": total,
        "counts": {str(label): int(count) for label, count in counts.items()},
        "legitimate_count": int((labeled == 0).sum()),
        "fraud_count": positives,
        "fraud_pct": float(100 * positives / total) if total else 0.0,
        "majority_minority_ratio": float(majority / minority) if minority else None,
        "majority_class_baseline_accuracy": float(majority / total) if total else None,
        "baseline_note": (
            "Illustrative majority-class prediction only; this is not a trained fraud model."
        ),
    }


def amount_summary(
    frame: pd.DataFrame,
    *,
    amount_column: str = AMOUNT_COLUMN,
    target_column: str = TARGET_COLUMN,
) -> pd.DataFrame:
    """Calculate class-wise amount statistics without changing amount values."""
    if amount_column not in frame or target_column not in frame:
        raise ValueError(f"Required columns: {amount_column!r} and {target_column!r}")
    records: list[dict[str, Any]] = []
    for label, group in frame.groupby(target_column, dropna=False, sort=True):
        values = group[amount_column].dropna().astype("float64")
        values = values[np.isfinite(values)]
        record: dict[str, Any] = {
            "class_label": label,
            "transactions": int(len(group)),
            "non_missing_amounts": int(len(values)),
            "zero_amount_count": int((values == 0).sum()),
            "mean": float(values.mean()) if len(values) else None,
            "median": float(values.median()) if len(values) else None,
            "std": float(values.std()) if len(values) > 1 else None,
            "min": float(values.min()) if len(values) else None,
            "q25": float(values.quantile(0.25)) if len(values) else None,
            "q75": float(values.quantile(0.75)) if len(values) else None,
            "q90": float(values.quantile(0.90)) if len(values) else None,
            "q95": float(values.quantile(0.95)) if len(values) else None,
            "q99": float(values.quantile(0.99)) if len(values) else None,
            "max": float(values.max()) if len(values) else None,
            "skewness": float(values.skew()) if len(values) > 2 else None,
        }
        records.append(record)
    return pd.DataFrame.from_records(records)


def time_bin_summary(
    frame: pd.DataFrame,
    *,
    bin_seconds: int = 21_600,
    minimum_transactions: int = 1_000,
    minimum_fraud_cases: int = 30,
    time_column: str = TIME_COLUMN,
    target_column: str = TARGET_COLUMN,
) -> pd.DataFrame:
    """Aggregate elapsed-time bins and flag low transaction or fraud counts."""
    if bin_seconds <= 0:
        raise ValueError("bin_seconds must be greater than zero")
    if minimum_transactions < 0 or minimum_fraud_cases < 0:
        raise ValueError("minimum count thresholds must be nonnegative")
    if time_column not in frame or target_column not in frame:
        raise ValueError(f"Required columns: {time_column!r} and {target_column!r}")
    valid = frame[[time_column, target_column]].dropna(subset=[time_column]).copy()
    if valid.empty:
        return pd.DataFrame(
            columns=[
                "elapsed_start_seconds",
                "elapsed_end_seconds",
                "transactions",
                "fraud_count",
                "fraud_rate",
                "low_volume",
                "low_fraud_count",
            ]
        )
    valid["elapsed_start_seconds"] = (
        np.floor(valid[time_column].astype("float64") / bin_seconds) * bin_seconds
    ).astype("int64")
    grouped = valid.groupby("elapsed_start_seconds", sort=True)
    result = (
        grouped[target_column]
        .agg(
            transactions="size",
            fraud_count=lambda labels: int((labels == 1).sum()),
        )
        .reset_index()
    )
    result["elapsed_end_seconds"] = result["elapsed_start_seconds"] + bin_seconds
    result["fraud_rate"] = result["fraud_count"] / result["transactions"]
    result["low_volume"] = result["transactions"] < minimum_transactions
    result["low_fraud_count"] = result["fraud_count"] < minimum_fraud_cases
    return result[
        [
            "elapsed_start_seconds",
            "elapsed_end_seconds",
            "transactions",
            "fraud_count",
            "fraud_rate",
            "low_volume",
            "low_fraud_count",
        ]
    ]


def correlation_matrix(
    frame: pd.DataFrame, *, method: str = "pearson", include_target: bool = True
) -> pd.DataFrame:
    """Return numeric Pearson or Spearman correlations for descriptive analysis."""
    if method not in {"pearson", "spearman"}:
        raise ValueError("method must be 'pearson' or 'spearman'")
    numeric = frame.select_dtypes(include="number")
    if not include_target and TARGET_COLUMN in numeric:
        numeric = numeric.drop(columns=[TARGET_COLUMN])
    return numeric.corr(method=method)


def class_feature_associations(
    frame: pd.DataFrame, *, target_column: str = TARGET_COLUMN
) -> pd.DataFrame:
    """Rank numeric features by absolute Spearman association with the binary label."""
    if target_column not in frame:
        raise ValueError(f"Target column {target_column!r} is required")
    numeric = frame.select_dtypes(include="number")
    features = numeric.drop(columns=[target_column], errors="ignore")
    records = []
    for name in features.columns:
        values = pd.concat([features[name], frame[target_column]], axis=1).dropna()
        if len(values) < 2 or values[name].nunique() < 2:
            coefficient = None
        else:
            coefficient = float(values[name].corr(values[target_column], method="spearman"))
            if not np.isfinite(coefficient):
                coefficient = None
        records.append(
            {
                "feature": str(name),
                "spearman_with_class": coefficient,
                "absolute_association": abs(coefficient) if coefficient is not None else None,
                "non_missing_pairs": int(len(values)),
            }
        )
    return pd.DataFrame.from_records(records).sort_values(
        "absolute_association", ascending=False, na_position="last", ignore_index=True
    )


def iqr_outlier_diagnostics(
    frame: pd.DataFrame, *, exclude: tuple[str, ...] = (TARGET_COLUMN,)
) -> pd.DataFrame:
    """Count IQR-flagged observations per numeric feature; never remove them."""
    records = []
    numeric = frame.select_dtypes(include="number")
    for name in numeric.columns:
        if name in exclude:
            continue
        values = numeric[name].dropna().astype("float64")
        values = values[np.isfinite(values)]
        if values.empty:
            continue
        q1, q3 = values.quantile([0.25, 0.75])
        spread = float(q3 - q1)
        lower = float(q1 - 1.5 * spread)
        upper = float(q3 + 1.5 * spread)
        count = int(((values < lower) | (values > upper)).sum())
        records.append(
            {
                "feature": str(name),
                "finite_values": int(len(values)),
                "q1": float(q1),
                "q3": float(q3),
                "iqr": spread,
                "lower_fence": lower,
                "upper_fence": upper,
                "outlier_count": count,
                "outlier_pct": float(100 * count / len(values)),
            }
        )
    return pd.DataFrame.from_records(records)
