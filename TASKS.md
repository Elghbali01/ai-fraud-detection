# Mission Tracker

## Mission 01 — Foundation and EDA

- [x] Audit repository, runtimes, disk, and Git configuration.
- [x] Establish Python package layout, configuration, scripts, and CI workflow.
- [x] Research dataset candidates and record source-reported characteristics.
- [x] Implement acquisition workflow, schema validation, data loading, profiling, analytics, and report generation.
- [x] Create four notebooks with explicit source status and fixture fallback.
- [x] Add controlled unit tests and reproducibility checks.
- [x] Document scientific limitations and Mission 02 interfaces.
- [x] Acquire the real ULB CSV, validate provenance, schema, checksum, and observed class counts.
- [x] Run real-data EDA and execute all four notebooks against the acquired CSV.
- [x] Add opt-in real-data integration coverage without making local data mandatory for unit tests or CI.
- [x] Complete data-quality, findings, and Mission 02 handoff documentation.
- [x] Create logical commits for the acquisition/environment fixes, real-data EDA artifacts, and integration test.
- [x] Push validated commits to origin/main and verify remote synchronization with a fresh fetch.

## Mission 02 — Machine learning engine

- [x] Freeze chronological train/validation/test partitions, timestamp ties, duplicate audits, and expanding-window development folds.
- [x] Implement leakage-safe preprocessing, Dummy/Logistic/Random Forest/HistGradientBoosting candidates, class-weight comparisons, calibration, threshold policies, and a separate Isolation Forest track.
- [x] Evaluate temporal-fold Average Precision, validation calibration and F2 threshold, final-test ranking and confusion metrics, uncertainty intervals, and fixed alert budgets.
- [x] Save versioned local supervised and anomaly artifacts with manifests, checksums, schema and library metadata; keep binaries ignored by Git.
- [x] Add reusable single/batch inference, CLI commands, Windows scripts, synthetic unit tests, and opt-in real-data integration tests.
- [x] Generate Mission 02 reports and five notebooks; execute all nine notebooks using clean kernels.
- [x] Document modeling, splitting, leakage, selection, calibration, anomaly behavior, reproducibility, and Mission 03 handoff.
- [x] Run full isolated validation, opt-in real-data integration, artifact checks, and inference smoke test.
- [x] Review changes, push validated commits to origin/main, and verify a clean synchronized working tree.

The final-test period was scored in two deterministic runs to correct missing Isolation Forest artifact persistence. The repetition did not change model selection or threshold and is disclosed in the leakage audit; future independent evaluation requires new later data.

## Mission 03 — Explainable AI and risk intelligence

- [x] Preserve the frozen Mission 02 classifier, calibration mapping, threshold, and consumed-test boundary.
- [x] Implement exact StandardScaler + LogisticRegression raw-log-odds contributions and numerical reconstruction checks.
- [x] Implement deterministic training-only SHAP background, global/local raw-log-odds explanations, and additivity checks.
- [x] Generate global importance, coefficient comparison, beeswarm, local waterfall, and validation risk/anomaly figures.
- [x] Implement neutral explanation narratives and versioned bounded single/batch intelligence services.
- [x] Implement probability display score, validation-only risk tiers, stable TopK/percentage ranking, and capacity diagnostics.
- [x] Reuse Isolation Forest with a known-legitimate training reference; keep anomaly percentile separate from fraud probability.
- [x] Implement validation-only supervised/anomaly correlation, overlap, Jaccard, capture, and quadrant diagnostics.
- [x] Generate machine-readable reports, risk policies, and notebooks 10–14 from the verified development partitions.
- [x] Add synthetic tests and an opt-in real-artifact integration test that does not load final-test rows.
- [x] Document explainability semantics, risk policy, anomaly meaning, limitations, and Mission 04 interfaces.
- [x] Run full isolated validation, execute all 14 notebooks, and verify opt-in Mission 03 real-data integration.
- [x] Review, commit, and push validated Mission 03 changes; verify origin/main synchronization.

## Mission 04 — FastAPI backend

