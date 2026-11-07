# Project Progress

## Mission 01 status at close (historical)

Mission 01 was complete against the source-verified ULB CSV. Its validation and GitHub delivery succeeded; the raw dataset is excluded from Git. No Mission 02 model had been trained at that time. Mission 02 is recorded separately below.

## Mission 02 status

The Mission 02 ML engine, scientific reports, validation, artifact verification, and GitHub delivery are complete. The engine, test, and scientific-results commits are pushed to origin/main. Fresh post-push fetch verification found local HEAD and origin/main matched, with zero commits ahead or behind and a clean working tree. Mission 03 has not started.

### Data and evaluation protocol

- Recomputed SHA-256 for data/raw/creditcard.csv: 76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89; size 150,828,752 bytes. This matches the verified Mission 01 provenance record.
- Split manifest: reports/ml/split_manifest.json; manifest ID 3547d288e55133319d9ab6c50b2f3224322b942c6a35e9ef257dbaaaedd22330.
- Chronological grouped-time partitions: train 199,364 rows / 384 fraud through Time 132,928; validation 42,722 / 56 fraud from 132,929–151,328; test 42,721 / 52 fraud from 151,329–172,792. No rows were excluded; equal Time values stay together.
- Duplicate audit: 773 exact duplicate groups / 1,854 rows / 1,081 copies beyond the first; zero conflicting labels and zero exact feature-vector or full-row duplicate signatures across partitions. No rows were removed.
- Three expanding training-only folds contained 52, 111, and 28 fraud cases in their validation windows. The final test partition was held until model selection, calibration method, and threshold were frozen.

### Model results

- Eight candidates across DummyClassifier, Logistic Regression, Random Forest, and HistGradientBoosting were compared on the same three training-only temporal folds. Class weighting was compared with unweighted candidates; no resampling was used.
- Balanced HistGradientBoosting had maximum mean CV Average Precision 0.75238 (SD 0.13229). The one-standard-error rule floor was 0.67601. The simpler balanced Logistic Regression, C=1, was selected with mean AP 0.73880 (SD 0.08916); final training fit took 1.04 seconds.
- A sigmoid probability mapping was fitted to training-only out-of-fold scores. On validation, raw vs calibrated Brier score was 0.019587 vs 0.000373, and log loss was 0.087627 vs 0.002241. Isotonic calibration was not fit due to the small positive sample.
- The maximum-F2 threshold selected on validation was 0.18359214. Validation precision was 0.84615, recall 0.78571, and alert count 52/42,722.
- Final test: Average Precision 0.73727; trapezoidal PR area 0.74608; ROC-AUC 0.97724; precision 0.90476; recall 0.73077; F1 0.80851; F2 0.76000; Brier 0.000450; log loss 0.002851; TN 42,665, FP 4, FN 14, TP 38. Wilson 95% recall interval was 0.5975–0.8323.
- Isolation Forest fit on 198,980 known Class 0 training rows; higher negative score_samples means more anomalous and is not a fraud probability. Validation AP/ROC-AUC was 0.02883/0.94776; final test AP/ROC-AUC was 0.03845/0.94518. Final-test fraud captures at top 0.1%, 0.5%, and 1% were 0, 13, and 25.

### Artifacts and inference

- Supervised joblib artifact SHA-256: 87f0e2f492fbed062e38b366a2d98e2a98a655f7e1c81657cd6986c1874fa088.
- Isolation Forest artifact SHA-256: e5c071d8e39a013f1ebacac600109633b15bc97fc43f64d085662399b5dc6d60.
- Both manifests were verified against local files and loaded with the isolated scikit-learn 1.9.1 environment. A three-row CSV smoke test verified deterministic single-batch repeat output, valid probabilities, the persisted threshold, and separate non-probability anomaly scores.
- The raw CSV, .venv, .venv-isolated, secrets patterns, and data/models artifacts are ignored by Git.

### Validation

