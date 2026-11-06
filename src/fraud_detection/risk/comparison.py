"""Validation-only comparison of supervised fraud scores and anomaly rankings."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.stats import spearmanr

from fraud_detection.risk.prioritization import percentage_budget_to_k


def compare_supervised_anomaly(
    labels: np.ndarray | list[int],
    fraud_probabilities: np.ndarray | list[float],
    anomaly_score_percentiles: np.ndarray | list[float],
    *,
    decision_threshold: float,
    anomaly_high_percentile: float = 0.95,
    percentage_budgets: tuple[float, ...] = (0.1, 0.5, 1.0),
) -> dict[str, Any]:
    """Compare rank agreement, top-K overlap, fraud capture, and four quadrants."""
    truth = np.asarray(labels, dtype=np.int8)
    probabilities = np.asarray(fraud_probabilities, dtype=np.float64)
    percentiles = np.asarray(anomaly_score_percentiles, dtype=np.float64)
    if (
        truth.ndim != 1
        or not len(truth)
        or probabilities.ndim != 1
        or percentiles.ndim != 1
        or not (len(truth) == len(probabilities) == len(percentiles))
    ):
        raise ValueError("Labels, supervised probabilities, and anomaly percentiles must align")
    if not np.isin(truth, [0, 1]).all():
        raise ValueError("Validation labels must be binary")
    if not np.isfinite(probabilities).all() or np.any((probabilities < 0) | (probabilities > 1)):
        raise ValueError("Fraud probabilities must be finite values in [0, 1]")
    if not np.isfinite(percentiles).all() or np.any((percentiles < 0) | (percentiles > 1)):
        raise ValueError("Anomaly percentiles must be finite values in [0, 1]")

    correlation = spearmanr(probabilities, percentiles).statistic
    n = len(truth)
    supervised_order = np.argsort(-probabilities, kind="stable")
    anomaly_order = np.argsort(-percentiles, kind="stable")
    total_fraud = int(truth.sum())
    budgets = []
    for percentage in percentage_budgets:
        k = percentage_budget_to_k(n, percentage)
        supervised_top = supervised_order[:k]
        anomaly_top = anomaly_order[:k]
        supervised_set = set(supervised_top.tolist())
        anomaly_set = set(anomaly_top.tolist())
        overlap = supervised_set & anomaly_set
        union = supervised_set | anomaly_set
        supervised_fraud = int(truth[supervised_top].sum())
        anomaly_fraud = int(truth[anomaly_top].sum())
        overlap_fraud = int(truth[list(overlap)].sum()) if overlap else 0
        budgets.append(
            {
                "budget_percentage": float(percentage),
                "k": int(k),
                "supervised_fraud_captured": supervised_fraud,
                "supervised_precision_at_k": float(supervised_fraud / k) if k else None,
                "supervised_recall_at_k": (
                    float(supervised_fraud / total_fraud) if total_fraud else None
                ),
                "anomaly_fraud_captured": anomaly_fraud,
                "anomaly_precision_at_k": float(anomaly_fraud / k) if k else None,
                "anomaly_recall_at_k": (
                    float(anomaly_fraud / total_fraud) if total_fraud else None
                ),
                "overlap_count": int(len(overlap)),
                "overlap_fraction_of_k": float(len(overlap) / k) if k else None,
                "jaccard": float(len(overlap) / len(union)) if union else 1.0,
                "fraud_captured_in_overlap": overlap_fraud,
                "fraud_fraction_of_overlap": (
                    float(overlap_fraud / len(overlap)) if overlap else None
                ),
            }
        )

    high_supervised = probabilities >= float(decision_threshold)
    high_anomaly = percentiles >= float(anomaly_high_percentile)
    quadrant_specs = (
        ("high_supervised_high_anomaly", high_supervised & high_anomaly),
        ("high_supervised_low_anomaly", high_supervised & ~high_anomaly),
        ("low_supervised_high_anomaly", ~high_supervised & high_anomaly),
        ("low_supervised_low_anomaly", ~high_supervised & ~high_anomaly),
    )
    quadrants = []
    for name, mask in quadrant_specs:
        count = int(mask.sum())
        fraud_count = int(truth[mask].sum())
        quadrants.append(
            {
                "quadrant": name,
                "rows": count,
                "fraud_labels": fraud_count,
                "fraud_prevalence": float(fraud_count / count) if count else None,
            }
        )
    return {
        "partition": "validation",
        "rows": int(n),
        "fraud_labels": total_fraud,
        "spearman_correlation": float(correlation) if np.isfinite(correlation) else None,
        "supervised_high_boundary": float(decision_threshold),
        "anomaly_high_boundary_percentile": float(anomaly_high_percentile),
        "alert_budgets": budgets,
        "quadrants": quadrants,
        "interpretation": (
            "The signals describe different targets and are reported side by side; no blended "
            "fraud score is defined."
        ),
    }
