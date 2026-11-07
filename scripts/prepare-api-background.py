"""Create the trusted Mission 03 training-only SHAP background artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fraud_detection.explainability.api_background import save_api_training_background  # noqa: E402
from fraud_detection.explainability.data import load_development_partitions  # noqa: E402
from fraud_detection.schema import FEATURE_COLUMNS  # noqa: E402


def main() -> None:
    """Generate a deterministic local artifact without parsing final-test rows."""
    data = load_development_partitions(
        ROOT / "data" / "raw" / "creditcard.csv",
        ROOT / "reports" / "ml" / "split_manifest.json",
    )
    mission03 = json.loads((ROOT / "reports" / "risk" / "mission03_results.json").read_text())
    record = save_api_training_background(
        data.training.loc[:, list(FEATURE_COLUMNS)],
        dataset_sha256=data.dataset_sha256,
        split_manifest_id=data.split_manifest_id,
        artifact_path=ROOT / "data" / "models" / "mission04-shap-training-background-v1.npz",
        manifest_path=ROOT / "reports" / "explainability" / "api_background_manifest.json",
        expected_background_sha256=mission03["shap"]["background_sha256"],
    )
    print(
        "Created training-only SHAP background: "
        f"{record['sample_size']} rows; sha256={record['artifact_sha256']}"
    )


if __name__ == "__main__":
    main()
