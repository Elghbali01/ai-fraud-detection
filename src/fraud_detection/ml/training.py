"""Time-aware cross-validation, bounded candidate comparison, and selection."""

from __future__ import annotations

import logging
import time
import warnings
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import average_precision_score, roc_auc_score

from fraud_detection.ml.baselines import ModelCandidate, make_candidates
from fraud_detection.ml.splitting import make_expanding_time_folds
from fraud_detection.schema import FEATURE_COLUMNS, TARGET_COLUMN

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class BenchmarkResult:
    """Candidate metrics plus selected-candidate out-of-fold predictions."""

    candidate_metrics: list[dict[str, Any]]
    candidates: dict[str, ModelCandidate]
    fold_predictions: dict[str, list[dict[str, np.ndarray]]]
    selected_name: str
    selection_details: dict[str, Any]


def benchmark_candidates(
    training_frame: pd.DataFrame,
    *,
    random_state: int = 17,
    cv_splits: int = 3,
) -> BenchmarkResult:
    """Compare fixed candidates on identical expanding-window training folds."""
    folds = make_expanding_time_folds(training_frame, n_splits=cv_splits)
    candidates = {
        candidate.name: candidate for candidate in make_candidates(random_state=random_state)
    }
    all_predictions: dict[str, list[dict[str, np.ndarray]]] = {}
    metrics: list[dict[str, Any]] = []
    for candidate_index, candidate in enumerate(candidates.values(), start=1):
        LOGGER.info(
            "Training candidate %s/%s: %s",
            candidate_index,
            len(candidates),
            candidate.name,
        )
        fold_aps: list[float] = []
        fold_rocs: list[float | None] = []
        predictions: list[dict[str, np.ndarray]] = []
        fit_seconds = 0.0
        prediction_seconds = 0.0
        recorded_warnings: set[str] = set()
        for fold in folds:
            fit_rows = training_frame.iloc[fold.fit_positions]
            validation_rows = training_frame.iloc[fold.validation_positions]
            estimator = clone(candidate.estimator)
            started = time.perf_counter()
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                estimator.fit(fit_rows.loc[:, list(FEATURE_COLUMNS)], fit_rows[TARGET_COLUMN])
            fit_seconds += time.perf_counter() - started
            recorded_warnings.update(str(item.message) for item in caught)
            started = time.perf_counter()
            scores = estimator.predict_proba(validation_rows.loc[:, list(FEATURE_COLUMNS)])[:, 1]
            prediction_seconds += time.perf_counter() - started
            truth = validation_rows[TARGET_COLUMN].to_numpy(dtype=np.int8)
            fold_aps.append(float(average_precision_score(truth, scores)))
            fold_rocs.append(float(roc_auc_score(truth, scores)))
            predictions.append({"y_true": truth, "scores": np.asarray(scores, dtype=np.float64)})
            LOGGER.info(
                "Candidate %s fold %s: AP=%.5f, fit_rows=%s, validation_rows=%s",
                candidate.name,
                fold.metadata["fold"],
                fold_aps[-1],
                fold.metadata["fit_rows"],
                fold.metadata["validation_rows"],
            )
        all_predictions[candidate.name] = predictions
        metrics.append(
            {
                "candidate": candidate.name,
                "family": candidate.family,
                "complexity": candidate.complexity,
                "hyperparameters": candidate.parameters,
                "fold_average_precision": fold_aps,
                "mean_average_precision": float(np.mean(fold_aps)),
                "std_average_precision": float(np.std(fold_aps, ddof=1))
                if len(fold_aps) > 1
                else 0.0,
                "fold_roc_auc": fold_rocs,
                "mean_roc_auc": float(np.mean([value for value in fold_rocs if value is not None])),
                "cv_fit_seconds": round(fit_seconds, 6),
                "cv_prediction_seconds": round(prediction_seconds, 6),
                "warnings": sorted(recorded_warnings),
            }
        )
    selected_name, selection_details = select_candidate(metrics)
    return BenchmarkResult(
        candidate_metrics=metrics,
        candidates=candidates,
        fold_predictions=all_predictions,
        selected_name=selected_name,
        selection_details=selection_details,
    )


def select_candidate(candidate_metrics: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    """Apply a one-standard-error rule, preferring the simplest competitive model."""
    if not candidate_metrics:
        raise ValueError("At least one candidate is required")
    best = max(candidate_metrics, key=lambda item: item["mean_average_precision"])
    folds = len(best["fold_average_precision"])
    standard_error = best["std_average_precision"] / np.sqrt(folds) if folds else 0.0
    floor = best["mean_average_precision"] - standard_error
    eligible = [item for item in candidate_metrics if item["mean_average_precision"] >= floor]
    chosen = min(
        eligible,
        key=lambda item: (
            item["complexity"],
            -item["mean_average_precision"],
            item["candidate"],
        ),
    )
    details = {
        "criterion": "one-standard-error rule; simplest candidate within one SE of maximum mean AP",
        "maximum_mean_average_precision": float(best["mean_average_precision"]),
        "maximum_candidate": best["candidate"],
        "standard_error": float(standard_error),
        "eligibility_floor": float(floor),
        "eligible_candidates": [item["candidate"] for item in eligible],
        "selected_candidate": chosen["candidate"],
    }
    return chosen["candidate"], details
