# Mission 02 Handoff

## Available dataset

Selected candidate: ULB Credit Card Fraud Detection, expected at data/raw/creditcard.csv. The file was not acquired in this environment. Kaggle CLI and credentials were absent, outbound network access was blocked, and no synthetic substitute is labeled as the real dataset. Use scripts/download_dataset.py after authorized local access is available.

## Validated schema

Version ulb-credit-card-v1: Time, V1–V28, Amount, Class; 31 numeric fields. Class labels allowed are 0 and 1. Target missingness and infinite numeric values fail validation. Extra columns are reported and permitted unless strict mode is selected. Feature nulls are reported for review. The loader does not mutate or drop records.

## Data quality and scientific findings

Local row count, class distribution, missingness, duplicate count, and numeric profiles remain unverified. The publisher page claims 284,807 rows and 492 fraud cases. The source describes Time as elapsed seconds, and V1–V28 as PCA-derived anonymized features. No currency unit or calendar origin is assumed.

## Reusable modules

- loading.py: safe CSV reads and ULB loader.
- schema.py: schema contract and validation result.
- profiling.py: column, null, duplicate, class, numeric, zero, non-finite, and memory profile.
- analytics.py: class imbalance, amount summaries, elapsed-time bins, correlation, rank associations, and IQR diagnostics.
- visualization.py: bounded class/amount/time/PCA/correlation figures.
- reporting.py and serialization.py: Markdown, CSV, JSON outputs.

## Evaluation strategy for Mission 02

Inspect source ordering and label counts over elapsed Time before choosing final validation. Compare a stratified random split baseline with a chronological holdout or forward-chaining strategy. The two-day span limits long-term generalization claims. Keep the latest test interval untouched during model/threshold selection, fit preprocessing only inside training folds, and report PR-AUC/AUPRC, precision, recall, confusion counts, and capacity/cost implications at declared thresholds. Accuracy alone is insufficient.

## Leakage risks

- Never include Class among predictive inputs.
- Do not fit scaling, imputation, feature selection, resampling, or calibration on the full dataset before splitting.
- Do not use future test observations for threshold/model selection.
- Inspect ordering, repeated rows, and any later engineered fields before training.
- Do not infer identity or temporal metadata that the CSV does not contain.

## Recommended baselines

1. Majority-class prediction as an illustrative metric sanity check only.
2. Logistic regression with training-fold-only scaling and class-aware metrics.
3. A tree-based baseline without assumptions about business semantics of PCA variables.
4. An unsupervised anomaly score evaluated separately from labeled classification; labels are only for evaluation.

## Expected ML interfaces

Mission 02 should expose a reproducible train/evaluate API consuming a validated feature frame and target column, with explicit split strategy, random seed, preprocessing pipeline, and metric report. Inference should accept the same versioned feature contract and return a predicted class/probability distinctly from anomaly score and future risk outputs.

## Known blockers and reproduction commands

Blocker: real ULB file and GitHub connectivity unavailable in this run. When authorized access is ready:

    .\.venv\Scripts\python.exe -m pip install kaggle
    .\.venv\Scripts\python.exe scripts\download_dataset.py
    .\scripts\run-eda.ps1
    .\.venv\Scripts\python.exe -m pytest

Fixture smoke checks:

    .\.venv\Scripts\python.exe -m fraud_detection.eda --synthetic-demo --output-dir reports
    .\.venv\Scripts\python.exe scripts\validate_notebooks.py
