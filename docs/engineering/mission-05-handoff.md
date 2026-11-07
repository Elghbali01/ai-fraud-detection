# Mission 05 handoff: local analyst frontend

Mission 04 provides a running, documented, local-only API. Start it from PowerShell with
`scripts/start-api.ps1`; the default URL is `http://127.0.0.1:8000`. The server supports explicit
development CORS origins on localhost/127.0.0.1 port 3000. CORS is not authentication. Keep the
frontend local and do not expose the unauthenticated API over a network.

## Frontend route map

- System and model: `GET /api/v1/health`, `/ready`, `/models/current`, `/models/capabilities`.
- Transaction review: `POST /predictions`, `/predictions/batch`, `/risk/score`,
  `/risk/prioritize`, and `POST /anomalies/score`.
- Explanations: `POST /explanations/local` (`linear_log_odds` or
  `shap_interventional_log_odds`); `GET /explanations/global`.
- File workflow: `POST /uploads/csv`, `POST /analyses`, then analysis detail, summary, and paginated
  results. User CSV analysis is synchronous and limited to 20,000 rows by default.
- Analyst workflow: `GET /history`, create/list/detail/update investigations, and add notes.

The authoritative request and response shapes are generated from the app's OpenAPI document and
summarized in `docs/backend/api-reference.md`.

History pages accept timestamp range (`from`/`to`), risk tier, model version, and analysis ID
filters. Prioritization requires exactly one Top-K count or percentage budget and can filter by
minimum 0–100 risk score and tier; percentage selection uses the Mission 03 ceiling convention.
Every direct prediction response includes a UTC timestamp. CSV uploads accept the documented CSV
media types and UTF-8 comma-delimited files only.

## Labels and UI semantics

Show `fraud_probability` as a model estimate; `risk_score` is its 0–100 display mapping. Show the
frozen threshold decision and validation-derived risk tier separately. Isolation Forest score and
training-reference percentile are separate, higher-means-more-anomalous signals. Linear/SHAP
contributions explain raw logistic log-odds. They are not additive to the later calibrated
probability. V1–V28 are anonymized PCA coordinates and have no asserted business meaning. A model
flag, anomaly, explanation, or analyst outcome does not itself establish ground truth.

## Data and limitations

API history stores derived scores, not feature values. Investigation notes/reasons are local user
text and the SQLite database is not encrypted at rest. There is no authentication, analyst
identity, multi-user conflict handling, frontend export endpoint, alert delivery, model update, or
monitoring. The API is for a trusted single-user local workflow only. The final-test period is
consumed; frontend work must not evaluate or tune the model using those observations.