- Full isolated check command: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-checks.ps1 -PythonPath .venv-isolated\Scripts\python.exe — passed.
- Routine pytest: 54 passed, 2 skipped in 13.48 seconds. Skips were the two opt-in local real-data integrations; they were run separately.
- Ruff lint: passed. Ruff format: 86 files already formatted. Python compile checks passed. Synthetic EDA smoke passed.
- Notebook validator executed all nine notebooks in clean kernels: the four Mission 01 notebooks and five Mission 02 notebooks.
- Opt-in command with RUN_REAL_DATA_TESTS=1: python -m pytest -m real_data -q — 2 passed, 54 deselected in 32.25 seconds. Environment variable was removed afterward.
- The first full validation attempt exposed Ruff import-order and line-length violations in Mission 02 notebook cells. Those cells were corrected; the complete validation was rerun and passed.

### Evaluation audit caveat

The first full real-data workflow discovered that the Isolation Forest artifact had not been persisted. Persistence was corrected and the workflow was run again so both artifacts could be verified. The frozen final-test partition was therefore scored twice in deterministic runs. The registry retains both experiment records; their final-test metrics are identical. No model, calibration, or threshold choice changed based on test metrics. Treat the test period as consumed; a genuinely independent evaluation requires later data.

See docs/ml/ and reports/ml/ for the implementation protocol, complete model comparison, calibration and threshold reports, anomaly analysis, final metrics, plots, manifest, and append-only experiment registry.

### GitHub delivery

- 02bd7a3 feat(ml): add reproducible modeling and inference engine.
- 44b8036 test(ml): add scientific validation coverage.
- ad56b46 docs(ml): publish experiments and mission 03 handoff.
- Push destination: origin/main. The push was non-forced; the remote was fetched and confirmed to have no remote-only commits first.
- Post-push fetch confirmed local HEAD and origin/main matched, zero commits ahead/behind, and a clean working tree. A follow-up documentation commit records this final delivery status.

## Real-data validation

- Source: Kaggle dataset mlg-ulb/creditcardfraud, retrieved through the authorized Kaggle CLI on 2026-11-06.
- File: data/raw/creditcard.csv, 150,828,752 bytes; SHA-256 76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89.
- Observed shape: 284,807 rows × 31 numeric columns; ordered schema Time, V1–V28, Amount, Class.
- Observed target: Class 0 = 284,315; Class 1 = 492; fraud share 0.172749%; majority/minority ratio 577.876:1.
- Quality: no missing or infinite values, no invalid labels, 1,081 extra exact duplicate copies, and 1,854 rows in duplicate groups. No raw records were removed.
- EDA, CSV tables, JSON summaries, and figures were generated into reports/ from the real CSV. See reports/EDA_REPORT.md and docs/data/eda-findings.md.
- All four tracked notebooks were executed on the real CSV with clean kernels.
- A marked, opt-in real-data integration test was added. Routine tests and CI remain independent of the local raw file.

## Engineering corrections

- The downloader now finds kaggle.exe next to the active project Python when the virtual environment is not activated, and disables interactive credential prompts.
- The EDA report includes verified source metadata, duplicate-group counts, class-conditional numeric summaries, correlation pairs, IQR diagnostics, and explicitly provisional chronological split counts.
- The class-count figure uses a labeled log scale and count/percentage annotations. Time-bin charts flag bins with fewer than 30 fraud cases.
- Notebook validation creates a temporary kernel spec targeting the active Python interpreter.
- The locked setup now includes wheel, which the existing no-build-isolation editable-install step requires on a fully isolated environment.
- The Windows check script accepts an explicit PythonPath so it can validate a genuinely isolated environment without replacing the existing .venv.

## Environment and resources

Python 3.11.8 was used. The existing .venv includes system-site packages, so it is not fully isolated. A separate ignored .venv-isolated was created from requirements-mission01.lock and the project installed editable there successfully after the lock and build-system metadata were corrected. The raw CSV and environments remain excluded from Git.

Node v20.19.6 was available but is not used by Mission 01. Kaggle CLI 2.2.5 was installed only for acquisition in the existing .venv; it is not a project dependency. After the isolated environment and validation runs, C: had 7,088,881,664 bytes free; .venv-isolated occupied 468,101,938 bytes and the raw CSV occupied 150,828,752 bytes.

