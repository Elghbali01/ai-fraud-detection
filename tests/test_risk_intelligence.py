"""Synthetic risk-policy and anomaly tests without external data."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest
import sklearn

from fraud_detection.ml.anomaly import fit_isolation_forest
from fraud_detection.ml.baselines import make_candidates
from fraud_detection.ml.calibration import fit_sigmoid_calibrator
from fraud_detection.ml.persistence import ModelBundle
from fraud_detection.risk.anomaly_intelligence import (
    anomaly_categories,
    anomaly_percentiles,
    build_training_anomaly_reference,
    load_anomaly_reference,
    save_anomaly_reference,
)
from fraud_detection.risk.comparison import compare_supervised_anomaly
from fraud_detection.risk.contracts import CONTRACT_VERSION, IntelligenceRecord
from fraud_detection.risk.prioritization import (
    percentage_budget_to_k,
    prioritize_transactions,
    validation_alert_budget_metrics,
)
from fraud_detection.risk.scoring import RiskScoringService, probability_to_risk_score
from fraud_detection.risk.service import RiskIntelligenceService
from fraud_detection.risk.tiers import (
    RiskTierPolicy,
    assign_risk_tiers,
    evaluate_risk_tiers,
    fit_risk_tier_policy,
)
from fraud_detection.schema import FEATURE_COLUMNS
from tests.ml_helpers import make_transaction_frame


def _synthetic_artifacts():
    frame = make_transaction_frame(240, seed=83)
    features = frame.loc[:, list(FEATURE_COLUMNS)]
    labels = frame["Class"].to_numpy(dtype=np.int8)
    estimator = make_candidates()[1].estimator
    estimator.fit(features, labels)
    raw = estimator.predict_proba(features)[:, 1]
    bundle = ModelBundle(
        estimator=estimator,
        calibrator=fit_sigmoid_calibrator(raw, labels),
        threshold=0.2,
        metadata={
            "model_version": "synthetic-risk-v1",
            "schema_version": "ulb-credit-card-v1",
            "feature_columns": list(FEATURE_COLUMNS),
            "scikit_learn_version": sklearn.__version__,
            "probability_calibration_status": "training-fold sigmoid test fixture",
        },
    )
    anomaly = fit_isolation_forest(frame, random_state=23)
    anomaly.metadata["model_version"] = "synthetic-anomaly-v1"
    anomaly.metadata["scikit_learn_version"] = sklearn.__version__
    return frame, features, labels, bundle, anomaly


def test_risk_score_and_validation_tier_policy_boundaries():
    probabilities = np.array([0.0, 0.01, 0.1, 0.2, 0.4, 0.8, 1.0])
    np.testing.assert_array_equal(probability_to_risk_score(probabilities), probabilities * 100)
    with pytest.raises(ValueError, match="finite values"):
        probability_to_risk_score([0.1, np.nan])

    policy = fit_risk_tier_policy(
        probabilities,
        decision_threshold=0.2,
        policy_version="risk-test-v1",
    )
    loaded = RiskTierPolicy.from_dict(json.loads(json.dumps(policy.to_dict())))
    tiers = assign_risk_tiers(probabilities, loaded)
    assert tiers[0] == "Low"
    assert np.all(tiers[probabilities >= 0.2] != "Low")
    assert list(tiers[-3:]) == ["High", "High", "Critical"]
    assert loaded.source_partition == "validation"
    summary = evaluate_risk_tiers(probabilities, [0, 0, 0, 1, 0, 1, 1], loaded)
    assert sum(item["rows"] for item in summary) == len(probabilities)


def test_priority_ranking_ties_budgets_and_validation_capacity():
    frame = pd.DataFrame(
        {
            "transaction_id": ["b", "a", "c", "d"],
            "fraud_probability": [0.7, 0.7, 0.5, 0.1],
        }
    )
    result = prioritize_transactions(frame, top_k=2)
    assert result.rows["transaction_id"].tolist() == ["a", "b"]
    assert result.rows["priority_rank"].tolist() == [1, 2]
    assert result.metadata["tie_break"].startswith("transaction_id")
    numeric_ties = pd.DataFrame({"transaction_id": [10, 2], "fraud_probability": [0.5, 0.5]})
    assert prioritize_transactions(numeric_ties, top_k=2).rows["transaction_id"].tolist() == [2, 10]
    with pytest.raises(ValueError, match="nonnegative integer"):
        prioritize_transactions(frame, top_k=1.5)
    assert percentage_budget_to_k(101, 0.5) == 1
    assert percentage_budget_to_k(101, 1.0) == 2
    assert percentage_budget_to_k(0, 10) == 0
    with pytest.raises(ValueError, match="percentage budget"):
        percentage_budget_to_k(10, 0)
    assert prioritize_transactions(frame.iloc[:0], top_k=3).rows.empty

    capacity = validation_alert_budget_metrics(
        [0, 1, 0, 1],
        [0.1, 0.9, 0.8, 0.2],
        count_budgets=(2,),
        percentage_budgets=(50,),
    )
    assert capacity[0]["fraud_captured"] == 1
    assert capacity[0]["k"] == 2
    assert capacity[1]["k"] == 2


def test_training_legitimate_anomaly_reference_and_percentile_categories(tmp_path):
    frame, features, _, _, anomaly = _synthetic_artifacts()
    reference = build_training_anomaly_reference(
        anomaly,
        frame.iloc[:160],
        dataset_sha256="synthetic-dataset",
        split_manifest_id="synthetic-split",
    )
    assert reference.metadata["source_partition"] == "training"
    assert reference.metadata["label_filter"] == "Class == 0 known-legitimate training rows"
    percentiles = anomaly_percentiles(
        [reference.sorted_scores[0], reference.sorted_scores[-1]], reference
    )
    assert percentiles[0] <= percentiles[1]
    assert anomaly_categories([0.0, 0.95, 0.99]).tolist() == [
        "Typical",
        "Unusual",
        "Highly unusual",
    ]
    manifest_path = tmp_path / "manifest.json"
    artifact_path = tmp_path / "reference.npz"
    save_anomaly_reference(reference, artifact_path, manifest_path)
    loaded = load_anomaly_reference(manifest_path)
    np.testing.assert_array_equal(loaded.sorted_scores, reference.sorted_scores)
    # Deterministic generation is safe to rerun and replaces its derived local archive.
    save_anomaly_reference(reference, artifact_path, manifest_path)
    np.testing.assert_array_equal(anomaly_percentiles([0.5], loaded).shape, (1,))
    assert len(features) == len(frame)


def test_supervised_anomaly_comparison_and_intelligence_contract():
    comparison = compare_supervised_anomaly(
        [0, 1, 0, 1],
        [0.1, 0.9, 0.2, 0.8],
        [0.2, 0.95, 0.9, 0.96],
        decision_threshold=0.5,
        percentage_budgets=(25.0, 50.0),
    )
    assert comparison["partition"] == "validation"
    assert comparison["spearman_correlation"] is not None
    assert len(comparison["quadrants"]) == 4
    assert all("combined" not in row for row in comparison["alert_budgets"])

    record = IntelligenceRecord(
        contract_version=CONTRACT_VERSION,
        model_version="fixture-v1",
        schema_version="ulb-credit-card-v1",
        transaction_id=None,
        fraud_probability=0.2,
        risk_score=20.0,
        risk_tier="High",
        predicted_class=1,
        decision_threshold=0.2,
        decision_status="flagged_for_review",
    ).to_dict()
    assert record["contract_version"] == CONTRACT_VERSION
    assert json.loads(json.dumps(record))["risk_score"] == 20.0


def test_risk_service_returns_separate_anomaly_and_calibrated_risk():
    frame, features, _, bundle, anomaly = _synthetic_artifacts()
    sample = frame.iloc[:160]
    scores = bundle.predict_probabilities(sample.loc[:, list(FEATURE_COLUMNS)])[1]
    policy = fit_risk_tier_policy(scores, decision_threshold=bundle.threshold)
    reference = build_training_anomaly_reference(
        anomaly,
        sample,
        dataset_sha256="synthetic-dataset",
        split_manifest_id="synthetic-split",
    )
    service = RiskIntelligenceService(
        RiskScoringService(bundle, policy),
        anomaly_experiment=anomaly,
        anomaly_reference=reference,
    )
    response = service.intelligence_one(features.iloc[180].to_dict(), transaction_id="txn-180")
    assert response["transaction_id"] == "txn-180"
    assert response["risk_score"] == pytest.approx(response["fraud_probability"] * 100)
    assert response["anomaly"]["score_is_probability"] is False
    assert any("not a fraud probability" in line for line in response["narrative"])
    batch = service.intelligence_batch(features.iloc[180:183], include_explanations=True)
    assert len(batch) == 3
    assert all(item["explanation"]["output_space"] == "raw_log_odds" for item in batch)
