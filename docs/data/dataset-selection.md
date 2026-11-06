# Dataset Selection and Source Review

Research and local verification date: 2026-11-06. ULB publisher claims and observations from the acquired CSV are distinguished below.

## Comparison

| Candidate | Provenance and authenticity | Size and labels | Licensing/access | Interpretability and local fit | Limitations |
|---|---|---|---|---|---|
| ULB Credit Card Fraud Detection | Kaggle page maintained by ULB Machine Learning Group; describes transactions collected in collaboration with Worldline from European cardholders in September 2013. The acquired file matched the source identity and schema. | Publisher lists 284,807 rows, 492 fraud labels, 31 columns, and a 150.83 MB CSV. Local file observed 284,807 rows, 492 frauds, 31 columns, 150,828,752 bytes, and passed ulb-credit-card-v1 validation. SHA-256: 76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89. | Kaggle data card shows database classification “Open Database” and contents classification “Database Contents”; that metadata is not interpreted here as a complete legal grant. Review current page terms and attribution/redistribution conditions before redistributing contents. | Numeric 31-column format and modest published CSV size fit local EDA. PCA features limit business interpretation. | Only two elapsed days; anonymized features; Time is not a calendar timestamp; no merchant/customer/device history; labels do not establish universal fraud behavior. |
| IEEE-CIS Fraud Detection | Official IEEE-CIS Kaggle competition data; two linked tables (transaction and identity), with some transactions lacking identity fields. Competition page describes online transaction fraud prediction; feature set mixes direct and masked/engineered fields. | Exact local row/column counts and byte size are unverified here. The official access page separates train/test transaction and identity files. | Competition rules/access conditions apply; no separate redistribution license was verified. | Richer mixed fields and multiple tables may support later feature-engineering research, but require joins, missingness handling, larger storage, and more compute. | Many fields are masked; missing identity coverage; competition data and target timing require leakage review. Counts and size should be measured after authorized acquisition. |
| PaySim | Original PaySim paper presents an agent-based mobile-money simulator calibrated from an original financial dataset. Public transaction rows are synthetic, not actual customer transactions. | Exact rows, columns, and storage depend on the particular redistributed version; not independently verified for a single canonical copy here. | The research paper describes the simulator, not a license for every Kaggle re-upload. Check the selected publisher's terms and attribution. | Useful for simulated mobile-money patterns and large-scale local testing, but it changes the target domain and can be generated at varying scale. | Synthetic labels reflect simulator rules and cannot stand in for observed production fraud; multiple versions can differ. |

## Decision

Select ULB as the primary Mission 01 dataset because its published data is compact, numerical, and has a clear 31-column schema. The acquired file passed schema validation and matched the published row and class counts. Its local provenance sidecar and observed data-quality details are documented in docs/data/data-quality-report.md.

## ULB scientific cautions

- V1–V28 are PCA-derived anonymized variables; they do not identify a physical transaction cause.
- Time is seconds elapsed since the first transaction in the dataset, not real calendar time.
- Amount has no currency unit stated on the dataset card; reports therefore use “dataset units.”
- The data card describes two days of transactions. Temporal validation findings cannot by themselves establish long-term drift.
- No location, merchant identity, device identifier, or customer history is supplied. Do not invent those analyses.
- A labeled historical case is not equivalent to a future model prediction, estimated risk, or unsupervised anomaly.

## Current acquisition and verification status

The CSV was acquired through the official Kaggle CLI on 2026-11-06 and validated without changing the raw rows. The local sidecar records the source URL, UTC retrieval time, schema report, observed counts, size, and SHA-256. The raw file is excluded from Git.

Historical initial audit: the file and Kaggle CLI were absent at the first repository audit, so no real-data findings were claimed then. The downloader fix made it possible to invoke the CLI installed beside the active project Python.

## Sources

- ULB dataset data card: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud (accessed 2026-11-06).
- IEEE-CIS competition data page: https://www.kaggle.com/competitions/ieee-fraud-detection/data (accessed 2026-11-06).
- Original PaySim paper: https://www.msc-les.org/proceedings/emss/emss2016/emss2016_249.html (accessed 2026-11-06).
