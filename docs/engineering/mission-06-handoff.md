# Mission 06 handoff — local analyst frontend

## Mission 05 scope

Mission 05 adds a Next.js App Router/React/strict-TypeScript local analyst application in
`frontend/`. It consumes the Mission 04 loopback API directly and includes overview, prediction,
CSV analysis, analysis results/history, transaction history, risk scoring/prioritization,
global/local explainability, separate anomaly scoring, investigation workflow, and system/model
status.

## Architecture and data boundary

The API client uses the real OpenAPI contract, no-store reads, bounded pages, explicit safe errors,
and no mock fallback. Feature values are validated against the exact Mission 04 schema and are not
persisted by frontend code. The backend persists direct scores and CSV-derived outputs; submitted
features are not retained in history. CSV analyses are synchronous and are paginated in the UI.

## Validation record

Final Mission 05 validation ran on 2026-11-07:

- `scripts/run-checks.ps1 -PythonPath '.venv-isolated\Scripts\python.exe'`: **81 passed, 4
  expected opt-in skips, 1 Starlette TestClient deprecation warning**. Ruff passed, 263 files were
  formatted, compile checks passed, all 14 notebooks executed, and the 200-row synthetic EDA smoke
  wrote only under ignored `reports/demo/`.
- With `RUN_REAL_DATA_TESTS=1`, `python -m pytest -m real_data -q`: **2 passed, 1 separately gated
  Mission 03 skip, 82 deselected, 1 warning**. The test verified the local ULB dataset and reports;
  it did not retrain a model or evaluate the consumed final-test partition.
- Frontend quality sequence: TypeScript, ESLint, Vitest reported **5 files and 16 tests passed**;
  optimized Next.js production build passed and generated 11 app routes.
- `scripts/smoke-frontend.ps1 -PythonPath '.venv-isolated\Scripts\python.exe' -ApiPort 8001
  -FrontendPort 3100`: health `alive`, readiness `ready`, frontend HTTP 200, and **8 Playwright
  tests passed** (7 real-API workflows plus one axe-core accessibility scan). The scan checked nine
  primary routes at 1440 px and 390 px against WCAG 2.1 A/AA and best-practice tags; no violations
  were reported.
- Browser: Playwright Chromium **158.0.8127.18**, installed in temporary project-local tooling.
  Visual QA checked nine routes at 1440, 1024, 768, and 390 px (36 route/viewport combinations).
  Every page had matching document and viewport widths and no browser page errors. Desktop/mobile
  screenshots included overview, prediction, CSV upload/results, transaction history, risk,
  explainability, anomaly review, investigations, and system status; analysis-detail, case-detail,
  prediction-result, local explanation, and prioritized-review states were also reviewed.
- Full-stack tests used throwaway Mission 05 SQLite/upload paths on API port 8001 and frontend port
  3100 because the user's other application occupied port 3000. The existing Mission 04 database
  and the separate application on port 3000 were not changed.

## Security gaps

- The API has no authentication or authorization; both services must remain local-only.
- CORS is not authentication and must not be treated as an access-control boundary.
- SQLite is not encrypted at rest. Investigation notes/reasons are local analyst text.
- There is no CSRF/session policy, multi-user identity, conflict resolution, centralized audit
  service, alert delivery, deployment secret management, or production monitoring.
- Browser test records are synthetic and can remain in the local SQLite database because the API
  has no investigation-delete route. They are named as test records and are not created at startup.

## Accessibility gaps

The app has semantic regions, labels, keyboard-focus styles, visible decision words, explicit
errors, and reduced-motion support. The automated axe-core scan reported zero violations for the
tested WCAG 2.1 A/AA and best-practice rules. Global SHAP and local attribution charts include
equivalent screen-reader tables. This does not replace manual keyboard and screen-reader checks;
focus order and assistive-technology behavior should be checked in the target environment.

## Performance and browser behavior

The frontend uses a small custom HTML/CSS chart layer instead of a charting framework, limits
history/result pages, and has no polling or broad client-side cache. The production build generated
11 routes. No bundle-size, route-latency, memory, or throughput benchmark was run. Large analysis
summaries may still need backend aggregation review before scaling.

## Scientific limitations

- The ULB dataset is historical and does not provide merchant, customer, location, or device
  identity. V1–V28 are anonymized PCA coordinates.
