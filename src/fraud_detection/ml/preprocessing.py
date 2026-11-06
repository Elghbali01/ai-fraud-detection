"""Feature validation and model-specific preprocessing pipelines."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from fraud_detection.exceptions import InferenceInputError
from fraud_detection.schema import FEATURE_COLUMNS, TARGET_COLUMN


def validate_features(features: pd.DataFrame | dict[str, Any]) -> pd.DataFrame:
    """Validate input shape, names, numeric types, and finite values in stable order."""
    if isinstance(features, dict):
        frame = pd.DataFrame([features])
    elif isinstance(features, pd.DataFrame):
        frame = features.copy()
    else:
        raise InferenceInputError("Features must be a pandas DataFrame or a feature mapping")
    if frame.empty:
        raise InferenceInputError("At least one transaction is required")
    if not frame.columns.is_unique:
        raise InferenceInputError("Feature names must be unique")
    if TARGET_COLUMN in frame.columns:
        raise InferenceInputError(f"Target column {TARGET_COLUMN!r} is not an inference feature")
    missing = [column for column in FEATURE_COLUMNS if column not in frame.columns]
    unexpected = [str(column) for column in frame.columns if column not in FEATURE_COLUMNS]
    if missing or unexpected:
        raise InferenceInputError(
            f"Feature schema mismatch; missing={missing}, unexpected={unexpected}"
        )
    ordered = frame.loc[:, list(FEATURE_COLUMNS)]
    non_numeric = [
        column for column in FEATURE_COLUMNS if not pd.api.types.is_numeric_dtype(ordered[column])
    ]
    if non_numeric:
        raise InferenceInputError(f"Features must be numeric: {non_numeric}")
    values = ordered.to_numpy(dtype=np.float64, na_value=np.nan)
    invalid = ~np.isfinite(values)
    if invalid.any():
        columns = sorted(set(ordered.columns[index] for index in np.where(invalid)[1]))
        raise InferenceInputError(f"Features contain missing or non-finite values: {columns}")
    return ordered.astype(np.float64)


def make_logistic_pipeline(*, c_value: float, class_weight: str | None) -> Pipeline:
    """Construct a scaling and regularized Logistic Regression pipeline."""
    from sklearn.linear_model import LogisticRegression

    return Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    C=c_value,
                    class_weight=class_weight,
                    max_iter=1_000,
                    random_state=17,
                    solver="lbfgs",
                ),
            ),
        ]
    )
