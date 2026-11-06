# Risk-tier policy

`risk-tier-policy-v1` defines descriptive Low, Elevated, High, and Critical categories using
validation probabilities only. Validation labels do not set the cutpoints. The policy preserves
the frozen Mission 02 decision threshold:

- Low upper boundary: `min(validation probability q95, decision threshold)`.
- Critical lower boundary: `max(decision threshold, q75 among validation probabilities at or
  above the threshold)`.
- Elevated is the interval from Low's exclusive boundary to the frozen threshold.
- High is the interval from the threshold to Critical's exclusive boundary.
- Critical includes its lower boundary and all higher probabilities.

The frozen threshold is `0.1835921396957453`. On the completed validation run, Low ends at
`0.00068414` and Critical begins at `0.90825134`. Consequently no threshold-positive prediction
can be Low. Validation diagnostics are in `reports/risk/validation_risk_tiers.csv` and
`RISK_ANALYSIS.md`; labels describe only the historic validation sample. These tiers are operational
triage categories, not calibrated probability bands or validated business decisions.
