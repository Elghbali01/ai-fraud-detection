"""Persist the already validated Mission 03 training-only SHAP background locally."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from fraud_detection.explainability.shap_engine import make_training_background
from fraud_detection.ml.persistence import sha256_file


def save_api_training_background(
    training_features,
    *,
    dataset_sha256: str,
    split_manifest_id: str,
    artifact_path: str | Path,
    manifest_path: str | Path,
    expected_background_sha256: str,
) -> dict[str, Any]:
    """Write a checksum-protected feature-only background without any labels."""
    background, metadata = make_training_background(
        training_features,
        sample_size=512,
        random_state=17,
        dataset_sha256=dataset_sha256,
        split_manifest_id=split_manifest_id,
    )
    if metadata["background_sha256"] != expected_background_sha256:
        raise ValueError("Generated background differs from the verified Mission 03 result")
    artifact = Path(artifact_path)
    manifest = Path(manifest_path)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{artifact.name}.", suffix=".npz", dir=artifact.parent, delete=False
        ) as handle:
            temporary = handle.name
        np.savez_compressed(temporary, features=background.to_numpy(dtype=np.float64))
        os.replace(temporary, artifact)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
    try:
        relative = os.path.relpath(artifact.resolve(), manifest.parent.resolve()).replace(
            os.sep, "/"
        )
    except ValueError:
        relative = str(artifact.resolve())
    record = {
        **metadata,
        "feature_space": "raw schema features; transformed by the persisted scaler at runtime",
        "source_partition": "training",
        "artifact_path": relative,
        "artifact_sha256": sha256_file(artifact),
        "artifact_size_bytes": artifact.stat().st_size,
        "artifact_format": "NumPy compressed archive; feature values only; ignored local artifact",
    }
    manifest.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record