## Final validation record

- Full isolated validation: .\scripts\run-checks.ps1 -PythonPath '.venv-isolated\Scripts\python.exe' — passed.
- Routine pytest in that run: 34 passed, 1 skipped. The real-data test is opt-in and was skipped because RUN_REAL_DATA_TESTS was unset; the skip is not counted as a pass.
- Ruff lint and format checks — passed; Ruff reported 50 files already formatted.
- Python compileall validation — passed.
- Notebook validation — all four notebooks executed sequentially using the active isolated Python kernel and the source-verified local CSV.
- Synthetic EDA smoke check — passed on the explicitly labeled 200-row fixture, written under ignored reports/demo.
- Opt-in real-data check: RUN_REAL_DATA_TESTS=1 .\.venv-isolated\Scripts\python.exe -m pytest -m real_data -q — 1 passed, 34 deselected. It verified the current file hash, exact schema, types, counts, quality checks, duplicate count, and EDA report generation.
- The raw dataset checksum was independently recomputed during final inspection and matched the provenance sidecar. The dataset and both virtual environments are ignored by Git.
- The fresh pre-commit fetch found origin/main at b5944298ea5bde211b83e84abbc735f564b55242, matching local HEAD; there were no remote-only commits.
- Four logical completion commits were created:
  - 4fc2a75 fix(data): harden downloader and isolated validation setup
  - 57d1d4a feat(eda): publish source-verified ULB analysis
  - 5dd0afa test: add opt-in real ULB integration coverage
  - 4e831fd docs: finalize real-data mission 01 handoff
- A normal non-forced push advanced origin/main from b5944298 to 4e831fd6. A fresh post-push fetch confirmed local HEAD and origin/main matched at 4e831fd6dd5b5cd38d2947dbbcaf418e7927c413, with 0 commits ahead, 0 behind, and a clean working tree. This final status update records that verified delivery.

## Historical record: initial audit before real acquisition

The previous audit found no local CSV or configured Kaggle CLI and recorded that the real-data work was blocked. The issue was resolved in this completion run; those earlier conclusions were accurate at the time and are retained here as history.

The prior Mission 01 implementation was pushed to origin/main through commit b5944298ea5bde211b83e84abbc735f564b55242. The earlier deterministic fixture validation and previous GitHub delivery were not evidence of real-data validation.

The preceding audit used Python 3.11.8 and Node 20.19.6, found a clean main branch at the time, and recorded varying C: free-space measurements. Kaggle CLI and local Kaggle credentials were absent in that first audit; the downloader exited before a network request. A later authorized fetch and push completed the previous implementation. No old raw-data or scientific findings were claimed.

Previous pushed commits, retained for history:

- 039d62a chore: establish mission 01 project foundation
- 9791dfc feat(data): implement dataset validation and profiling
- c71531a feat(eda): implement reproducible fraud analysis
- 57ce707 test: add data quality and analytics coverage
- a07c1f6 docs: finalize mission 01 documentation
- 20be8db docs: record mission 01 delivery status
- b301caa docs: confirm synchronized mission 01 delivery
- 7b2b1e8 docs: clarify verified blockers and dependencies
- f33ae6d docs: update final resource and delivery audit
- b594429 docs: record latest resource audit

The earlier fixture-only validation recorded 32 passing tests and successful Ruff, compile, notebook, and synthetic EDA checks. Those results did not verify the real ULB dataset. Earlier push verification found local and remote at b594429 with a clean tree before this completion work began.

## Generated artifacts

- Four notebooks under notebooks/.
- Real-data report at reports/EDA_REPORT.md.
- Six figures under reports/figures/.
- CSV summaries under reports/tables/, including full numeric profiles and class-conditional summaries.
- JSON outputs under reports/summaries/, including eda_status.json and eda_summary.json.
- Source provenance sidecar and raw CSV under ignored data/raw/.

## Mission 02 readiness

