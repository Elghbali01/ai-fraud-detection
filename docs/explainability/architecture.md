# Explainability architecture

Mission 03 adds an offline and reusable explanation layer over the frozen Mission 02 `ModelBundle`.
It does not train a second fraud model. Artifact loading is limited to project-generated local
manifests whose checksums and schemas are verified before trusted `joblib` deserialization.

## Modules and data flow

- `explainability/data.py` verifies the ULB fingerprint and split manifest, then parses only the
  chronological training and validation prefix. It never constructs a frame from final-test rows.
- `linear.py` extracts the fitted `StandardScaler` and `LogisticRegression`, transforms features,
  computes exact coefficient contributions, and checks the raw decision score and estimator
  probability identities.
- `shap_engine.py` selects a deterministic training-only background, builds an interventional
  SHAP linear explainer, and verifies raw-log-odds additivity.
- `global_explanations.py` computes validation feature summaries and training-sample/validation
  ranking stability. `local_explanations.py` provides bounded single and batch explanations.
- `narratives.py` creates deterministic neutral text. `visualization.py` exports headless plots.
- `risk/` maps calibrated probability to a display score, applies versioned validation-derived
  tiers, ranks investigation queues, references the separate anomaly detector, and compares the
  two signals without blending them.
- `risk/contracts.py` exposes the `mission03-intelligence-v1` JSON-ready response contract.

## Input and output boundary

Inference accepts exactly the 30 numeric Mission 02 features in `FEATURE_COLUMNS`; `Class`, missing
fields, extra fields, duplicate names, nonnumeric values, NaN, and infinity are rejected. The
service reuses a loaded bundle and imposes a 100-row limit on detailed explanation batches. Scoring
batches are separately bounded at 10,000 rows. SHAP plots are generated for selected examples,
never per request.

Responses keep calibrated probability, 0–100 display score, frozen-threshold class, risk tier,
raw-log-odds explanation, and optional anomaly score in separate named fields. Explanations omit
the 30 raw input values. Model version, schema version, contract version, threshold, method,
output-space semantics, and reconstruction diagnostics are included where relevant.

## Reproducible generation

Run `scripts/generate-explanations.ps1` after the local raw data and trusted Mission 02 artifacts
are present. It writes reports under `reports/explainability/` and `reports/risk/`; the compact
training-only anomaly reference is stored under ignored `data/models/`. Use
`scripts/validate-explainability.ps1` for synthetic tests and its `-RealData` switch for the
opt-in real-artifact integration. The final-test partition is consumed and excluded from every
Mission 03 explanation, policy, and diagnostic.
