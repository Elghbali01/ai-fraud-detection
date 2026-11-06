# Isolation Forest anomaly experiment

Isolation Forest is implemented as a separate unsupervised-style ranking experiment. It is fitted on 198,980 Class 0 transactions from the training partition. The known-legitimate label filter is explicitly part of the fit protocol; labels are not passed as features. The model uses the 30 numeric transaction fields without scaling, with 100 trees, max_samples=256, contamination=auto, two workers, and seed 17.

The reported score is negative IsolationForest score_samples, so higher values mean more anomalous. It is a continuous anomaly score, not a calibrated probability and not a supervised fraud decision. The API exposes it through a separate function and response schema.

## Ranking results

| Partition | Average Precision | ROC-AUC | Fraud captured at top 0.1% / 0.5% / 1% |
|---|---:|---:|---:|
| Validation, 56 frauds | 0.02883 | 0.94776 | 0 / 2 / 13 |
| Final test, 52 frauds | 0.03845 | 0.94518 | 0 / 13 / 25 |

At the final-test 1% budget, the detector captures 25 of 52 frauds, but its precision is only 5.84%. This illustrates that unusualness and fraud are different concepts. The supervised model and Isolation Forest top-K lists overlap by 6.98%, 19.16%, and 21.73% at 0.1%, 0.5%, and 1% budgets. Their score scales are not combined.

The experiment is descriptive, based on one short dataset and small fraud counts. It does not justify a production anomaly threshold or a blended risk score. See reports/ml/ANOMALY_DETECTION.md for figures and full budget tables.
