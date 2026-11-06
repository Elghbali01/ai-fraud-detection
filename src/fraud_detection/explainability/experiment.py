"""Reproducible Mission 03 reports using training and validation partitions only."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import shap

from fraud_detection.explainability.data import load_development_partitions
from fraud_detection.explainability.global_explanations import (
    attribution_stability,
    summarize_global_attributions,
)
from fraud_detection.explainability.linear import (
    exact_linear_attributions,
    get_logistic_pipeline_parts,
)
from fraud_detection.explainability.local_explanations import ExplainabilityService
from fraud_detection.explainability.narratives import explanation_narrative
from fraud_detection.explainability.shap_engine import (
    ShapExplanationBatch,
    build_linear_explainer,
    explain_with_shap,
    make_training_background,
)
from fraud_detection.explainability.visualization import (
    plot_alert_capacity,
    plot_coefficient_vs_shap,
    plot_global_shap_importance,
    plot_linear_contribution_waterfall,
    plot_local_shap_waterfall,
    plot_risk_score_distribution,
    plot_risk_tier_analysis,
    plot_shap_beeswarm,
    plot_supervised_anomaly_quadrants,
    plot_top_k_overlap,
)
from fraud_detection.ml.anomaly import anomaly_scores
from fraud_detection.ml.persistence import (
    load_anomaly_artifact,
    load_model_bundle,
    sha256_file,
)
from fraud_detection.ml.preprocessing import validate_features
from fraud_detection.provenance import MISSION01_ULB_SHA256
from fraud_detection.risk.anomaly_intelligence import (
    anomaly_categories,
    anomaly_percentiles,
    build_training_anomaly_reference,
    save_anomaly_reference,
)
from fraud_detection.risk.comparison import compare_supervised_anomaly
from fraud_detection.risk.prioritization import validation_alert_budget_metrics
from fraud_detection.risk.scoring import validate_risk_scoring_metadata
from fraud_detection.risk.tiers import evaluate_risk_tiers, fit_risk_tier_policy
from fraud_detection.schema import FEATURE_COLUMNS, TARGET_COLUMN

BACKGROUND_SIZE = 512
TRAIN_STABILITY_SIZE = 5_000
VALIDATION_PLOT_SIZE = 5_000
RANDOM_SEED = 17
SHAP_TOLERANCE = 1e-7


def _read_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    artifact = (path.parents[2] / data["artifact_path"]).resolve()
    if not artifact.is_file() or sha256_file(artifact) != data["artifact_sha256"]:
        raise ValueError(f"Artifact does not match trusted manifest: {path}")
    return {**data, "resolved_artifact_path": artifact}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _subset_shap(batch: ShapExplanationBatch, positions: np.ndarray) -> ShapExplanationBatch:
    return ShapExplanationBatch(
        values=batch.values.iloc[positions].copy(),
        base_values=batch.base_values[positions].copy(),
        decision_function=batch.decision_function[positions].copy(),
        additivity=batch.additivity,
        background_metadata=batch.background_metadata,
    )


def _json_local_result(result: dict[str, Any]) -> dict[str, Any]:
    """Keep the complete attribution table, without repeating transformed inputs."""
    return {
        key: value
        for key, value in result.items()
        if key not in {"transformed_features", "coefficients"}
    }


def _markdown_global(
    summary: pd.DataFrame,
    *,
    validation_rows: int,
    max_error: float,
    shap_error: float,
) -> str:
    top = summary.head(10)
    rows = "\n".join(
        f"| {r.feature} | {r.mean_abs_shap_log_odds:.6f} | {r.coefficient:.6f} | "
        f"{r.mean_abs_shap_fraud:.6f} | {r.mean_abs_shap_legitimate:.6f} |"
        for r in top.itertuples()
    )
    return f"""# Mission 03 global explainability results

## Scope and method

