# Instructions for Future Codex Missions

## Project structure

- Keep reusable Python logic in src/fraud_detection; notebooks and scripts should import it.
- Preserve the src package layout and keep backend/frontend work within their roadmap missions.
- Keep raw data under data/raw and out of Git. Keep generated analytical outputs small and reproducible.
- Record architectural changes as concise ADRs under docs/decisions.

## Coding and quality

- Use Python 3.11, type hints for public APIs, concise docstrings, focused functions, and clear domain exceptions.
- Follow Ruff formatting and lint settings in pyproject.toml.
- Add tests for behavior and edge cases; do not test only file existence.
- Keep scripts Windows-friendly and avoid administrator or machine-wide configuration changes.
- Use structured, useful logs and never include credential values in logs.

## Scientific integrity

- Never fabricate dataset findings, model scores, test results, download results, provenance, or source permissions.
- Label observed data, synthetic fixtures, predictions, risk estimates, anomaly scores, and explanations distinctly.
- Never claim an anomaly or prediction proves fraud.
- Treat V1–V28 as anonymized PCA features; do not invent semantics or physical causes.
- Preserve raw data. Report duplicates, missingness, zeros, and outliers before considering changes.
- Do not fit learned preprocessing on all rows before a train/test split.
- Do not use a future test partition for feature, model, or threshold selection.
- Document hypotheses separately from observed findings and associations separately from causation.

## Dependencies and security

- Declare runtime and development dependencies in pyproject.toml with compatible version constraints.
- Avoid global installs, paid services, large model frameworks, and unnecessary heavy dependencies.
- Never request, print, hardcode, or commit passwords, tokens, Kaggle credentials, or private data.
- Use authorized local credentials only. Do not bypass dataset access controls.
- Do not commit raw datasets, local virtual environments, caches, credentials, or model binaries.

## Git workflow

- Inspect status, branch, remotes, and recent history before changes.
- Preserve unrelated user changes and stage only intended files.
- Never force push, reset unrelated history, or claim remote success without verification.
- Use focused commits with accurate messages.

## Documentation

- Update README.md, TASKS.md, PROGRESS.md, and relevant engineering/data documentation when behavior changes.
- Keep source provenance and access dates for dataset research.
- Record exact checks and results; do not report unexecuted checks as passed.
- Keep Mission 02 handoff and API contracts aligned with tested code.
