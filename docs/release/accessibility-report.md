# Mission 06 accessibility report

**Review date:** 2026-11-07
**Scope:** automated browser scans, keyboard skip-link check, responsive layout, and measured text-color pairs.

## Automated results

- Axe-core 4.14.0 checked nine primary routes at 1440×960 and 390×844 CSS pixels: **18 route/viewport
  scans, zero reported violations** for the configured WCAG 2.1 A/AA and best-practice tags.
- The expanded responsive browser test checked the same nine routes at widths 1440, 1024, 768, and
  390: **36 combinations, no document-level horizontal overflow**.
- Keyboard automation verified the skip link receives initial focus, activates, and moves focus to
  the main landmark. The main landmark is programmatically focusable.
- SHAP charts retain equivalent data tables; decision labels use text in addition to color; the
  application supports reduced-motion preferences.

## Contrast measurements

WCAG relative-luminance contrast was calculated from the final foreground/background hex values.
These pairs exceed the 4.5:1 normal-text AA threshold:

| UI text | Foreground | Background | Contrast |
|---|---|---|---:|
| Sidebar section labels and footer | `#91a1b5` | `#0a101a` | 7.23:1 |
| Page breadcrumb | `#91a1b5` | `#080d16` | 7.38:1 |
| Input placeholders and field hints | `#8494a9` | `#0c1420` | 5.97:1 |
| Secondary table metadata | `#8494a9` | `#111a28` | 5.65:1 |

The low-contrast metadata and placeholder colors found during visual review were lightened before
the final production build and browser run.

## Limits

Automated axe results are not a WCAG conformance certificate. No manual screen-reader session,
speech-input test, or external assistive-technology review was performed. Color measurements cover
the listed pairs; they are not an exhaustive proof for every dynamic state, monitor, or user theme.
Manual keyboard and screen-reader review remains appropriate before any broader release.
