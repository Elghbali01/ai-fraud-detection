# Mission 05 frontend architecture

## Runtime boundary

The analyst application lives in `frontend/` and uses the Next.js App Router, React, and strict
TypeScript. Route modules remain small and delegate interactive work to page components in
`frontend/components/pages/`. The shared shell in `frontend/components/shell.tsx` owns navigation
and the top-level health/readiness indicators. Shared API contracts, validation, formatting, and
request hooks live in `frontend/lib/`.

The browser calls the local FastAPI service at
`http://127.0.0.1:8000/api/v1` by default. `NEXT_PUBLIC_FRAUD_API_URL` can select another local
base URL at build/start time. Requests use `cache: "no-store"`; read hooks abort stale requests on
route or filter changes and expose explicit loading, error, and refresh states. The UI does not
provide a mock transport or a fallback data store.

This client boundary is deliberate: the API is an unauthenticated, loopback-only single-user
service, and Mission 04 CORS allows the documented local frontend origins. CORS is not
authentication. Do not expose either service to a network or deploy the current browser client as
a shared multi-user application.

## Route map

| Route | Workflow |
| --- | --- |
| `/` | Bounded overview of persisted prediction history, recent risk tiers, and analyses |
| `/predict` | Single and batch prediction; optional local explanation |
| `/csv` | Feature-only upload, validation, synchronous analysis, recent analysis list |
| `/analyses/[analysisId]` | Summary, tier/anomaly distributions, paginated derived results, confirmed deletion |
| `/transactions` | Filtered/paginated history, derived record detail, linked investigation creation |
| `/risk` | Persisted risk policy, one-record scoring, budgeted alert prioritization |
| `/explainability` | Validation-time global SHAP baseline and local linear/SHAP request |
| `/anomalies` | Separate bounded Isolation Forest score and training-reference percentile |
| `/investigations` | List, create, detail, allowed status/outcome updates, append-only notes/events |
| `/system` | Health, readiness, model metadata, and server-advertised capabilities |

## Data and component boundaries

- `lib/api.ts` is the single HTTP entry point. It preserves sanitized API messages, HTTP status,
  stable error codes, and request IDs. Network failures become explicit offline errors.
- `lib/use-api.ts` is a small read-resource hook. It does not poll or cache results; pages request
  bounded API pages and offer a refresh action where it is useful.
- `lib/features.ts` mirrors the authoritative feature names and rejects missing, extra, boolean,
  string, and non-finite values before submitting. Backend validation remains authoritative.
- `components/ui.tsx` provides shared cards, labels, risk badges, empty/loading/error states,
  callouts, and forms. Icons are local inline SVGs; there is no remote icon/font runtime dependency.
- `components/charts.tsx` renders compact HTML/SVG/CSS bars from returned API values. It does not
  generate fabricated chart rows or fetch unbounded history.

The only persistent application data is handled by the backend. The browser does not store
transaction features, credentials, investigation text, or API responses in a custom local database.

## State and failure behavior

Each page requests its own data from explicit API paths. Mutations display their response or a
sanitized failure; they do not update analytics with invented values. Empty responses render a
guided empty state. Unavailable API data remains unavailable in the UI and can be retried. Direct
predictions and investigations are persisted by the API; prioritization and local explanations
are computed from the submitted feature vector and are not persisted as history records.

## Deferred architecture work

Mission 06 should evaluate authentication and multi-user authorization before remote deployment,
review API request/response versioning and retry policy, audit bounded server aggregation, and
measure production bundle and rendering costs with a representative workstation. No service worker,
remote analytics, or client-side result cache is installed.
