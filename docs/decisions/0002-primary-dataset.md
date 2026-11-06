# ADR 0002 — Primary dataset candidate

- Status: accepted and locally verified on 2026-11-06.
- Decision: select the ULB Credit Card Fraud Detection dataset as the Mission 01 candidate.
- Reason: compact numeric schema, a publisher-documented binary label, and explicit feature/time limitations are suitable for a local first iteration.
- Verification: the source-identified Kaggle CSV passed ulb-credit-card-v1 validation and matched the observed 284,807-row, 31-column schema and 284,315/492 class counts. The local SHA-256 and retrieval metadata are recorded in the ignored data/raw/dataset-provenance.json sidecar.
- Consequence: the ULB file is the Mission 01 EDA source. Keep IEEE-CIS and PaySim as comparison candidates, not substitutes. The raw CSV remains excluded from Git.
