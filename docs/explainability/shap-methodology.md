# SHAP methodology

SHAP 0.51.0 is used with `shap.Explainer(..., algorithm="linear")` and an Independent
interventional masker around the persisted logistic estimator. The model input to this explainer
is the fitted `StandardScaler` feature space. The explained output is the uncalibrated estimator's
raw decision function in log-odds.

## Background and determinism

- Source: Mission 02 training rows only; no label filtering or rebalancing, so the natural training
  prevalence is retained.
- Method: uniform sample without replacement, sorted by original row position after selection.
- Size: 512 rows; seed: 17.
- Provenance: dataset SHA-256, split manifest ID, ordered feature names, SHAP version, and a
  background content digest are stored in `reports/risk/mission03_results.json`.
- Anomaly reference rows are a separate artifact and are not used as the SHAP background.

The explainer is checked against the raw estimator decision function with tolerance `1e-7`.
Validation covered all 42,722 observations: additivity passed, with maximum absolute error
`3.20e-14` and mean absolute error `4.24e-16`. A deterministic 5,000-row training sample is used
for descriptive rank stability. The beeswarm rendering uses a separate deterministic validation
sample of at most 5,000 rows; feature means and rank summaries use all validation rows.

The background expectation is a SHAP baseline over the chosen training sample. It differs from the
linear model intercept at a zero-transformed vector. Neither baseline is the calibrated probability
baseline. SHAP values are not additive contributions to the later calibrated probability and do
not establish causality.
