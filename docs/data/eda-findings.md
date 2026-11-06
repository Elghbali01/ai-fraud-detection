# Real ULB EDA Findings

**Status:** generated from the acquired, hash-verified Kaggle CSV on 2026-11-06. The raw file is not committed. Reproduce with data/raw/creditcard.csv and scripts/run-eda.ps1.

## Dataset and quality

The file has 284,807 rows and 31 numeric columns in the expected order: Time, V1–V28, Amount, Class. It contains no missing values, infinite values, or invalid labels. It uses 30 float64 columns and an int64 Class. Deep DataFrame memory usage is 70,632,268 bytes; the CSV is 150,828,752 bytes. The full checksum and acquisition record are in data/raw/dataset-provenance.json.

There are 1,081 exact duplicate copies beyond the first. In total, 1,854 rows participate in exact duplicate groups: 1,822 labeled 0 and 32 labeled 1. The extra copies include 1,062 Class 0 rows and 19 Class 1 rows. No records were removed. Exact duplicates share their complete Time and other feature values; near duplicates were not assessed.

Time ranges from 0 to 172,792 elapsed seconds and is monotonic in file order with no decreases. It has 124,592 distinct values. The feature does not contain a calendar origin.

## Class imbalance

- Class 0: 284,315 transactions (99.827251%).
- Class 1: 492 transactions (0.172749%).
- Majority/minority count ratio: 577.876:1.
- Predicting Class 0 for every row would be 99.827251% accurate and detect zero fraud cases (0% recall for Class 1).

The last value is a trivial metric sanity check, not a trained model. Accuracy by itself cannot establish useful fraud detection.

## Amount

Amounts range from 0 to 25,691.16 dataset units. They are strongly right-skewed in both classes.

| Class | Count | Mean | Median | Std. dev. | 90th percentile | 99th percentile | Max | Skewness |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 284,315 | 88.291 | 22.00 | 250.105 | 202.724 | 1,016.966 | 25,691.16 | 17.003 |
| 1 | 492 | 122.211 | 9.25 | 256.683 | 346.746 | 1,357.428 | 2,125.87 | 3.754 |

Fraud-labeled rows have a higher mean but a lower median than legitimate rows, consistent with a highly skewed distribution and some large amounts. This is descriptive association, not evidence that transaction size causes fraud. Visualizations use signed log transforms for readability only; the source values are preserved.

## Elapsed time

Eight six-hour bins were generated. All have at least 1,000 transactions. One bin has fewer than 30 fraud examples and should not support strong rate comparisons.

| Elapsed interval (hours) | Transactions | Fraud labels | Observed fraud rate |
|---|---:|---:|---:|
| 0–6 | 12,340 | 55 | 0.4457% |
| 6–12 | 35,061 | 91 | 0.2595% |
| 12–18 | 46,850 | 71 | 0.1515% |
| 18–24 | 50,535 | 64 | 0.1266% |
| 24–30 | 11,594 | 69 | 0.5951% |
| 30–36 | 35,851 | 27 | 0.0753% |
| 36–42 | 49,585 | 63 | 0.1271% |
| 42–48 | 42,991 | 52 | 0.1210% |

These are observed rates over elapsed-time bins in this historical file, not stable business patterns. Do not infer clock time, day of week, calendar dates, or future behavior from Time.

## PCA features and correlations

The ten largest absolute Spearman associations between a single numeric feature and Class are modest in magnitude: V14 −0.06461, V4 +0.06305, V12 −0.06287, V11 +0.06014, V10 −0.05956, V3 −0.05928, V2 +0.05106, V16 −0.04994, V9 −0.04950, and V7 −0.04831. These univariate rank associations do not rule out multivariate or nonlinear signal and are not model feature-selection results.

The strongest off-diagonal Spearman feature pairs include V21/V22 (+0.67672), V2/Amount (−0.50205), Time/V3 (−0.47335), V27/V28 (+0.45850), and V6/V8 (+0.44405). Correlation is descriptive; the anonymized V fields cannot be explained as business causes.

Class-conditional distributions are plotted for the four most strongly associated PCA fields. Summary statistics for every numeric feature by label, Pearson and Spearman matrices, and all field ranges are in reports/tables/.

## Outlier diagnostics

The 1.5×IQR fences flag 31,904 Amount values (11.202%): the lower fence is −101.7475 and the upper fence is 184.5125. The highest PCA-field flag rates are V27 (39,163; 13.751%), V28 (30,342; 10.654%), V20 (27,770; 9.750%), V8 (24,134; 8.474%), and V6 (22,965; 8.063%). These are statistical diagnostics only. No records were removed, and an IQR outlier is not necessarily fraud.

## Candidate evaluation partition

Time order supports examining a forward-in-time holdout. A descriptive row-quantile split, keeping each equal-Time group together, yields:

| Candidate partition | Time range (seconds) | Rows | Class 0 | Class 1 |
|---|---:|---:|---:|---:|
| Train candidate | 0–132,929 | 199,368 | 198,984 | 384 |
| Validation candidate | 132,930–151,328 | 42,718 | 42,662 | 56 |
| Test candidate | 151,329–172,792 | 42,721 | 42,669 | 52 |

The cutoffs are Time 132,929 and 151,328 seconds; respectively 4 and 3 source rows have those exact cutoff values and stay together. This is a diagnostic proposal, not a final split. The holdout periods contain few positive cases, so uncertainty around metrics must be reported. A secondary stratified random development comparison should group exact duplicate rows. Keep the latest test data untouched for final evaluation.

## Limitations and next steps

- The data reflects a short historical period and does not represent a modern production stream.
- V1–V28 have no available direct business meanings; model explanations must preserve that limitation.
- There are no entity identifiers to support customer-level or merchant-level split checks.
- Labels, predictions, probabilities, anomaly scores, and human decisions must remain distinct.
- No model was trained or selected in Mission 01. Use the handoff protocol in docs/engineering/mission-02-handoff.md.
