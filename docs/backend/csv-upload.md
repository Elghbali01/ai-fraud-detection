# Feature-only CSV uploads and analyses

`POST /api/v1/uploads/csv` accepts one multipart field named `file` with media type `text/csv`,
`application/csv`, or `application/vnd.ms-excel`. The parser expects UTF-8 (optional BOM) and comma
delimiter. The original client filename
is ignored. The server streams bytes to a generated UUID `.csv` under ignored `data/uploads/`,
computes SHA-256 while writing, and then reads the file with Python's strict CSV parser.

The header must exactly match the 30 names and order in
`fraud_detection.schema.FEATURE_COLUMNS`: `Time`, `V1`–`V28`, `Amount`. `Class` is rejected. Each
row must have exactly 30 parseable finite numeric values. Empty CSVs, duplicate headers, wrong
order, extras, blank rows, missing cells, invalid numbers, malformed quotes, and over-limit data
are rejected; failed files are deleted. Default limits are 32 MiB and 20,000 rows.

The response contains a UUID upload identifier, byte size, row count, SHA-256, and schema version.
It does not expose the filesystem path or client filename. Create a bounded synchronous job with
`POST /api/v1/analyses` and `{"upload_id":"..."}`. The job saves pending/running/completed/failed
state, streams the file again in 256-row chunks, and persists derived prediction outputs only.
`GET /analyses/{id}/results` paginates those outputs; `GET /summary` returns aggregate scores and
counts, flagged percentage, creation timestamp, and model version. No raw row values or label-based
precision/recall are stored.

Analysis endpoints return `429` when the process-local concurrency limit is occupied. The upload
file expires after 24 hours by default, and deleting the last analysis for an upload removes both
the file and upload metadata. The retention interval can be changed with
`FRAUD_API_UPLOAD_RETENTION_HOURS`.

Run one API process. If it stops before a synchronous analysis finishes, startup marks its
pending/running job failed with `analysis_interrupted_by_restart`; it does not resume computation.
