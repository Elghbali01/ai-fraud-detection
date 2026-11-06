"""Synthetic explanation tests that need no local dataset or model artifacts."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import sklearn

from fraud_detection.explainability.global_explanations import summarize_global_attributions
from fraud_detection.explainability.linear import exact_linear_attributions
from fraud_detection.explainability.local_explanations import ExplainabilityService
from fraud_detection.explainability.shap_engine import (
    build_linear_explainer,
    explain_with_shap,
    make_training_background,
)
from fraud_detection.ml.baselines import make_candidates
from fraud_detection.ml.calibration import fit_sigmoid_calibrator
from fraud_detection.ml.persistence import ModelBundle
from fraud_detection.schema import FEATURE_COLUMNS
from tests.ml_helpers import make_transaction_frame


@pytest.fixture
def fitted_bundle_and_features():
    frame = make_transaction_frame(240, seed=61)
    features = frame.loc[:, list(FEATURE_COLUMNS)]
    labels = frame["Class"].to_numpy(dtype=np.int8)
    estimator = make_candidates()[1].estimator
    estimator.fit(features, labels)
    raw = estimator.predict_proba(features)[:, 1]
    calibrator = fit_sigmoid_calibrator(raw, labels)
    bundle = ModelBundle(
        estimator=estimator,
        calibrator=calibrator,
        threshold=0.2,
        metadata={
            "model_version": "synthetic-explainability-v1",
            "schema_version": "ulb-credit-card-v1",
            "feature_columns": list(FEATURE_COLUMNS),
            "scikit_learn_version": sklearn.__version__,
            "probability_calibration_status": "training-fold sigmoid test fixture",
        },
    )
    return bundle, features, labels


def test_exact_linear_attributions_reconstruct_log_odds_and_raw_probability(
    fitted_bundle_and_features,
):
    bundle, features, _ = fitted_bundle_and_features
    result = exact_linear_attributions(bundle, features.iloc[:12])
    assert result.contributions.columns.tolist() == list(FEATURE_COLUMNS)
    assert np.max(result.reconstruction_error) < 1e-10
    assert np.max(result.sigmoid_probability_error) < 1e-10
    reconstructed = result.intercept + result.contributions.sum(axis=1).to_numpy()
    np.testing.assert_allclose(reconstructed, result.decision_function, atol=1e-10, rtol=1e-10)
    assert not np.allclose(result.raw_estimator_probability, result.calibrated_probability)


def test_training_background_is_deterministic_and_shap_is_additive(
    fitted_bundle_and_features,
):
    bundle, features, labels = fitted_bundle_and_features
    train = features.iloc[:180]
    background_a, metadata_a = make_training_background(
        train,
        sample_size=48,
        random_state=29,
        dataset_sha256="synthetic-dataset",
        split_manifest_id="synthetic-split",
    )
    background_b, metadata_b = make_training_background(
        train,
        sample_size=48,
        random_state=29,
        dataset_sha256="synthetic-dataset",
        split_manifest_id="synthetic-split",
    )
    pd.testing.assert_frame_equal(background_a, background_b)
    assert metadata_a["background_sha256"] == metadata_b["background_sha256"]
    assert metadata_a["partition"] == "training"
    assert metadata_a["label_filter"] == "none; natural training prevalence"

    explainer, _ = build_linear_explainer(bundle, background_a, random_state=29)
    result = explain_with_shap(
        bundle,
        explainer,
        features.iloc[180:192],
        background_metadata=metadata_a,
    )
    assert result.values.columns.tolist() == list(FEATURE_COLUMNS)
    assert result.additivity["passed"]
    assert result.additivity["maximum_absolute_error"] < 1e-7
    summary = summarize_global_attributions(
        result,
        labels[180:192],
        validation_linear_contributions=exact_linear_attributions(
            bundle, features.iloc[180:192]
        ).contributions,
        coefficients=result.values.columns.to_series().map(
            dict(
                zip(
                    FEATURE_COLUMNS,
                    bundle.estimator.named_steps["classifier"].coef_[0],
                    strict=True,
                )
            )
        ),
    )
    assert summary.iloc[0]["mean_abs_shap_log_odds"] >= summary.iloc[-1]["mean_abs_shap_log_odds"]


def test_local_service_keeps_calibrated_probability_separate_from_log_odds(
    fitted_bundle_and_features,
):
    bundle, features, _ = fitted_bundle_and_features
    service = ExplainabilityService(bundle, max_batch_size=4)
    one = service.explain_one(features.iloc[0].to_dict(), transaction_id="case-1", top_n=None)
    assert one["transaction_id"] == "case-1"
    assert one["explanation"]["output_space"] == "raw_log_odds"
    assert one["explanation"]["calibrated_probability_additivity_claim"] is False
    assert one["explanation"]["all_contributions_returned"] is True
    batch = service.explain_batch(features.iloc[:3], top_n=5)
    assert len(batch) == 3
    assert batch[0]["fraud_probability"] == one["fraud_probability"]
    with pytest.raises(ValueError, match="exceeds configured limit"):
        service.explain_batch(features.iloc[:5])


def test_invalid_features_are_rejected_by_explanation_service(fitted_bundle_and_features):
    bundle, features, _ = fitted_bundle_and_features
    service = ExplainabilityService(bundle)
    invalid = features.iloc[[0]].assign(Time=float("inf"))
    with pytest.raises(ValueError, match="non-finite"):
        service.explain_one(invalid)
