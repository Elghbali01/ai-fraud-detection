"""Acquire and validate the ULB dataset through the authorized Kaggle CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
SOURCE_URL = "https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud"
DATASET_ID = "mlg-ulb/creditcardfraud"
EXPECTED_CSV = "creditcard.csv"
PUBLISHED_CSV_BYTES = 151_000_000
SAFETY_BYTES = 100 * 1024 * 1024


def sha256_file(path: Path) -> str:
    """Calculate a file digest using bounded memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_csv(path: Path) -> dict[str, object]:
    """Check the candidate file against the versioned schema and summarize labels."""
    from fraud_detection.loading import load_ulb_csv
    from fraud_detection.schema import validate_ulb_frame

    frame = load_ulb_csv(path)
    validation = validate_ulb_frame(frame)
    counts = frame["Class"].value_counts().sort_index()
    return {
        "row_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "columns": [str(column) for column in frame.columns],
        "class_distribution": {str(label): int(count) for label, count in counts.items()},
        "schema_validation": validation.to_dict(),
    }


def existing_file_result(destination: Path) -> int:
    """Validate an existing dataset without overwriting it."""
    try:
        details = validate_csv(destination)
    except Exception as exc:
        print(f"Existing dataset is invalid and was left untouched: {exc}", file=sys.stderr)
        return 2
    print(
        f"Validated existing dataset: {destination.name}; {destination.stat().st_size:,} bytes; "
        f"SHA-256 {sha256_file(destination)}"
    )
    metadata_path = destination.parent / "dataset-provenance.json"
    if metadata_path.is_file():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata.get("sha256") == sha256_file(destination):
                print("Existing provenance metadata matches the dataset checksum.")
            else:
                print("Existing provenance metadata does not match this file; it was not changed.")
        except (OSError, json.JSONDecodeError):
            print("Existing provenance metadata could not be parsed; it was not changed.")
    else:
        print("Acquisition provenance is unknown for this pre-existing local file.")
    print(f"Observed rows/columns: {details['row_count']:,}/{details['column_count']}")
    return 0


def download(destination: Path) -> int:
    """Download into a temporary directory, validate, and atomically install."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return existing_file_result(destination)

    free_bytes = shutil.disk_usage(destination.parent).free
    required_bytes = PUBLISHED_CSV_BYTES * 2 + SAFETY_BYTES
    if free_bytes < required_bytes:
        print(
            f"Insufficient free space: {free_bytes:,} bytes available; "
            f"at least {required_bytes:,} bytes required.",
            file=sys.stderr,
        )
        return 2

    kaggle = shutil.which("kaggle")
    if kaggle is None:
        print(
            "Kaggle CLI is unavailable. Install it in the project environment and configure "
            "authorized local Kaggle credentials before retrying. No credentials were read or "
            "printed.",
            file=sys.stderr,
        )
        return 2

    temporary_root = destination.parent
    try:
        with tempfile.TemporaryDirectory(prefix=".ulb-download-", dir=temporary_root) as temp_name:
            temp_dir = Path(temp_name)
            command = [
                kaggle,
                "datasets",
                "download",
                "-d",
                DATASET_ID,
                "-f",
                EXPECTED_CSV,
                "-p",
                str(temp_dir),
            ]
            try:
                result = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=900,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                print(
                    f"Kaggle download could not complete ({type(exc).__name__}). "
                    "Temporary files will be removed.",
                    file=sys.stderr,
                )
                return 2
            if result.returncode != 0:
                print(
                    f"Kaggle CLI exited with code {result.returncode}. Diagnostic output is "
                    "withheld to avoid exposing credential details; confirm account access and "
                    "network availability.",
                    file=sys.stderr,
                )
                return 2

            candidate = _find_csv(temp_dir)
            details = validate_csv(candidate)
            if destination.exists():
                print(
                    "Destination appeared during download; leaving it untouched.", file=sys.stderr
                )
                return 2
            os.replace(candidate, destination)

        checksum = sha256_file(destination)
        metadata = {
            "dataset_id": DATASET_ID,
            "source_url": SOURCE_URL,
            "retrieved_at_utc": datetime.now(UTC).isoformat(),
            "file_name": destination.name,
            "file_size_bytes": destination.stat().st_size,
            "sha256": checksum,
            **details,
        }
        metadata_path = destination.parent / "dataset-provenance.json"
        temporary_metadata = metadata_path.with_suffix(".json.tmp")
        temporary_metadata.write_text(
            json.dumps(metadata, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary_metadata, metadata_path)
        print(
            f"Acquired and validated {destination.name}: {details['row_count']:,} rows, "
            f"{details['column_count']} columns, {destination.stat().st_size:,} bytes."
        )
        print(f"SHA-256: {checksum}")
        print(f"Provenance metadata: {metadata_path.name}")
        return 0
    except (OSError, ValueError, zipfile.BadZipFile, pd.errors.ParserError) as exc:
        print(
            f"Dataset acquisition/validation failed ({type(exc).__name__}). "
            "Incomplete temporary files were removed.",
            file=sys.stderr,
        )
        return 2


def _find_csv(directory: Path) -> Path:
    """Find the expected CSV in either a direct response or Kaggle zip archive."""
    direct = directory / EXPECTED_CSV
    if direct.is_file():
        return direct
    archives = list(directory.glob("*.zip"))
    if len(archives) != 1:
        raise FileNotFoundError("Expected one Kaggle zip or direct creditcard.csv download.")
    with zipfile.ZipFile(archives[0]) as archive:
        matches = [
            member
            for member in archive.infolist()
            if Path(member.filename).name == EXPECTED_CSV and not member.is_dir()
        ]
        if len(matches) != 1:
            raise FileNotFoundError("Kaggle archive must contain exactly one creditcard.csv.")
        member = matches[0]
        with archive.open(member) as source, direct.open("wb") as target:
            shutil.copyfileobj(source, target, length=1024 * 1024)
    return direct


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "raw" / EXPECTED_CSV,
        help="Destination CSV path (raw data remains excluded from Git).",
    )
    args = parser.parse_args()
    output_path = args.output if args.output.is_absolute() else ROOT / args.output
    return download(output_path.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
