# ADR 0007: leakage-safe Mission 02 evaluation

## Status

Accepted for the Mission 02 experiment.

## Context

The ULB dataset is time ordered, highly imbalanced, and includes exact duplicate transactions. A random split could place identical or future-adjacent rows across train and test. Only 492 fraud labels are available, making validation estimates noisy.

## Decision

Use a predeclared chronological 70/15/15 split with complete Time ties assigned to one partition. Audit exact feature-vector and full-row signatures across all partitions and reject any cross-partition signature. Keep all rows; do not silently deduplicate. Rank eight bounded model candidates by mean Average Precision over three expanding-window folds inside training. Select the simplest candidate within one standard error of the maximum. Fit calibration on training-only out-of-fold scores, select a maximum-F2 threshold on validation, then evaluate the frozen model on the latest partition. Fit Isolation Forest separately on known Class 0 training rows.

## Consequences

The evaluation better matches forward-in-time use than a shuffled split but does not prove future-month or production generalization. Time grouping changes exact partition percentages slightly. Small fold and held-out fraud counts create uncertainty. No random split sensitivity experiment is reported because the forward-in-time protocol was chosen before training and is the primary target.

The final test partition was scored twice in deterministic completion runs because the initial run omitted the Isolation Forest artifact manifest. Both runs produced identical test metrics; the repeat was not used to change model, calibration, or threshold. This is disclosed as an audit limitation, and independent testing now requires later data.
