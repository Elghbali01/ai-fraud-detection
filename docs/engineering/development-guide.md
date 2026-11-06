# Development Guide

## Requirements

Windows 11, Python 3.11, Git, and enough disk space for the dataset and temporary download. Node 20 is recorded for later frontend missions but is not used by Mission 01.

## Install

From PowerShell in the repository root:

    .\scripts\setup.ps1

From CMD:

    powershell -NoProfile -File scripts\setup.ps1

The setup installs the package and the exact Windows/Python 3.11 dependency set from requirements-mission01.lock into .venv. For repeatability, do not install project packages globally. When the machine has no network and already has that exact dependency set available, the optional offline mode creates a virtual environment with system packages visible:

    .\scripts\setup.ps1 -OfflineSystemPackages

The offline fallback reuses machine-wide packages and is not fully isolated. The lock pins the transitive Windows/Python 3.11 runtime and development dependency graph resolved from the available environment. When changing dependencies, update pyproject.toml and regenerate/verify the lock from a clean Python 3.11 Windows environment with package-index access.

## Download and validate data

Install Kaggle CLI into the project environment if needed, configure account authorization locally, then run:

    .\.venv\Scripts\python.exe -m pip install kaggle
    .\.venv\Scripts\python.exe scripts\download_dataset.py

The command checks available space, leaves pre-existing files untouched, uses temporary storage, validates the exact ULB schema and target labels before atomic placement, computes SHA-256, and writes provenance metadata in data/raw. Raw files are ignored by Git.

## Run EDA

    .\scripts\run-eda.ps1

CMD alternative:

    .venv\Scripts\python.exe -m fraud_detection.eda --dataset data\raw\creditcard.csv --output-dir reports

Fixture-only smoke analysis:

    .\.venv\Scripts\python.exe -m fraud_detection.eda --synthetic-demo --output-dir reports

Fixture reports are placed under reports/demo and visibly state that they are synthetic. Do not merge them into the real-data EDA report.

## Development conventions

- Keep calculations in src/fraud_detection and imports explicit.
- Keep notebooks sequential and clear kernel state; each notebook selects its source independently.
- Preserve raw data and use outputs only for reports.
- Use a fixed seed where sampling is used.
- Keep report metadata deterministic except acquisition provenance timestamps.

## Windows notes

- PowerShell runner scripts can also be called from CMD through powershell -NoProfile -File.
- If local script policy blocks execution, use -ExecutionPolicy Bypass for the one process only; no persistent policy is changed.
- No administrator rights, Docker, WSL, or global package installation is required.
