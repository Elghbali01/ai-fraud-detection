# Explainability limitations

- V1–V28 are anonymized PCA-derived variables. Time is elapsed seconds without a calendar anchor;
  Amount is the only directly named transaction measure. No merchant, customer, device, or
  geographic causes can be inferred.
- Coefficient and SHAP attributions describe the fitted model's statistical behavior. They do not
  establish causality or prove a transaction is fraudulent.
- SHAP explains raw logistic log-odds with an interventional training background. It does not
  decompose the post-fit calibrated probability.
- The background and attribution ranks are finite-sample summaries. Training-to-validation rank
  stability does not measure future stability.
- There are 492 fraud labels in the complete dataset, 56 in validation, and 52 in the consumed
  final-test partition. The final-test set was not loaded for Mission 03; no new independent
  test result is available.
- Calibration, threshold utility, alert capacity, and tier prevalence can change under distribution
  shift. No independent future period, business costs, investigator feedback, or economic utility
  has been assessed.
- The Isolation Forest detects unusualness relative to a known-legitimate training reference. It
  is not a fraud probability and is reported separately from the supervised score.
