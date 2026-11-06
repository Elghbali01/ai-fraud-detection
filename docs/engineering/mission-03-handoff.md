# Mission 03 handoff: Explainable AI and risk intelligence

Mission 02 supplies a reproducible supervised scoring bundle, a separate anomaly detector, aggregate evaluation reports, and stable Python inference functions. It does not include SHAP, narrative generation, an API, or a frontend.

## Selected supervised model

- Candidate: balanced Logistic Regression, C=1, StandardScaler.
- Calibration: sigmoid mapping fitted from training-only expanding-fold out-of-fold predictions.
- Decision threshold: 0.1835921396957453, selected on validation by maximum F2.
- Feature order: Time, V1–V28, Amount. Class is the training target only and must never be sent to inference.
- Schema: ulb-credit-card-v1; numeric finite values are required, and missing or extra feature names are rejected.
- Local artifact: reports/ml/artifact_manifest.json points to the trusted, ignored joblib bundle and stores its checksum, threshold, schema, dataset fingerprint, split manifest, and library versions.
- Loader: fraud_detection.ml.persistence.load_model_bundle. The artifact is local and trusted; never expose arbitrary joblib loading to API callers.
- Inference functions: fraud_detection.ml.inference.predict_one and predict_batch.

The batch result includes fraud_probability, raw_model_score, predicted_class, decision_threshold, model_version, and probability_calibration_status. The probability comes from the training-fold sigmoid mapping and validation improved Brier score and log loss; it is not guaranteed to remain calibrated after distribution or prevalence shift.

## Evaluation snapshot

On 42,721 chronological final-test rows with 52 frauds, the selected threshold produced Average Precision 0.73727 (trapezoidal PR area 0.74608), ROC-AUC 0.97724, precision 0.90476, recall 0.73077, F1 0.80851, F2 0.76000, and TN=42,665, FP=4, FN=14, TP=38. The same frozen final-test partition was scored in two completion runs to repair and verify the missing anomaly artifact; results were identical and neither run's test metrics drove selection. See docs/ml/leakage-prevention.md and reports/ml/EXPERIMENT_REGISTRY.json.

## Separate anomaly interface

The Isolation Forest artifact is described by reports/ml/anomaly_artifact_manifest.json and loaded with fraud_detection.ml.persistence.load_anomaly_artifact. Use fraud_detection.ml.inference.predict_anomaly_batch for anomaly_score, score_direction, score_is_probability, and model_version. Higher scores mean more unusual. The model was fit on Class 0 rows from training only. Do not treat its score as fraud probability or blend it with the supervised probability without a separately validated design.

## Explanation recommendations

V1–V28 are anonymized PCA-derived variables. Explanations may describe their numeric contributions in the learned model but must not invent merchant, location, customer, device, or transaction-category meanings. Time is elapsed seconds without a calendar origin. Amount is the only directly named transaction measure. Correlation or feature contribution is not causation.

For Logistic Regression, Mission 03 can explain the linear log-odds contributions after applying the persisted StandardScaler. The explanation code must use the same feature order and scaler as inference, distinguish raw-score contribution from sigmoid-calibrated probability, and verify that the summed contributions reproduce the model score. SHAP LinearExplainer or direct coefficient-times-scaled-feature contributions are plausible candidates; validate the chosen method against the persisted pipeline before exposing explanations. Avoid assigning business meaning to PCA coordinates.

For Isolation Forest, any feature attribution should be explicitly about anomaly score, separate from fraud-risk explanations. Its detector identifies unusual points relative to the fit sample and does not learn the fraud label.

## Suggested future FastAPI contract

Accept one validated JSON object or a bounded batch containing exactly the 30 numeric features in the schema. Reject Class, missing names, unexpected names, non-numeric values, NaN, and infinity. Return model version, schema version, calibrated fraud probability, predicted class at the persisted threshold, threshold, calibration status, and an optional explanation object. Expose anomaly ranking through a distinct endpoint or response field with score semantics clearly labeled; do not combine it into probability.

Load the configured trusted artifact once at application startup. Do not accept model paths or artifact bytes from requests. Preserve the stable inference module as the service boundary, add request limits, and keep model metadata available for health and audit routes.

## Known limitations

- Only 492 labeled fraud examples occur in the whole dataset; validation and final test contain 56 and 52.
- The observation period is short and Time has no calendar anchor.
- Exact duplicate signatures were kept within a partition, but entity and near-duplicate leakage cannot be assessed.
- Probability calibration and threshold utility may shift with prevalence or behavior changes.
- The final test partition was scored twice during the persistence correction; its metrics are not an untouched future evaluation now.
- No production, economic-loss, analyst-capacity, or causal claim is supported.
