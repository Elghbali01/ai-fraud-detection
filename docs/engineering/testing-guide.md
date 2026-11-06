# Testing and Validation Guide

## Unit suite

Run from PowerShell:

    .\.venv\Scripts\python.exe -m pytest

or from CMD:

    .venv\Scripts\python.exe -m pytest

Fixtures are small and deterministic; routine unit tests do not require the real dataset.

## Quality checks

    .\.venv\Scripts\python.exe -m ruff check .
    .\.venv\Scripts\python.exe -m ruff format --check .
    .\.venv\Scripts\python.exe -m compileall -q src scripts tests
    .\.venv\Scripts\python.exe scripts\validate_notebooks.py
    .\.venv\Scripts\python.exe -m fraud_detection.eda --synthetic-demo --output-dir reports

Or run all commands through scripts/run-checks.ps1.
Pass -PythonPath .venv-isolated\Scripts\python.exe to the Windows check script to use a separately created, lockfile-based environment. The standard .venv fallback may use system-site packages when requested by the offline setup mode.

Notebook validation executes notebooks sequentially with nbclient from the repository root. If data/raw/creditcard.csv is absent, notebooks use and label a deterministic synthetic fixture. This confirms execution mechanics only; it is not an integration test of ULB observations.

## Optional real-data integration check

Routine unit tests and CI do not require the full CSV. After an authorized download with its provenance sidecar, opt in from PowerShell:

    $env:RUN_REAL_DATA_TESTS = "1"
    .\.venv\Scripts\python.exe -m pytest -m real_data
    Remove-Item Env:RUN_REAL_DATA_TESTS

The marked test checks the dataset identifier, byte-level SHA-256, expected row/column counts and ordered schema, numeric dtypes, class labels and counts, missingness, finite values, exact duplicates, and generated report artifacts. If the opt-in flag, CSV, or provenance sidecar is absent, pytest reports a clear skip. A skip is not a pass of real-data integration.

To regenerate the committed real-data report and figures:

    .\scripts\run-eda.ps1

Inspect data/raw/dataset-provenance.json, reports/EDA_REPORT.md, reports/summaries/eda_summary.json, reports/tables/, and reports/figures/. Confirm that data_classification is source_verified_file and verify the checksum and schema before interpreting results.