This report uses the frozen Mission 02 classifier and only the manifest-defined training and
validation partitions. Global SHAP summaries and label-stratified descriptions use all
{validation_rows:,} validation observations. SHAP values explain the classifier's raw
decision-function output in raw log-odds, not the later sigmoid-calibrated probability. The
deterministic Independent background contains 512 unweighted training rows at natural prevalence.

The exact engine uses StandardScaler-transformed feature values and fitted logistic coefficients.
Its zero-transformed-feature intercept is a model reference point, not a population average.
Anonymized V1–V28 coordinates have no asserted business meaning; contributions describe model
behavior and do not establish causality.

## Leading mean absolute validation SHAP values

| Feature | Mean abs SHAP | Scaled coefficient | Fraud mean abs SHAP | Legitimate mean abs SHAP |
|---|---:|---:|---:|---:|
{rows}

## Numerical checks

- Maximum absolute exact linear reconstruction error: `{max_error:.3e}`.
- Maximum absolute SHAP additivity error: `{shap_error:.3e}`.
- Sigmoid(raw decision score) matches the estimator's raw probability.
- This equality is within floating-point tolerance.
- The persisted calibration mapping is reported separately.
- No explanation is represented as an additive decomposition of calibrated probability.

## Stability and limits

See `mission03_results.json` for train-sample versus validation rank stability and per-feature
summaries. These descriptive validation analyses are not a new independent test evaluation. The
final-test partition is consumed and was not loaded for this mission.
"""


def _markdown_risk(results: dict[str, Any]) -> str:
    tiers = "\n".join(
        "| {tier} | {rows:,} | {fraud_labels:,} | {prevalence} | {alerts:,} |".format(
            tier=row["tier"],
            rows=row["rows"],
            fraud_labels=row["fraud_labels"],
            prevalence=(
                f"{row['fraud_prevalence']:.3%}" if row["fraud_prevalence"] is not None else "n/a"
            ),
            alerts=row["predicted_alerts"],
        )
        for row in results["risk"]["validation_tiers"]
    )
    budgets = "\n".join(
        "| {name} | {k:,} | {fraud_captured:,} | {precision} | {recall} |".format(
            name=row["name"],
            k=row["k"],
            fraud_captured=row["fraud_captured"],
            precision=(
                f"{row['precision_at_k']:.3%}" if row["precision_at_k"] is not None else "n/a"
            ),
            recall=(f"{row['recall_at_k']:.3%}" if row["recall_at_k"] is not None else "n/a"),
        )
        for row in results["risk"]["validation_alert_budgets"]
    )
    quadrants = "\n".join(
        f"| {row['quadrant']} | {row['rows']:,} | {row['fraud_labels']:,} |"
        for row in results["supervised_anomaly_comparison"]["quadrants"]
    )
    policy = results["risk"]["policy"]
    comparison = results["supervised_anomaly_comparison"]
    quantiles = results["anomaly"]["reference_score_quantiles"]
    return f"""# Mission 03 risk and anomaly analysis

## Scope

This is a descriptive analysis of {results["partitions"]["validation_rows"]:,} frozen validation
rows ({results["partitions"]["validation_fraud_labels"]:,} labeled fraud cases). It does not use
the consumed final-test partition. Tier cutpoints are derived from validation probabilities only;
validation labels are used only for the diagnostics below. No business costs are assumed.

The display score is 100 times the sigmoid-calibrated fraud probability. The persisted decision
threshold remains {policy["decision_threshold"]:.12f}. The tier policy is operational triage,
not a calibrated probability band. Low ends below {policy["low_upper_exclusive"]:.8f}; Critical
begins at {policy["critical_lower_inclusive"]:.8f}. A decision-positive record cannot be Low.

## Validation tier diagnostics

| Tier | Rows | Historical fraud labels | Label prevalence | Model alerts |
|---|---:|---:|---:|---:|
{tiers}

These observed label prevalences describe this validation period and are not future guarantees.

## Fixed review-capacity diagnostics

