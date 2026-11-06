"""Separate Isolation Forest experiment with explicit anomaly-score semantics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, roc_auc_score

from fraud_detection.ml.evaluation import alert_budget_metrics
from fraud_detection.schema import FEATURE_COLUMNS, TARGET_COLUMN


@dataclass(frozen=True)
class AnomalyExperiment:
    """Isolation Forest fitted to known legitimate training rows."""

    estimator: IsolationForest
    metadata: dict[str, Any]


def fit_isolation_forest(
    training_frame: pd.DataFrame,
    *,
    random_state: int = 17,
) -> AnomalyExperiment:
    """Fit Isolation Forest on Class 0 training rows; exclude the target from inputs."""
    legitimate = training_frame.loc[training_frame[TARGET_COLUMN].eq(0), list(FEATURE_COLUMNS)]
    if len(legitimate) < 2:
        raise ValueError("Isolation Forest requires at least two legitimate training rows")
    estimator = IsolationForest(
        n_estimators=100,
        max_samples=min(256, len(legitimate)),
        contamination="auto",
        random_state=random_state,
        n_jobs=2,
    )
    estimator.fit(legitimate)
    return AnomalyExperiment(
        estimator=estimator,
        metadata={
            "fit_rows": int(len(legitimate)),
            "fit_positive_rows": 0,
            "training_label_filter": "Class == 0 rows from training partition only",
            "features": list(FEATURE_COLUMNS),
            "feature_columns": list(FEATURE_COLUMNS),
            "score_definition": "higher = more anomalous; score is -IsolationForest.score_samples",
            "parameters": estimator.get_params(deep=False),
        },
    )


def anomaly_scores(
    experiment: AnomalyExperiment | IsolationForest, features: pd.DataFrame
) -> np.ndarray:
    """Return continuous anomaly scores where larger values mean more unusual."""
    estimator = experiment.estimator if isinstance(experiment, AnomalyExperiment) else experiment
    return -estimator.score_samples(features.loc[:, list(FEATURE_COLUMNS)])


def evaluate_anomaly_ranking(labels: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    """Evaluate anomaly ranking without treating scores as probabilities."""
    truth = np.asarray(labels, dtype=np.int8)
    values = np.asarray(scores, dtype=np.float64)
    if truth.ndim != 1 or values.ndim != 1 or len(truth) != len(values) or not len(truth):
        raise ValueError("labels and anomaly scores must be aligned nonempty vectors")
    result: dict[str, Any] = {
        "rows": int(len(truth)),
        "fraud_count": int(truth.sum()),
        "score_direction": "higher = more anomalous",
        "score_is_probability": False,
        "average_precision": float(average_precision_score(truth, values)),
        "alert_budgets": alert_budget_metrics(truth, values),
    }
    result["roc_auc"] = float(roc_auc_score(truth, values)) if np.unique(truth).size == 2 else None
    return result


def compare_top_ranked_overlap(
    supervised_scores: np.ndarray,
    anomaly_values: np.ndarray,
    *,
    budgets: tuple[float, ...] = (0.1, 0.5, 1.0),
) -> list[dict[str, Any]]:
    """Compare the top-ranked row sets without combining the two score scales."""
    supervised = np.asarray(supervised_scores, dtype=np.float64)
    anomaly = np.asarray(anomaly_values, dtype=np.float64)
    if supervised.ndim != 1 or anomaly.ndim != 1 or len(supervised) != len(anomaly):
        raise ValueError("supervised and anomaly score vectors must align")
    output = []
    for budget in budgets:
        k = min(len(supervised), max(1, int(np.ceil(len(supervised) * budget / 100))))
        supervised_top = set(np.argsort(-supervised, kind="stable")[:k].tolist())
        anomaly_top = set(np.argsort(-anomaly, kind="stable")[:k].tolist())
        intersection = len(supervised_top & anomaly_top)
        union = len(supervised_top | anomaly_top)
        output.append(
            {
                "budget_percentage": float(budget),
                "k": int(k),
                "overlap_count": int(intersection),
                "overlap_percentage_of_k": float(100 * intersection / k),
                "jaccard": float(intersection / union) if union else 1.0,
            }
        )
    return output
