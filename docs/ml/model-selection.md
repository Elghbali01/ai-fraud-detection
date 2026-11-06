# Model selection

## Frozen criterion

Before candidate training, the protocol fixed Average Precision as the primary ranking measure and defined three expanding temporal folds inside the 70% training window. Each candidate uses the same folds. The winning model is selected by a one-standard-error rule: find the best mean fold AP, calculate its standard error, retain candidates at or above the best mean minus one standard error, then select the simplest candidate in that eligible group.

This criterion addresses the high fold-to-fold variability and avoids choosing a more complex model for a small, noisy AP difference. The candidate list and hyperparameters are bounded and recorded in reports/ml/EXPERIMENT_REGISTRY.json.

## Selected candidate

Balanced Logistic Regression with C=1 and StandardScaler was selected. Balanced HistGradientBoosting had the highest mean CV AP (0.75238, SD 0.13229); the standard error was 0.07638 and the eligibility floor was 0.67601. Balanced Logistic Regression achieved mean AP 0.73880 (SD 0.08916), within the one-standard-error range, with substantially lower training cost and a compact inference pipeline.

Its final fit on all training rows took 1.04 seconds. Candidate fold fit time was 1.85 seconds total. Timing is environment-specific.

## Validation and final-test separation

After selection was frozen, validation comparisons at the fixed reference threshold 0.5 were generated for descriptive context only. A sigmoid mapper was fitted from training-only out-of-fold scores; its validation assessment was not used to select a different model. The maximum-F2 threshold was then selected from validation labels and recorded. Only after those development choices were frozen was the final time window scored.

The final test results are not a model-ranking criterion. The same frozen test partition was scored in two deterministic completion runs because the first run omitted the Isolation Forest artifact manifest. The second run repaired persistence; no selection or threshold choice was based on either test score. The duplicate evaluation is disclosed in leakage-prevention.md and the append-only experiment registry.

## Performance summary

The selected model's final chronological test Average Precision was 0.73727 and ROC-AUC was 0.97724. At the validation-selected threshold, final-test precision was 0.90476 and recall 0.73077, with 4 false positives and 14 missed frauds among 42,721 transactions. There were only 52 test fraud cases, so these estimates are uncertain. See reports/ml/FINAL_MODEL_REPORT.md for the complete metrics and uncertainty intervals.
