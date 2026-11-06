# Mission 03 global explainability results

## Scope and method

This report uses the frozen Mission 02 classifier and only the manifest-defined training and
validation partitions. Global SHAP summaries and label-stratified descriptions use all
42,722 validation observations. SHAP values explain the classifier's raw
decision-function output in raw log-odds, not the later sigmoid-calibrated probability. The
deterministic Independent background contains 512 unweighted training rows at natural prevalence.

The exact engine uses StandardScaler-transformed feature values and fitted logistic coefficients.
Its zero-transformed-feature intercept is a model reference point, not a population average.
Anonymized V1–V28 coordinates have no asserted business meaning; contributions describe model
behavior and do not establish causality.

## Leading mean absolute validation SHAP values

| Feature | Mean abs SHAP | Scaled coefficient | Fraud mean abs SHAP | Legitimate mean abs SHAP |
|---|---:|---:|---:|---:|
| V4 | 0.902842 | 1.145355 | 2.901984 | 0.900218 |
| Amount | 0.837881 | 1.885155 | 1.304580 | 0.837268 |
| V1 | 0.825538 | 0.975388 | 1.012771 | 0.825293 |
| V14 | 0.732885 | -1.071027 | 6.583947 | 0.725206 |
| V6 | 0.602495 | -0.799756 | 0.886108 | 0.602122 |
| V2 | 0.574702 | 0.890625 | 1.143987 | 0.573955 |
| V12 | 0.540608 | -1.039557 | 3.447265 | 0.536793 |
| V22 | 0.538752 | 0.542467 | 0.575140 | 0.538704 |
| Time | 0.535726 | -0.247757 | 0.543035 | 0.535716 |
| V10 | 0.496586 | -0.739954 | 2.328190 | 0.494182 |

## Numerical checks

- Maximum absolute exact linear reconstruction error: `2.842e-14`.
- Maximum absolute SHAP additivity error: `3.197e-14`.
- Sigmoid(raw decision score) matches the estimator's raw probability.
- This equality is within floating-point tolerance.
- The persisted calibration mapping is reported separately.
- No explanation is represented as an additive decomposition of calibrated probability.

## Stability and limits

See `mission03_results.json` for train-sample versus validation rank stability and per-feature
summaries. These descriptive validation analyses are not a new independent test evaluation. The
final-test partition is consumed and was not loaded for this mission.