- [x] Add FastAPI, Pydantic, SQLAlchemy, Alembic, multipart, Uvicorn, and HTTPX dependencies and a resolved Python 3.11 lock.
- [x] Load and cross-check only manifest-pinned Mission 02/03 model, risk, anomaly, training-background, and global-summary artifacts.
- [x] Implement strict prediction, batch, explanation, risk, prioritization, anomaly, health, readiness, model, and capability routes.
- [x] Implement true chunk-counted upload limits, exact feature-only CSV validation, bounded synchronous analyses, aggregate summaries, and deletion/retention.
- [x] Add SQLite tables and explicit Alembic upgrade, derived-only history, and analyst investigation/notes/events.
- [x] Add local-only binding, explicit CORS, request IDs, sanitized errors, body/batch/concurrency/page limits, and privacy/security documentation.
- [x] Add synthetic API behavior tests and an opt-in verified-artifact test that sends synthetic inputs only.
- [x] Run the complete isolated project checks and Mission 04 live HTTPX smoke against a real local server.
- [x] Document API, database, CSV, investigation, security, local startup, tests, and Mission 05 integration.
- [x] Review files/secrets/ignore rules; create logical commits, push normally to origin/main, then verify clean synchronization.

## Mission 05 — Next.js frontend

- [x] Audit the Mission 04 OpenAPI schema and preserve its request, response, pagination, and scientific semantics.
- [x] Build a responsive design system, application shell, navigation, health indicators, reusable states, and reduced-motion behavior.
- [x] Implement API-backed overview, single/batch prediction, CSV upload/analysis/results, transaction history, risk prioritization, explainability, anomaly review, investigations, and model/system status.
- [x] Add typed feature validation, explicit offline/error states, bounded result pages, and no production mock fallback.
- [x] Add Vitest coverage and Playwright API/browser workflows, including WCAG 2.1 A/AA axe scans.
- [x] Run isolated backend regression, real-data integration, frontend quality/build, full-stack smoke, browser E2E, visual viewport, and automated accessibility checks.
- [x] Document frontend architecture, design, API integration, workflows, local setup, test results, limitations, and Mission 06 handoff.
- [x] Review Git contents and ignore rules, create logical commits, push to `origin/main`, and verify clean synchronization.

## Mission 06 — Delivery hardening

- [x] Audit repository state, dataset checksum, tracked-file boundaries, and preserve the consumed Mission 02 final-test boundary.
- [x] Harden local production CSP/security headers, investigation outcome language, and visual contrast/layout.
- [x] Run safe isolated backend checks, verified-artifact integration, frontend type/lint/unit/build checks, full browser workflows, accessibility scans, and the local demo smoke.
- [x] Record dependency audits, local performance observations, accessibility results, screenshots, architecture, showcase, demo walkthrough, and release checklist.
- [x] Add guarded loopback demo start/stop scripts; verify the demo database persists and only task-owned processes are stopped.
- [x] Review Git contents and ignore rules, commit the validated release, push normally to `origin/main`, and verify clean synchronization.

The aggregate notebook/check wrapper and broad `real_data` marker were intentionally not re-run in this closeout because they include paths that reopen consumed Mission 02 final-test results. Safe underlying checks were run individually. See `docs/release/final-audit.md` for exact results and limitations.

## Post-release — one-click Windows launcher

- [x] Add root-level `START_AI_FRAUD.bat` and `STOP_AI_FRAUD.bat` using process-scoped Windows PowerShell execution-policy bypass.
- [x] Make the existing demo scripts Windows PowerShell 5.1-compatible and start FastAPI to readiness before starting Next.js to HTTP readiness.
- [x] Add preflight checks, duplicate-session reuse, ignored timestamped logs, safe PID/executable/start-time shutdown, and no-install/no-retrain behavior.
- [x] Verify CMD invocation, Windows PowerShell 5.1, a complete PowerShell 7 startup and stop, duplicate reuse, repeated stop, foreign-port preservation, backend/frontend startup failure handling, logs, and SQLite/model preservation.
- [x] Document the one-click workflow, requirements, ports, and common errors in README and the post-release launcher audit.

The successful CMD test was not an Explorer double-click. PowerShell 7 completed a separate full startup and safe stop. Windows invoked the default URL handler after endpoint checks, but a visible browser page was not independently verified in this session. See `docs/engineering/post-release-launcher.md`.
