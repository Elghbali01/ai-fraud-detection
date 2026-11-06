"""Mission 02 model, metric, calibration, and threshold behavior."""

from __future__ import annotations

import numpy as np
import pytest
from sklearn.base import clone

from fraud_detection.ml.baselines import make_candidates
from fraud_detection.ml.calibration import apply_sigmoid_calibrator, fit_sigmoid_calibrator
from fraud_detection.ml.evaluation import alert_budget_metrics, classification_metrics
from fraud_detection.ml.preprocessing import make_logistic_pipeline
from fraud_detection.ml.thresholds import select_threshold
from fraud_detection.ml.training import benchmark_candidates, select_candidate
from fraud_detection.schema import FEATURE_COLUMNS
from tests.ml_helpers import make_transaction_frame


def test_all_declared_model_families_train_and_return_probabilities():
    frame = make_transaction_frame(120)
    benchmark = benchmark_candidates(frame, cv_splits=3)
    names = {row["family"] for row in benchmark.candidate_metrics}
    assert names == {
        "DummyClassifier",
        "LogisticRegression",
        "RandomForestClassifier",
        "HistGradientBoostingClassifier",
    }
    assert len(benchmark.candidate_metrics) == 8
    assert benchmark.selected_name in benchmark.candidates
    for _candidate, folds in benchmark.fold_predictions.items():
        assert len(folds) == 3
        for fold in folds:
            assert fold["scores"].shape == fold["y_true"].shape
            assert np.isfinite(fold["scores"]).all()
            assert np.all((fold["scores"] >= 0) & (fold["scores"] <= 1))


def test_one_standard_error_selection_prefers_the_simpler_candidate():
    candidates = [
        {
            "candidate": "complex",
            "complexity": 3,
            "mean_average_precision": 0.50,
            "std_average_precision": 0.09,
            "fold_average_precision": [0.41, 0.50, 0.59],
        },
        {
            "candidate": "simple",
            "complexity": 1,
            "mean_average_precision": 0.48,
            "std_average_precision": 0.08,
            "fold_average_precision": [0.40, 0.48, 0.56],
        },
    ]
    selected, details = select_candidate(candidates)
    assert selected == "simple"
    assert details["maximum_candidate"] == "complex"


def test_scaler_is_fitted_only_on_the_rows_passed_to_the_training_pipeline():
    frame = make_transaction_frame(120)
    training = frame.iloc[:80]
    full_features = frame.loc[:, list(FEATURE_COLUMNS)]
    pipeline = make_logistic_pipeline(c_value=1.0, class_weight=None)
    pipeline.fit(training.loc[:, list(FEATURE_COLUMNS)], training["Class"])
    fitted_mean = pipeline.named_steps["scaler"].mean_
    training_mean = training.loc[:, list(FEATURE_COLUMNS)].mean().to_numpy()
    full_mean = full_features.mean().to_numpy()
    assert np.allclose(fitted_mean, training_mean)
    assert not np.allclose(fitted_mean, full_mean)


def test_random_forest_predictions_are_reproducible_for_fixed_seed():
    frame = make_transaction_frame(120)
    candidate = next(item for item in make_candidates() if item.name == "random_forest_balanced")
    features = frame.loc[:, list(FEATURE_COLUMNS)]
    first = clone(candidate.estimator).fit(features, frame["Class"]).predict_proba(features)
    second = clone(candidate.estimator).fit(features, frame["Class"]).predict_proba(features)
    assert np.allclose(first, second, rtol=0, atol=1e-15)


def test_classification_metrics_include_counts_and_distinguish_pr_areas():
    result = classification_metrics(
        [0, 0, 1, 1],
        [0.1, 0.8, 0.2, 0.9],
        threshold=0.5,
    )
    assert (result["true_negative"], result["false_positive"]) == (1, 1)
    assert (result["false_negative"], result["true_positive"]) == (1, 1)
    assert result["precision"] == 0.5
    assert result["recall"] == 0.5
    assert result["average_precision"] != result["pr_auc_trapezoid"]
    assert result["recall_wilson_95_ci"] is not None


def test_single_class_metrics_are_defined_without_a_roc_auc():
    result = classification_metrics([0, 0, 0], [0.01, 0.2, 0.3], threshold=0.5)
    assert result["roc_auc"] is None
    assert result["balanced_accuracy"] is None
    assert result["false_positive"] == 0
    assert np.isfinite(result["log_loss"])


def test_alert_budgets_have_exact_declared_k():
    metrics = alert_budget_metrics([0] * 98 + [1, 1], np.arange(100, dtype=float))
    assert [row["k"] for row in metrics] == [1, 1, 1]
    assert metrics[-1]["true_positives"] == 1


def test_threshold_policies_and_infeasible_constraints_are_explicit():
    labels = np.asarray([0, 0, 1, 1])
    scores = np.asarray([0.05, 0.15, 0.4, 0.9])
    f2 = select_threshold(labels, scores, policy="max_f2")
    assert f2.metrics["recall"] == 1
    assert (
        select_threshold(labels, scores, policy="min_recall", min_recall=0.5).metrics["recall"]
        >= 0.5
    )
    assert (
        select_threshold(
            labels,
            scores,
            policy="min_precision",
            min_precision=0.5,
        ).metrics["precision"]
        >= 0.5
    )
    budget = select_threshold(
        labels,
        scores,
        policy="alert_budget",
        alert_budget_percentage=25,
    )
    assert budget.metrics["alert_count"] <= 1
    with pytest.raises(ValueError, match="explicit false-positive"):
        select_threshold(labels, scores, policy="cost_sensitive")
    with pytest.raises(ValueError, match="infeasible"):
        select_threshold(
            np.asarray([1, 0, 0]),
            np.asarray([0.1, 0.9, 0.8]),
            policy="min_precision",
            min_precision=0.9,
        )


def test_sigmoid_calibration_returns_bounded_values_and_rejects_one_class_fit():
    labels = np.asarray([0] * 80 + [1] * 20)
    scores = np.concatenate([np.linspace(0.01, 0.4, 80), np.linspace(0.2, 0.9, 20)])
    calibrator = fit_sigmoid_calibrator(scores, labels)
    calibrated = apply_sigmoid_calibrator(calibrator, np.asarray([0.0, 0.5, 1.0]))
    assert np.isfinite(calibrated).all()
    assert np.all((calibrated >= 0) & (calibrated <= 1))
    with pytest.raises(ValueError, match="both labels"):
        fit_sigmoid_calibrator(np.asarray([0.1, 0.2]), np.asarray([0, 0]))
