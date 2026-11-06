# Modeling strategy

Mission 02 compares compact scikit-learn models on the verified ULB dataset. The supervised input schema is Time, V1–V28, and Amount in the order recorded by the split manifest; Class is the target and is excluded from every inference feature set.

## Candidate families

All candidates use seed 17 and the same three expanding-window folds inside the training partition:

| Candidate | Configuration |
|---|---|
| Dummy prior | DummyClassifier with strategy=prior |
| Logistic Regression, unweighted C=0.1 | L2 regularization, StandardScaler, max iterations 2,000 |
| Logistic Regression, unweighted C=1 | L2 regularization, StandardScaler, max iterations 2,000 |
| Logistic Regression, balanced C=1 | L2 regularization, StandardScaler, class_weight=balanced, max iterations 2,000 |
| Random Forest, unweighted | 100 trees, depth 16, leaf minimum 2, sqrt features, 2 workers |
| Random Forest, balanced | Same forest with balanced_subsample class weighting |
| HistGradientBoosting, unweighted | 100 iterations, learning rate 0.08, 15 leaves, L2=1, early stopping disabled |
| HistGradientBoosting, balanced | Same histogram booster with class_weight=balanced |

Logistic Regression scaling is fitted independently within each training fold and included in the persisted estimator pipeline. Tree models use the original numeric feature scales. No oversampling is used.

## Results and interpretation

The maximum cross-validation mean Average Precision was 0.75238 for balanced HistGradientBoosting, with fold standard deviation 0.13229. The one-standard-error floor was 0.67601. Balanced Logistic Regression had mean AP 0.73880 (folds 0.68663, 0.84174, 0.68801) and was the simplest candidate within that floor, so it was selected. It also has a compact artifact and a transparent linear scoring structure that will be useful for Mission 03.

The full candidate comparison, per-fold metrics, fixed-0.5 validation diagnostics, and fit times are in reports/ml/MODEL_COMPARISON.md and reports/ml/model_comparison.csv. The fixed-0.5 validation results were generated only after the candidate selection freeze and were descriptive; they did not change the selected model.

## Class imbalance

Fraud is about 0.173% of the complete data. The experiment compares unweighted candidates with balanced logistic and histogram boosting and balanced-subsample Random Forest. No class is resampled, and evaluation partitions retain their observed prevalence. Class weighting changes the score distribution; the selected probability mapping and operational threshold are therefore fit and assessed as separate steps.

Accuracy is not used as a selection metric. Average Precision is the primary ranking metric, supported by ROC-AUC, precision/recall, confusion counts, calibration measures, and fixed alert-budget summaries.

## Limits

The dataset is a short historical sample with anonymized PCA features and no entity history. Model ranking can vary across temporal folds, especially with only 28 fraud cases in the third fold. The comparison does not establish performance on later months, another institution, or a live fraud stream.
