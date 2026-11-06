# ULB Data Dictionary

Schema contract version: ulb-credit-card-v1.

## Expected columns

| Field | Type | Meaning | Notes |
|---|---|---|---|
| Time | Numeric | Seconds elapsed between this transaction and the first transaction in the dataset. | Not a calendar timestamp; do not infer date/hour-of-day. |
| V1–V28 | Numeric | PCA-transformed input variables. | The source withholds original feature meanings. Correlations and SHAP values cannot be mapped automatically to business causes. |
| Amount | Numeric | Transaction amount as supplied by the dataset. | No currency unit is assumed in this project. Zero remains a valid numeric value. |
| Class | Binary numeric target | 1 denotes a fraud label; 0 denotes a genuine/legitimate label. | Historical annotation, not a model output or legal determination. |

Expected ordered column list:

    Time, V1, V2, ..., V28, Amount, Class

The validator requires all 31 fields to be numeric and labels to be 0 or 1. Missing feature values are reported for data-quality review; target nulls are invalid. Infinite values are invalid. Extra columns are reported and permitted by default; strict mode rejects them. Validation does not change or remove any observations.

## Source statements versus local facts

The source page describes European card transactions from September 2013, covering two days, and lists 284,807 rows, 492 frauds, 31 columns, and a 150.83 MB CSV. Those are publisher-provided claims until a downloaded file is validated. Actual row count, class distribution, nulls, duplicates, data types, and checksum remain pending local acquisition.

## Missingness and zeros

Null/NaN means missing. Numeric zero is counted separately and retained as a valid value unless domain evidence establishes otherwise. Do not replace zeros with missing values as a blanket preprocessing rule.
