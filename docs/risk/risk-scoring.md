# Risk scoring

The supervised output `fraud_probability` is the frozen Mission 02 training-fold sigmoid
calibration applied to raw logistic probability. `risk_score` is exactly `100 *
fraud_probability`; it is a display transformation, not another model. The decision status uses
the persisted threshold `0.1835921396957453`.

These fields must remain distinct:

- calibrated fraud probability: probability estimate under the stored mapping;
- display score: probability multiplied by 100;
- predicted class: thresholded decision status for review;
- risk tier: validation-derived analyst triage category;
- anomaly score and percentile: separate Isolation Forest unusualness signal;
- explanation: raw logistic log-odds attribution.

No field proves fraud or automatically blocks a transaction. Probability calibration and ranking
utility are not guaranteed under prevalence or behavior change.

## API-ready use

`RiskScoringService.score_batch()` validates the 30-feature schema, reuses `ModelBundle`, checks
the tier-policy threshold at construction, and enforces a 10,000-row default batch bound.
`RiskIntelligenceService` adds optional anomaly scores and bounded explanations. The
`mission03-intelligence-v1` contract carries model/schema versions and clear field semantics.
