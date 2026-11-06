# AI Fraud Detection & Explainable Intelligence

An extensible financial fraud analytics project. Mission 01 establishes a reproducible data-quality and exploratory analysis layer; later missions add supervised and anomaly models, explanations, an API, and a frontend.

## Business and scientific objective

Help analysts examine historical transaction labels, compare candidate detections, inspect estimated risk, and understand model outputs. The product must keep confirmed historical labels separate from predictions, risk estimates, anomaly scores, and explanations. A score or outlier is not proof of fraud.

## Current status

Mission 01 code, tests, notebooks, and documentation are implemented. Real ULB acquisition and real-data EDA remain blocked because this environment has no Kaggle CLI or credentials and outbound GitHub/Kaggle access is unavailable. No real-data statistics are claimed. The synthetic smoke fixture is clearly labeled and only validates code paths.

## Architecture

- src/fraud_detection: schema contract, loading, profiling, analytics, plots, and report generation.
- scripts: Windows setup, checks, acquisition, and execution entry points.
- notebooks: analytical narratives that call the reusable package.
- data/raw: local source datasets, excluded from Git.
- reports: reproducible reports, tables, and figures; fixture outputs are kept separate.
- backend and frontend integration are reserved for their roadmap missions.

See docs/architecture/system-overview.md.

## Technology

Python 3.11, NumPy, pandas, SciPy, Matplotlib, Seaborn, pytest, Ruff, Jupyter notebooks, and GitHub Actions. No model training or heavy ML frameworks are included in Mission 01.

## Dataset

The primary candidate is the ULB Credit Card Fraud Detection dataset distributed on Kaggle. Its source describes anonymized European card transactions from September 2013, with PCA features V1–V28, elapsed seconds in Time, Amount, and a binary Class label. Its published counts are source-reported and have not yet been verified against a local file. See docs/data/dataset-selection.md and docs/data/data-dictionary.md.

## Setup

PowerShell from the project root:

    .\scripts\setup.ps1
    .\.venv\Scripts\Activate.ps1

CMD from the project root:

    powershell -NoProfile -File scripts\setup.ps1
    .venv\Scripts\activate.bat

The setup creates a project-local .venv and installs the exact Windows/Python 3.11 dependency set from requirements-mission01.lock. pyproject.toml remains the primary project metadata and dependency constraint source. It does not install Docker, WSL, Node packages, or heavy ML frameworks. If Windows blocks running a local PowerShell script, use a one-process execution policy option rather than changing a machine-wide policy:

    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup.ps1

The policy option applies only to that PowerShell process.

## Dataset acquisition

The acquisition script uses the official Kaggle CLI and credentials already configured locally. It never displays credentials, leaves incomplete files behind, refuses to replace an existing file, validates schema and labels, records file size and SHA-256, and writes provenance metadata beside the ignored raw file.

    .\.venv\Scripts\python.exe -m pip install kaggle
    .\.venv\Scripts\python.exe scripts\download_dataset.py

Complete Kaggle account access and configure credentials locally before acquisition. Never put credentials in this repository or chat. The script will fail safely if the CLI, credentials, or network are unavailable.

## Run EDA

After acquiring and validating the dataset:

    .\scripts\run-eda.ps1

Or run from CMD:

    .venv\Scripts\python.exe -m fraud_detection.eda --dataset data\raw\creditcard.csv --output-dir reports

The report generator writes EDA_REPORT.md, a JSON summary, quality profile, numerical tables, and a bounded set of figures. To smoke-test without real data, explicitly run:

    .\.venv\Scripts\python.exe -m fraud_detection.eda --synthetic-demo --output-dir reports

Fixture output goes under reports/demo and is not ULB evidence.

## Checks

PowerShell:

    .\scripts\run-checks.ps1

CMD:

    .venv\Scripts\python.exe -m pytest
    .venv\Scripts\python.exe -m ruff check .
    .venv\Scripts\python.exe -m ruff format --check .
    .venv\Scripts\python.exe -m compileall -q src scripts tests
    .venv\Scripts\python.exe scripts\validate_notebooks.py

## Six-mission roadmap

1. Foundation, dataset validation, data engineering, and EDA.
2. Supervised machine learning, evaluation, and anomaly detection.
3. Explainable AI and risk intelligence.
4. FastAPI backend.
5. Next.js frontend and integration.
6. Hardening, end-to-end testing, documentation, and portfolio delivery.

## Scientific limitations

- V1–V28 are anonymized PCA components; they have no direct business names or causal meaning.
- Time is elapsed seconds from the first transaction in this dataset, not a calendar timestamp.
- The data has no supplied customer, merchant, location, or device history.
- Accuracy can conceal poor minority-class detection; later model evaluation must include precision-recall and threshold-specific measures.
- No final model is trained or selected in Mission 01.
- Licensing and permitted redistribution must be checked at the source before sharing dataset contents.
