# AI Fraud Detection & Explainable Intelligence

An extensible financial fraud analytics project. Missions 01 and 02 establish verified data analysis and a reproducible fraud-scoring engine; later missions add explanations, an API, and a frontend.

## Business and scientific objective

Help analysts examine historical transaction labels, compare candidate detections, inspect estimated risk, and understand model outputs. The product must keep confirmed historical labels separate from predictions, risk estimates, anomaly scores, and explanations. A score or outlier is not proof of fraud.

## Current status

Missions 01 and 02 are complete and their validated deliverables are pushed to origin/main. A fresh post-push fetch confirmed local and remote synchronization. Mission 02 compares supervised classifiers and a separate Isolation Forest, uses chronological leakage controls, training-fold probability calibration, and a validation-selected threshold. The latest run selected balanced Logistic Regression and produced aggregate reports under reports/ml/. The raw ULB CSV, model binaries, and virtual environments remain excluded from Git. The final test period was scored twice in deterministic runs to correct and verify missing Isolation Forest artifact persistence; the repeat and its limitations are recorded in docs/ml/leakage-prevention.md. Mission 03 is ready to begin, but no SHAP explanations or production service have been built. See PROGRESS.md for validation and delivery history.

## Architecture

- src/fraud_detection: schema contract, loading, profiling, analytics, plots, report generation, ML training, evaluation, persistence, and inference.
- scripts: Windows setup, checks, acquisition, and execution entry points.
- notebooks: analytical narratives that call the reusable package.
- data/raw: local source datasets, excluded from Git.
- reports: reproducible EDA and ML reports, tables, and figures; fixture outputs are kept separate.
- backend and frontend integration are reserved for their roadmap missions.

See docs/architecture/system-overview.md.

## Technology

Python 3.11, NumPy, pandas, SciPy, scikit-learn, joblib, Matplotlib, Seaborn, pytest, Ruff, Jupyter notebooks, and GitHub Actions. No PyTorch, TensorFlow, GPU, cloud service, or heavy tracking server is required.

## Dataset

The primary dataset is the ULB Credit Card Fraud Detection dataset distributed on Kaggle. Its locally acquired file passed the ulb-credit-card-v1 schema check: 284,315 Class 0 and 492 Class 1 rows, 31 numeric fields, no nulls or infinities, and 1,081 duplicate copies beyond first. Time is elapsed seconds; V1–V28 are anonymized PCA-derived fields. See docs/data/data-quality-report.md, docs/data/data-dictionary.md, and reports/EDA_REPORT.md.

## Setup

PowerShell from the project root:

    .\scripts\setup.ps1
    .\.venv\Scripts\Activate.ps1

CMD from the project root:

    powershell -NoProfile -File scripts\setup.ps1
    .venv\Scripts\activate.bat

The setup creates a project-local .venv and installs the resolved Windows/Python 3.11 dependency set from requirements-mission02.lock. requirements-mission01.lock is retained as the earlier Mission 01 environment record. pyproject.toml remains the project dependency constraint source. If Windows blocks running a local PowerShell script, use a one-process execution policy option rather than changing a machine-wide policy:

    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup.ps1

The policy option applies only to that PowerShell process.

## Dataset acquisition

The acquisition script uses the official Kaggle CLI and credentials already configured locally. It never displays credentials, leaves incomplete files behind, refuses to replace an existing file, validates schema and labels, records file size and SHA-256, and writes provenance metadata beside the ignored raw file. Kaggle CLI is a one-time acquisition tool and is not a project runtime dependency.

    .\.venv\Scripts\python.exe -m pip install kaggle
    .\.venv\Scripts\python.exe scripts\download_dataset.py

For a fresh clone without the local ignored CSV, install Kaggle CLI and configure authorized credentials locally before acquisition. Never put credentials in this repository or chat. The script will fail safely if the CLI, credentials, or network are unavailable.

## Run EDA

After acquiring and validating the dataset:

    .\scripts\run-eda.ps1

