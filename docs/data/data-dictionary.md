# ULB Data Dictionary

Schema contract: ulb-credit-card-v1. The acquired file passed the contract validation on 2026-11-06.

## Source and observed file

Source: [ULB Credit Card Fraud Detection on Kaggle](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud). The locally acquired CSV has 284,807 rows and 31 ordered fields: Time, V1–V28, Amount, Class. All 31 fields are numeric: 30 float64 and one int64 target. No field contains missing or infinite values in this file.

The raw CSV remains local and is excluded from Git. Its byte count and checksum are recorded in data/raw/dataset-provenance.json and summarized in docs/data/data-quality-report.md.

## Fields

| Field | Observed type | Meaning | Observed values and cautions |
|---|---|---|---|
| Time | float64 | Elapsed seconds between a transaction and the first transaction in the file, according to the dataset description. | 0–172,792 seconds; 124,592 distinct values. File order is monotonic by Time. It is not a calendar timestamp and must not be converted into dates or time-of-day. |
| V1–V28 | float64 | Anonymized PCA-derived input variables. | Numeric, with no missing or infinite values in the acquired file. Original feature meanings are withheld; do not attach business names or causal meaning. Each field's observed range, quantiles, zero count, and uniqueness are in reports/tables/column_profile.csv. |
| Amount | float64 | Transaction amount as supplied in the file. | 0–25,691.16 dataset units. No currency unit is assumed. There are 1,825 zero values, retained as observed numeric values. |
| Class | int64 | Historical binary dataset label. | 0: 284,315 transactions; 1: 492 transactions. This is a source label, not a prediction, risk score, or legal finding. |

## Ordered schema

Time, V1, V2, V3, V4, V5, V6, V7, V8, V9, V10, V11, V12, V13, V14, V15, V16, V17, V18, V19, V20, V21, V22, V23, V24, V25, V26, V27, V28, Amount, Class.

The validator requires all 31 fields to be numeric and Class labels to be 0 or 1. Missing target values and infinite numeric values are invalid. Missing feature values are reported for quality review. Unexpected extra fields are reported and permitted by default; strict mode rejects them. Validation does not alter or remove observations.

## Missingness, zeros, duplicates

The acquired file contains no nulls or infinite values. Numeric zero is counted separately from missingness and is retained. The data contains 1,081 duplicate copies beyond the first and 1,854 rows that belong to exact duplicate groups; none were removed. Duplicate totals and class-conditional summaries are generated under reports/.

Publisher descriptions refer to a short, historical set of European card transactions. The dataset does not include customer, merchant, device, location, or calendar-time identifiers, and it does not support direct real-world identity or causal interpretation.
