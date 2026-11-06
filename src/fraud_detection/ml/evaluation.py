"""Metrics for rare-event classification and fixed review-capacity policies."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    auc,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    fbeta_score,
    log_loss,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)


def wilson_interval(
    successes: int, trials: int, *, z: float = 1.959963984540054
) -> list[float] | None:
    """Return a two-sided Wilson score interval or None when no trials exist."""
    if trials <= 0:
        return None
    proportion = successes / trials
    denominator = 1 + z**2 / trials
    center = (proportion + z**2 / (2 * trials)) / denominator
    margin = z * np.sqrt(proportion * (1 - proportion) / trials + z**2 / (4 * trials**2))
    return [
        float(max(0, center - margin / denominator)),
        float(min(1, center + margin / denominator)),
    ]


def classification_metrics(
    y_true: Iterable[int],
    probabilities: Iterable[float],
    *,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Calculate class-aware ranking, calibration, and threshold metrics."""
    truth = np.asarray(list(y_true), dtype=np.int8)
    scores = np.asarray(list(probabilities), dtype=np.float64)
    if truth.ndim != 1 or scores.ndim != 1 or len(truth) != len(scores) or not len(truth):
        raise ValueError("y_true and probabilities must be nonempty aligned one-dimensional arrays")
    if not np.isin(truth, [0, 1]).all():
        raise ValueError("y_true must contain only binary labels 0 and 1")
    if not np.isfinite(scores).all() or np.any((scores < 0) | (scores > 1)):
        raise ValueError("probabilities must be finite values in [0, 1]")
    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("threshold must be a finite value in [0, 1]")

    predictions = (scores >= threshold).astype(np.int8)
    tn, fp, fn, tp = (
        int(value) for value in confusion_matrix(truth, predictions, labels=[0, 1]).ravel()
    )
    positives = tp + fn
    negatives = tn + fp
    precision = float(precision_score(truth, predictions, zero_division=0))
    recall = float(recall_score(truth, predictions, zero_division=0))
    if len(np.unique(truth)) == 2:
        roc_auc: float | None = float(roc_auc_score(truth, scores))
        balanced_accuracy: float | None = float(balanced_accuracy_score(truth, predictions))
    else:
        roc_auc = None
        balanced_accuracy = None
    if len(np.unique(truth)) == 2:
        precisions, recalls, _ = precision_recall_curve(truth, scores)
        average_precision = float(average_precision_score(truth, scores))
        pr_auc_trapezoid = float(auc(recalls, precisions))
    else:
        average_precision = None
        pr_auc_trapezoid = None
    return {
        "rows": int(len(truth)),
        "positive_count": int(positives),
        "negative_count": int(negatives),
        "fraud_prevalence": float(truth.mean()),
        "average_precision": average_precision,
        "pr_auc_trapezoid": pr_auc_trapezoid,
        "roc_auc": roc_auc,
        "threshold": float(threshold),
        "precision": precision,
        "recall": recall,
        "f1": float(f1_score(truth, predictions, zero_division=0)),
        "f2": float(fbeta_score(truth, predictions, beta=2, zero_division=0)),
        "specificity": float(tn / negatives) if negatives else None,
        "balanced_accuracy": balanced_accuracy,
        "accuracy": float(accuracy_score(truth, predictions)),
        "brier_score": float(brier_score_loss(truth, scores)),
        "log_loss": float(log_loss(truth, scores, labels=[0, 1])),
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "true_positive": tp,
        "alert_count": int(predictions.sum()),
        "alert_percentage": float(100 * predictions.mean()),
        "recall_wilson_95_ci": wilson_interval(tp, positives),
        "precision_wilson_95_ci": wilson_interval(tp, tp + fp),
    }


def alert_budget_metrics(
    y_true: Iterable[int],
    scores: Iterable[float],
    *,
    budgets: tuple[float, ...] = (0.1, 0.5, 1.0),
) -> list[dict[str, Any]]:
    """Measure exact top-K alert capacity; ties use original row order deterministically."""
    truth = np.asarray(list(y_true), dtype=np.int8)
    values = np.asarray(list(scores), dtype=np.float64)
    if truth.ndim != 1 or values.ndim != 1 or len(truth) != len(values) or not len(truth):
        raise ValueError("y_true and scores must be nonempty aligned arrays")
    if not np.isfinite(values).all():
        raise ValueError("scores must be finite")
    if any(not 0 < budget <= 100 for budget in budgets):
        raise ValueError("alert budgets must be percentages in (0, 100]")
    order = np.argsort(-values, kind="stable")
    total_positive = int(truth.sum())
    output = []
    for budget in budgets:
        k = min(len(truth), max(1, int(np.ceil(len(truth) * budget / 100))))
        captured = int(truth[order[:k]].sum())
        output.append(
            {
                "budget_percentage": float(budget),
                "k": int(k),
                "alerts": int(k),
                "true_positives": captured,
                "precision_at_k": float(captured / k),
                "recall_at_k": float(captured / total_positive) if total_positive else None,
            }
        )
    return output


def threshold_table(
    y_true: Iterable[int],
    probabilities: Iterable[float],
    *,
    selected_threshold: float,
    grid_size: int = 101,
) -> list[dict[str, Any]]:
    """Build a compact threshold curve including the selected operating point."""
    scores = np.asarray(list(probabilities), dtype=np.float64)
    truth = np.asarray(list(y_true), dtype=np.int8)
    if grid_size < 3:
        raise ValueError("grid_size must be at least 3")
    thresholds = np.unique(
        np.concatenate(
            [np.quantile(scores, np.linspace(0, 1, grid_size)), np.asarray([selected_threshold])]
        )
    )
    return [
        {
            "threshold": float(value),
            **{
                key: classification_metrics(truth, scores, threshold=float(value))[key]
                for key in (
                    "precision",
                    "recall",
                    "f1",
                    "f2",
                    "false_positive",
                    "false_negative",
                    "alert_count",
                    "alert_percentage",
                )
            },
        }
        for value in thresholds
    ]
