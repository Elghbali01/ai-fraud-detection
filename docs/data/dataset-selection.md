# Dataset Selection and Source Review

Research date: 2026-11-06. Source-reported values below are not measurements from a locally acquired file. The real ULB CSV was not available during Mission 01 execution.

## Comparison

| Candidate | Provenance and authenticity | Size and labels | Licensing/access | Interpretability and local fit | Limitations |
|---|---|---|---|---|---|
| ULB Credit Card Fraud Detection | Kaggle page maintained by ULB Machine Learning Group; describes transactions collected in collaboration with Worldline from European cardholders in September 2013. Real historical transactions, anonymized. | Page describes 284,807 rows, 492 fraud labels, 31 columns, and lists creditcard.csv at 150.83 MB. These are page claims pending local verification. | Kaggle data card shows database classification “Open Database” and contents classification “Database Contents”; that metadata is not interpreted here as a complete legal grant. Review current page terms and attribution/redistribution conditions. Kaggle access may require an account. | Numeric 31-column format, modest published CSV size, and local fit make this the best Mission 01 candidate. PCA features limit business interpretation. | Only two elapsed days; anonymized features; not a calendar timestamp; no merchant/customer/device history; labels do not establish universal fraud behavior. |
| IEEE-CIS Fraud Detection | Official IEEE-CIS Kaggle competition data; two linked tables (transaction and identity), with some transactions lacking identity fields. Competition page describes online transaction fraud prediction; feature set mixes direct and masked/engineered fields. | Exact local row/column counts and byte size are unverified here. The official access page separates train/test transaction and identity files. | Competition rules/access conditions apply; no separate redistribution license was verified. | Richer mixed fields and multiple tables may support later feature-engineering research, but require joins, missingness handling, larger storage, and more compute. | Many fields are masked; missing identity coverage; competition data and target timing require leakage review. Counts and size should be measured after authorized acquisition. |
| PaySim | Original PaySim paper presents an agent-based mobile-money simulator calibrated from an original financial dataset. Public transaction rows are synthetic, not actual customer transactions. | Exact rows, columns, and storage depend on the particular redistributed version; not independently verified for a single canonical copy here. | The research paper describes the simulator, not a license for every Kaggle re-upload. Check the selected publisher's terms and attribution. | Useful for simulated mobile-money patterns and large-scale local testing, but it changes the target domain and can be generated at varying scale. | Synthetic labels reflect simulator rules and cannot stand in for observed production fraud; multiple versions can differ. |

## Decision

Select ULB as the primary Mission 01 candidate because its published data is compact, numerical, and has a clear 31-column schema. Do not switch to a different dataset for perceived prestige. The selection is provisional until an authorized CSV is acquired and its actual schema, row count, class counts, and checksum are recorded.

## ULB scientific cautions

- V1–V28 are PCA-derived anonymized variables; they do not identify a physical transaction cause.
- Time is seconds elapsed since the first transaction in the dataset, not real calendar time.
- Amount has no currency unit stated on the dataset card; reports therefore use “dataset units.”
- The data card describes two days of transactions. Temporal validation findings cannot by themselves establish long-term drift.
- No location, merchant identity, device identifier, or customer history is supplied. Do not invent those analyses.
- A labeled historical case is not equivalent to a future model prediction, estimated risk, or unsupervised anomaly.

## Acquisition and verification status

At audit time the expected file was absent; Kaggle CLI and authorized local credentials were unavailable, so the downloader exited before a network request. No alternate data was downloaded or represented as ULB. The downloader is scripts/download_dataset.py and will record a source URL, UTC retrieval time, schema report, observed counts, size, and SHA-256 after a successful validated download.

## Sources

- ULB dataset data card: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud (accessed 2026-11-06).
- IEEE-CIS competition data page: https://www.kaggle.com/competitions/ieee-fraud-detection/data (accessed 2026-11-06).
- Original PaySim paper: https://www.msc-les.org/proceedings/emss/emss2016/emss2016_249.html (accessed 2026-11-06).
