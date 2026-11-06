# Mission 03 risk and anomaly analysis

## Scope

This is a descriptive analysis of 42,722 frozen validation
rows (56 labeled fraud cases). It does not use
the consumed final-test partition. Tier cutpoints are derived from validation probabilities only;
validation labels are used only for the diagnostics below. No business costs are assumed.

The display score is 100 times the sigmoid-calibrated fraud probability. The persisted decision
threshold remains 0.183592139696. The tier policy is operational triage,
not a calibrated probability band. Low ends below 0.00068414; Critical
begins at 0.90825134. A decision-positive record cannot be Low.

## Validation tier diagnostics

| Tier | Rows | Historical fraud labels | Label prevalence | Model alerts |
|---|---:|---:|---:|---:|
| Low | 40,585 | 4 | 0.010% | 0 |
| Elevated | 2,085 | 8 | 0.384% | 0 |
| High | 18 | 10 | 55.556% | 18 |
| Critical | 34 | 34 | 100.000% | 34 |

These observed label prevalences describe this validation period and are not future guarantees.

## Fixed review-capacity diagnostics

Ranking is by calibrated fraud probability descending. Percentage budgets use ceiling, including
at least one row for any nonempty dataset. Identifier then stable input order resolves ties when
identifiers are available; this validation report uses stable source-row order.

| Budget | K | Fraud captured | Precision@K | Recall@K |
|---|---:|---:|---:|---:|
| top_10 | 10 | 10 | 100.000% | 17.857% |
| top_50 | 50 | 43 | 86.000% | 76.786% |
| top_100 | 100 | 48 | 48.000% | 85.714% |
| top_0.1_percent | 43 | 40 | 93.023% | 71.429% |
| top_0.5_percent | 214 | 51 | 23.832% | 91.071% |
| top_1_percent | 428 | 51 | 11.916% | 91.071% |

## Separate anomaly signal

Isolation Forest scores are `-score_samples`; higher means more anomalous and the value is not a
fraud probability. Its empirical reference contains 198,980
known-legitimate training rows. Training-reference score quantiles are p50=0.386069,
p95=0.476849, and p99=0.574136. Validation percentiles use the
empirical midrank against this fixed training reference.

Validation Spearman correlation between calibrated fraud probability and anomaly percentile is
0.0754. This is a comparison, not a combined score.

| Validation quadrant | Rows | Historical fraud labels |
|---|---:|---:|
| high_supervised_high_anomaly | 52 | 44 |
| high_supervised_low_anomaly | 0 | 0 |
| low_supervised_high_anomaly | 2,896 | 6 |
| low_supervised_low_anomaly | 39,774 | 6 |

The two signals remain separate. No formula blends them into a production fraud score. Real-world
investigation capacity, costs, calibration stability, and independent future utility are unknown.
