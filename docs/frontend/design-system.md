# Mission 05 design system

## Product direction

The application is a dark local analyst console: restrained navy surfaces, thin slate borders,
cool cyan action accents, violet explainability accents, and distinct success, warning, and danger
states. Typography uses local system sans-serif and monospace stacks so the interface makes no
third-party font request. Icons are small inline SVGs. Animation is limited to loading shimmer,
status breathing, transitions, and toast entrance; `prefers-reduced-motion` disables the motion.

## Tokens

Tokens are declared in `frontend/app/globals.css` and reused across the shell and pages:

| Role | Token | Value |
| --- | --- | --- |
| Page background | `--bg` | `#080d16` |
| Raised background | `--bg-raised` | `#0d1420` |
| Surface | `--surface` | `#111a28` |
| Elevated surface | `--surface-raised` | `#162234` |
| Border | `--border` | `#223146` |
| Primary text | `--text` | `#eef4fb` |
| Secondary text | `--text-soft` | `#b1bfd0` |
| Muted text | `--muted` | `#78899e` |
| Primary accent | `--accent` | `#5ed8e8` |
| Analytical accent | `--violet` | `#a99bff` |
| Success | `--success` | `#66d8a1` |
| Warning | `--warning` | `#f1bf73` |
| Danger | `--danger` | `#ff7787` |
| Radius | `--radius-*` | 8 / 12 / 18 px |
| Motion | `--motion` | 180 ms eased transition |

Risk tiers use separate colors for Low, Elevated, High, and Critical, and all tier displays also
show a text label. Labels and status words remain visible in tables and result cards.

## Layout and responsive behavior

The desktop sidebar is fixed at 252 px and the main column is fluid. The top bar is sticky and
shows actual API and model readiness. The content area is capped at 1,550 px and uses reusable
two-, three-, and four-column grids. At 1,160 px, metric grids reduce columns; at 850 px the
sidebar becomes a mobile drawer; at 620 px cards and forms reflow for narrow screens. Tables scroll
horizontally instead of hiding columns.

## Chart conventions

Charts are deliberately compact, label-first summaries. Tier bars use counts from a bounded API
page or a server summary. Global SHAP bars show mean absolute raw log-odds magnitude; local bars
show signed raw log-odds contributions around a zero marker. Anomaly scores and percentiles use a
separate table and are not drawn on probability scales.

## Component styling

Buttons, badges, cards, metric cards, callouts, loading skeletons, error states, empty states,
pagination, tables, and form controls share common classes. New pages should use these primitives
and CSS variables rather than introducing a page-specific color palette or a heavy UI framework.
