"""Minimal verification for the downloader's local source metadata."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fraud_detection.schema import SCHEMA_VERSION

KAGGLE_DATASET_ID = "mlg-ulb/creditcardfraud"


def sha256_file(path: str | Path) -> str:
    """Hash a file with bounded memory."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def has_verified_kaggle_provenance(path: str | Path) -> bool:
    """Return true only when the sidecar identifies this dataset and exact file bytes."""
    source = Path(path)
    metadata_path = source.parent / "dataset-provenance.json"
    if not source.is_file() or not metadata_path.is_file():
        return False
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        metadata.get("dataset_id") == KAGGLE_DATASET_ID
        and metadata.get("file_name") == source.name
        and metadata.get("schema_validation", {}).get("schema_version") == SCHEMA_VERSION
        and metadata.get("sha256") == sha256_file(source)
    )


def resolve_project_path(path: str | Path, *, project_root: Path) -> Path:
    """Resolve a relative user path against the repository, not the shell cwd."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else project_root / candidate
