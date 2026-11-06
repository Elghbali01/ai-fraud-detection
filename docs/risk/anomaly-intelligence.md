# Separate anomaly intelligence

The existing trusted Mission 02 Isolation Forest is reused without refitting. Its anomaly score is
`-IsolationForest.score_samples`; higher means more anomalous and the score is never a fraud
probability.

The reference empirical distribution is created by scoring the 198,980 known-legitimate rows in
the training partition. Percentiles use the empirical midrank (count below plus half the ties,
divided by the reference size). Categories are Typical below p95, Unusual from p95 to p99, and
Highly unusual at or above p99. The reference manifest records dataset and split identity, model
version, score quantiles, method, and artifact checksum. The derived NumPy score archive is local
under ignored `data/models/` and can be deterministically regenerated with the report script.

Supervised probability and anomaly percentile are compared on validation through Spearman rank
correlation, TopK capture, overlap, Jaccard similarity, and four threshold-defined quadrants.
Neither score is blended into a single production rank. An unusual observation can be legitimate;
a fraud prediction and an anomaly flag describe different learned targets.
