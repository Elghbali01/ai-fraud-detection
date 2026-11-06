# EDA Findings

Status: real-data findings pending dataset acquisition.

## Verified from the publisher's dataset description

- The source describes two days of European card transactions from September 2013.
- Time means elapsed seconds from the first transaction in the file.
- V1–V28 are PCA-derived anonymized inputs; Amount and Time are not PCA-transformed, and Class is the response.
- The source page reports 284,807 transactions and 492 fraud labels. These counts are not locally verified.
- The source warns that accuracy is not meaningful for the highly imbalanced task and recommends a precision-recall measure.

## Not yet observed locally

No local ULB file was available. Actual class share, amount distribution, temporal counts/rates, feature associations, missingness, duplicates, extreme values, and correlations remain unknown. No numeric EDA conclusions should be inferred from the source description alone.

## Implemented analyses

The EDA package calculates per-class amount summaries, six-hour elapsed-time bins with low-volume flags, Pearson and Spearman numeric correlations, Spearman feature-label associations, IQR outlier diagnostics, and bounded class/amount/time/feature charts. IQR results do not remove data. Amount transforms are chart-only.

## Mission 02 implications

Inspect actual temporal ordering, label distribution across time, class density per candidate period, and any repeated records after acquisition. Compare stratified random validation with chronological validation. Keep the future test period separate from model and threshold selection, and fit transformations within training folds. No final split protocol is selected before real characteristics are inspected.
