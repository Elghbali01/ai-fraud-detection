"""Cross-fitted sigmoid probability calibration and reliability summaries."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss


def _logit(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, 1e-7, 1 - 1e-7)
    return np.log(clipped / (1 - clipped)).reshape(-1, 1)


def fit_sigmoid_calibrator(
    out_of_fold_scores: np.ndarray,
    out_of_fold_labels: np.ndarray,
) -> LogisticRegression:
    """Fit a one-dimensional Platt mapping to held-out training-fold scores only."""
    scores = np.asarray(out_of_fold_scores, dtype=np.float64)
    labels = np.asarray(out_of_fold_labels, dtype=np.int8)
    if scores.ndim != 1 or labels.ndim != 1 or len(scores) != len(labels) or len(scores) == 0:
        raise ValueError("out-of-fold scores and labels must be aligned nonempty vectors")
    if not np.isfinite(scores).all() or np.any((scores < 0) | (scores > 1)):
        raise ValueError("out-of-fold scores must be finite values in [0, 1]")
    if set(np.unique(labels)) != {0, 1}:
        raise ValueError("sigmoid calibration requires both labels in out-of-fold data")
    calibrator = LogisticRegression(C=1.0, max_iter=1_000, solver="lbfgs", random_state=17)
    calibrator.fit(_logit(scores), labels)
    return calibrator


def apply_sigmoid_calibrator(
    calibrator: LogisticRegression,
    probabilities: np.ndarray,
) -> np.ndarray:
    """Map estimator probabilities using the fitted sigmoid calibration model."""
    values = np.asarray(probabilities, dtype=np.float64)
    if values.ndim != 1 or not np.isfinite(values).all() or np.any((values < 0) | (values > 1)):
        raise ValueError("probabilities must be a finite one-dimensional vector in [0, 1]")
    return calibrator.predict_proba(_logit(values))[:, 1]


def expected_calibration_error(
    labels: np.ndarray,
    probabilities: np.ndarray,
    *,
    bins: int = 10,
) -> float:
    """Return equal-frequency expected calibration error for compact diagnostics."""
    truth = np.asarray(labels, dtype=np.int8)
    scores = np.asarray(probabilities, dtype=np.float64)
    if len(truth) != len(scores) or not len(truth) or bins < 2:
        raise ValueError("labels and probabilities must align and bins must be at least two")
    edges = np.quantile(scores, np.linspace(0, 1, min(bins, len(scores)) + 1))
    edges = np.unique(edges)
    if len(edges) < 2:
        return float(abs(truth.mean() - scores.mean()))
    bin_ids = np.searchsorted(edges[1:-1], scores, side="right")
    error = 0.0
    for bin_id in np.unique(bin_ids):
        mask = bin_ids == bin_id
        error += mask.mean() * abs(float(truth[mask].mean() - scores[mask].mean()))
    return float(error)


def calibration_summary(
    labels: np.ndarray,
    raw_probabilities: np.ndarray,
    calibrated_probabilities: np.ndarray,
) -> dict[str, Any]:
    """Compare uncalibrated and sigmoid outputs on a designated evaluation split."""
    truth = np.asarray(labels, dtype=np.int8)
    raw = np.asarray(raw_probabilities, dtype=np.float64)
    calibrated = np.asarray(calibrated_probabilities, dtype=np.float64)
    if len(truth) != len(raw) or len(truth) != len(calibrated) or not len(truth):
        raise ValueError("Calibration labels and probability arrays must have equal nonzero size")

    def quantiles(values: np.ndarray) -> dict[str, float]:
        positions = np.asarray([0.0, 0.5, 0.9, 0.99, 1.0])
        quantile_values = np.quantile(values, positions)
        names = ("min", "median", "p90", "p99", "max")
        return {name: float(value) for name, value in zip(names, quantile_values, strict=True)}

    return {
        "evaluation_rows": int(len(truth)),
        "evaluation_fraud_count": int(truth.sum()),
        "method": (
            "one-dimensional sigmoid (Platt), fit on training-only expanding-fold predictions"
        ),
        "raw": {
            "brier_score": float(brier_score_loss(truth, raw)),
            "log_loss": float(log_loss(truth, raw, labels=[0, 1])),
            "expected_calibration_error": expected_calibration_error(truth, raw),
            "probability_quantiles": quantiles(raw),
        },
        "sigmoid": {
            "brier_score": float(brier_score_loss(truth, calibrated)),
            "log_loss": float(log_loss(truth, calibrated, labels=[0, 1])),
            "expected_calibration_error": expected_calibration_error(truth, calibrated),
            "probability_quantiles": quantiles(calibrated),
        },
        "brier_improved": bool(brier_score_loss(truth, calibrated) < brier_score_loss(truth, raw)),
        "log_loss_improved": bool(
            log_loss(truth, calibrated, labels=[0, 1]) < log_loss(truth, raw, labels=[0, 1])
        ),
        "isotonic_status": (
            "not fitted: limited positive count makes a flexible mapping prone to overfit"
        ),
    }
