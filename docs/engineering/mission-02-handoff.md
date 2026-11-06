# Mission 02 Handoff from Mission 01 (historical)

This is the pre-training handoff written when Mission 01 closed. Mission 02 is now complete. The implemented evaluation protocol, actual timestamp boundaries, results, and deviations from this proposal are recorded in docs/ml/data-splitting.md, docs/ml/mission-02-plan.md, and reports/ml/. In particular, no secondary stratified-random sensitivity run was performed; the chronological protocol was selected before training.

## Validated dataset

The locally acquired ULB Credit Card Fraud Detection CSV is source-verified by the dataset identifier, valid ulb-credit-card-v1 schema, and SHA-256 sidecar check. It contains 284,807 rows and 31 numeric columns: Time, V1–V28, Amount, and Class. Class counts are 284,315 label 0 and 492 label 1 (0.172749% positive; 577.876:1 count ratio). There are no missing values, infinities, or invalid target labels. There are 1,081 exact duplicate copies beyond first, across 1,854 rows in duplicate groups.

The raw file is excluded from Git. Provenance is recorded in data/raw/dataset-provenance.json, and the validated report is reports/EDA_REPORT.md. Do not substitute a fixture for the ULB observations.

## Key findings and risks

- A predict-all-zero rule has 99.827251% accuracy and 0% fraud recall. Accuracy is insufficient.
- Amount is right-skewed; the fraud-class median is 9.25 and mean 122.211, while the legitimate median is 22 and mean 88.291. These are descriptive, not causal.
- Time is monotonic in row order, spans 0–172,792 elapsed seconds, and has no calendar origin.
- A row-quantile chronological candidate gives 384, 56, and 52 positive cases in train, validation, and test. Those holdout counts are small and performance intervals may be wide.
- Exact duplicates should not cross random partitions. The proposed temporal boundaries preserve identical Time values; near-duplicate similarity was not assessed.
- The dataset has no customer, merchant, location, or device identity fields. It cannot support entity-level generalization checks.
- V1–V28 are anonymized PCA-derived values; no business meanings or causal explanations are available.

## Recommended evaluation design

1. Freeze the schema, source checksum, and experiment configuration. Keep Class out of all features.
2. Start with a chronological candidate: train on Time through 132,929 seconds, validation through 151,328 seconds, and reserve the later 151,329–172,792-second period as a candidate final test. Reassess this design before training because the validation/test subsets contain only 56/52 fraud cases. Do not use the final period for model selection or threshold tuning.
3. Compare a stratified random development evaluation as a secondary, optimistic view. Group exact duplicate rows into the same fold. Keep the chronological holdout as the primary robustness view; do not silently choose whichever split gives the best score.
4. Fit imputers, scalers, feature selection, calibration, and any resampling inside training folds only. Never select features on the full dataset. If resampling is evaluated, apply it only to each training fold.
5. Save seeds, package versions, source hash, split definitions, preprocessing, estimator parameters, and metric outputs. Reproduce all data-derived fit steps from training data only.

The two-day source period limits claims about longer-term performance. Report exact evaluation windows and positive counts. Use confidence intervals or other uncertainty summaries where practical; 52 positive test examples do not support fine-grained claims.

## Supervised baseline track

Compare, using identical splits and a reproducible preprocessing pipeline:

1. DummyClassifier as a metric sanity baseline.
2. LogisticRegression with training-fold-only scaling and explicit class-imbalance handling.
3. RandomForest.
4. HistGradientBoosting.

Do not assume class weights or resampling improve operational performance; compare methods on untouched validation data. Avoid adding identifiers or inferred calendar features absent from the source.

## Separate unsupervised track

Evaluate IsolationForest separately from supervised classification. Fit it without Class, then use labels only to evaluate ranking or detection behavior. Report its anomaly score and operating threshold distinctly from predicted fraud probability, historical Class, and human confirmation. Do not present an anomaly as proof of fraud.

## Metrics and threshold selection

Report PR-AUC/AUPRC as a primary ranking measure, plus precision, recall, F1 where useful, confusion-matrix counts, ROC-AUC as a secondary measure, and precision/recall at operational review capacity. Include positive counts and uncertainty. Accuracy alone is misleading at 0.172749% fraud prevalence.

Choose thresholds on validation data against a stated cost or review-capacity objective. If calibrated probabilities are needed, fit and assess calibration using training/validation procedures only. Freeze model and threshold before using the final test. Report the chosen threshold, predicted positive volume, false positives, true positives, false negatives, and resulting precision/recall.

## Reusable Mission 01 components

- loading.py and schema.py: CSV loading and versioned schema checks.
- profiling.py: null, duplicate, numeric, class, and memory profiles.
- analytics.py: class balance, amount summaries, elapsed-time bins, correlations, associations, and IQR diagnostics.
- visualization.py and reporting.py: reproducible figures, tables, and summaries.

Mission 01 completed EDA and did not train or select any model. This handoff is an evaluation plan; it is not a claim that a split or model has been validated for production.
