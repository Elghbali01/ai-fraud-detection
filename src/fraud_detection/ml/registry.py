"""Append-only local JSON experiment registry."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def current_git_revision(project_root: str | Path) -> tuple[str | None, bool]:
    """Return the current commit and whether tracked or untracked changes exist."""
    root = Path(project_root)
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=root, check=True, capture_output=True, text=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None, True
    return revision, bool(status.strip())


def append_experiment(path: str | Path, experiment: dict[str, Any]) -> dict[str, Any]:
    """Append one uniquely identified record without silently replacing history."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file():
        records = json.loads(destination.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise ValueError(f"Experiment registry must contain a JSON list: {destination}")
    else:
        records = []
    experiment_id = experiment.get("experiment_id")
    if not experiment_id or any(item.get("experiment_id") == experiment_id for item in records):
        raise ValueError("Experiment ID is missing or already exists; registry is append-only")
    records.append(experiment)
    destination.write_text(
        json.dumps(records, indent=2, default=_json_default) + "\n", encoding="utf-8"
    )
    return experiment


def new_experiment_id(selected_candidate: str, split_manifest_id: str) -> tuple[str, str]:
    """Return a unique UTC-tagged experiment ID and its creation timestamp."""
    now = datetime.now(UTC)
    timestamp = now.isoformat(timespec="microseconds")
    compact = now.strftime("%Y%m%dT%H%M%S%fZ")
    experiment_id = f"m02-{compact}-{selected_candidate}-{split_manifest_id[:8]}"
    return experiment_id, timestamp


def _json_default(value: Any) -> Any:
    """Convert common array and scalar types without losing stored values."""
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Cannot serialize {type(value).__name__} to experiment registry")
