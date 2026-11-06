# Exact linear attributions

The frozen classifier is a fitted `StandardScaler` followed by balanced binary
`LogisticRegression`. Mission 03 reads the fitted transformer and estimator from the verified
Mission 02 bundle; it does not assume feature scales or fit another scaler.

For a transaction with transformed feature vector `x'`, the engine calculates
`z = intercept + sum(coef_i * x'_i)`. `intercept` is the raw model's reference at zero transformed
feature values, not a population mean. Each signed term is an exact contribution to the raw
decision-function log-odds. Positive terms increase that raw score, negative terms decrease it,
and values within `1e-12` are labeled negligible in local detail.

The runtime checks `intercept + sum(contributions)` against `decision_function` with absolute and
relative tolerance `1e-10`. It also checks `expit(decision_function)` against the estimator's raw
`predict_proba` output. Both identities passed on all 42,722 validation rows; the recorded maximum
linear reconstruction error is `2.84e-14` and raw sigmoid probability error is zero.

The output also contains the calibrated probability and the unchanged Mission 02 threshold, but
the exact linear terms do not add to the calibrated probability. The training-only sigmoid
calibration is a separate mapping after the raw classifier. Attribution indicates the fitted
model's behavior; it does not show that a feature caused fraud. V1–V28 remain anonymized
PCA-derived coordinates.
