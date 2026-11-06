# Mission 02 implementation plan

## Frozen scientific protocol

- Verify the local ULB source against its provenance SHA-256 before each real-data run.
- Partition the source in its existing monotonic time order using cumulative row quantiles at 70% and 85%. Choose the nearest cumulative boundary among unique `Time` values; equal timestamps stay together. The resulting primary split is chronological and contains no exclusions.
- Keep the latest 15% as a sealed final test. Select models only by mean Average Precision across three expanding-window folds inside the training partition. The folds are formed from five row-balanced blocks of complete timestamp groups; every validation block is later than its corresponding fit block.
- Compare a prior DummyClassifier; Logistic Regression with standard scaling (unweighted C=0.1, unweighted C=1, and balanced C=1); Random Forest (unweighted and balanced-subsample); and HistGradientBoosting (unweighted and balanced). Hyperparameters and the seed are fixed and written to the experiment registry.
- Refit the selected candidate on the complete training partition. Fit a one-dimensional sigmoid calibrator only to its held-out predictions from the training-only expanding folds. Use validation for calibration assessment and to choose a maximum-F2 threshold. After selection is frozen, score all candidates on validation at the fixed 0.5 reference threshold for descriptive comparison only; those results do not change the winner. Do not use test labels for model, calibration, or threshold selection.
- Fit Isolation Forest separately on Class 0 rows from training only. Rank validation and final-test transactions by `-score_samples` (higher means more anomalous); do not describe these scores as probabilities.
- Report ranking, threshold, confusion-count, calibration, alert-budget, and anomaly results. State the uncertainty from the short observation period and small validation/test fraud counts.

## Implementation sequence

1. Add the split engine and compact manifest; validate timestamp and duplicate boundaries before model fitting.
2. Add reusable preprocessing, candidate construction, time-aware selection, calibration, threshold, and metric modules.
3. Add the independent Isolation Forest track, local experiment registry, trusted artifact persistence, and inference API.
4. Run the complete real-data workflow once, with the test partition opened only after development choices are frozen.
5. Generate compact reports, figures, and executed educational notebooks from reusable package outputs.
6. Add synthetic unit tests and an opt-in real-data smoke path; run all checks.
7. Update project tracking, architecture decisions, and the Mission 03 handoff; inspect the full diff, commit logically, push normally, and verify synchronization.

No random resampling or feature selection is planned. No row-level prediction data or model binary will be committed. Stratified random evaluation is omitted because the predeclared forward-in-time evaluation is the primary target and the available positive sample is small; it will not be used to tune the primary model.