Historical Mission 01 handoff, superseded by the Mission 02 evaluation and final-test audit above: the recommended evaluation approach and model tracks are in docs/engineering/mission-02-handoff.md. It includes DummyClassifier, LogisticRegression, RandomForest, and HistGradientBoosting as supervised baselines, plus a separate IsolationForest track. At that point, the recommendation was to preserve the final test period and choose thresholds on validation; the later final-test consumption caveat is recorded above. No model training or selection occurred in Mission 01.

## Mission 03 status — implementation and validation complete

Mission 03 reuses the frozen Mission 02 classifier, calibration mapping, anomaly detector, feature schema, and threshold. It reads the manifest-defined training and validation CSV prefix only. The consumed final-test rows and labels are not parsed or scored.

### Data, artifacts, and environment

- Recomputed `data/raw/creditcard.csv` SHA-256: `76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89`; this matches Mission 01 provenance and the split/artifact manifests.
- Training/validation rows parsed: 199,364 / 42,722. Mission 03 final-test rows and labels loaded: 0 / 0.
- Selected classifier SHA-256: `87f0e2f492fbed062e38b366a2d98e2a98a655f7e1c81657cd6986c1874fa088`. Isolation Forest SHA-256: `e5c071d8e39a013f1ebacac600109633b15bc97fc43f64d085662399b5dc6d60`. Both local manifests were verified after report generation.
- Python 3.11.8; NumPy 2.3.5; pandas 3.0.5; SciPy 1.16.3; scikit-learn 1.9.1; SHAP 0.51.0; joblib 1.6.0. `pip check` reported no broken requirements.
- The existing preflight observed approximately 5.2 GB free disk and 5.54 GiB available RAM. SHAP used a bounded 512-row training background, a 5,000-row training stability sample, and a 5,000-row validation beeswarm sample; full validation summaries were computed for 42,722 rows.

### Explanation and risk results

- The exact StandardScaler/logistic attributions reconstructed all validation raw decision scores; maximum absolute error was `2.84e-14`. The sigmoid of raw decision scores matched raw estimator probabilities with maximum error `0.0`. Calibrated probabilities remain a separate training-fold sigmoid mapping and are not described as additive SHAP/linear outputs.
- SHAP 0.51.0 used the deterministic uniform training-only natural-prevalence background (512 rows, seed 17), transformed model feature space, and raw-log-odds output. Additivity passed on all 42,722 validation rows with maximum absolute error `3.20e-14` and mean absolute error `4.24e-16`.
- Leading validation mean-absolute SHAP features were V4, Amount, V1, V14, V6, V2, V12, V22, Time, and V10. These are model attributions; V1–V28 remain anonymized PCA coordinates and no causal interpretation is claimed.
- The frozen threshold remains `0.1835921396957453`. Validation-only operational tier cutpoints were Low `< 0.0006841357`, Elevated `[0.0006841357, 0.1835921397)`, High `[0.1835921397, 0.9082513380)`, and Critical `>= 0.9082513380`. The 42,722 validation rows included 52 threshold flags; no decision-positive row is labeled Low.
- Validation TopK capture was 10/10 at K=10, 43/50 at K=50, and 48/100 at K=100. Percentage-budget K uses ceiling: 0.1%=43 rows (40 fraud labels captured), 0.5%=214 (51), and 1%=428 (51). These are retrospective validation diagnostics, not future utility claims.
- The anomaly reference contains 198,980 known-legitimate training scores (p50 `0.386069`, p95 `0.476849`, p99 `0.574136`). Validation supervised/anomaly Spearman correlation was `0.07542`; at 0.1% review budget the top-K sets overlapped in 2 rows (Jaccard `0.02381`). Scores remain separate; no blended fraud score is defined.

### Deliverables and validation

