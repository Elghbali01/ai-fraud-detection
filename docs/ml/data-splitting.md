# Mission 02 data splitting protocol

## Primary split

The primary evaluation uses the source's existing nondecreasing `Time` order. It is an elapsed-seconds feature without a calendar origin. Boundaries are selected before model training from cumulative row counts grouped by unique `Time`: choose the unique timestamp whose cumulative row count is nearest to 70% of all rows, and the timestamp nearest to 85%. The complete timestamp group at each boundary belongs to the earlier partition. This keeps transactions with identical elapsed time together and prevents chronology from being reversed.

The manifest in `reports/ml/split_manifest.json` records the source SHA-256, schema, method, exact cutoffs, counts, class percentages, software versions, duplicate audits, and development-fold boundaries. The manifest contains aggregate metadata only; row positions are regenerated deterministically from the verified CSV.

The expected source-derived split is 199,364 training rows through `Time=132928`, 42,722 validation rows from `132929` through `151328`, and 42,721 final-test rows from `151329` through `172792`. Expected fraud counts are 384, 56, and 52. The actual generated manifest is authoritative if source verification or split checks detect a difference.

## Development folds and test isolation

Model candidates are ranked by mean Average Precision on three expanding-window folds created only within training rows. Training timestamps are divided into five row-balanced, tie-preserving blocks. Each fold fits on the first two, three, or four blocks and validates on the next block. Feature scaling and every learned model transformation are fitted on the fold's fit rows only. This design keeps each fold's validation later in time than its fit data.

After selection, the winning configuration is fitted on all training rows. A sigmoid probability mapping is fitted to the winning candidate's out-of-fold training predictions. Validation is used to assess calibration and choose the predeclared maximum-F2 operating threshold. Once these decisions are frozen, all candidates are scored on validation at the fixed 0.5 reference threshold for descriptive comparison only; this does not change the selected model. The final test remains closed until model, calibration, and threshold are recorded. Its labels are used once for final metrics and never for revisions.

## Duplicate controls

No rows are removed. The split audit checks both exact full rows and feature vectors (`Time`, `V1`–`V28`, `Amount`) across all three partitions, and reports conflicting labels for repeated feature vectors. Identical feature vectors include identical `Time`; complete timestamp groups therefore keep them together. A feature signature appearing across partitions is a hard validation error. Near-duplicate similarity and entity-level leakage cannot be assessed because the source contains no entity identifiers.

## Scope and limitations

The later 15% test window contains 52 fraud cases. This chronological evaluation better reflects forward-in-time use than a shuffled split, but the dataset spans only about two days and does not establish performance on later months or a production stream. Time grouping can make partition sizes differ slightly from nominal percentages. The temporal CV folds are also limited by time-varying label counts; fold-level results must accompany their mean. A separate random-split sensitivity experiment is not part of the frozen primary protocol.
