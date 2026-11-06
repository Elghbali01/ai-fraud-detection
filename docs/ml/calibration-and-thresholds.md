# Calibration and decision thresholds

## Probability calibration

The selected class-weighted Logistic Regression estimator is calibrated by fitting a one-dimensional sigmoid mapping to its out-of-fold scores on training data. The calibration fit uses training-only labels. Validation data is held out to compare the raw estimator scores with the mapped probabilities; isotonic regression was not fitted because the number of positives is limited and its more flexible mapping would be at risk of overfit.

On the 42,722-row validation period with 56 fraud cases:

| Scores | Brier score | Log loss | Equal-frequency ECE |
|---|---:|---:|---:|
| Raw estimator | 0.019587 | 0.087627 | 0.061911 |
| Training-fold sigmoid | 0.000373 | 0.002241 | 0.000173 |

These validation improvements support using the sigmoid-mapped output for this experiment. They do not prove calibration under changing prevalence or future data. The response labels the output as a training-fold sigmoid probability, not as a production guarantee.

## Threshold policy

The decision threshold is chosen on validation to maximize F2, which weights recall more heavily than precision. The selected threshold is 0.18359214. At that point validation precision is 0.84615, recall is 0.78571, and 52 of 42,722 transactions are alerts (0.1217%). The policy module also supports explicit recall/precision constraints, fixed alert capacity, F1, and cost-sensitive inputs; infeasible constraints return an explicit error.

The threshold is persisted with the supervised model artifact and applied to the calibrated fraud probability. It is an operating policy for this dataset and objective, not an inherent fraud boundary. A production workflow should set capacity and harm costs with domain owners and monitor changes in class prevalence.

## Final test operating point

Applying the already frozen threshold to the final period produced precision 0.90476, recall 0.73077, F1 0.80851, and F2 0.76000. The confusion counts were TN=42,665, FP=4, FN=14, and TP=38. The test set contains 52 fraud examples; the Wilson 95% recall interval is 0.5975–0.8323. A small positive count limits certainty.

Average Precision and trapezoidal PR area are reported separately. The final-test values are 0.73727 and 0.74608, respectively.

## Alert budgets

Top-K uses K=floor(N × budget percentage / 100), with at least one alert for a nonempty partition. On the final test, 0.1%, 0.5%, and 1% budgets correspond to 43, 214, and 428 ranked transactions and capture 38, 42, and 42 frauds. These are ranking scenarios, distinct from the threshold-selected confusion matrix. They do not imply staffing capacity or monetary impact.

Detailed threshold curves and budget tables are in reports/ml/THRESHOLD_ANALYSIS.md and reports/ml/alert_budget_comparison.csv.
