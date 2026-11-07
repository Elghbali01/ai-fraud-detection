# Mission 04 security boundaries

## Local trust boundary

- Bind to `127.0.0.1` by default. Settings reject non-loopback IPs/hostnames and wildcard CORS.
- CORS defaults to explicit localhost/127.0.0.1 development origins. This is a browser policy,
  not authentication or authorization.
- This single-user local service has no authentication, user identity attribution, TLS, or
  production network boundary. It must not be exposed to a LAN or public network.
- `/docs` and `/openapi.json` are available locally and describe the implemented routes.

## Input and resource controls

- JSON bodies default to 2 MiB; multipart CSV bytes default to 32 MiB and are counted from actual
  ASGI chunks as they arrive, with a separate upload-stream count.
- CSVs require the ordered 30-column feature schema, are limited to 20,000 data rows, and are
  parsed in a strict streaming reader. Duplicate/extra headers, `Class`, malformed quoting,
  missing/non-numeric/non-finite values, blank records, and over-limit files are rejected.
- Prediction batches default to 1,000; explanation batches default to 25; active CSV analyses
  default to one. Pagination is bounded to 100 records per page.
- Input filenames and file paths are not used for storage. UUID names are generated server-side;
  uploads resolve only beneath `data/uploads`.
- Model paths, joblib bytes, and artifact manifests are never accepted from HTTP callers.

## Data handling and response behavior

- SQLite stores model outputs and aggregates, not raw feature vectors or uploaded filenames.
- Local uploads use a 24-hour default retention window. Analysis rows are chunked; aggregate
  summaries do not contain labels or label-derived metrics for user CSVs.
- Request IDs are returned on handled responses. Request bodies, credentials, local paths, and
  stack traces are not included in public error responses or routine logs. Error payloads include
  a stable code, safe message, request ID, UTC timestamp, and sanitized validation locations.
- Manual investigation notes/reasons can contain sensitive text; SQLite is not encrypted and
  access relies on the local operating-system account.

These controls reduce accidental exposure in the intended local workflow. They do not make the
service suitable for multi-user or production deployment without a separate security design.
