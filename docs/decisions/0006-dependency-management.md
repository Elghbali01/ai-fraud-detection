# ADR 0006 — Python dependencies

- Status: accepted.
- Decision: use pyproject.toml with compatible Python 3.11 runtime/development ranges and a project-local virtual environment.
- Reason: only data handling, plots, notebook execution, lint, and tests are needed in Mission 01.
- Consequence: requirements-mission01.lock pins the resolved Windows/Python 3.11 runtime and development dependency graph. Clean setup installs those exact versions; offline mode can reuse system packages but is not fully isolated. Refresh the lock when pyproject.toml dependencies change. Do not add SHAP, XGBoost, FastAPI, Next.js, PyTorch, TensorFlow, or a Kaggle CLI dependency until their mission or immediate workflow needs them.
