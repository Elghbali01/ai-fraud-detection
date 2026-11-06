"""Separate Isolation Forest score semantics and ranking behavior."""

from __future__ import annotations

from fraud_detection.ml.anomaly import (
    anomaly_scores,
    compare_top_ranked_overlap,
    evaluate_anomaly_ranking,
    fit_isolation_forest,
)
from fraud_detection.ml.inference import predict_anomaly_batch
from fraud_detection.ml.persistence import load_anomaly_artifact, save_anomaly_artifact
from fraud_detection.schema import FEATURE_COLUMNS
from tests.ml_helpers import make_transaction_frame


def test_isolation_forest_fits_legitimate_training_rows_and_ranks_outliers():
    frame = make_transaction_frame(120)
    frame.loc[:, list(FEATURE_COLUMNS)] = frame.loc[:, list(FEATURE_COLUMNS)].to_numpy() * 0.01
    frame.loc[110:, "Class"] = 1
    frame.loc[110:, list(FEATURE_COLUMNS)] = 8.0
    experiment = fit_isolation_forest(frame.iloc[:110])
    scores = anomaly_scores(experiment, frame.loc[:, list(FEATURE_COLUMNS)])
    assert experiment.metadata["fit_positive_rows"] == 0
    assert experiment.metadata["fit_rows"] == int(frame.iloc[:110]["Class"].eq(0).sum())
    assert scores[110:].mean() > scores[:100].mean()

    metrics = evaluate_anomaly_ranking(frame["Class"].to_numpy(), scores)
    assert metrics["score_is_probability"] is False
    assert metrics["score_direction"] == "higher = more anomalous"
    assert metrics["average_precision"] > 0.5
    overlap = compare_top_ranked_overlap(scores, scores)
    assert all(row["overlap_percentage_of_k"] == 100 for row in overlap)


def test_anomaly_artifact_round_trip_preserves_score_and_semantics(tmp_path):
    import sklearn

    frame = make_transaction_frame(120)
    experiment = fit_isolation_forest(frame)
    experiment.metadata.update(
        {
            "model_version": "synthetic-anomaly-v1",
            "schema_version": "ulb-credit-card-v1",
            "feature_columns": list(FEATURE_COLUMNS),
            "scikit_learn_version": sklearn.__version__,
        }
    )
    artifact = tmp_path / "anomaly.joblib"
    manifest = save_anomaly_artifact(experiment, artifact)
    loaded = load_anomaly_artifact(artifact, expected_sha256=manifest["artifact_sha256"])
    before = predict_anomaly_batch(experiment, frame.loc[:4, list(FEATURE_COLUMNS)])
    after = predict_anomaly_batch(loaded, frame.loc[:4, list(FEATURE_COLUMNS)])
    assert before["anomaly_score"].tolist() == after["anomaly_score"].tolist()
    assert after["score_is_probability"].eq(False).all()
    assert after["model_version"].eq("synthetic-anomaly-v1").all()
