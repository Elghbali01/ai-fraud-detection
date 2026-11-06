# ADR 0001 — Python package layout

- Status: accepted.
- Decision: place reusable data and EDA logic in src/fraud_detection and configure packaging, tests, and Ruff in pyproject.toml.
- Reason: notebooks, scripts, and later backend services need one importable implementation; src layout catches undeclared import-path assumptions.
- Consequence: local development installs the package into .venv or sets PYTHONPATH=src for checks.
