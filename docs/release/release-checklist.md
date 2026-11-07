# Mission 06 local release checklist

**Release boundary:** local portfolio demonstration only. This checklist records the completed
closeout and the limits that remain before any broader deployment.

## Completed

- [x] Preserve Mission 01–05 work and the consumed Mission 02 final-test boundary.
- [x] Verify local ULB dataset size and SHA-256; exclude source CSV, model artifacts, uploads,
  runtime databases, and Python virtual environments from Git.
- [x] Validate Python and frontend code, dependencies, API artifacts, frontend build, unit tests,
  browser workflows, responsive widths, accessibility scans, and demo start/stop behavior.
- [x] Keep demo API and frontend bound to loopback; verify the launcher refuses occupied ports and
  the stop helper validates process identity before stopping.
- [x] Capture synthetic-only portfolio screenshots and document architecture, system behavior,
  security, accessibility, local performance observations, and browser results.
- [x] Document dependency audit findings and retain the moderate development-only npm advisory as
  a maintenance item.
- [x] Inspect changed files for credentials and unrelated staged changes; fetch `origin/main`
  before delivery; commit and push without force; verify `main` and `origin/main` match and the
  working tree is clean.

## Explicitly outside this release

- [ ] Authentication, authorization, analyst identity, and multi-user case ownership.
- [ ] Encryption at rest, deployment secret management, production monitoring, or network/cloud
  deployment.
- [ ] Manual screen-reader and speech-input validation or a WCAG conformance claim.
- [ ] Concurrent-load, production hardware, or peak-memory performance benchmarks.
- [ ] Independent evaluation on a later labeled cohort. Mission 02's final-test period is consumed.
- [ ] Any assertion that synthetic/demo outputs are real fraud labels or operational outcomes.

Do not use the local demo with real cardholder data or expose the unauthenticated API beyond the
local machine. See [security review](security-review.md), [accessibility report](accessibility-report.md),
and [performance report](performance-report.md) for details.
