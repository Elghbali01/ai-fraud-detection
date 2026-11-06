"""Command-line entry points for Mission 03 explainability and risk analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from fraud_detection.explainability.data import load_development_partitions
from fraud_detection.explainability.experiment import (
    project_root_from_module,
    run_mission03_experiment,
)
from fraud_detection.explainability.local_explanations import ExplainabilityService
from fraud_detection.explainability.shap_engine import (
    build_linear_explainer,
    make_training_background,
)
from fraud_detection.ml.persistence import load_model_bundle
from fraud_detection.ml.preprocessing import validate_features
from fraud_detection.risk.anomaly_intelligence import load_anomaly_reference
from fraud_detection.risk.prioritization import prioritize_transactions
from fraud_detection.risk.scoring import RiskScoringService
from fraud_detection.risk.service import RiskIntelligenceService
from fraud_detection.risk.tiers import RiskTierPolicy
from fraud_detection.schema import FEATURE_COLUMNS


def _root() -> Path:
    return project_root_from_module()


def _model(root: Path):
    manifest_path = root / "reports/ml/artifact_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact_path = (root / manifest["artifact_path"]).resolve()
    return load_model_bundle(artifact_path, expected_sha256=manifest["artifact_sha256"])


def _service(root: Path, *, with_anomaly: bool = False) -> RiskIntelligenceService:
    bundle = _model(root)
    policy = RiskTierPolicy.from_dict(
        json.loads((root / "reports/risk/risk_tier_policy.json").read_text(encoding="utf-8"))
    )
    scoring = RiskScoringService(bundle, policy)
    if not with_anomaly:
        return RiskIntelligenceService(scoring)
    anomaly_manifest_path = root / "reports/ml/anomaly_artifact_manifest.json"
    anomaly_manifest = json.loads(anomaly_manifest_path.read_text(encoding="utf-8"))
    from fraud_detection.ml.persistence import load_anomaly_artifact

    anomaly_model = load_anomaly_artifact(
        (root / anomaly_manifest["artifact_path"]).resolve(),
        expected_sha256=anomaly_manifest["artifact_sha256"],
    )
    reference = load_anomaly_reference(root / "reports/risk/anomaly_reference_manifest.json")
    return RiskIntelligenceService(
        scoring,
        anomaly_experiment=anomaly_model,
        anomaly_reference=reference,
    )


def _read_features(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".json":
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
        frame = pd.DataFrame([payload]) if isinstance(payload, dict) else pd.DataFrame(payload)
    else:
        frame = pd.read_csv(path)
    return validate_features(frame)


def _write_json(path: Path | None, payload: Any) -> None:
    text = json.dumps(payload, indent=2, allow_nan=False) + "\n"
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fraud-explain", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser(
        "generate", help="Generate global reports and validation risk analysis"
    )
    generate.add_argument("--root", type=Path, default=_root())

    local = subparsers.add_parser("explain-local", help="Explain one feature record")
    local.add_argument("input", type=Path)
    local.add_argument(
        "--method",
        choices=["linear_log_odds", "shap_interventional_log_odds"],
        default="linear_log_odds",
    )
    local.add_argument("--transaction-id")
    local.add_argument("--top-n", type=int, default=10)
    local.add_argument("--output", type=Path)
    local.add_argument("--root", type=Path, default=_root())

    score = subparsers.add_parser("score", help="Score a single transaction or bounded CSV batch")
    score.add_argument("input", type=Path)
    score.add_argument(
        "--anomaly", action="store_true", help="Include separate anomaly reference intelligence"
    )
    score.add_argument(
        "--explain", action="store_true", help="Include linear explanations for at most 100 rows"
    )
    score.add_argument("--output", type=Path)
    score.add_argument("--root", type=Path, default=_root())

    prioritize = subparsers.add_parser(
        "prioritize", help="Rank a feature CSV under a review budget"
    )
    prioritize.add_argument("input", type=Path)
    budget = prioritize.add_mutually_exclusive_group(required=True)
    budget.add_argument("--top-k", type=int)
    budget.add_argument("--budget-percent", type=float)
    prioritize.add_argument("--output", type=Path)
    prioritize.add_argument("--root", type=Path, default=_root())

    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.command == "generate":
        result = run_mission03_experiment(root)
        print(
            json.dumps(
                {
                    "report": "reports/risk/mission03_results.json",
                    "validation_rows": result["partitions"]["validation_rows"],
                    "shap_additivity": result["shap"]["validation_additivity"],
                },
                indent=2,
            )
        )
        return 0

    if args.command == "explain-local":
        features = _read_features(args.input)
        if len(features) != 1:
            parser.error("explain-local input must contain exactly one transaction")
        bundle = _model(root)
        explainer = None
        background_metadata = None
        if args.method == "shap_interventional_log_odds":
            parts = load_development_partitions(
                root / "data/raw/creditcard.csv", root / "reports/ml/split_manifest.json"
            )
            background, background_metadata = make_training_background(
                parts.training.loc[:, list(FEATURE_COLUMNS)],
                dataset_sha256=parts.dataset_sha256,
                split_manifest_id=parts.split_manifest_id,
            )
            explainer, _ = build_linear_explainer(bundle, background)
        service = ExplainabilityService(
            bundle,
            shap_explainer=explainer,
            shap_background_metadata=background_metadata,
        )
        result = service.explain_one(
            features,
            transaction_id=args.transaction_id,
            method=args.method,
            top_n=args.top_n,
        )
        _write_json(args.output, result)
        return 0

    if args.command == "score":
        features = _read_features(args.input)
        service = _service(root, with_anomaly=args.anomaly)
        if args.explain and len(features) > service.max_explanation_batch:
            parser.error("Detailed explanation requests are limited to 100 rows")
        result = service.intelligence_batch(features, include_explanations=args.explain)
        _write_json(args.output, result)
        return 0

    if args.command == "prioritize":
        features = _read_features(args.input)
        service = _service(root)
        scored = service.score_batch(features)
        ranked = prioritize_transactions(
            scored,
            top_k=args.top_k,
            budget_percentage=args.budget_percent,
            transaction_id_column="transaction_id",
        )
        _write_json(
            args.output,
            {"metadata": ranked.metadata, "transactions": ranked.rows.to_dict(orient="records")},
        )
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