Ranking is by calibrated fraud probability descending. Percentage budgets use ceiling, including
at least one row for any nonempty dataset. Identifier then stable input order resolves ties when
identifiers are available; this validation report uses stable source-row order.

| Budget | K | Fraud captured | Precision@K | Recall@K |
|---|---:|---:|---:|---:|
{budgets}

## Separate anomaly signal

Isolation Forest scores are `-score_samples`; higher means more anomalous and the value is not a
fraud probability. Its empirical reference contains {results["anomaly"]["reference_rows"]:,}
known-legitimate training rows. Training-reference score quantiles are p50={quantiles["p50"]:.6f},
p95={quantiles["p95"]:.6f}, and p99={quantiles["p99"]:.6f}. Validation percentiles use the
empirical midrank against this fixed training reference.

Validation Spearman correlation between calibrated fraud probability and anomaly percentile is
{comparison["spearman_correlation"]:.4f}. This is a comparison, not a combined score.

| Validation quadrant | Rows | Historical fraud labels |
|---|---:|---:|
{quadrants}

The two signals remain separate. No formula blends them into a production fraud score. Real-world
investigation capacity, costs, calibration stability, and independent future utility are unknown.
"""


def _markdown_local(examples: list[dict[str, Any]]) -> str:
    blocks = []
    for result in examples:
        explanation = result["explanation"]
        positives = (
            ", ".join(
                f"{item['feature']} ({item['contribution']:+.4f})"
                for item in explanation["top_positive_features"][:5]
            )
            or "none above numerical tolerance"
        )
        negatives = (
            ", ".join(
                f"{item['feature']} ({item['contribution']:+.4f})"
                for item in explanation["top_negative_features"][:5]
            )
            or "none below numerical tolerance"
        )
        blocks.append(
            f"### {result['selection_rule']}\n\n"
            f"Validation source row `{result['transaction_id']}`; label used only for this "
            f"descriptive validation view: "
            f"`{result['validation_label_for_descriptive_analysis']}`. "
            f"Calibrated probability: `{result['fraud_probability']:.8f}`; frozen threshold: "
            f"`{result['decision_threshold']:.8f}`; status: `{result['decision_status']}`.\n\n"
            f"Top positive SHAP terms in raw log-odds: {positives}.\n\n"
            f"Top negative SHAP terms in raw log-odds: {negatives}.\n\n"
            f"{result['narrative'][-1]}"
        )
    return (
        "# Mission 03 selected local explanations\n\n"
        "Examples were chosen deterministically from validation by highest probability, closest "
        "to the frozen threshold, and median probability, with duplicate rows removed. These "
        "descriptions use raw-log-odds SHAP values and are not calibrated-probability "
        "decompositions. They describe model behavior, not causes.\n\n" + "\n\n".join(blocks) + "\n"
    )


def run_mission03_experiment(
    project_root: str | Path,
    *,
    dataset_path: str | Path | None = None,
    background_size: int = BACKGROUND_SIZE,
    stability_size: int = TRAIN_STABILITY_SIZE,
    validation_plot_size: int = VALIDATION_PLOT_SIZE,
    random_seed: int = RANDOM_SEED,
) -> dict[str, Any]:
    """Generate the full Mission 03 experiment from frozen artifacts and dev data.

    The CSV reader in ``load_development_partitions`` parses exactly the train and
    validation prefix. No final-test feature values or labels enter this run.
    """
    root = Path(project_root).resolve()
    dataset = Path(dataset_path) if dataset_path else root / "data/raw/creditcard.csv"
    split_path = root / "reports/ml/split_manifest.json"
    classifier_manifest = _read_manifest(root / "reports/ml/artifact_manifest.json")
    anomaly_manifest = _read_manifest(root / "reports/ml/anomaly_artifact_manifest.json")
    parts = load_development_partitions(dataset, split_path)
    if parts.dataset_sha256 != MISSION01_ULB_SHA256:
        raise ValueError("Development data does not match the verified Mission 01 fingerprint")

    bundle = load_model_bundle(
        classifier_manifest["resolved_artifact_path"],
        expected_sha256=classifier_manifest["artifact_sha256"],
    )
    anomaly_experiment = load_anomaly_artifact(
        anomaly_manifest["resolved_artifact_path"],
        expected_sha256=anomaly_manifest["artifact_sha256"],
    )
    if bundle.threshold != float(classifier_manifest["threshold"]):
        raise ValueError("Loaded classifier threshold differs from its frozen manifest")
    if bundle.metadata.get("dataset_sha256") != parts.dataset_sha256:
        raise ValueError("Classifier and development data fingerprints differ")
    if anomaly_manifest["dataset_sha256"] != parts.dataset_sha256:
        raise ValueError("Anomaly artifact and development data fingerprints differ")

    train_x = validate_features(parts.training.loc[:, list(FEATURE_COLUMNS)])
    validation_x = validate_features(parts.validation.loc[:, list(FEATURE_COLUMNS)])
    validation_y = parts.validation[TARGET_COLUMN].to_numpy(dtype=np.int8)
    train_y = parts.training[TARGET_COLUMN].to_numpy(dtype=np.int8)

    background, background_metadata = make_training_background(
        train_x,
        sample_size=background_size,
        random_state=random_seed,
        dataset_sha256=parts.dataset_sha256,
        split_manifest_id=parts.split_manifest_id,
    )
    explainer, transformed_background = build_linear_explainer(
        bundle,
        background,
        random_state=random_seed,
    )
    validation_shap = explain_with_shap(
        bundle,
        explainer,
        validation_x,
        background_metadata=background_metadata,
        tolerance=SHAP_TOLERANCE,
    )

    rng = np.random.default_rng(random_seed)
    training_sample_positions = np.sort(
        rng.choice(len(train_x), size=min(stability_size, len(train_x)), replace=False)
    )
    training_sample_x = train_x.iloc[training_sample_positions]
    training_shap = explain_with_shap(
        bundle,
        explainer,
        training_sample_x,
        background_metadata=background_metadata,
        tolerance=SHAP_TOLERANCE,
    )
    stability = attribution_stability(training_shap, validation_shap)

    validation_linear = exact_linear_attributions(bundle, validation_x)
    _, scaler, classifier = get_logistic_pipeline_parts(bundle)
    summary = summarize_global_attributions(
        validation_shap,
        validation_y,
        validation_linear_contributions=validation_linear.contributions,
        coefficients=pd.Series(classifier.coef_[0], index=FEATURE_COLUMNS),
    )

    validation_probability = validation_linear.calibrated_probability
    threshold = float(bundle.threshold)
    policy = fit_risk_tier_policy(validation_probability, decision_threshold=threshold)
    policy_consistency = validate_risk_scoring_metadata(policy, model_threshold=threshold)
    if not policy_consistency["threshold_consistent"]:
        raise ValueError("Risk tier threshold is inconsistent with the frozen model threshold")
    tiers = evaluate_risk_tiers(validation_probability, validation_y, policy)
    alert_budgets = validation_alert_budget_metrics(validation_y, validation_probability)

    anomaly_reference = build_training_anomaly_reference(
        anomaly_experiment,
        parts.training,
        dataset_sha256=parts.dataset_sha256,
        split_manifest_id=parts.split_manifest_id,
    )
    reference_path = root / "data/models/mission03-anomaly-reference-v1.npz"
    reference_manifest_path = root / "reports/risk/anomaly_reference_manifest.json"
    save_anomaly_reference(
        anomaly_reference,
        reference_path,
        reference_manifest_path,
    )
    anomaly_validation_scores = anomaly_scores(anomaly_experiment, validation_x)
    anomaly_validation_percentiles = anomaly_percentiles(
        anomaly_validation_scores,
        anomaly_reference,
    )
    comparison = compare_supervised_anomaly(
        validation_y,
        validation_probability,
        anomaly_validation_percentiles,
        decision_threshold=threshold,
    )

    validation_df = pd.DataFrame(
        {
            "source_row_index": parts.validation.index.to_numpy(dtype=np.int64),
            "fraud_probability": validation_probability,
            "risk_score": 100.0 * validation_probability,
            "anomaly_score": anomaly_validation_scores,
            "anomaly_percentile": anomaly_validation_percentiles,
            "anomaly_category": anomaly_categories(anomaly_validation_percentiles),
            "label": validation_y,
        }
    )
    # Recompute tier labels through the public policy assignment to keep one policy path.
    from fraud_detection.risk.tiers import assign_risk_tiers

    validation_df["risk_tier"] = assign_risk_tiers(validation_probability, policy)

    # Examples are selected from validation by deterministic score-based rules.
    selected: list[tuple[str, int]] = []
    candidates = [
        ("highest_validation_probability", int(np.argmax(validation_probability))),
        (
            "closest_to_frozen_threshold",
            int(np.argmin(np.abs(validation_probability - threshold))),
        ),
        (
            "median_validation_probability",
            int(
                np.argsort(validation_probability, kind="stable")[len(validation_probability) // 2]
            ),
        ),
    ]
    seen: set[int] = set()
    for rule, position in candidates:
        if position not in seen:
            selected.append((rule, position))
            seen.add(position)
    selected_positions = np.asarray([position for _, position in selected], dtype=np.int64)
    selected_x = validation_x.iloc[selected_positions]
    selected_shap = explain_with_shap(
        bundle,
        explainer,
        selected_x,
        background_metadata=background_metadata,
        tolerance=SHAP_TOLERANCE,
    )
    selected_linear = exact_linear_attributions(bundle, selected_x)
    service = ExplainabilityService(
        bundle,
        shap_explainer=explainer,
        shap_background_metadata=background_metadata,
        max_batch_size=max(3, len(selected_positions)),
    )
    local_results = []
    for row_position, (rule, validation_position) in enumerate(selected):
        source_index = int(parts.validation.index[validation_position])
        result = service.explain_one(
            selected_x.iloc[[row_position]],
            transaction_id=source_index,
            method="shap_interventional_log_odds",
            top_n=None,
        )
        result["selection_rule"] = rule
        result["partition"] = "validation"
        result["validation_label_for_descriptive_analysis"] = int(validation_y[validation_position])
        anomaly_record = {
            "score": float(anomaly_validation_scores[validation_position]),
            "percentile": float(anomaly_validation_percentiles[validation_position]),
            "category": str(
                anomaly_categories([anomaly_validation_percentiles[validation_position]])[0]
            ),
            "score_direction": "higher = more anomalous",
            "score_is_probability": False,
        }
        result["anomaly"] = anomaly_record
        result["narrative"] = explanation_narrative(result, anomaly=anomaly_record)
        local_results.append(_json_local_result(result))

    report_root = root / "reports"
    explain_dir = report_root / "explainability"
    risk_dir = report_root / "risk"
    figure_dir = explain_dir / "figures"
    for directory in (explain_dir, risk_dir, figure_dir):
        directory.mkdir(parents=True, exist_ok=True)

    summary.to_csv(explain_dir / "global_shap_feature_summary.csv", index=False)
    pd.DataFrame(local_results).to_json(
        explain_dir / "selected_local_explanations.json",
        orient="records",
        indent=2,
    )
    pd.DataFrame(tiers).to_csv(risk_dir / "validation_risk_tiers.csv", index=False)
    pd.DataFrame(alert_budgets).to_csv(risk_dir / "validation_alert_budgets.csv", index=False)
    _write_json(risk_dir / "risk_tier_policy.json", policy.to_dict())

    # Use all validation rows for importance and fixed samples for dense displays.
    plot_global_shap_importance(summary, figure_dir / "global_shap_importance.png")
    plot_coefficient_vs_shap(summary, figure_dir / "coefficient_vs_shap.png")
    plot_risk_score_distribution(
        validation_probability, threshold, risk_dir / "figures/risk_score_distribution.png"
    )
    plot_risk_tier_analysis(tiers, risk_dir / "figures/risk_tier_analysis.png")
    plot_alert_capacity(alert_budgets, risk_dir / "figures/alert_capacity.png")
    plot_supervised_anomaly_quadrants(
        validation_probability,
        anomaly_validation_percentiles,
        validation_y,
        decision_threshold=threshold,
        anomaly_threshold=0.95,
        path=risk_dir / "figures/supervised_anomaly_quadrants.png",
    )
    plot_top_k_overlap(comparison, risk_dir / "figures/top_k_overlap.png")
    plot_linear_contribution_waterfall(
        selected_linear,
        0,
        figure_dir / "local_linear_contributions.png",
        title=f"Exact linear contribution: {selected[0][0]} validation row",
    )
    plot_local_shap_waterfall(
        selected_shap,
        pd.DataFrame(
            scaler.transform(selected_x), columns=list(FEATURE_COLUMNS), index=selected_x.index
        ),
        1 if len(selected) > 1 else 0,
        figure_dir / "local_shap_waterfall.png",
        title=f"SHAP raw log-odds: {selected[min(1, len(selected) - 1)][0]} validation row",
    )
    validation_plot_positions = np.sort(
        rng.choice(
            len(validation_x),
            size=min(validation_plot_size, len(validation_x)),
            replace=False,
        )
    )
    plot_shap_beeswarm(
        _subset_shap(validation_shap, validation_plot_positions),
        pd.DataFrame(
            scaler.transform(validation_x.iloc[validation_plot_positions]),
            columns=list(FEATURE_COLUMNS),
            index=validation_x.index[validation_plot_positions],
        ),
        figure_dir / "validation_shap_beeswarm.png",
    )

    # Real-valued internal checks; JSON exports are aggregate and validation-scoped.
    maximum_linear_error = float(validation_linear.reconstruction_error.max(initial=0.0))
    maximum_sigmoid_error = float(validation_linear.sigmoid_probability_error.max(initial=0.0))
    max_shap_error = float(validation_shap.additivity["maximum_absolute_error"])
    if maximum_sigmoid_error > 1e-10:
        raise ValueError("Raw logistic sigmoid consistency exceeded tolerance")
    risk_output = {
        "mission": "Mission 03",
        "report_version": "mission03-results-v1",
        "data_scope": (
            "frozen training and validation partitions only; final-test partition not loaded"
        ),
        "dataset_sha256": parts.dataset_sha256,
        "split_manifest_id": parts.split_manifest_id,
        "partitions": {
            "training_rows": int(len(parts.training)),
            "training_fraud_labels": int(train_y.sum()),
            "validation_rows": int(len(parts.validation)),
            "validation_fraud_labels": int(validation_y.sum()),
            "final_test_rows_loaded": 0,
            "final_test_labels_loaded": 0,
        },
        "environment": {
            "python": ".venv-isolated runtime",
            "shap_version": shap.__version__,
            "numpy_version": np.__version__,
        },
        "model": {
            "model_version": str(bundle.metadata["model_version"]),
            "classifier_sha256": classifier_manifest["artifact_sha256"],
            "anomaly_model_version": str(
                anomaly_experiment.metadata.get("model_version", anomaly_manifest["model_version"])
            ),
            "anomaly_sha256": anomaly_manifest["artifact_sha256"],
            "threshold": threshold,
            "threshold_source": "frozen Mission 02 artifact manifest",
            "calibration": "training-only out-of-fold sigmoid mapping persisted in ModelBundle",
        },
        "linear_explainability": {
            "output_space": "raw_log_odds",
            "attribution_space": "StandardScaler-transformed feature space",
            "validation_maximum_absolute_reconstruction_error": maximum_linear_error,
            "maximum_raw_sigmoid_probability_error": maximum_sigmoid_error,
            "calibrated_probability_additivity_claimed": False,
        },
        "shap": {
            **background_metadata,
            "background_transformed_sha256": hashlib.sha256(
                transformed_background.to_numpy(dtype=np.float64).tobytes(order="C")
            ).hexdigest(),
            "validation_rows_explained": int(len(validation_x)),
            "validation_additivity": validation_shap.additivity,
            "training_stability_sample_rows": int(len(training_sample_x)),
            "training_stability_sample_seed": int(random_seed),
            "validation_beeswarm_sample_rows": int(min(validation_plot_size, len(validation_x))),
            "validation_beeswarm_seed": int(random_seed),
            "global_top_10_features": summary.head(10)["feature"].tolist(),
            "additivity_tolerance": SHAP_TOLERANCE,
        },
        "global_attributions": {
            "stability": stability,
            "top_features": summary.head(10).to_dict(orient="records"),
            "summary_csv": "reports/explainability/global_shap_feature_summary.csv",
        },
        "local_examples": local_results,
        "risk": {
            "risk_score": "100 * calibrated fraud probability",
            "policy": policy.to_dict(),
            "policy_threshold_consistency": policy_consistency,
            "validation_tiers": tiers,
            "validation_alert_budgets": alert_budgets,
            "validation_median_probability": float(np.median(validation_probability)),
            "validation_flagged_rows": int(np.sum(validation_probability >= threshold)),
        },
        "anomaly": {
            "score_direction": "higher = more anomalous",
            "score_is_probability": False,
            "reference_manifest": "reports/risk/anomaly_reference_manifest.json",
            "reference_rows": int(len(anomaly_reference.sorted_scores)),
            "reference_source_partition": "training known-legitimate rows only",
            "reference_score_quantiles": anomaly_reference.metadata["score_quantiles"],
            "validation_category_counts": {
                str(name): int(count)
                for name, count in zip(
                    *np.unique(
                        anomaly_categories(anomaly_validation_percentiles), return_counts=True
                    ),
                    strict=True,
                )
            },
        },
        "supervised_anomaly_comparison": comparison,
        "limitations": [
            "Mission 02 final-test observations are consumed and were not loaded in Mission 03.",
            "Validation findings are descriptive and do not establish future performance.",
            "V1–V28 are anonymized PCA-derived coordinates; attribution is not causal.",
            "Risk tiers are operational categories, not calibrated probability bands.",
            "Anomaly scores are separate from calibrated fraud probabilities and are not blended.",
        ],
    }
    _write_json(risk_dir / "mission03_results.json", risk_output)
    (risk_dir / "RISK_ANALYSIS.md").write_text(_markdown_risk(risk_output), encoding="utf-8")
    (explain_dir / "LOCAL_EXPLANATIONS.md").write_text(
        _markdown_local(local_results), encoding="utf-8"
    )
    (explain_dir / "GLOBAL_EXPLAINABILITY.md").write_text(
        _markdown_global(
            summary,
            validation_rows=len(validation_x),
            max_error=maximum_linear_error,
            shap_error=max_shap_error,
        ),
        encoding="utf-8",
    )
    _write_json(
        explain_dir / "shap_additivity_validation.json",
        {
            "output_space": "raw_log_odds",
            "partition": "validation",
            "rows": int(len(validation_x)),
            "tolerance": SHAP_TOLERANCE,
            **validation_shap.additivity,
        },
    )
    _write_json(
        risk_dir / "supervised_anomaly_comparison.json",
        comparison,
    )
    return risk_output


def project_root_from_module() -> Path:
    """Locate the repository root from this installed source module."""
    return Path(__file__).resolve().parents[3]
