# Mission 06 final audit

**Status:** local portfolio release validated on 2026-11-07. This is not a production deployment.

## Scope and preservation

The final audit continued the existing Mission 01–05 implementation on `main` from
`e1b1bc71aa249d00a270277eca40874d7268c921`. Existing scientific outputs and ignored user data were
preserved. No model was retrained, no threshold or risk policy was retuned, and no consumed final-test
row was opened for new scoring. The final Git delivery is recorded in
[`PROGRESS.md`](../../PROGRESS.md).

## Scientific integrity

- `data/raw/creditcard.csv`: **150,828,752 bytes**, SHA-256
  `76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89`; excluded from Git.
- The verified source contains 284,807 rows, 492 positive labels (0.172749%), no missing or infinite
  values, and 1,081 exact duplicate copies beyond first. `Time` is elapsed seconds, and V1–V28 are
  anonymized PCA-derived coordinates.
- Supervised artifact SHA-256:
  `87f0e2f492fbed062e38b366a2d98e2a98a655f7e1c81657cd6986c1874fa088`.
- Isolation Forest artifact SHA-256:
  `e5c071d8e39a013f1ebacac600109633b15bc97fc43f64d085662399b5dc6d60`.
- SHAP background SHA-256:
  `b9ea884dda7cb73312c935aa21cff6dcb551763eb8dbf119077622d037c36b3d`.
- Model artifact checks verified the exact feature order `Time,V1..V28,Amount`, the frozen threshold
  `0.1835921396957453`, model version
  `mission02:m02-20261106T185430319319Z-logistic_balanced_c1-3547d288`, and split manifest ID
  `3547d288e55133319d9ab6c50b2f3224322b942c6a35e9ef257dbaaaedd22330`.
- Risk tiers use the persisted `risk-tier-policy-v1` validation-derived policy. SHAP values remain
  raw-log-odds contributions; Isolation Forest scores remain a separate non-probability signal.
- Mission 02's reported final-test metrics are historical only. That partition was scored in two
  recorded completion runs to repair missing artifact persistence. No new evaluation was run in
  Mission 06; future independent evaluation requires later labeled data.

## Source reports and notebooks

The four requested reports were inspected against the verified ULB source. The Mission 02 handoff
now has an appended source-data closeout that distinguishes observed Mission 01 results from its
original pre-model evaluation plan.

- [`reports/EDA_REPORT.md`](../../reports/EDA_REPORT.md)
- [`docs/data/data-quality-report.md`](../data/data-quality-report.md)
- [`docs/data/eda-findings.md`](../data/eda-findings.md)
- [`docs/engineering/mission-02-handoff.md`](../engineering/mission-02-handoff.md)

Historical Mission 01 records state that all four EDA notebooks were executed on the hash-verified
ULB CSV. The Mission 05 record states that all 14 notebooks were executed, with notebooks 01–04
using the ULB CSV and notebooks 05–14 reading persisted Mission 02/03 outputs. Mission 06 did not
re-execute the notebook runner: it executes the full historical notebook set, including a notebook
that presents consumed final-test results. The on-disk notebooks do not persist cell outputs. This
audit does not claim fresh notebook execution.

## Validation evidence

### Backend and scientific artifacts

- `.venv-isolated\Scripts\python.exe -m pytest -q`: **81 passed, 4 skipped, 1 warning**.
- `RUN_MISSION04_ARTIFACT_TESTS=1 .venv-isolated\Scripts\python.exe -m pytest -m mission04_real_artifacts -q`:
  **1 passed, 84 deselected, 1 warning**. It loaded verified artifacts and sent synthetic inputs.
- Ruff check: passed. Ruff format check: **179 files already formatted**. Python compile check:
  passed. `pip check`: no broken requirements.
- `verify-model-artifacts.ps1` and `verify-api-artifacts.ps1`: passed.
- `pip-audit` after the dependency refresh: **111 installed packages checked, 0 known
  vulnerabilities**.

The four normal-suite skips are opt-in tests for Mission 04 artifact integration, Mission 03 real
data, Mission 02 model/data integration, and the Mission 01 real-data integration. The safe Mission
04 artifact integration ran separately. The broader `RUN_REAL_DATA_TESTS=1` marker and aggregate
`scripts/run-checks.ps1` wrapper were not run: they include model/final-period or historical notebook
execution paths that would cross the Mission 02 freeze boundary. The safe underlying checks were
run individually. No synthetic EDA smoke was needed for this closeout.

### Frontend and browser

- TypeScript: passed. ESLint: passed. Vitest: **5 files, 16 tests passed**.
- Optimized Next.js production build: passed; 11 dynamic application routes generated.
- Final Playwright suite on local production frontend/API: **14 passed in 52.8 seconds**, Chromium
  `158.0.8127.18`, zero failures.
- Nine primary routes were checked at 1440, 1024, 768, and 390 CSS-pixel widths (**36
  route/viewport combinations**) with no document overflow.
- Axe checked nine routes at desktop 1440 and mobile 390 (**18 route/viewport scans**) with zero
  reported WCAG 2.1 A/AA or best-practice violations. A keyboard test verified that the skip link
  focuses the main landmark.
- A separate browser smoke of the repeatable demo startup passed **1 test**.

### Runtime and persistence

Synthetic API/UI scenarios covered prediction, invalid input, bounded batch, CSV validation and
analysis, deletion, risk ranking, separate anomaly output, SHAP semantics, history pagination and
filtering, case status and notes, offline/recovery behavior, and mobile navigation. Investigation
status and notes were verified after an API process restart against the isolated synthetic SQLite
database. The dedicated demo database migrated to Alembic revision `0002_prediction_semantics` and
was preserved by the verified stop script.

## Visual and portfolio artifacts

Ten authentic local browser screenshots are in `docs/assets/screenshots/`. They use explicitly
synthetic feature vectors, contain no ground-truth labels, and show no real customer data. Visual
inspection fixed a card overflow at desktop width and clarified investigation outcome/ground-truth
copy. The local-only production CSP also adds a nonce, `strict-dynamic`, loopback-only API connect
source, and standard response headers; inline styles remain allowed for the current UI design.

## Dependency audit result

The active Python lock was refreshed to patched Pillow, Tornado, and setuptools versions. The
post-update Python advisory scan is clean. `npm audit` reported **10 moderate development-only
findings**, all through `minimatch` 10.2.6; `npm audit --omit=dev` reported **0 vulnerabilities** in
the 20 production dependencies. npm's available full-tree remediation would downgrade the
Next.js ESLint companion configuration to 15.5.29 while Next.js remains 16.4.5, so the toolchain was
not downgraded. The finding is recorded as a remaining development-tooling limitation in the
[security review](security-review.md).

## Remaining limits

This release is intended for local portfolio demonstration only. The API has no authentication or
authorization, SQLite is not encrypted at rest, and CORS is not an access-control boundary. No
manual screen-reader session, independent future-period model evaluation, production deployment,
business-impact measurement, or concurrent-load benchmark is claimed. See the dedicated
[security](security-review.md), [accessibility](accessibility-report.md), and
[performance](performance-report.md) reports.

## Git delivery

The implementation and demo-hardening commit is
`6ca7cdfdb9e76bcbe2f1ed985b09bb1456834ddb`
(`feat(mission-06): harden local dashboard and demo launcher`). The scientific, release, and
portfolio closeout is committed separately after it. Both commits are pushed normally to
`origin/main`; no force push or history rewrite is used. A fresh post-push fetch verifies local
`main` and `origin/main` at the final release commit, zero commits ahead or behind, and a clean
working tree. The final release commit hash is reported in the delivery summary.
