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

Notebook validation executes notebooks sequentially with nbclient from the repository root. If data/raw/creditcard.csv is absent, notebooks use and label a deterministic synthetic fixture. This confirms execution mechanics only; it is not an integration test of ULB observations.

## Real-data integration check

After an authorized download:

    .\.venv\Scripts\python.exe scripts\download_dataset.py
    .\scripts\run-eda.ps1

Inspect data/raw/dataset-provenance.json, reports/EDA_REPORT.md, reports/summaries/eda_summary.json, tables, and figures. Confirm that data_classification is source_verified_file and verify the checksum and schema before interpreting results.
