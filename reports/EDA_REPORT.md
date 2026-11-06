# Exploratory Data Analysis

**Data status:** SOURCE_VERIFIED_FILE. **Dataset identifier:** creditcard.csv.

## Dataset overview

- Rows: 284,807
- Columns: 31
- Deep memory usage: 70,632,268 bytes
- Duplicate rows: 1,081 (reported, not removed)
- Rows in exact duplicate groups: 1,854
- Missing values: 0
- Infinite values: 0
- Numeric dtypes: 30 float64, 1 int64
- Time range: 0.0–172792.0 elapsed seconds
- Amount range: 0.0–25691.16 dataset units
- Schema validation: valid (ulb-credit-card-v1)

### Provenance

- Source: [https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud)
- Dataset identifier: `mlg-ulb/creditcardfraud`
- Retrieved at (UTC): 2026-11-06T17:05:21.945758+00:00
- File size: 150,828,752 bytes
- SHA-256: `76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89`
- Acquisition schema check: `ulb-credit-card-v1`, valid=True; the current file hash was verified before analysis.

## Label distribution

- Legitimate labels (0): 284,315
- Fraud labels (1): 492
- Fraud share: 0.172749%
- Majority/minority ratio: 577.8760162601626
- Majority-class baseline accuracy: 0.9982725143693799

Illustrative majority-class prediction only; this is not a trained fraud model.
A predict-all-legitimate rule would achieve the displayed accuracy while detecting none of the fraud cases (0% fraud recall). Accuracy alone is therefore misleading; Mission 02 should report precision-recall metrics and threshold-specific confusion counts.

## Amount summaries

| class_label | transactions | non_missing_amounts | zero_amount_count | mean | median | std | min | q25 | q75 | q90 | q95 | q99 | max | skewness |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 284315 | 284315 | 1798 | 88.291 | 22 | 250.105 | 0 | 5.65 | 77.05 | 202.724 | 364.409 | 1016.97 | 25691.2 | 17.0031 |
| 1 | 492 | 492 | 27 | 122.211 | 9.25 | 256.683 | 0 | 1 | 105.89 | 346.746 | 640.905 | 1357.43 | 2125.87 | 3.75448 |

Amounts are reported in dataset units. A signed log transform appears only in plots; it handles zeros and negative values without modifying the loaded values.

## Elapsed-time activity

| elapsed_start_seconds | elapsed_end_seconds | transactions | fraud_count | fraud_rate | low_volume | low_fraud_count |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 21600 | 12340 | 55 | 0.00445705 | False | False |
| 21600 | 43200 | 35061 | 91 | 0.00259548 | False | False |
| 43200 | 64800 | 46850 | 71 | 0.00151547 | False | False |
| 64800 | 86400 | 50535 | 64 | 0.00126645 | False | False |
| 86400 | 108000 | 11594 | 69 | 0.00595135 | False | False |
| 108000 | 129600 | 35851 | 27 | 0.000753117 | False | True |
| 129600 | 151200 | 49585 | 63 | 0.00127055 | False | False |
| 151200 | 172800 | 42991 | 52 | 0.00120956 | False | False |

Time is treated as elapsed seconds from the dataset origin. The analysis does not convert it into calendar timestamps. Bins below the configured minimum are marked low volume; bins with fewer than 30 fraud cases are marked low_fraud_count. Neither group should support strong rate comparisons.

Time ordering check: monotonic_increasing=True; decreases=0; unique Time values=124,592. This is elapsed-time ordering, not a calendar timestamp.

## PCA-derived feature analysis

V1–V28 are anonymized PCA-derived numeric fields. Their values and associations are reported without assigning business meanings. The feature-label table below ranks Spearman associations by absolute magnitude; it is descriptive, not causal or a feature-selection result.

| feature | spearman_with_class | absolute_association | non_missing_pairs |
| --- | --- | --- | --- |
| V14 | -0.0646135 | 0.0646135 | 284807 |
| V4 | 0.0630453 | 0.0630453 | 284807 |
| V12 | -0.0628701 | 0.0628701 | 284807 |
| V11 | 0.060143 | 0.060143 | 284807 |
| V10 | -0.0595639 | 0.0595639 | 284807 |
| V3 | -0.0592784 | 0.0592784 | 284807 |
| V2 | 0.0510618 | 0.0510618 | 284807 |
| V16 | -0.0499363 | 0.0499363 | 284807 |
| V9 | -0.0494988 | 0.0494988 | 284807 |
| V7 | -0.0483079 | 0.0483079 | 284807 |

