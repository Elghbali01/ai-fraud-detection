# ADR 0003 — Dataset storage and provenance

- Status: accepted.
- Decision: store downloaded raw CSVs under data/raw, exclude them from Git, and write a checksum plus provenance JSON beside a validated download.
- Reason: raw inputs may be large and have separate access terms; reproducibility requires identifying the exact local file.
- Consequence: analyses must fail clearly when data is unavailable. Do not silently replace the source or mutate raw rows.
