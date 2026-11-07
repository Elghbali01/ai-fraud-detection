# Mission 05 FastAPI integration

The authoritative contract is the local Mission 04 OpenAPI document and `docs/backend/api-reference.md`.
The frontend base defaults to `http://127.0.0.1:8000/api/v1`; configure
`NEXT_PUBLIC_FRAUD_API_URL` only for another trusted local URL. All requests use `no-store` and
the frontend does not silently substitute mocks.

## Routes used by the interface

| API route | Frontend use |
| --- | --- |
| `GET /health`, `GET /ready` | Topbar connection/model state and system page |
| `GET /models/current`, `GET /models/capabilities` | Frozen metadata, upload and batch limits |
| `POST /predictions` | Single transaction prediction; persisted to history |
| `POST /predictions/batch` | Bounded batch prediction; explanations disabled by default |
| `GET /history`, `GET /history/{record_id}` | Overview, filters, pagination, and derived record details |
| `GET /risk/policy`, `POST /risk/score`, `POST /risk/prioritize` | Persisted tier policy, one score, and bounded budget ranking |
| `POST /explanations/local`, `GET /explanations/global` | Local raw-log-odds explanation and validation-time summary |
| `POST /anomalies/score` | Separate Isolation Forest score and reference percentile |
| `POST /uploads/csv`, `POST /analyses` | Feature-only upload, validation, and synchronous analysis |
| `GET /analyses`, `GET /analyses/{id}`, `GET /analyses/{id}/summary` | Analysis history, durable state, and aggregate summary |
| `GET /analyses/{id}/results`, `DELETE /analyses/{id}` | Paginated derived rows and confirmed analysis deletion |
| `GET /investigations`, `POST /investigations` | Case list and create |
| `GET /investigations/{id}`, `PATCH /investigations/{id}` | Case details and allowed workflow updates |
| `POST /investigations/{id}/notes` | Append-only analyst note |

## Request schemas

Prediction, local explanation, risk scoring, batch, prioritization, and anomaly inputs use exactly
`Time`, `V1` through `V28`, and `Amount`. `Class`, extra/missing fields, booleans, strings, NaN,
and infinity are rejected. The local explanation body wraps the vector in `features`; batch,
priority, and anomaly bodies use `transactions`. A feature-only CSV requires the exact 30 columns,
UTF-8 (optional BOM), and comma delimiter. The frontend validates JSON shape before sending, but
the backend remains the authority.

## Response semantics

- `fraud_probability` is the persisted sigmoid-mapped model estimate; `risk_score` is its 0–100
  display mapping; `predicted_class` reflects the frozen threshold; `risk_tier` comes from the
  validation-derived operational policy.
- Linear and interventional SHAP contributions are raw logistic log-odds. They are not additive to
  the later calibrated probability and do not express causality.
- Isolation Forest anomaly score is a separate signal. Higher is more anomalous relative to the
  training reference. It is not a fraud probability and is not blended into prioritization.
- Investigation outcomes are explicitly analyst-recorded, not ground truth.
- Unlabeled CSV analyses return review-score summaries; they do not calculate precision or recall.

## Pagination and bounds

The overview requests at most 100 history rows, and labels page-derived counts as recent. History
uses pages of 25 with backend `total` and supports UTC `from`/`to`, risk tier, model version,
analysis ID, and order filters. Investigation lists use 50-row pages. Analysis results use 50-row
pages and the analysis `requested_rows` as the pagination bound. CSV and batch limits are read from
`GET /models/capabilities` when the API is available. No page downloads unbounded history.

## Errors and CORS

The shared API client preserves the backend's safe `message`, `error` code, HTTP status, and
`request_id`. A failed connection becomes an explicit offline state. Validation failures remain
visible to the user and are not rewritten as successful predictions. The API's explicit local CORS
configuration includes the loopback frontend origins on ports 3000 and 3100; CORS is not authentication.
