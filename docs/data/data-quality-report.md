# Data Quality Report

Status: incomplete for real ULB data as of 2026-11-06.

## Acquisition state

No real dataset file was present in data/raw during the initial audit. Kaggle CLI and local Kaggle credentials were absent and outbound source access was unavailable. Accordingly, there are no observed dataset row, column, class, missingness, duplicate, type, or integrity findings to report.

The published ULB source claims 284,807 transactions, 492 positive labels, 31 columns, and a 150.83 MB CSV. These are source statements, not local measurements.

## Implemented quality checks

The reusable profiler and schema validator report row and column counts, deep memory size, per-column dtype, missing count/percentage, distinct values, constants, numeric summaries and quantiles, zeros, non-finite values, duplicate records, required/missing/unexpected fields, invalid labels, and class counts/imbalance. Duplicate rows are never deleted automatically.

Small synthetic fixtures verify edge cases. Their results are not shown here as real-data findings. Generate this report from a local file with the acquisition script followed by the EDA command in the development guide.