- Reports: `reports/explainability/GLOBAL_EXPLAINABILITY.md`, `LOCAL_EXPLANATIONS.md`, `global_shap_feature_summary.csv`, `selected_local_explanations.json`, `shap_additivity_validation.json`, and versioned results under `reports/risk/`.
- Figures: global SHAP importance, validation beeswarm, coefficient/SHAP comparison, exact linear local contributions, SHAP local waterfall, risk distribution, risk-tier diagnostics, alert capacity, supervised/anomaly quadrants, and TopK overlap.
- Notebooks 10–14 were created from the reusable modules and all 14 project notebooks executed in clean kernels.
- Full isolated check command: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-checks.ps1 -PythonPath '.venv-isolated\Scripts\python.exe'` — passed. It reported 63 passed and 3 expected opt-in real-data skips; Ruff, formatting (134 Python/notebook files), compileall, notebook execution, and synthetic EDA smoke all passed.
- Opt-in Mission 03 integration command with `RUN_MISSION03_REAL_DATA=1`: `python -m pytest -m mission03_real_data -q` — 1 passed, 65 deselected. It verified checksums, full development split sizes, exact reconstruction, SHAP additivity, anomaly-reference provenance, and zero final-test rows in Mission 03 results.
- Synthetic CLI smoke exercised bounded scoring with explanations and anomaly output plus percentage prioritization. Artifact verification and `pip check` passed. Raw data, `.venv`, `.venv-isolated`, model binaries, and derived anomaly reference are ignored by Git.
- Known limits remain: anonymized PCA variables, a short historical sample and few fraud labels, calibration/distribution shift, consumed final test, no new independent future cohort, and no validated business cost or production utility.
- GitHub delivery: implementation commit `aab197b512aa7b71d102f0815a15230ee6311142` and report/documentation commit `f7ac3d386344bc5b5627103e6a7be6c1d534f57f` were pushed to `origin/main` by normal fast-forward from Mission 02 commit `d330df1`; no force push or history rewrite was used. A fresh post-push fetch at this checkpoint found local `HEAD` and `origin/main` both at `f7ac3d386344bc5b5627103e6a7be6c1d534f57f`, zero commits ahead/behind, and a clean working tree. This delivery status is being recorded in the follow-up progress commit.

## Mission 04 status — implementation and validation complete

Mission 04 adds a local FastAPI service over the unchanged Mission 02 classifier and Mission 03
explainability, risk, anomaly, and prioritization services. It does not retrain, recalibrate, read
the ULB CSV at API startup, or use the consumed final-test partition for API examples or smoke
requests.

### Data and trusted artifacts

- Rechecked `data/raw/creditcard.csv`: SHA-256
  `76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89`, matching the acquisition
  record. Git ignore rules exclude the raw file, model binaries, SQLite runtime files, upload files,
  `.env`, `.venv`, and `.venv-isolated`.
- Verified the supervised model SHA-256
  `87f0e2f492fbed062e38b366a2d98e2a98a655f7e1c81657cd6986c1874fa088`, Isolation Forest SHA-256
  `e5c071d8e39a013f1ebacac600109633b15bc97fc43f64d085662399b5dc6d60`, and training-only SHAP
  background SHA-256 `b9ea884dda7cb73312c935aa21cff6dcb551763eb8dbf119077622d037c36b3d`. Artifact
  verification also checked the dataset/split provenance and all 30 global SHAP summary rows.
- Preserved the persisted decision threshold `0.1835921396957453`, calibration mapping, and risk
  policy. The API derives predictions from the actual frozen artifacts.

### Backend, persistence, and security

- Added typed local configuration with `.env.example`, a loopback-only launch script, explicit local
  CORS allowlist, request IDs, bounded JSON/CSV/batch/explanation/pagination/concurrency settings,
  and consistent sanitized errors. OpenAPI now has concrete health, readiness, prediction, batch,
  upload, analysis, and validation-error response schemas.
- Implemented the prediction, batch, explanation, risk, M03 prioritization, anomaly, upload,
  analysis, history, and investigation routes. Prioritization supports Top-K and ceiling-rounded
  percentage budgets, minimum risk score, tier filters, and stable tie ordering. History supports
  timestamp, tier, model-version, and analysis filters with stable ordering.
- CSV input is streamed under a byte cap, UTF-8 (optional BOM) and comma delimiter, exact ordered
  feature columns, strict finite values, bounded rows, and explicit supported media types. CSV
  analyses persist only derived outputs and aggregates. Uploads expire after 24 hours by default.
- Added SQLite/Alembic migrations, derived-only prediction history, investigations, notes, and
  workflow events. Startup verifies the Alembic head; interrupted synchronous jobs are marked failed
  with `analysis_interrupted_by_restart`, not resumed. The migration transaction fix was covered by
  a repeatability test.
- Local smoke and API tests use synthetic vectors only. The real ULB dataset, model binaries, API
  background sample, and SQLite database are not included in Git. There is no authentication,
  analyst identity, encryption-at-rest, or production deployment claim.

### Final validation evidence (2026-11-07)

- `scripts/run-checks.ps1 -PythonPath '.venv-isolated\Scripts\python.exe'`: **78 passed, 4
  expected opt-in skips**, 1 Starlette TestClient deprecation warning. Ruff passed, 168 files were
  already formatted, Python compile checks passed, all 14 notebooks executed, and the 200-row
  synthetic EDA smoke wrote under `reports/demo/` only. The four skipped tests are opt-in artifact
  or real-data integrations; Mission 04's artifact integration was run separately below.
- `scripts/run-api-checks.ps1 -PythonPath '.venv-isolated\Scripts\python.exe'`: **15 passed, 1
  expected opt-in skip**, Ruff passed, 48 files formatted. The skip is the separately executed
  trusted-artifact integration test.
- With `RUN_MISSION04_ARTIFACT_TESTS=1`,
  `python -m pytest -m mission04_real_artifacts -q`: **1 passed, 81 deselected**. It loaded actual
  verified Mission 02/03 artifacts but sent only synthetic zero-valued API vectors; SHAP
  reconstruction and training-background provenance passed.
- `scripts/smoke-api.ps1 -PythonPath '.venv-isolated\Scripts\python.exe'`: **30 endpoint operations
  passed over real HTTPX requests to a running local Uvicorn server**. Coverage included health,
  readiness, OpenAPI, metadata, prediction, batch, local/global explanation, risk, prioritization,
  anomaly, CSV upload, analysis/summary/results, history, investigation create/update/note/detail,
  and safe error responses. In the final smoke run, ten synthetic single predictions measured
  49.569 ms median and 71.459 ms p95 in an isolated final smoke run; these are local smoke timings,
  not a throughput benchmark.
- `scripts/verify-api-artifacts.ps1` and `pip check` passed. `scripts/init-db.ps1` was exercised by
  the live smoke with a temporary SQLite database and both migrations. PowerShell scripts parsed
  successfully.
- The four reports remain source-based ULB results: `reports/EDA_REPORT.md`,
  `docs/data/data-quality-report.md`, `docs/data/eda-findings.md`, and the Mission 02/03 handoffs.
  The first four notebooks load the verified ULB CSV through `load_notebook_frame()`; notebooks
  05–14 consume the persisted Mission 02/03 artifacts. The full notebook runner executed all 14.

### Remaining limitations and delivery

- This remains an unauthenticated, single-user loopback development API. Do not bind it to a LAN or
  public interface. SQLite is not encrypted, investigation text is user-entered, jobs are
  synchronous/process-local, and the API has no alert delivery, authentication, monitoring, or
  deployment hardening.
- Model scientific limits remain unchanged: anonymized PCA inputs, a short historical dataset,
  distribution shift risk, no independent later cohort, and a consumed final-test period. At this
  Mission 04 checkpoint, Mission 05 implementation had not started; its completion is recorded below.
- Delivery review confirmed there were no unrelated staged changes, credential patterns, raw data,
  model binaries, runtime databases, uploads, or virtual environments in Git. Ignore rules were
  checked for all of those local-only files. The pre-push fetch found `origin/main` at the Mission 03
  baseline `526e3ee250906870f359ce9e2c9de53f8e862d78`; the local Mission 04 commits were a clean
  fast-forward from that commit.
- Mission 04 implementation commit `367fdb22c946891f90eb61b0d928a59898731b43` and documentation
  commit `22cad85d508887b12f1484fe128bb4531faa909e` were pushed to `origin/main` without force or
  history rewriting. A post-push fetch verified local `HEAD` and `origin/main` both at
  `22cad85d508887b12f1484fe128bb4531faa909e`, zero commits ahead/behind, and a clean working tree.

## Mission 05 status — implementation and validation complete

Mission 05 adds the responsive Next.js analyst command center in `frontend/`. It consumes the
existing local Mission 04 API with typed request/response contracts and no production mock-data
fallback. It covers overview, guided single prediction, bounded/filterable batch prediction, CSV
upload and paginated analysis, transaction history, risk policy and prioritization, global/local
explainability, separate anomaly scoring, investigation workflows, and model/system status. Local
explanations display the full 30-feature raw-log-odds waterfall; both attribution charts provide
screen-reader data tables. The CSV workflow accepts file picker and drag-and-drop and downloads an
exact header-only feature template.

### Validation evidence (2026-11-07)

- `scripts/run-checks.ps1 -PythonPath '.venv-isolated\Scripts\python.exe'`: **81 passed, 4 expected
  opt-in skips, 1 Starlette TestClient deprecation warning**. Ruff, formatting, compile checks, and
  the synthetic 200-row EDA smoke passed; all 14 notebooks executed. The first four notebooks used
  the verified ULB CSV and notebooks 05–14 used the persisted Mission 02/03 artifacts.
- With `RUN_REAL_DATA_TESTS=1`, `python -m pytest -m real_data -q`: **2 passed, 1 separately gated
  Mission 03 skip, 82 deselected, 1 warning**. The checksum and real-data integration were verified;
  no model was retrained and the consumed final-test partition was not evaluated.
- Frontend quality checks: TypeScript, ESLint, production build, and **5 Vitest files / 16
  tests passed**. Next.js generated 11 app routes.
- `scripts/smoke-frontend.ps1 -PythonPath '.venv-isolated\Scripts\python.exe' -ApiPort 8001
  -FrontendPort 3100`: health and readiness passed, frontend HTTP 200, and **8 Playwright tests
  passed** (7 real-API workflows and one axe-core suite). Axe checked nine routes at 1440 px and
  390 px for WCAG 2.1 A/AA and best-practice violations; none were reported.
- Visual QA exercised nine routes at 1440, 1024, 768, and 390 px (**36 route/viewport
  combinations**); all rendered without horizontal overflow or browser page errors. Key desktop
  and mobile workflow states were reviewed in Playwright screenshots.
- The ULB CSV remains local: 150,828,752 bytes, SHA-256
  `76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89`. Reports contain source
  results for all 284,807 rows and 492 fraud labels. The raw file, model artifacts, database, and
  virtual environments are excluded from Git.
- The end-to-end checks used throwaway SQLite/upload paths and loopback ports 8001/3100 because a
  separate user application occupied port 3000. Mission 04's existing default database and that
  separate application were not changed.

### Corrections and remaining limitations

- Added fresh/legacy SQLite initialization handling, aligned Alembic settings access with the
  installed configuration interface, and added regression tests for database initialization.
- Added typed guided feature validation, batch sort/filter controls, CSV drag/drop and template
  download, complete local log-odds waterfalls, and equivalent accessible chart data tables.
- The service remains unauthenticated and loopback-only; it is not approved for LAN or production
  use. Keyboard-only/screen-reader review and target-environment contrast review remain manual.
  Bundle-size, latency, memory, and throughput benchmarks were not run. The data is historical,
  anonymized, and lacks merchant/customer/device context; Mission 02's final-test period is
  consumed. Mission 06 has not started.

### GitHub delivery

- Implementation commit `e95d597467b3e86eeb1f8fa6a317789ba7084848` and documentation closeout
  commit `0280849fe182f0cdc2eac82789268dd1382afab2` were pushed normally to `origin/main` from
  base `b429ca723a6aa22356bf5e38102d24c30cd78c02`; no force push or history rewrite was used.
- A fresh post-push fetch verified local `main` and `origin/main` both at
  `0280849fe182f0cdc2eac82789268dd1382afab2`, zero commits ahead/behind, and a clean working tree.

## Mission 06 status — local portfolio release complete

Mission 06 completed the delivery hardening and portfolio closeout on 2026-11-07. The result is
intended for a local synthetic-data demonstration only. It does not authorize production, LAN, or
cloud deployment. Existing Mission 01–05 outputs were preserved; no model was retrained, no threshold
or risk policy was retuned, and no new Mission 02 final-test evaluation was performed.

### Validation evidence

- Verified `data/raw/creditcard.csv`: **150,828,752 bytes**, SHA-256
  `76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89`; it remains ignored and
  untracked. The local source retains 284,807 rows, 492 positive labels, no missing or infinite
  values, and 1,081 duplicate copies beyond first.
- Isolated Python suite: **81 passed, 4 expected opt-in skips, 1 deprecation warning**. Ruff check,
  Ruff format check (179 files already formatted), compile check, and `pip check` passed. Safe
  Mission 04 artifact integration: **1 passed, 84 deselected, 1 warning**; requests used synthetic
  inputs with the verified local artifacts. Model and API artifact verifiers passed.
- Python advisory scan checked **111 installed packages and found zero known vulnerabilities** after
  the active lock/build constraints were updated for Pillow, Tornado, and setuptools. Full npm audit
  retained **10 moderate development-only minimatch advisories** and no high/critical findings;
  `npm audit --omit=dev` found **zero production dependency vulnerabilities**.
- Frontend TypeScript and ESLint passed; Vitest reported **5 files / 16 tests passed**; the
  optimized Next.js production build passed with 11 dynamic routes.
- Final Playwright run: **14 passed in 52.8 seconds**. Nine main routes at four widths produced 36
  combinations with no horizontal overflow. Axe checked nine routes at desktop and mobile widths
  (18 scans) with zero configured WCAG 2.1 A/AA or best-practice violations. The skip-link keyboard
  check and separate local-demo browser smoke (**1 passed**) succeeded.
- Generated local performance observations are recorded in `docs/release/performance-report.md`;
  they are not a concurrent-load or production benchmark. The demo database was preserved when the
  verified stop helper shut down its recorded processes.

The full `scripts/run-checks.ps1` wrapper and broad opt-in `real_data` marker were not re-run in this
closeout because their complete paths include historical notebook/ML flows that access Mission 02's
consumed final-test results. Safe underlying checks were run separately. The four notebooks' prior
Mission 01 executions against the verified ULB CSV are preserved in earlier audit records; this
closeout does not claim new notebook execution.

### Closeout changes and remaining limits

Mission 06 added nonce-based CSP and response headers, responsive overflow/contrast fixes, clearer
investigation outcome semantics, a guarded production-bundle demo start/stop pair, synthetic-only
portfolio screenshots, and release/security/accessibility/performance/browser documentation. The
Python lock now uses patched Pillow 13.0.0, Tornado 6.6, and setuptools 84.1.0. The npm development
advisory remains documented because the available full-tree suggested fix downgrades the Next.js
ESLint companion package across the current Next 16 toolchain.

The API has no authentication or authorization; SQLite is not encrypted at rest. Manual screen-reader
review, speech input, independent future-period evaluation, production deployment, concurrent-load
testing, peak-memory measurement, and business-impact validation remain unperformed. See
`docs/release/final-audit.md`, `docs/release/security-review.md`,
`docs/release/accessibility-report.md`, `docs/release/performance-report.md`, and
`docs/release/release-checklist.md`.

### Mission 06 GitHub delivery

Implementation commit `6ca7cdfdb9e76bcbe2f1ed985b09bb1456834ddb`
(`feat(mission-06): harden local dashboard and demo launcher`) was created from the fetched
Mission 05 baseline. The scientific and portfolio documentation closeout is committed separately
after it. Both commits were pushed normally to `origin/main` without a force push or history rewrite.
A fresh post-push fetch verified local `main` and `origin/main` at the final release commit, zero
commits ahead or behind, and a clean working tree. The final release commit hash is in the delivery
summary.
