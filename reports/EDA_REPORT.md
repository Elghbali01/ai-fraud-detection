# Exploratory Data Analysis — Incomplete

**Real-data status:** blocked; no local ULB dataset was available during this mission.

The Kaggle CLI and authorized local Kaggle credentials were not present, and outbound access to dataset and GitHub hosts was denied. Therefore this report contains no observed ULB transaction statistics, findings, or plots. The ULB dataset page reports 284,807 rows and 492 fraud labels, but those publisher figures have not been checked against the actual CSV and are not presented as local results.

The reusable EDA, reports, charts, and notebooks are implemented. Small deterministic fixtures are used only for tests and a separately labeled smoke path. Fixture results do not describe the ULB dataset.

To generate the real report after authorized acquisition:

    .\.venv\Scripts\python.exe scripts\download_dataset.py
    .\scripts\run-eda.ps1

Until then, real-data EDA remains incomplete.