- The Mission 02 final-test partition is consumed. The UI does not rerun or reframe its metrics as
  live production analytics.
- Fraud probability, 0–100 display score, frozen threshold decision, operational tier, anomaly
  signal, explanation, and analyst outcome are presented separately.
- Linear and SHAP attribution values are raw log-odds; they are not calibrated-probability
  contributions and do not imply causality.
- No real-world fraud-cost validation or future-period performance claim is made.

## Deployment constraints

No cloud deployment is authorized for this mission. Before a network deployment, design and test
authentication, per-user authorization, request throttling, CSRF policy, server-side input/file
retention, encrypted storage, audit/log handling, secret management, observability, and an external
security review. Keep model artifacts immutable and never expose raw local paths or manifests.

## Recommended hardening priorities

1. Extend accessibility review with keyboard-only workflows, screen-reader review, and contrast checks in the target environment.
2. Add a vetted authentication/authorization layer before multi-user use and define case ownership.
3. Add safe investigation deletion/retention policy and explicit cleanup of synthetic smoke data.
4. Add API request timeouts, bounded concurrency feedback, cancellation guidance, and offline retry
   policy.
5. Measure production bundle/chunk sizes, large-history render cost, and 20,000-row CSV behavior.
6. Add monitored, later-period evaluation on a new labeled dataset; do not reopen the consumed test.
7. Review data licensing before sharing the dataset or user-uploaded content.

## Portfolio demonstration workflow

Run the API and frontend on loopback; use one explicit synthetic vector to show single prediction,
local explanation, and separate anomaly interpretation. Upload a clearly labeled synthetic CSV,
inspect the summary/results, then delete the analysis. Demonstrate global SHAP as a validation-time
baseline, and create a named synthetic investigation only if prepared to leave a local test case.
Avoid screenshots containing private local data or presenting synthetic results as production.

At the time this Mission 05 handoff was originally recorded, Mission 06 had not started. Its final closeout is appended below.

## Mission 06 closeout — local portfolio release

Mission 06 completed as a local portfolio demonstration, not a production release. The final audit,
security review, accessibility report, performance observations, browser results, release checklist,
architecture diagrams, showcase, and demo walkthrough are linked from the repository README.

- Final backend state: 81 passed, 4 expected opt-in skips, and one Starlette `TestClient` deprecation
  warning; the safe Mission 04 artifact integration separately passed (1 passed, 84 deselected).
- Python quality checks, artifact verifiers, package consistency, and the post-update advisory scan
  passed. The scanner found zero known Python package vulnerabilities among 111 installed packages.
- Frontend TypeScript, ESLint, Vitest (16 tests), and the optimized production build passed.
- Final Playwright suite: 14 passed; nine main routes had no horizontal overflow at four viewport
  widths; 18 axe scans reported zero configured violations. The guarded local demo start/stop smoke
  passed separately.
- Updated Python dependencies address the observed Pillow, Tornado, and setuptools advisories. npm
  still reports 10 moderate development-only `minimatch` advisories; the production dependency audit
  reported zero. See `../release/security-review.md`.
- Mission 06 did not rerun the broad notebook/check wrapper or `real_data` marker because those paths
  include access to consumed Mission 02 final-test outputs. It made no new performance evaluation,
  retraining, or threshold change.
- Demo startup uses the existing production build on loopback ports 8001/3100. The stop helper checks
  executable, PID, and process start time and preserves `data/backend/mission06-demo.sqlite3` and
  uploaded files. The unrelated user-owned development server on port 3000 was left running.

The Mission 01 source dataset remains local and ignored. Its verified SHA-256 is
`76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89`; the closeout did not rerun
notebooks that consume historical final-test outputs. Mission 02's final-test period remains
consumed. Authentication, encryption at rest, manual screen-reader validation, network deployment,
concurrent-load testing, and independent future-period evaluation remain outside this local release.

### Mission 06 Git delivery

The implementation commit is `6ca7cdfdb9e76bcbe2f1ed985b09bb1456834ddb`
(`feat(mission-06): harden local dashboard and demo launcher`). The final documentation closeout is
committed after it and pushed to `origin/main` without force or history rewriting. A fresh fetch
verifies local `main` and `origin/main` at the final release commit, no ahead/behind commits, and a
clean working tree. The final release commit hash is provided in the delivery summary.
