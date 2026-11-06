# ADR 0004 — Notebooks call reusable package code

- Status: accepted.
- Decision: notebooks contain analytical questions, presentation, and interpretation; computations live in src/fraud_detection.
- Reason: testing and later API reuse require calculations independent of notebook execution order.
- Consequence: notebooks select their data source explicitly and distinguish a source-verified dataset, an unverified local file, and a synthetic fixture.
