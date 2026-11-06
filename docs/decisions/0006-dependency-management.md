# ADR 0006 — Python dependencies

- Status: accepted.
- Decision: use pyproject.toml with compatible Python 3.11 runtime/development ranges and a project-local virtual environment.
- Reason: only data handling, plots, notebook execution, lint, and tests are needed in Mission 01.
- Consequence: a full transitive lock was not generated because package indexes were unreachable during implementation. Clean online setup resolves the declared constraints; offline mode can reuse system packages but is not a dependency snapshot. Do not add SHAP, XGBoost, FastAPI, Next.js, PyTorch, TensorFlow, or a Kaggle CLI dependency until their mission or immediate workflow needs them.
