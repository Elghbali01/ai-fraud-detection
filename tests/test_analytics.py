from __future__ import annotations

import pandas as pd
import pytest

from fraud_detection.analytics import (
    amount_summary,
    class_feature_associations,
    class_imbalance,
    correlation_matrix,
    iqr_outlier_diagnostics,
    time_bin_summary,
)


def test_class_imbalance_and_majority_baseline_are_exact(transaction_frame):
    result = class_imbalance(transaction_frame)

    assert result["legitimate_count"] == 11
    assert result["fraud_count"] == 1
    assert result["fraud_pct"] == pytest.approx(100 / 12)
    assert result["majority_minority_ratio"] == 11
    assert result["majority_class_baseline_accuracy"] == pytest.approx(11 / 12)
    assert "not a trained" in result["baseline_note"]


def test_amount_summary_preserves_zero_and_reports_class_statistics(transaction_frame):
    result = amount_summary(transaction_frame)
    legitimate = result.loc[result["class_label"] == 0].iloc[0]
    fraud = result.loc[result["class_label"] == 1].iloc[0]

    assert legitimate["transactions"] == 11
    assert legitimate["zero_amount_count"] == 1
    assert legitimate["median"] == 50
    assert fraud["mean"] == 1_000


def test_time_bin_aggregation_counts_low_volume_and_fraud_rates(transaction_frame):
    result = time_bin_summary(
        transaction_frame,
        bin_seconds=500,
        minimum_transactions=4,
    )

    assert result["transactions"].sum() == 12
    assert result["fraud_count"].sum() == 1
    assert result.loc[result["fraud_count"] > 0, "fraud_rate"].iloc[0] == pytest.approx(0.5)
    assert result["low_volume"].tolist() == [False, False, True]
    assert result["low_fraud_count"].all()


def test_time_bin_validation_and_empty_input(transaction_frame):
    with pytest.raises(ValueError, match="greater than zero"):
        time_bin_summary(transaction_frame, bin_seconds=0)

    result = time_bin_summary(transaction_frame.iloc[:0])
    assert result.empty
    assert "fraud_rate" in result.columns
    assert "low_fraud_count" in result.columns


def test_correlation_methods_and_feature_associations_are_reproducible(transaction_frame):
    pearson = correlation_matrix(transaction_frame, method="pearson")
    spearman = correlation_matrix(transaction_frame, method="spearman")
    associations = class_feature_associations(transaction_frame)

    pd.testing.assert_frame_equal(pearson, correlation_matrix(transaction_frame))
    assert "Class" in pearson.columns
    assert "Class" not in correlation_matrix(transaction_frame, include_target=False)
    assert spearman.shape == pearson.shape
    assert "V1" in associations["feature"].tolist()
    assert associations["absolute_association"].dropna().is_monotonic_decreasing
    with pytest.raises(ValueError, match="method"):
        correlation_matrix(transaction_frame, method="kendall")


def test_iqr_outlier_diagnostics_flags_without_mutating(transaction_frame):
    original = transaction_frame.copy(deep=True)

    result = iqr_outlier_diagnostics(transaction_frame)
    amount = result.loc[result["feature"] == "Amount"].iloc[0]

    assert amount["outlier_count"] >= 1
    pd.testing.assert_frame_equal(transaction_frame, original)
    assert "Class" not in result["feature"].tolist()
