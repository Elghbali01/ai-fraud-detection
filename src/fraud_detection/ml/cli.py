"""Command line entry points for training, artifact checks, and local inference."""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from fraud_detection.exceptions import ArtifactError
from fraud_detection.loading import load_ulb_csv
from fraud_detection.ml.experiment import run_ml_experiment
from fraud_detection.ml.inference import predict_anomaly_batch, predict_batch
from fraud_detection.ml.persistence import (
    load_anomaly_artifact,
    load_model_bundle,
    verify_artifact_manifest,
)
from fraud_detection.ml.splitting import create_temporal_split, write_split_manifest
from fraud_detection.provenance import has_verified_kaggle_provenance, sha256_file

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _resolve(value: str) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fraud-ml")
    commands = parser.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser(
        "prepare", help="verify data and freeze the chronological split manifest"
    )
    prepare.add_argument("--dataset", default="data/raw/creditcard.csv")
    prepare.add_argument("--output-directory", default="reports/ml")

    run = commands.add_parser(
        "run", help="train, select, evaluate once, and generate Mission 02 outputs"
    )
    run.add_argument("--dataset", default="data/raw/creditcard.csv")
    run.add_argument("--output-directory", default="reports/ml")
    run.add_argument("--artifact-directory", default="data/models")
    run.add_argument("--random-state", type=int, default=17)
    run.add_argument("--cv-splits", type=int, default=3)

    evaluate = commands.add_parser(
        "evaluate", help="print the latest saved evaluation without retraining"
    )
    evaluate.add_argument("--results", default="reports/ml/latest_results.json")

    verify = commands.add_parser(
        "verify-artifact", help="verify a trusted local artifact and manifest"
    )
    verify.add_argument("--manifest", required=True)

    predict = commands.add_parser("predict", help="score a local CSV using a trusted saved model")
    predict.add_argument("--artifact", required=True)
    predict.add_argument("--input-csv", required=True)
    predict.add_argument("--output-csv")

    predict_anomaly = commands.add_parser(
        "predict-anomaly", help="score unusualness with a separate Isolation Forest artifact"
    )
    predict_anomaly.add_argument("--artifact", required=True)
    predict_anomaly.add_argument("--input-csv", required=True)
    predict_anomaly.add_argument("--output-csv")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    args = _parser().parse_args(argv)
    if args.command == "prepare":
        dataset = _resolve(args.dataset)
        output = _resolve(args.output_directory)
        if not has_verified_kaggle_provenance(dataset):
            raise ArtifactError("Dataset does not match the local verified ULB provenance sidecar")
        frame = load_ulb_csv(dataset, strict_columns=True)
        split = create_temporal_split(frame, dataset_sha256=sha256_file(dataset))
        manifest_path = output / "split_manifest.json"
        if manifest_path.is_file():
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            if existing.get("manifest_id") != split.manifest["manifest_id"]:
                raise ArtifactError(
                    "Existing manifest differs; refusing to replace frozen split protocol"
                )
        else:
            write_split_manifest(split, manifest_path)
        print(
            json.dumps(
                {
                    "manifest_id": split.manifest["manifest_id"],
                    "path": str(manifest_path),
                    "partitions": split.manifest["partitions"],
                },
                indent=2,
            )
        )
        return 0

    if args.command == "run":
        result = run_ml_experiment(
            _resolve(args.dataset),
            output_directory=_resolve(args.output_directory),
            artifact_directory=_resolve(args.artifact_directory),
            random_state=args.random_state,
            cv_splits=args.cv_splits,
        )
        print(
            json.dumps(
                {
                    "experiment_id": result["experiment_id"],
                    "selected_model": result["selected_model"],
                    "threshold": result["threshold"]["threshold"],
                    "final_test_metrics": result["final_test"]["metrics"],
                    "artifact": result["artifact"],
                    "anomaly_artifact": result["anomaly"]["artifact"],
                },
                indent=2,
            )
        )
        return 0

    if args.command == "evaluate":
        result_path = _resolve(args.results)
        result = json.loads(result_path.read_text(encoding="utf-8"))
        print(
            json.dumps(
                {
                    "experiment_id": result["experiment_id"],
                    "selected_model": result["selected_model"],
                    "threshold": result["threshold"],
                    "validation_metrics": result["validation"]["metrics"],
                    "final_test_metrics": result["final_test"]["metrics"],
                    "anomaly_metrics": result["anomaly"]["final_test"],
                    "anomaly_artifact": result["anomaly"]["artifact"],
                },
                indent=2,
            )
        )
        return 0

    if args.command == "verify-artifact":
        manifest_path = _resolve(args.manifest)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not verify_artifact_manifest(manifest):
            raise ArtifactError("Artifact checksum or byte-size verification failed")
        if manifest.get("artifact_type") == "anomaly_detector":
            bundle = load_anomaly_artifact(
                manifest["artifact_path"], expected_sha256=manifest["artifact_sha256"]
            )
            metadata = {
                "model_version": bundle.metadata["model_version"],
                "feature_columns": bundle.metadata["feature_columns"],
                "score_direction": "higher = more anomalous",
                "score_is_probability": False,
            }
        else:
            bundle = load_model_bundle(
                manifest["artifact_path"], expected_sha256=manifest["artifact_sha256"]
            )
            metadata = {
                "model_version": bundle.metadata["model_version"],
                "feature_columns": bundle.metadata["feature_columns"],
                "threshold": bundle.threshold,
            }
        print(
            json.dumps(
                {
                    "verified": True,
                    "artifact_sha256": manifest["artifact_sha256"],
                    **metadata,
                },
                indent=2,
            )
        )
        return 0

    if args.command in {"predict", "predict-anomaly"}:
        if args.command == "predict-anomaly":
            bundle = load_anomaly_artifact(_resolve(args.artifact))
        else:
            bundle = load_model_bundle(_resolve(args.artifact))
        input_frame = pd.read_csv(_resolve(args.input_csv), low_memory=False)
        scored = (
            predict_anomaly_batch(bundle, input_frame)
            if args.command == "predict-anomaly"
            else predict_batch(bundle, input_frame)
        )
        if args.output_csv:
            destination = _resolve(args.output_csv)
            destination.parent.mkdir(parents=True, exist_ok=True)
            scored.to_csv(destination, index=False)
            print(f"Wrote {len(scored):,} scored rows to {destination}")
        else:
            print(scored.to_json(orient="records", indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
