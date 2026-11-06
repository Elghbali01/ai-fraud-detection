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
- GitHub delivery: validated changes are ready for the authorized normal commits and push; no force push or history rewrite is planned.
