# Mission 04 API reference

Base URL: `http://127.0.0.1:8000/api/v1`. OpenAPI and Swagger UI are available at `/openapi.json`
and `/docs`. Requests that accept transactions require exactly the 30 numeric feature fields in
`fraud_detection.schema.FEATURE_COLUMNS`; `Class`, missing fields, extras, strings, booleans,
NaN, and infinity are rejected. Every handled response carries `X-Request-ID`.

## Routes

| Method | Route | Purpose |
|---|---|---|
| GET | `/health` | Process liveness plus safe model/database/explanation/anomaly component states |
| GET | `/ready` | Verified runtime and migrated database readiness |
| GET | `/models/current` | Model/schema versions, frozen threshold, calibration and anomaly semantics |
| GET | `/models/capabilities` | Input, batch, explanation, and analysis limits |
| POST | `/predictions` | Score one feature mapping; append derived output to history |
| POST | `/predictions/batch` | Score a bounded `transactions` list; optional bounded explanations |
| POST | `/explanations/local` | One exact linear or interventional SHAP explanation |
| GET | `/explanations/global` | Checked-in Mission 03 validation SHAP summary |
| GET | `/risk/policy` | Frozen threshold and validation-derived tier policy |
| POST | `/risk/score` | One scored risk record, also recorded in history |
| POST | `/risk/prioritize` | Mission 03 stable ranking with Top-K or percentage budget, minimum score, and tier filters |
| POST | `/anomalies/score` | Separate Isolation Forest score and training-reference percentile |
| POST | `/uploads/csv` | Stream and validate a feature-only CSV upload |
| POST | `/analyses` | Synchronously score an existing validated `upload_id` |
| GET | `/analyses` | Paginated analysis list |
| GET | `/analyses/{analysis_id}` | Durable state and aggregate summary |
| GET | `/analyses/{analysis_id}/summary` | Aggregate-only analysis summary |
| GET | `/analyses/{analysis_id}/results` | Paginated derived row outputs, without input features |
| DELETE | `/analyses/{analysis_id}` | Delete the analysis and, when unreferenced, its upload |
| GET | `/history` | Paginated history filtered by `from`, `to`, risk tier, model version, or analysis ID |
| GET | `/history/{record_id}` | One derived history record |
| POST | `/investigations` | Create a manual investigation, optionally linked to a prediction |
| GET | `/investigations` | Paginated investigations; optional status filter |
| GET | `/investigations/{investigation_id}` | Investigation, notes, and append-only events |
| PATCH | `/investigations/{investigation_id}` | Update allowed workflow status and analyst-recorded outcome |
| POST | `/investigations/{investigation_id}/notes` | Add an analyst note |

## Prediction example

```json
{
  "Time": 0,
  "V1": 0,
  "V2": 0,
  "V3": 0,
  "V4": 0,
  "V5": 0,
  "V6": 0,
  "V7": 0,
  "V8": 0,
  "V9": 0,
  "V10": 0,
  "V11": 0,
  "V12": 0,
  "V13": 0,
  "V14": 0,
  "V15": 0,
  "V16": 0,
  "V17": 0,
  "V18": 0,
  "V19": 0,
  "V20": 0,
  "V21": 0,
  "V22": 0,
  "V23": 0,
  "V24": 0,
  "V25": 0,
  "V26": 0,
  "V27": 0,
  "V28": 0,
  "Amount": 0
}
```

Responses include the persisted probability calibration status, risk-policy version, and an ISO 8601
UTC `timestamp`. They
distinguish `fraud_probability` (persisted sigmoid-mapped output), `risk_score` (100
times that value), `predicted_class` (frozen Mission 02 threshold), `risk_tier` (operational
validation-derived category), and `anomaly` (separate non-probability Isolation Forest output).
Linear and SHAP explanation contributions use raw model log-odds, not calibrated-probability
additivity. None of these fields proves fraud.

## Batch, error, and pagination behavior

`/predictions/batch` and `/anomalies/score` accept `{"transactions": [{...}]}`. Batch rows default
to a maximum of 1,000; explanations default to a maximum of 25 rows. Pagination defaults to 50
history rows or 100 analysis results, with a hard maximum of 100 per page. Validation errors return
`422` with `error`, a safe `message`, `request_id`, UTC `timestamp`, and generic validation
categories/locations;
feature values are never echoed. Other expected errors return the same core fields with a stable
error code. Unexpected failures are sanitized and do not return tracebacks.

### Alert prioritization

`POST /risk/prioritize` requires exactly one of `top_k` or `budget_percentage`. Optional
`min_risk_score` is on the 0–100 display-score scale and maps to the corresponding probability
cutoff; optional `risk_tiers` selects the persisted policy tiers. Percentage budgets use the
Mission 03 ceiling rule. Ties are ordered by numeric input index, then stable input order. No
anomaly score is blended into the supervised ranking.

### History filters

`GET /history` accepts `from` and `to` ISO 8601 timestamps (UTC assumed when the offset is omitted),
`risk_tier`, `model_version`, `analysis_id`, and `sort_order=asc|desc`. Default ordering is newest
first. `created_at` and record UUID form a stable secondary ordering key.

### CSV media and parsing

Uploads require `text/csv`, `application/csv`, or `application/vnd.ms-excel`; data is decoded as
UTF-8 with an optional BOM and comma delimiter. Unsupported media types return 415. Size is counted
from streamed request chunks, not only the declared `Content-Length`.

Analyses of unlabeled uploaded data do not calculate precision, recall, or other label-based
metrics. Their summary includes score range/mean, flagged count, tier counts, and separate anomaly
category counts, flagged percentage, creation timestamp, and model version. These are predictions
for review, not confirmed fraud counts.

A process restart does not resume synchronous CSV work. Jobs left pending or running are marked
failed during startup with `analysis_interrupted_by_restart`.
