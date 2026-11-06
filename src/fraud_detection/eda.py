"""Command line entry point for reproducible ULB EDA."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from fraud_detection.demo import make_synthetic_ulb_fixture
from fraud_detection.loading import load_ulb_csv
from fraud_detection.provenance import has_verified_kaggle_provenance, resolve_project_path
from fraud_detection.reporting import generate_eda_artifacts

LOGGER = logging.getLogger("fraud_detection.eda")
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    """Create the EDA command line parser."""
    parser = argparse.ArgumentParser(description="Profile and explore a ULB transaction CSV.")
    parser.add_argument(
        "--dataset", type=Path, default=PROJECT_ROOT / "data" / "raw" / "creditcard.csv"
    )
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "reports")
    parser.add_argument(
        "--synthetic-demo",
        action="store_true",
        help="Run a clearly labeled deterministic fixture smoke analysis, not real-data EDA.",
    )
    parser.add_argument("--demo-rows", type=int, default=200)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run EDA and return a process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args(argv)
    args.dataset = resolve_project_path(args.dataset, project_root=PROJECT_ROOT)
    args.output_dir = resolve_project_path(args.output_dir, project_root=PROJECT_ROOT)
    if args.synthetic_demo:
        frame = make_synthetic_ulb_fixture(row_count=args.demo_rows)
        output_dir = args.output_dir / "demo"
        classification = "synthetic_fixture"
        dataset_name = "deterministic synthetic fixture (not ULB observations)"
    else:
        if not args.dataset.is_file():
            LOGGER.error(
                "Dataset unavailable at %s. Run python scripts/download_dataset.py after "
                "authorized Kaggle access is configured.",
                args.dataset,
            )
            return 2
        try:
            frame = load_ulb_csv(args.dataset)
        except Exception:
            LOGGER.exception("Could not load or validate the requested dataset")
            return 2
        output_dir = args.output_dir
        classification = (
            "source_verified_file"
            if has_verified_kaggle_provenance(args.dataset)
            else "unverified_local_file"
        )
        dataset_name = args.dataset.name

    try:
        summary = generate_eda_artifacts(
            frame,
            output_dir,
            data_classification=classification,
            dataset_name=dataset_name,
        )
    except Exception:
        LOGGER.exception("EDA artifact generation failed")
        return 1

    LOGGER.info(
        "Generated %d-row, %d-column %s analysis at %s",
        summary["profile"]["row_count"],
        summary["profile"]["column_count"],
        classification,
        output_dir,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
