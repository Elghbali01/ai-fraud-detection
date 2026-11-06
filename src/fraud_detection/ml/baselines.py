"""Bounded, reproducible supervised candidate definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sklearn.base import ClassifierMixin
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier

from fraud_detection.ml.preprocessing import make_logistic_pipeline

SEED = 17


@dataclass(frozen=True)
class ModelCandidate:
    """A named, fixed hyperparameter candidate for the Mission 02 benchmark."""

    name: str
    family: str
    complexity: int
    parameters: dict[str, Any]
    estimator: ClassifierMixin


def make_candidates(*, random_state: int = SEED) -> list[ModelCandidate]:
    """Return the declared baseline and bounded model comparison candidates."""
    # The logistic pipeline's seed is fixed in the package factory for stability.
    candidates = [
        ModelCandidate(
            name="dummy_prior",
            family="DummyClassifier",
            complexity=0,
            parameters={"strategy": "prior"},
            estimator=DummyClassifier(strategy="prior"),
        ),
        ModelCandidate(
            name="logistic_unweighted_c0_1",
            family="LogisticRegression",
            complexity=1,
            parameters={"C": 0.1, "class_weight": None, "scaler": "StandardScaler"},
            estimator=make_logistic_pipeline(c_value=0.1, class_weight=None),
        ),
        ModelCandidate(
            name="logistic_unweighted_c1",
            family="LogisticRegression",
            complexity=1,
            parameters={"C": 1.0, "class_weight": None, "scaler": "StandardScaler"},
            estimator=make_logistic_pipeline(c_value=1.0, class_weight=None),
        ),
        ModelCandidate(
            name="logistic_balanced_c1",
            family="LogisticRegression",
            complexity=1,
            parameters={"C": 1.0, "class_weight": "balanced", "scaler": "StandardScaler"},
            estimator=make_logistic_pipeline(c_value=1.0, class_weight="balanced"),
        ),
    ]
    for class_weight, label in ((None, "unweighted"), ("balanced_subsample", "balanced")):
        parameters = {
            "n_estimators": 100,
            "max_depth": 16,
            "min_samples_leaf": 2,
            "max_features": "sqrt",
            "class_weight": class_weight,
            "n_jobs": 2,
            "random_state": random_state,
        }
        candidates.append(
            ModelCandidate(
                name=f"random_forest_{label}",
                family="RandomForestClassifier",
                complexity=2,
                parameters=parameters,
                estimator=RandomForestClassifier(**parameters),
            )
        )
    for class_weight, label in ((None, "unweighted"), ("balanced", "balanced")):
        parameters = {
            "learning_rate": 0.08,
            "max_iter": 100,
            "max_leaf_nodes": 15,
            "l2_regularization": 1.0,
            "class_weight": class_weight,
            "early_stopping": False,
            "random_state": random_state,
        }
        candidates.append(
            ModelCandidate(
                name=f"hist_gradient_boosting_{label}",
                family="HistGradientBoostingClassifier",
                complexity=3,
                parameters=parameters,
                estimator=HistGradientBoostingClassifier(**parameters),
            )
        )
    return candidates
