"""Global SHAP summaries and training-to-validation attribution stability."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from fraud_detection.explainability.shap_engine import ShapExplanationBatch
from fraud_detection.schema import FEATURE_COLUMNS


def summarize_global_attributions(
    validation_shap: ShapExplanationBatch,
    validation_labels: np.ndarray,
    *,
    validation_linear_contributions: pd.DataFrame,
    coefficients: pd.Series,
) -> pd.DataFrame:
    """Summarize validation SHAP values overall and by historical label."""
    labels = np.asarray(validation_labels, dtype=np.int8)
    values = validation_shap.values.to_numpy(dtype=np.float64)
    linear = validation_linear_contributions.to_numpy(dtype=np.float64)
    if values.shape[0] != len(labels) or linear.shape != values.shape:
        raise ValueError("Validation labels and attribution matrices must align")
    fraud = labels == 1
    legitimate = labels == 0
    rows = []
    for index, feature in enumerate(FEATURE_COLUMNS):
        column = values[:, index]
        rows.append(
            {
                "feature": feature,
                "coefficient": float(coefficients.loc[feature]),
                "absolute_coefficient": float(abs(coefficients.loc[feature])),
                "mean_abs_shap_log_odds": float(np.mean(np.abs(column))),
                "mean_shap_log_odds": float(np.mean(column)),
                "positive_shap_fraction": float(np.mean(column > 0)),
                "mean_abs_shap_legitimate": (
                    float(np.mean(np.abs(column[legitimate]))) if legitimate.any() else None
                ),
                "mean_abs_shap_fraud": (
                    float(np.mean(np.abs(column[fraud]))) if fraud.any() else None
                ),
                "mean_shap_fraud_minus_legitimate": (
                    float(np.mean(column[fraud]) - np.mean(column[legitimate]))
                    if fraud.any() and legitimate.any()
                    else None
                ),
                "mean_abs_exact_linear_contribution": float(np.mean(np.abs(linear[:, index]))),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["mean_abs_shap_log_odds", "feature"],
        ascending=[False, True],
        ignore_index=True,
    )


def attribution_stability(
    training_shap: ShapExplanationBatch,
    validation_shap: ShapExplanationBatch,
) -> dict[str, Any]:
    """Compare mean-absolute SHAP rankings across a bounded train sample and validation."""
    train_importance = training_shap.values.abs().mean(axis=0).reindex(FEATURE_COLUMNS)
    validation_importance = validation_shap.values.abs().mean(axis=0).reindex(FEATURE_COLUMNS)
    correlation = spearmanr(train_importance, validation_importance)
    train_rank = train_importance.rank(ascending=False, method="average")
    validation_rank = validation_importance.rank(ascending=False, method="average")
    return {
        "training_sample_rows": int(len(training_shap.values)),
        "validation_rows": int(len(validation_shap.values)),
        "spearman_rank_correlation": float(correlation.statistic),
        "training_top_10": train_importance.sort_values(ascending=False).head(10).index.tolist(),
        "validation_top_10": validation_importance.sort_values(ascending=False)
        .head(10)
        .index.tolist(),
        "mean_absolute_rank_difference": float(np.mean(np.abs(train_rank - validation_rank))),
        "interpretation": (
            "Descriptive attribution-rank stability only; it is not a causal or performance test."
        ),
    }
