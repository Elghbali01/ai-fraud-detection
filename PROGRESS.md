# Project Progress

## Mission 01 status

The scientific portion of Mission 01 has been completed against the source-verified ULB CSV. Final Git delivery and synchronization verification are recorded below after completion. No Mission 02 model was trained.

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
- Three logical completion commits now exist locally:
  - 4fc2a75 fix(data): harden downloader and isolated validation setup
  - 57d1d4a feat(eda): publish source-verified ULB analysis
  - 5dd0afa test: add opt-in real ULB integration coverage
- Documentation has been updated with the final validation evidence. The docs commit, push, and post-push synchronization check are still pending.

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

The recommended evaluation approach and model tracks are in docs/engineering/mission-02-handoff.md. It includes DummyClassifier, LogisticRegression, RandomForest, and HistGradientBoosting as supervised baselines, plus a separate IsolationForest track. Preserve the final test period for one independent evaluation and choose any threshold on validation data. No model training or selection occurred in Mission 01.
