# Mission 04 handoff: FastAPI backend

Mission 03 supplies verified local artifacts, reusable explanation and risk services, generated
contracts, validation-only policies, and the reports under `reports/explainability/` and
`reports/risk/`. Mission 04 should expose those interfaces without retraining or recomputing
validation policies at request time.

## Artifact loading

- Supervised: `fraud_detection.ml.persistence.load_model_bundle(path, expected_sha256=...)`.
- Anomaly: `load_anomaly_artifact(path, expected_sha256=...)`.
- Risk policy: `RiskTierPolicy.from_dict(...)` from `reports/risk/risk_tier_policy.json`.
- Anomaly reference: `load_anomaly_reference(...)` from
  `reports/risk/anomaly_reference_manifest.json`.
- Load trusted project-generated files once at application startup. Never accept paths, joblib
  bytes, or artifact manifests from a request. Keep `data/models/`, the raw dataset, and local
  environments out of Git and out of public HTTP responses.

## Python services

- `ExplainabilityService(bundle, shap_explainer=None, max_batch_size=100)` provides
  `explain_one()` and `explain_batch()`. Linear explanations are available without constructing
  SHAP; SHAP requests require an explainer built from the persisted-schema training background.
- `RiskScoringService(bundle, policy)` provides bounded calibrated scores and tiers; construction
  rejects a policy whose threshold differs from the model.
- `RiskIntelligenceService(scoring_service, explanation_service, anomaly_experiment,
  anomaly_reference)` provides `score_batch()`, `intelligence_one()`, and `intelligence_batch()`.
  Detailed explanations are capped at 100 rows by default; scoring is capped at 10,000.
- Inputs contain exactly 30 finite numeric fields in the persisted `FEATURE_COLUMNS` order after
  validation. The target `Class`, missing values, duplicate names, and extras are rejected.

## Response semantics and errors

Use contract version `mission03-intelligence-v1`. Return schema/model version, calibrated
`fraud_probability`, `risk_score` (100 times probability), the persisted threshold and class,
risk tier, optional explanation, and optional separate anomaly fields. SHAP and linear
contributions are in raw log-odds; do not describe them as calibrated-probability contributions.
Anomaly score is not a probability. Return input/schema errors as 4xx, unavailable or invalid
artifacts as startup/health failures, and internal inference/explanation errors as controlled 5xx
responses with request IDs and no stack traces or feature dumps.

## Suggested routes

- `GET /health`: readiness, schema version, model version, and artifact verification state.
- `GET /metadata`: threshold, calibration status, policy and contract versions, limits, and score
  semantics; do not return local paths or training data.
- `POST /score`: one record or a bounded batch; optional anomaly output.
- `POST /explain`: one record or at most 100 selected records; linear by default and SHAP only
  when the training-background explainer was loaded.
- `POST /prioritize`: bounded batch with an explicit TopK or percentage review budget and stable
  ordering.

## Security and performance

Set body-size and batch-size limits, reject `Class`, cap explanation count, sanitize IDs in logs,
and avoid storing raw transaction features. Keep trusted artifacts outside upload-accessible
directories. Load models once per worker, reuse the SHAP explainer, and do not generate plots in
request handlers. Run `pip check`, contract tests, synthetic endpoint tests, and opt-in integration
against train/validation development rows only. The final-test partition is consumed. Independent
future evaluation requires new later data.

The frontend mission can use existing static plots and JSON fields as examples, but should present
probability, decision status, risk tier, anomaly percentile, and raw-log-odds explanation as
separate visual elements. Do not imply PCA variables have human-readable causes.
