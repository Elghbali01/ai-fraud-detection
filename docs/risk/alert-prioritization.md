# Alert prioritization

`prioritize_transactions()` ranks by calibrated fraud probability descending. A caller chooses
exactly one fixed `top_k` or percentage budget. A percentage converts to `ceil(N * percent / 100)`;
for nonempty input, a valid positive percentage selects at least one row. The count is capped at
the available filtered rows. Pagination is bounded to 1,000 rows per request.

Ties resolve by transaction identifier ascending, then stable input order when an ID column is
present. Numeric IDs remain numerically sorted; otherwise identifiers use deterministic typed
lexical order. Without IDs, stable input order resolves ties. Filtering on probability or tier is
optional. The queue needs no labels; labels enter only the explicit validation diagnostics.

`validation_alert_budget_metrics()` reports Precision@K, Recall@K, fraud captures, and false
alerts for K=10/50/100 and 0.1%/0.5%/1% on validation. The actual diagnostics are written to
`reports/risk/validation_alert_budgets.csv`. They are retrospective capacity illustrations, not
production workload or cost estimates.
