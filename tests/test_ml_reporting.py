"""Synthetic report rendering smoke coverage without claiming ULB evidence."""

from __future__ import annotations

import numpy as np

from fraud_detection.ml.evaluation import alert_budget_metrics, classification_metrics
from fraud_detection.ml.reporting import generate_ml_reports


def test_report_generator_writes_metric_tables_and_figures_from_supplied_results(tmp_path):
    validation_labels = np.asarray([0, 0, 1, 1])
    validation_scores = np.asarray([0.02, 0.3, 0.4, 0.9])
    test_labels = np.asarray([0, 0, 1, 1])
    test_scores = np.asarray([0.03, 0.2, 0.5, 0.8])
    anomaly_scores = np.asarray([0.1, 0.8, 0.4, 0.9])
    candidate_metrics = {
        "candidate": "logistic",
        "family": "LogisticRegression",
        "complexity": 1,
        "hyperparameters": {"C": 1.0},
        "fold_average_precision": [0.7, 0.8, 0.75],
        "mean_average_precision": 0.75,
        "std_average_precision": 0.05,
        "fold_roc_auc": [0.8, 0.85, 0.9],
        "mean_roc_auc": 0.85,
        "cv_fit_seconds": 1.2,
        "cv_prediction_seconds": 0.1,
        "warnings": [],
    }
    results = {
        "experiment_id": "synthetic-report-test",
        "created_at_utc": "2026-11-06T00:00:00+00:00",
        "dataset_sha256": "synthetic-only",
        "split_manifest": {
            "manifest_id": "synthetic-split",
            "development_folds": [{"validation_fraud": 2}],
            "partitions": {
                "train": {
                    "rows": 8,
                    "class_counts": {"0": 6, "1": 2},
                    "time_min": 0,
                    "time_max": 10,
                },
                "validation": {
                    "rows": 4,
                    "class_counts": {"0": 2, "1": 2},
                    "time_min": 11,
                    "time_max": 20,
                },
                "test": {
                    "rows": 4,
                    "class_counts": {"0": 2, "1": 2},
                    "time_min": 21,
                    "time_max": 30,
                },
            },
        },
        "candidate_metrics": [candidate_metrics],
        "model_validation": [
            {
                "candidate": "logistic",
                "metrics": classification_metrics(validation_labels, validation_scores),
                "fit_seconds": 1.0,
                "prediction_seconds": 0.1,
            }
        ],
        "selected_model": {
            "name": "logistic",
            "family": "LogisticRegression",
        },
        "selection": {"criterion": "synthetic test rule"},
        "calibration": {
            "method": "sigmoid",
            "raw": {
                "brier_score": 0.2,
                "log_loss": 0.6,
                "expected_calibration_error": 0.1,
                "probability_quantiles": {"median": 0.2},
            },
            "sigmoid": {
                "brier_score": 0.1,
                "log_loss": 0.4,
                "expected_calibration_error": 0.05,
                "probability_quantiles": {"median": 0.3},
            },
            "brier_improved": True,
            "log_loss_improved": True,
        },
        "threshold": {
            "threshold": 0.4,
            "policy": "max_f2",
        },
        "validation": {
            "metrics": classification_metrics(validation_labels, validation_scores, threshold=0.4),
            "alert_budgets": alert_budget_metrics(validation_labels, validation_scores),
        },
        "final_test": {
            "metrics": classification_metrics(test_labels, test_scores, threshold=0.4),
            "alert_budgets": alert_budget_metrics(test_labels, test_scores),
        },
        "anomaly": {
            "fit": {"fit_rows": 10},
            "validation": {"average_precision": 0.7, "roc_auc": 0.8},
            "final_test": {
                "average_precision": 0.6,
                "roc_auc": 0.75,
                "alert_budgets": alert_budget_metrics(test_labels, anomaly_scores),
            },
            "artifact": {
                "artifact_path": "synthetic/anomaly.joblib",
                "artifact_sha256": "synthetic-only",
            },
            "top_ranked_overlap_validation": [
                {"budget_percentage": row["budget_percentage"], "overlap_percentage_of_k": 50}
                for row in alert_budget_metrics(validation_labels, validation_scores)
            ],
            "top_ranked_overlap_final_test": [
                {"budget_percentage": row["budget_percentage"], "overlap_percentage_of_k": 50}
                for row in alert_budget_metrics(test_labels, test_scores)
            ],
        },
        "artifact": {
            "artifact_path": "synthetic/supervised.joblib",
            "artifact_sha256": "synthetic-only",
        },
        "threshold_table": [
            {"threshold": 0.2, "precision": 0.5, "recall": 1.0, "f2": 0.8},
            {"threshold": 0.4, "precision": 1.0, "recall": 1.0, "f2": 1.0},
        ],
        "registry_snapshot": [{"experiment_id": "synthetic-report-test"}],
    }
    plot_data = {
        "test_labels": test_labels,
        "test_probabilities": test_scores,
        "validation_labels": validation_labels,
        "validation_raw_probabilities": validation_scores,
        "validation_probabilities": validation_scores,
        "test_anomaly_scores": anomaly_scores,
    }

    generated = generate_ml_reports(results, plot_data, tmp_path)
    report = (tmp_path / "FINAL_MODEL_REPORT.md").read_text(encoding="utf-8")
    assert "Average Precision" in report
    assert "synthetic-report-test" not in report
    assert len([path for path in generated if path.suffix == ".png"]) == 9
    assert (tmp_path / "model_comparison.csv").is_file()
    assert (tmp_path / "EXPERIMENT_REGISTRY.json").is_file()
