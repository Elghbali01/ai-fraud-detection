"""Load and verify the complete local Mission 02/03 API artifact set."""

from __future__ import annotations

import json

from backend.app.core.config import Settings
from backend.app.services.artifacts import load_runtime

runtime = load_runtime(Settings())
print(
    json.dumps(
        {
            "status": "verified",
            "model_version": runtime.bundle.metadata["model_version"],
            "classifier_sha256": runtime.artifact_metadata["classifier_sha256"],
            "anomaly_sha256": runtime.artifact_metadata["anomaly_sha256"],
            "dataset_sha256": runtime.artifact_metadata["dataset_sha256"],
            "split_manifest_id": runtime.artifact_metadata["split_manifest_id"],
            "shap_background_sha256": runtime.shap_metadata["artifact_sha256"],
            "global_summary_rows": runtime.artifact_metadata["global_summary_rows"],
        },
        indent=2,
    )
)
