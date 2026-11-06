"""End-to-end reproducible Mission 02 training and sealed evaluation workflow."""

from __future__ import annotations

import json
import logging
import platform
import time
import warnings
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone

from fraud_detection.loading import load_ulb_csv
from fraud_detection.ml.anomaly import (
    anomaly_scores,
    compare_top_ranked_overlap,
    evaluate_anomaly_ranking,
    fit_isolation_forest,
)
from fraud_detection.ml.calibration import (
    apply_sigmoid_calibrator,
    calibration_summary,
    fit_sigmoid_calibrator,
)
from fraud_detection.ml.evaluation import (
    alert_budget_metrics,
    classification_metrics,
    threshold_table,
)
from fraud_detection.ml.persistence import (
    ModelBundle,
    save_anomaly_artifact,
    save_model_bundle,
)
from fraud_detection.ml.preprocessing import validate_features
from fraud_detection.ml.registry import append_experiment, current_git_revision, new_experiment_id
from fraud_detection.ml.reporting import generate_ml_reports
from fraud_detection.ml.splitting import create_temporal_split, write_split_manifest
from fraud_detection.ml.thresholds import select_threshold
from fraud_detection.ml.training import BenchmarkResult, benchmark_candidates
from fraud_detection.provenance import (
    MISSION01_ULB_SHA256,
    has_verified_kaggle_provenance,
)
from fraud_detection.provenance import (
    sha256_file as dataset_sha256_file,
)
from fraud_detection.schema import FEATURE_COLUMNS, TARGET_COLUMN

LOGGER = logging.getLogger(__name__)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, allow_nan=False, default=_json_default) + "\n", encoding="utf-8"
    )


