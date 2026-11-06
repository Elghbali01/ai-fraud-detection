# Evaluation protocol

The primary split is forward-in-time with complete equal-Time groups. Split boundaries and all duplicate counts are frozen in `split_manifest.json` before training. Folds are expanding windows inside training only. Candidate selection uses mean fold Average Precision with a one-standard-error simplicity rule. Sigmoid calibration is fitted to out-of-fold predictions from those training-only folds. Validation assesses calibration and selects a maximum-F2 threshold. Post-freeze candidate validation scores use threshold 0.5 for descriptive comparison only. The test labels are first used after the model, calibration, and threshold are frozen.

| Partition | Rows | Class 0 | Class 1 | Time range (elapsed seconds) |
|---|---:|---:|---:|---:|
| train | 199,364 | 198,980 | 384 | 0–132928 |
| validation | 42,722 | 42,666 | 56 | 132929–151328 |
| test | 42,721 | 42,669 | 52 | 151329–172792 |

Training fold fraud counts: [52, 111, 28]. The source covers only a short historical window and does not establish later-period or production performance.
