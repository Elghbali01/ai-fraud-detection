# Data Quality Report

**Status:** source-verified ULB file acquired and validated on 2026-11-06.
**Contract:** ulb-credit-card-v1.
**Raw file:** data/raw/creditcard.csv (local and excluded from Git).

## Provenance and integrity

- Publisher: [ULB Credit Card Fraud Detection on Kaggle](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud)
- Kaggle dataset identifier: mlg-ulb/creditcardfraud
- Retrieved through the Kaggle CLI on 2026-11-06 at 17:05:21 UTC.
- File size: 150,828,752 bytes.
- SHA-256: 76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89
- Sidecar: data/raw/dataset-provenance.json; the acquisition script recorded identity, schema result, class counts, size, retrieval time, and checksum. The EDA runner rechecked the hash before classifying the input as source-verified.

The CSV was not edited or cleaned in place. Reports and diagnostics describe the source rows as acquired.

## Observed structure and labels

| Check | Observed result |
|---|---:|
| Rows | 284,807 |
| Columns | 31 |
| Ordered schema | Time, V1–V28, Amount, Class |
| Data types | 30 float64, 1 int64 (Class) |
| Schema validation | Valid; no missing or unexpected required fields |
| Missing values | 0 |
| Infinite values | 0 |
| Invalid or missing target labels | 0 |
| Label 0 | 284,315 (99.827251%) |
| Label 1 | 492 (0.172749%) |
| Majority/minority ratio | 577.876:1 |
| Deep in-memory DataFrame size | 70,632,268 bytes |
| Exact duplicate copies beyond first | 1,081 |
| Rows participating in exact duplicate groups | 1,854 |

Among extra duplicate copies, 1,062 have label 0 and 19 have label 1. Duplicate rows were not removed. An exact duplicate is identical across all 31 fields; near-duplicate similarity was not assessed.

The validator confirmed numeric fields and binary labels {0, 1}. Time and Amount have observed ranges of 0–172,792 seconds and 0–25,691.16 dataset units. Amount units/currency are not assumed. Time is monotonic in file order, with zero decreases and 124,592 unique values. It is elapsed time from the first transaction, not a calendar timestamp.

Publisher-reported row and label counts match the local file. This match, schema check, Kaggle dataset identifier, and byte-level sidecar hash provide evidence of source identity; the sidecar is a local acquisition record, not an independent publisher checksum.

## Reproducible validation

From the repository root in PowerShell:

~~~powershell
.\.venv\Scripts\python.exe scripts\download_dataset.py
.\scripts\run-eda.ps1
~~~

The downloader refuses to replace an existing valid dataset. For a downloaded file, validate the CSV and inspect the provenance sidecar before using the generated findings. The repository ignores data/raw/**; do not stage the raw CSV or Kaggle credentials.

The optional integration check validates the expected shape, ordered schema, types, labels, nulls, finite values, duplicate count, checksum, and generated EDA artifacts:

~~~powershell
$env:RUN_REAL_DATA_TESTS = "1"
.\.venv\Scripts\python.exe -m pytest -m real_data
Remove-Item Env:RUN_REAL_DATA_TESTS
~~~

The full column profile, including per-field ranges, quantiles, zeros, and distinct counts, is in reports/tables/column_profile.csv and reports/summaries/data_quality_profile.json.

## Interpretation limits

- Duplicate records remain in place. Mission 02 should keep exact duplicate groups together when using random partitions or use time cutoffs that keep identical Time values together.
- A zero is a measured value, not missingness; do not blanket-replace zeros.
- IQR flags are exploratory. They do not label fraud or justify automatic removal.
- The dataset covers a short, historical period and contains no customer, merchant, location, or device identifiers.
- V1–V28 are anonymized PCA-derived features. Their ranges and associations do not supply direct business explanations.
- The observed label is a historical dataset annotation, not a model output or legal determination.