def _json_default(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def _frozen_split_manifest(frame: pd.DataFrame, source: Path, output: Path):
    checksum = dataset_sha256_file(source)
    if not has_verified_kaggle_provenance(source):
        raise ValueError(
            "ML training requires a CSV that matches the verified local ULB provenance sidecar"
        )
    if checksum != MISSION01_ULB_SHA256:
        raise ValueError("The local ULB CSV differs from the Mission 01 SHA-256 baseline")
    split = create_temporal_split(frame, dataset_sha256=checksum)
    manifest_path = output / "split_manifest.json"
    if manifest_path.is_file():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("manifest_id") != split.manifest["manifest_id"]:
            raise ValueError(
                "Existing split manifest differs from the verified source or frozen protocol; "
                "refusing to train against a changed split"
            )
    else:
        write_split_manifest(split, manifest_path)
    return split


def _selected_oof_predictions(
    benchmark: BenchmarkResult,
) -> tuple[np.ndarray, np.ndarray]:
    folds = benchmark.fold_predictions[benchmark.selected_name]
    labels = np.concatenate([fold["y_true"] for fold in folds])
    scores = np.concatenate([fold["scores"] for fold in folds])
    return labels, scores


def run_ml_experiment(
    dataset_path: str | Path,
    *,
    output_directory: str | Path,
    artifact_directory: str | Path,
    random_state: int = 17,
    cv_splits: int = 3,
) -> dict[str, Any]:
    """Train the frozen candidate set, calibrate, select a threshold, and test once."""
    source = Path(dataset_path).resolve()
    output = Path(output_directory)
    artifact_root = Path(artifact_directory)
    output.mkdir(parents=True, exist_ok=True)
    artifact_root.mkdir(parents=True, exist_ok=True)

    frame = load_ulb_csv(source, strict_columns=True)
    source_hash = dataset_sha256_file(source)
    split = _frozen_split_manifest(frame, source, output)
    LOGGER.info("Verified ULB data and frozen split %s", split.manifest["manifest_id"])
    if cv_splits != len(split.manifest["development_folds"]):
        raise ValueError("cv_splits differs from the persisted, pre-training split manifest")
    train = frame.iloc[split.train_positions].copy()
    validation = frame.iloc[split.validation_positions].copy()
    # Test labels are deliberately not passed to any model-selection/calibration/threshold function.
    test = frame.iloc[split.test_positions].copy()

    workflow_started = time.perf_counter()
    benchmark = benchmark_candidates(train, random_state=random_state, cv_splits=cv_splits)
    candidate = benchmark.candidates[benchmark.selected_name]
    oof_labels, oof_scores = _selected_oof_predictions(benchmark)
    calibrator = fit_sigmoid_calibrator(oof_scores, oof_labels)
    LOGGER.info("Selected %s using training-only temporal folds", benchmark.selected_name)

    final_estimator = clone(candidate.estimator)
    final_fit_started = time.perf_counter()
    with warnings.catch_warnings(record=True) as fit_warnings:
        warnings.simplefilter("always")
        final_estimator.fit(train.loc[:, list(FEATURE_COLUMNS)], train[TARGET_COLUMN])
    final_fit_seconds = time.perf_counter() - final_fit_started

    validation_features = validate_features(validation.loc[:, list(FEATURE_COLUMNS)])
    validation_started = time.perf_counter()
    validation_raw = final_estimator.predict_proba(validation_features)[:, 1]
    validation_probabilities = apply_sigmoid_calibrator(calibrator, validation_raw)
    validation_prediction_seconds = time.perf_counter() - validation_started
    validation_labels = validation[TARGET_COLUMN].to_numpy(dtype=np.int8)
    calibration = calibration_summary(validation_labels, validation_raw, validation_probabilities)
    threshold_result = select_threshold(
        validation_labels,
        validation_probabilities,
        policy="max_f2",
    )
    validation_metrics = classification_metrics(
        validation_labels,
        validation_probabilities,
        threshold=threshold_result.threshold,
    )
    validation_budgets = alert_budget_metrics(validation_labels, validation_probabilities)
    threshold_points = threshold_table(
        validation_labels,
        validation_probabilities,
        selected_threshold=threshold_result.threshold,
    )

    experiment_id, created_at = new_experiment_id(candidate.name, split.manifest["manifest_id"])
    git_revision, dirty_worktree = current_git_revision(Path(__file__).resolve().parents[3])
    selection_freeze = {
        "experiment_id": experiment_id,
        "frozen_before_final_test_evaluation": True,
        "dataset_sha256": source_hash,
        "split_manifest_id": split.manifest["manifest_id"],
        "selected_model": {
            "name": candidate.name,
            "family": candidate.family,
            "hyperparameters": candidate.parameters,
        },
        "selection": benchmark.selection_details,
        "calibration": {
            "method": calibration["method"],
            "fit_rows": int(len(oof_labels)),
            "fit_fraud_rows": int(oof_labels.sum()),
            "fit_source": "held-out scores from expanding folds inside the training partition",
        },
        "threshold": {
            "policy": threshold_result.policy,
            "value": threshold_result.threshold,
            "validation_metrics": threshold_result.metrics,
            "constraint_feasible": threshold_result.constraint_feasible,
        },
        "preprocessing": {
            "features": list(FEATURE_COLUMNS),
            "logistic_scaler": (
                "StandardScaler fitted inside each training fold and final training partition"
            ),
            "tree_models": "no feature scaling",
            "resampling": "none",
        },
        "frozen_at_utc": created_at,
        "source_revision": git_revision,
        "source_worktree_dirty_at_fit": dirty_worktree,
    }
    freeze_path = output / "selection_freezes" / f"selection-freeze-{experiment_id}.json"
    _write_json(freeze_path, selection_freeze)
    LOGGER.info(
        "Selection frozen before final test: model=%s threshold=%.8g",
        candidate.name,
        threshold_result.threshold,
    )

    # Descriptive comparison only: these fixed-0.5 validation scores cannot change the freeze.
    model_validation: list[dict[str, Any]] = []
    for candidate_name, validation_candidate in benchmark.candidates.items():
        if candidate_name == candidate.name:
            estimator = final_estimator
            validation_fit_seconds = final_fit_seconds
            candidate_warning_messages = sorted({str(item.message) for item in fit_warnings})
        else:
            estimator = clone(validation_candidate.estimator)
            candidate_fit_started = time.perf_counter()
            with warnings.catch_warnings(record=True) as candidate_warnings:
                warnings.simplefilter("always")
                estimator.fit(train.loc[:, list(FEATURE_COLUMNS)], train[TARGET_COLUMN])
            validation_fit_seconds = time.perf_counter() - candidate_fit_started
            candidate_warning_messages = sorted({str(item.message) for item in candidate_warnings})
        candidate_prediction_started = time.perf_counter()
        candidate_scores = estimator.predict_proba(validation_features)[:, 1]
        candidate_prediction_seconds = time.perf_counter() - candidate_prediction_started
        model_validation.append(
            {
                "candidate": candidate_name,
                "family": validation_candidate.family,
                "reference_threshold": 0.5,
                "metrics": classification_metrics(
                    validation_labels, candidate_scores, threshold=0.5
                ),
                "fit_seconds": validation_fit_seconds,
                "prediction_seconds": candidate_prediction_seconds,
                "warnings": candidate_warning_messages,
            }
        )
        LOGGER.info(
            "Post-freeze validation comparison %s: AP=%.5f at fixed threshold 0.5",
            candidate_name,
            model_validation[-1]["metrics"]["average_precision"],
        )

    anomaly_started = time.perf_counter()
    anomaly_experiment = fit_isolation_forest(train, random_state=random_state)
    anomaly_fit_seconds = time.perf_counter() - anomaly_started
    LOGGER.info(
        "Isolation Forest fit completed on %s legitimate training rows",
        anomaly_experiment.metadata["fit_rows"],
    )
    validation_anomaly = anomaly_scores(
        anomaly_experiment, validation.loc[:, list(FEATURE_COLUMNS)]
    )
    validation_anomaly_metrics = evaluate_anomaly_ranking(validation_labels, validation_anomaly)
    validation_overlap = compare_top_ranked_overlap(validation_probabilities, validation_anomaly)

    # Open the sealed test outcome only after the selection freeze is durably written.
    test_features = validate_features(test.loc[:, list(FEATURE_COLUMNS)])
    test_started = time.perf_counter()
    test_raw = final_estimator.predict_proba(test_features)[:, 1]
    test_probabilities = apply_sigmoid_calibrator(calibrator, test_raw)
    supervised_test_prediction_seconds = time.perf_counter() - test_started
    test_labels = test[TARGET_COLUMN].to_numpy(dtype=np.int8)
    test_metrics = classification_metrics(
        test_labels,
        test_probabilities,
        threshold=threshold_result.threshold,
    )
    test_budgets = alert_budget_metrics(test_labels, test_probabilities)
    test_anomaly = anomaly_scores(anomaly_experiment, test_features)
    test_anomaly_metrics = evaluate_anomaly_ranking(test_labels, test_anomaly)
    test_overlap = compare_top_ranked_overlap(test_probabilities, test_anomaly)
    LOGGER.info("Sealed final-test metrics computed once after selection freeze")

    anomaly_experiment.metadata.update(
        {
            "model_version": f"mission02-anomaly:{experiment_id}",
            "schema_version": "ulb-credit-card-v1",
            "feature_columns": list(FEATURE_COLUMNS),
            "dataset_sha256": source_hash,
            "split_manifest_id": split.manifest["manifest_id"],
            "random_state": random_state,
            "scikit_learn_version": sklearn.__version__,
            "joblib_version": joblib.__version__,
            "validation_ranking_metrics": validation_anomaly_metrics,
            "final_test_ranking_metrics": test_anomaly_metrics,
        }
    )
    anomaly_artifact_path = artifact_root / f"{experiment_id}-isolation-forest.joblib"
    anomaly_artifact = save_anomaly_artifact(anomaly_experiment, anomaly_artifact_path)
    if anomaly_artifact_path.is_relative_to(Path.cwd()):
        anomaly_artifact["artifact_path"] = str(anomaly_artifact_path.relative_to(Path.cwd()))

    model_version = f"mission02:{experiment_id}"
    probability_status = (
        "sigmoid mapping fitted on training-only cross-fitted scores; validation "
        f"Brier improved={calibration['brier_improved']}, "
        f"log_loss improved={calibration['log_loss_improved']}"
    )
    code_revision, worktree_dirty = current_git_revision(Path(__file__).resolve().parents[3])
    model_metadata = {
        "model_version": model_version,
        "schema_version": "ulb-credit-card-v1",
        "feature_columns": list(FEATURE_COLUMNS),
        "target_column_excluded": TARGET_COLUMN,
        "dataset_sha256": source_hash,
        "split_manifest_id": split.manifest["manifest_id"],
        "selected_model": candidate.name,
        "model_family": candidate.family,
        "hyperparameters": candidate.parameters,
        "random_state": random_state,
        "calibration_method": "sigmoid cross-fitted on training partition",
        "probability_calibration_status": probability_status,
        "validation_calibration": calibration,
        "decision_threshold": threshold_result.threshold,
        "threshold_policy": threshold_result.policy,
        "validation_metrics": validation_metrics,
        "final_test_metrics": test_metrics,
        "cv_selection": benchmark.selection_details,
        "fit_seconds_cv_total": float(
            sum(item["cv_fit_seconds"] for item in benchmark.candidate_metrics)
        ),
        "final_estimator_fit_seconds": final_fit_seconds,
        "validation_prediction_seconds": validation_prediction_seconds,
        "final_test_prediction_seconds": supervised_test_prediction_seconds,
        "scikit_learn_version": sklearn.__version__,
        "joblib_version": joblib.__version__,
        "python_version": platform.python_version(),
        "training_protocol": split.manifest["protocol_version"],
        "training_warning_messages": sorted({str(item.message) for item in fit_warnings}),
        "code_revision": code_revision,
        "code_worktree_dirty_at_artifact_creation": worktree_dirty,
        "created_at_utc": created_at,
    }
    bundle = ModelBundle(
        estimator=final_estimator,
        calibrator=calibrator,
        threshold=threshold_result.threshold,
        metadata=model_metadata,
    )
    artifact_path = artifact_root / f"{experiment_id}.joblib"
    artifact = save_model_bundle(bundle, artifact_path)
    artifact["artifact_path"] = (
        str(artifact_path.relative_to(Path.cwd()))
        if artifact_path.is_relative_to(Path.cwd())
        else str(artifact_path)
    )
    anomaly_results = {
        "fit": anomaly_experiment.metadata,
        "fit_seconds": anomaly_fit_seconds,
        "validation": validation_anomaly_metrics,
        "final_test": test_anomaly_metrics,
        "top_ranked_overlap_validation": validation_overlap,
        "top_ranked_overlap_final_test": test_overlap,
        "artifact": anomaly_artifact,
    }
    results: dict[str, Any] = {
        "experiment_id": experiment_id,
        "created_at_utc": created_at,
        "dataset_sha256": source_hash,
        "split_manifest": split.manifest,
        "source_revision": code_revision,
        "source_worktree_dirty_at_run": worktree_dirty,
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
        "candidate_metrics": benchmark.candidate_metrics,
        "selection": benchmark.selection_details,
        "selected_model": {
            "name": candidate.name,
            "family": candidate.family,
            "hyperparameters": candidate.parameters,
            "final_fit_seconds": final_fit_seconds,
            "training_warnings": sorted({str(item.message) for item in fit_warnings}),
        },
        "calibration": calibration,
        "calibration_training_sample": {
            "rows": int(len(oof_labels)),
            "fraud_rows": int(oof_labels.sum()),
            "positive_prevalence": float(oof_labels.mean()),
        },
        "threshold": {
            "threshold": threshold_result.threshold,
            "policy": threshold_result.policy,
            "details": threshold_result.details,
            "constraint_feasible": threshold_result.constraint_feasible,
            "validation_metrics_at_selected_threshold": threshold_result.metrics,
        },
        "validation": {
            "metrics": validation_metrics,
            "raw_score_metrics_at_default_0_5": classification_metrics(
                validation_labels, validation_raw, threshold=0.5
            ),
            "alert_budgets": validation_budgets,
            "prediction_seconds": validation_prediction_seconds,
        },
        "model_validation": model_validation,
        "final_test": {
            "metrics": test_metrics,
            "alert_budgets": test_budgets,
            "prediction_seconds": supervised_test_prediction_seconds,
        },
        "anomaly": anomaly_results,
        "artifact": artifact,
        "selection_freeze_path": str(freeze_path),
        "threshold_table": threshold_points,
        "experiment_wall_seconds": time.perf_counter() - workflow_started,
    }

    registry_entry = {
        "experiment_id": experiment_id,
        "timestamp_utc": created_at,
        "dataset_fingerprint": source_hash,
        "split_manifest_id": split.manifest["manifest_id"],
        "model_family": candidate.family,
        "candidate_name": candidate.name,
        "hyperparameters": candidate.parameters,
        "random_seed": random_state,
        "preprocessing_configuration": model_metadata["training_protocol"],
        "training_duration_seconds": final_fit_seconds,
        "cv_training_seconds_all_candidates": model_metadata["fit_seconds_cv_total"],
        "validation_metrics": validation_metrics,
        "calibration_method": model_metadata["calibration_method"],
        "calibration_status": probability_status,
        "selected_threshold": threshold_result.threshold,
        "artifact_path": artifact["artifact_path"],
        "artifact_sha256": artifact["artifact_sha256"],
        "anomaly_artifact_path": anomaly_artifact["artifact_path"],
        "anomaly_artifact_sha256": anomaly_artifact["artifact_sha256"],
        "code_version": code_revision,
        "code_worktree_dirty": worktree_dirty,
        "final_test_metrics": test_metrics,
    }
    registry_path = output / "EXPERIMENT_REGISTRY.json"
    append_experiment(registry_path, registry_entry)
    results["registry_snapshot"] = json.loads(registry_path.read_text(encoding="utf-8"))

    plot_data = {
        "test_labels": test_labels,
        "test_probabilities": test_probabilities,
        "validation_labels": validation_labels,
        "validation_raw_probabilities": validation_raw,
        "validation_probabilities": validation_probabilities,
        "test_anomaly_scores": test_anomaly,
    }
    generate_ml_reports(results, plot_data, output)
    return results
