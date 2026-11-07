# Mission 06 browser and workflow results

**Run date:** 2026-11-07

**Browser:** Playwright Chromium 158.0.8127.18

**Target:** local production frontend on `127.0.0.1:3100`, API on `127.0.0.1:8001`, isolated synthetic SQLite and upload paths.

## Final browser suite

The final Playwright suite completed with **14 passed, 0 failed** in 52.8 seconds. It contained 13
workflow and responsive/accessibility checks plus one axe scan test. The UI was exercised against
the real local API and frozen, checksum-verified artifacts using synthetic feature vectors and CSV
rows. It did not evaluate the ULB dataset or reopen Mission 02's final-test partition.

Coverage included:

- Dashboard and API health/readiness presentation.
- Single and bounded batch prediction, including invalid-input behavior.
- Local raw-log-odds explanation and separate anomaly score semantics.
- Global validation-time explanation presentation.
- Synthetic feature-only CSV upload, result summary, and paginated rows.
- History filters, pagination, and localized count formatting.
- Risk prioritization, investigation status and annotation semantics, and model/system status.
- Offline/recovery states and mobile navigation.
- Skip-link keyboard focus and activation.

## Responsive and accessibility runs

- Nine primary routes at 1440, 1024, 768, and 390 CSS-pixel widths: **36 route/viewport
  combinations**, no document-level horizontal overflow.
- Axe-core 4.14.0 on nine routes at 1440 and 390 CSS pixels: **18 scans**, zero reported violations
  for the configured WCAG 2.1 A/AA and best-practice rules.
- The skip link received keyboard focus, activated, and transferred focus to the focusable main
  landmark.
- A separate smoke of the production demo launcher and UI completed with **1 passed**.

## Related checks

- Vitest: **5 files, 16 tests passed**.
- TypeScript, ESLint, and optimized production build: passed; Next.js generated 11 dynamic routes.
- Python regression suite: **81 passed, 4 expected skips, 1 deprecation warning**. Safe verified-
  artifact integration separately reported **1 passed, 84 deselected, 1 warning**.

The screenshots in `docs/assets/screenshots/` are authentic local captures using explicitly synthetic
records. Automated browser results are not a manual screen-reader review or WCAG conformance
certification. The aggregate notebook validator and broad real-data marker were not re-run because
they include access to Mission 02's consumed final-test outputs; see the [final audit](final-audit.md).
