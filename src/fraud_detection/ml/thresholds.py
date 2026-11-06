"""Decision-threshold selection on designated development labels."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class ThresholdResult:
    """A selected inclusive probability threshold and its development diagnostics."""

    threshold: float
    policy: str
    metrics: dict[str, Any]
    constraint_feasible: bool
    details: dict[str, Any]


def _candidate_counts(
    labels: np.ndarray, scores: np.ndarray
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    unique_scores = np.unique(scores)
    thresholds = np.unique(np.concatenate([unique_scores, np.asarray([1.0])]))
    positives = int(labels.sum())
    negatives = len(labels) - positives
    order = np.argsort(-scores, kind="stable")
    sorted_scores = scores[order]
    sorted_labels = labels[order]
    cumulative_tp = np.cumsum(sorted_labels == 1, dtype=np.int64)
    # For each inclusive threshold, count sorted scores greater than or equal to it.
    alert_counts = np.searchsorted(-sorted_scores, -thresholds, side="right")
    tp = np.zeros(len(thresholds), dtype=np.int64)
    nonzero = alert_counts > 0
    tp[nonzero] = cumulative_tp[alert_counts[nonzero] - 1]
    fp = alert_counts - tp
    fn = positives - tp
    tn = negatives - fp
    precision = np.divide(tp, tp + fp, out=np.zeros_like(tp, dtype=np.float64), where=(tp + fp) > 0)
    recall = np.divide(tp, positives, out=np.zeros_like(tp, dtype=np.float64), where=positives > 0)
    f1 = np.divide(
        2 * precision * recall,
        precision + recall,
        out=np.zeros_like(precision),
        where=(precision + recall) > 0,
    )
    f2 = np.divide(
        5 * precision * recall,
        4 * precision + recall,
        out=np.zeros_like(precision),
        where=(4 * precision + recall) > 0,
    )
    return thresholds, {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "f2": f2,
        "alerts": alert_counts,
    }


def select_threshold(
    labels: np.ndarray,
    probabilities: np.ndarray,
    *,
    policy: str = "max_f2",
    min_recall: float | None = None,
    min_precision: float | None = None,
    alert_budget_percentage: float | None = None,
    false_positive_cost: float | None = None,
    false_negative_cost: float | None = None,
) -> ThresholdResult:
    """Select a threshold under an explicit objective, using development data only.

    Supported policies are ``max_f1``, ``max_f2``, ``min_recall`` (maximize
    precision subject to the supplied recall floor), ``min_precision`` (maximize
    recall subject to the supplied precision floor), ``alert_budget`` and
    ``cost_sensitive``. Infeasible constraints raise ValueError with attainable
    bounds instead of returning an unlabelled fallback.
    """
    truth = np.asarray(labels, dtype=np.int8)
    scores = np.asarray(probabilities, dtype=np.float64)
    if truth.ndim != 1 or scores.ndim != 1 or len(truth) != len(scores) or not len(truth):
        raise ValueError("labels and probabilities must be nonempty aligned vectors")
    if not np.isin(truth, [0, 1]).all() or not np.isfinite(scores).all():
        raise ValueError("labels must be binary and probabilities finite")
    if np.any((scores < 0) | (scores > 1)):
        raise ValueError("probabilities must be in [0, 1]")
    thresholds, values = _candidate_counts(truth, scores)

    if policy in {"max_f1", "max_f2"}:
        objective = values["f1" if policy == "max_f1" else "f2"]
        best_value = objective.max()
        feasible = np.flatnonzero(objective == best_value)
        # Prefer fewer alerts, then the higher threshold when scores tie.
        chosen = min(feasible, key=lambda index: (values["alerts"][index], -thresholds[index]))
        details = {"objective": policy, "objective_value": float(best_value)}
    elif policy == "min_recall":
        if min_recall is None or not 0 <= min_recall <= 1:
            raise ValueError("min_recall policy requires min_recall in [0, 1]")
        eligible = np.flatnonzero(values["recall"] >= min_recall)
        if not len(eligible):
            raise ValueError(
                f"Recall constraint {min_recall} is infeasible; maximum attainable recall is "
                f"{float(values['recall'].max()):.6f}"
            )
        chosen = min(
            eligible,
            key=lambda index: (
                -values["precision"][index],
                values["alerts"][index],
                -thresholds[index],
            ),
        )
        details = {"minimum_recall": min_recall, "objective": "maximum precision"}
    elif policy == "min_precision":
        if min_precision is None or not 0 <= min_precision <= 1:
            raise ValueError("min_precision policy requires min_precision in [0, 1]")
        eligible = np.flatnonzero(values["precision"] >= min_precision)
        if not len(eligible):
            raise ValueError(
                f"Precision constraint {min_precision} is infeasible; "
                "maximum attainable precision is "
                f"{float(values['precision'].max()):.6f}"
            )
        chosen = min(
            eligible,
            key=lambda index: (
                -values["recall"][index],
                values["alerts"][index],
                -thresholds[index],
            ),
        )
        details = {"minimum_precision": min_precision, "objective": "maximum recall"}
    elif policy == "alert_budget":
        if alert_budget_percentage is None or not 0 < alert_budget_percentage <= 100:
            raise ValueError("alert_budget policy requires alert_budget_percentage in (0, 100]")
        max_alerts = max(1, int(np.floor(len(truth) * alert_budget_percentage / 100)))
        eligible = np.flatnonzero(values["alerts"] <= max_alerts)
        chosen = min(
            eligible,
            key=lambda index: (
                -values["recall"][index],
                values["alerts"][index],
                -thresholds[index],
            ),
        )
        details = {
            "alert_budget_percentage": alert_budget_percentage,
            "maximum_alerts": max_alerts,
            "objective": "maximum recall without exceeding capacity",
        }
    elif policy == "cost_sensitive":
        if false_positive_cost is None or false_negative_cost is None:
            raise ValueError(
                "cost_sensitive policy requires explicit false-positive and false-negative costs"
            )
        if (
            false_positive_cost < 0
            or false_negative_cost < 0
            or not (false_positive_cost + false_negative_cost)
        ):
            raise ValueError("Explicit error costs must be nonnegative and not both zero")
        costs = values["fp"] * false_positive_cost + values["fn"] * false_negative_cost
        minimum = costs.min()
        feasible = np.flatnonzero(costs == minimum)
        chosen = min(feasible, key=lambda index: (values["alerts"][index], -thresholds[index]))
        details = {
            "false_positive_cost": false_positive_cost,
            "false_negative_cost": false_negative_cost,
            "minimum_total_cost": float(minimum),
            "cost_semantics": "user-supplied scenario; not a measured business cost",
        }
    else:
        raise ValueError(f"Unsupported threshold policy: {policy}")

    tp, fp, fn, tn = (int(values[key][chosen]) for key in ("tp", "fp", "fn", "tn"))
    alerts = tp + fp
    metrics = {
        "precision": float(values["precision"][chosen]),
        "recall": float(values["recall"][chosen]),
        "f1": float(values["f1"][chosen]),
        "f2": float(values["f2"][chosen]),
        "false_positive": fp,
        "false_negative": fn,
        "true_positive": tp,
        "true_negative": tn,
        "alert_count": alerts,
        "alert_percentage": float(100 * alerts / len(truth)),
    }
    return ThresholdResult(
        threshold=float(thresholds[chosen]),
        policy=policy,
        metrics=metrics,
        constraint_feasible=True,
        details=details,
    )
