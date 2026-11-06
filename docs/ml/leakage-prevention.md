# Leakage prevention

The primary experiment follows the predeclared chronological protocol in reports/ml/EVALUATION_PROTOCOL.md and reports/ml/split_manifest.json.

## Partition and fold boundaries

- Rows remain in source time order. Complete groups sharing an identical Time value stay in one partition.
- Train, validation, and final test contain 199,364, 42,722, and 42,721 rows, respectively. Their fraud counts are 384, 56, and 52.
- The model-selection folds are expanding-window folds made only from the training partition. Every fold validates strictly after its fit window.
- The final 15% time window is reserved for one final metric computation after the model configuration, calibration method, and threshold were frozen.

## Duplicate controls

The split audit found 773 exact duplicate groups, covering 1,854 rows and 1,081 copies beyond the first. No rows were deleted. Identical feature-vector signatures and exact full-row signatures were checked across all partitions; both had zero cross-partition groups and zero cross-partition rows. Repeated feature vectors had no conflicting labels. Because Time is part of the feature vector and tied timestamps are grouped, exact copies remain together.

This audit cannot identify near-duplicates or repeated entities: the source contains no transaction, account, merchant, or customer identifiers.

## Feature and preprocessing controls

Class is never passed into a model as a feature. The feature list is centrally defined and persisted in both artifact manifests. The scaler for Logistic Regression is part of the scikit-learn pipeline and is fit on each fold's fit rows; the final pipeline is fit only on the training partition. Validation and test rows are transformed by that fitted pipeline.

The sigmoid calibrator is trained on out-of-fold training scores only. Validation is used to assess calibration and choose the F2 threshold. Neither calibration nor threshold selection sees the final test labels.

Isolation Forest is a separate experiment. Class is used only to choose the known-legitimate training subset and to evaluate ranking. It is not an input feature; no validation or test labels enter its fit.

## Final-test audit caveat

The first complete real-data run exposed a missing persistence artifact for Isolation Forest after its final ranking metrics had been computed. After correcting artifact persistence, the complete deterministic workflow was run again so both supervised and anomaly artifacts could be verified. This means the same frozen final-test partition was scored in two recorded runs. The model-selection rule, calibration fit, threshold, and implementation choices were not changed in response to final-test metrics; both registry entries report identical final-test metrics. The repetition is retained in reports/ml/EXPERIMENT_REGISTRY.json and should be treated as an audit caveat. Future model development must not use this test result; independent evaluation requires new later data.
