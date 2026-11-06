# Master Specification

## Product vision

Build a local-first financial fraud analysis platform that helps analysts inspect transaction data, review candidate detections, compare models, obtain transaction-level risk estimates, understand model behavior, prioritize cases, explore visual summaries, and export analysis. The product does not make a fraud determination on behalf of the analyst.

## Functional requirements

### Mission 01

- Load and validate a documented transaction schema without modifying raw source data.
- Profile missingness, duplicates, zero values, type issues, class balance, descriptive statistics, and unusual values.
- Provide reproducible EDA, tables, charts, machine-readable summaries, notebooks, and a Mission 02 handoff.

### Later missions

- Train supervised fraud classifiers with leakage-safe evaluation and threshold analysis.
- Produce separately identified anomaly scores, calibrated or otherwise documented risk estimates, and SHAP-based explanations.
- Provide versioned FastAPI interfaces and a Next.js analyst interface.
- Compare models and allow useful outputs to be exported.

## Non-functional requirements

- Windows 11 and Python 3.11 compatibility.
- Local reproducibility, deterministic seeds for randomized sampling, and machine-readable artifacts.
- Small dependency footprint, no paid API, Docker, WSL, PyTorch, or TensorFlow requirement.
- Modular functions with type hints, clear exceptions, tests, linting, and documentation.
- Raw datasets, credentials, and local environments remain outside version control.

## Scientific principles

- Historical labels, predictions, risk scores, anomaly scores, and explanations are distinct.
- Predictions and anomalies never constitute proof of fraud.
- Associations do not establish causality; PCA features are not business concepts.
- Do not fit learned preprocessing on complete data before splitting.
- Do not use a future test partition for model or threshold selection.
- Never fabricate dataset statistics, model performance, test outcomes, or data provenance.
- Preserve raw inputs and report duplicates/outliers before considering any exclusions.

## Architecture boundaries

- Reusable data and analytics logic belongs in src/fraud_detection.
- Notebooks and scripts orchestrate package functions and do not duplicate business logic.
- Training and evaluation code belongs to Mission 02 modules; explainability belongs to Mission 03.
- FastAPI schemas and services belong to backend in Mission 04.
- The frontend communicates through documented API contracts in Mission 05.
- Model binaries and raw datasets are not checked into Git.

## Security and privacy

- Do not print, hardcode, commit, or request credentials.
- Use only authorized local dataset credentials.
- Do not persist unnecessary transaction-level data in reports.
- Keep local paths and secrets out of generated artifacts.
- Review dataset license and terms independently from project code.

## Evaluation requirements

Report class-aware precision, recall, PR-AUC/AUPRC, confusion counts at declared thresholds, calibration when relevant, and operational capacity/cost trade-offs. Compare at least a simple baseline, retain a time-aware validation, and reserve test data from model and threshold selection.

## Integration requirements

Future APIs must reuse package contracts, validate input schemas, distinguish outputs by meaning, version model and schema artifacts, and expose enough provenance for reproducibility. The frontend must clearly label all output types and show explanation limitations.