Class-conditional summaries for every numeric predictor are in tables/class_conditional_summaries.csv. The selected PCA figure shows density distributions for the four highest absolute Spearman-associated PCA fields; full feature ranges and quantiles are in tables/column_profile.csv.

## Feature associations and outliers

Selected numeric feature associations with the label use Spearman correlation, sorted by absolute coefficient. They are descriptive, may be unstable for rare labels, and do not establish causality.

| feature | spearman_with_class | absolute_association | non_missing_pairs |
| --- | --- | --- | --- |
| V14 | -0.0646135 | 0.0646135 | 284807 |
| V4 | 0.0630453 | 0.0630453 | 284807 |
| V12 | -0.0628701 | 0.0628701 | 284807 |
| V11 | 0.060143 | 0.060143 | 284807 |
| V10 | -0.0595639 | 0.0595639 | 284807 |
| V3 | -0.0592784 | 0.0592784 | 284807 |
| V2 | 0.0510618 | 0.0510618 | 284807 |
| V16 | -0.0499363 | 0.0499363 | 284807 |
| V9 | -0.0494988 | 0.0494988 | 284807 |
| V7 | -0.0483079 | 0.0483079 | 284807 |

The full Pearson and Spearman matrices are in tables/pearson_correlations.csv and tables/spearman_correlations.csv. High absolute correlations are descriptive and may reflect transformed or anonymized variables.

Strongest off-diagonal predictor correlations by absolute magnitude (excluding Class):

| feature_a | feature_b | correlation | absolute_correlation |
| --- | --- | --- | --- |
| V21 | V22 | 0.676718 | 0.676718 |
| V2 | Amount | -0.502052 | 0.502052 |
| Time | V3 | -0.473348 | 0.473348 |
| V27 | V28 | 0.458497 | 0.458497 |
| V6 | V8 | 0.444053 | 0.444053 |

| feature | outlier_count | outlier_pct | lower_fence | upper_fence |
| --- | --- | --- | --- | --- |
| V27 | 39163 | 13.7507 | -0.313667 | 0.333872 |
| Amount | 31904 | 11.202 | -101.748 | 184.512 |
| V28 | 30342 | 10.6535 | -0.249819 | 0.27514 |
| V20 | 27770 | 9.75046 | -0.728865 | 0.650184 |
| V8 | 24134 | 8.47381 | -1.01259 | 1.13131 |
| V6 | 22965 | 8.06336 | -2.51859 | 2.14886 |
| V23 | 18541 | 6.51002 | -0.626079 | 0.611875 |
| V12 | 15348 | 5.38891 | -1.94129 | 2.15395 |

The 1.5×IQR rule flags values outside each feature's quartile fences; it is an exploratory diagnostic, not a fraud definition. For Amount, the fences are -101.748 and 184.512, flagging 31,904 rows (11.202%). No observations were removed. Fraudulent observations may be statistically unusual, but ordinary values can also be fraud.

## Leakage-aware evaluation notes

A descriptive 70/15/15 chronological candidate was formed by selecting row-quantile Time cutoffs 132929 and 151328 seconds, then keeping equal Time values together:

| candidate | rows | Class 0 | Class 1 | Time min | Time max |
| --- | --- | --- | --- | --- | --- |
| train_candidate | 199368 | 198984 | 384 | 0 | 132929 |
| validation_candidate | 42718 | 42662 | 56 | 132930 | 151328 |
| test_candidate | 42721 | 42669 | 52 | 151329 | 172792 |

This is a split diagnostic only, not a trained or selected evaluation partition.

Keep repeated exact rows in the same temporal partition by using the Time cutoffs above; this avoids exact duplicate copies crossing those candidate boundaries. Near-duplicate similarity was not assessed. Compare a chronological holdout with stratified random development validation as a secondary view. Fit imputation, scaling, feature selection, resampling, and calibration only inside training folds. Reserve the latest test period for one final evaluation and never use it for model or threshold selection.

## Scientific limitations

- PCA-derived V1–V28 values are anonymized and do not map directly to business concepts.
- Predictions, estimated risk, anomaly scores, and confirmed historical labels are different quantities.
- No model was trained in Mission 01.
- Candidate 70/15/15 cutoffs are descriptive and have not been selected as a final split.
- Data-dependent conclusions below apply only to the data status identified at the top.

## Artifacts

Figures: class_distribution.png, amount_distribution.png, amount_by_class.png, time_activity.png, selected_pca_distributions.png, selected_correlations.png

Tables and machine-readable summaries are in sibling tables/ and summaries/ directories.
