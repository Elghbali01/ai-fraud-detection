# Mission 05 accessibility notes

## Implemented behavior

- Pages use semantic headings, main/navigation landmarks, real links for route changes, native
  buttons for actions, tables for tabular results, field labels, and visible keyboard focus.
- The application provides a skip link, an accessible mobile navigation toggle, and `aria-current`
  on the active route.
- Form validation errors use alert roles. Loading surfaces use status roles. Empty states explain
  why no data appears and offer a next step when possible.
- Risk state includes a tier word and decision text in addition to color. Anomaly and SHAP pages
  state their output-space limitations in text.
- Reduced-motion preferences disable shimmer, breathing, toast, and transition animation.
- Inputs use native controls and limits; no hover-only control is required for navigation or form
  submission.
- Tables are horizontally scrollable at small widths rather than hiding required output columns.

## Automated review and remaining limits

The final automated axe-core run checked WCAG 2.1 A/AA and best-practice rules across nine primary
routes at 1440 px and 390 px and reported zero violations. This is not a conformance certification.
The global SHAP summary and local explanation waterfall expose equivalent screen-reader data
tables. Keyboard-only and screen-reader review remains manual work. The investigation detail
layout, long IDs, and mobile tables need continued assistive-technology testing.

Mission 06 should extend accessibility review with keyboard-only workflows, verify focus order and
dialog behavior with assistive technology, and measure text/graphic contrast in the target
environment. Future charts that convey decision-critical values should include equivalent data
tables.
