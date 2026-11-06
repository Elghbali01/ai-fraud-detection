# Probability and calibration semantics

The model exposes three distinct probability/score values:

1. `raw_decision_score`: the fitted logistic model's linear decision function in log-odds.
2. `raw_estimator_probability`: `sigmoid(raw_decision_score)`, which equals the classifier's
   uncalibrated `predict_proba` output.
3. `fraud_probability`: the persisted sigmoid calibration applied to the raw estimator
   probability. Its mapping was fit on training-only out-of-fold scores.

`risk_score` is a presentation-only scaling: `100 * fraud_probability`. The binary decision uses
the exact persisted Mission 02 threshold `0.1835921396957453`; it is not refit here. SHAP and exact
linear attributions explain item 1. They are not additive differences of item 2 or item 3. A
calibrated probability is an estimate under the fitted calibration and historical data, not a
guarantee under prevalence or behavior shift.

The model output includes calibration status and threshold. Mission 03 does not claim that a
validation-derived tier is calibrated or that a prediction proves fraud.
