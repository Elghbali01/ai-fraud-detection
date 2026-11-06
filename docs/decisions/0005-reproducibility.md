# ADR 0005 — Reproducible analysis outputs

- Status: accepted.
- Decision: keep deterministic fixture seeds, explicit time-bin parameters, schema versioning, JSON-compatible reports, and bounded class-stratified chart sampling.
- Reason: repeatable outputs help compare changes and limit figure memory/time use.
- Consequence: source retrieval metadata includes a UTC timestamp and is expected to vary; analytical summaries do not include local absolute paths.