Or run from CMD:

    .venv\Scripts\python.exe -m fraud_detection.eda --dataset data\raw\creditcard.csv --output-dir reports

The report generator writes EDA_REPORT.md, a JSON summary, quality profile, numerical tables, and a bounded set of figures. To smoke-test without real data, explicitly run:

    .\.venv\Scripts\python.exe -m fraud_detection.eda --synthetic-demo --output-dir reports

Fixture output goes under reports/demo and is not ULB evidence.

Key generated outputs include reports/EDA_REPORT.md, reports/figures/, reports/tables/, reports/summaries/eda_summary.json, and reports/summaries/data_quality_profile.json.

## Checks

PowerShell:

    .\scripts\run-checks.ps1

To run the same checks with another interpreter, including a fully isolated environment:

    .\scripts\run-checks.ps1 -PythonPath .venv-isolated\Scripts\python.exe

CMD:

    .venv\Scripts\python.exe -m pytest
    .venv\Scripts\python.exe -m ruff check .
    .venv\Scripts\python.exe -m ruff format --check .
    .venv\Scripts\python.exe -m compileall -q src scripts tests
    .venv\Scripts\python.exe scripts\validate_notebooks.py

Routine pytest and CI do not require the local CSV. To run the opt-in real-data integration check:

    $env:RUN_REAL_DATA_TESTS = "1"
    .\.venv\Scripts\python.exe -m pytest -m real_data -q
    Remove-Item Env:RUN_REAL_DATA_TESTS

## Mission 02 machine learning

The package entry point is fraud-ml. For a new, declared experiment, first freeze the verified chronological split and then run the bounded training/evaluation workflow:

    .\.venv\Scripts\python.exe -m fraud_detection.ml.cli prepare
    .\scripts\train-models.ps1

Training selects from expanding temporal folds inside the training partition, fits sigmoid calibration from training-only out-of-fold scores, selects the F2 threshold on validation, and then scores the final time window. Because this workflow evaluates the final test, do not rerun it to make development decisions; Mission 02's final period is now consumed. The duplicated completion evaluation used to repair missing anomaly-artifact persistence is documented in the leakage audit.

Inspect already saved aggregate results without retraining:

    .\scripts\evaluate-models.ps1

Verify the local supervised and anomaly artifacts:

    .\scripts\verify-model-artifacts.ps1

Saved results, the split manifest, reports, and figures are under reports/ml/. Joblib model files are local under data/models/ and ignored by Git. Only load trusted local artifacts created by this project; joblib deserialization can execute code.

Key documentation:

- docs/ml/data-splitting.md and docs/ml/leakage-prevention.md
- docs/ml/modeling-strategy.md and docs/ml/model-selection.md
- docs/ml/calibration-and-thresholds.md and docs/ml/anomaly-detection.md
- docs/ml/reproducibility.md
- docs/engineering/mission-03-handoff.md
- reports/ml/FINAL_MODEL_REPORT.md and reports/ml/MODEL_COMPARISON.md

## Six-mission roadmap

1. Foundation, dataset validation, data engineering, and EDA — complete.
2. Supervised machine learning, evaluation, and anomaly detection — complete.
3. Explainable AI and risk intelligence.
4. FastAPI backend.
5. Next.js frontend and integration.
6. Hardening, end-to-end testing, documentation, and portfolio delivery.

## Scientific limitations

- V1–V28 are anonymized PCA components; they have no direct business names or causal meaning.
- Time is elapsed seconds from the first transaction in this dataset, not a calendar timestamp.
- The data has no supplied customer, merchant, location, or device history.
- Accuracy can conceal poor minority-class detection; later model evaluation must include precision-recall and threshold-specific measures.
- The chosen model and threshold have only been evaluated on one short historical dataset. The final test is no longer an untouched set because it was scored in two deterministic completion runs; independent future evaluation requires new later data.
- The selected model is not production-ready. There is no future-period validation, authenticated service, monitoring, or business-cost analysis.
- Licensing and permitted redistribution must be checked at the source before sharing dataset contents.
