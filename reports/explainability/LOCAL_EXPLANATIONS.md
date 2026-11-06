# Mission 03 selected local explanations

Examples were chosen deterministically from validation by highest probability, closest to the frozen threshold, and median probability, with duplicate rows removed. These descriptions use raw-log-odds SHAP values and are not calibrated-probability decompositions. They describe model behavior, not causes.

### highest_validation_probability

Validation source row `199896`; label used only for this descriptive validation view: `1`. Calibrated probability: `0.90825134`; frozen threshold: `0.18359214`; status: `flagged_for_review`.

Top positive SHAP terms in raw log-odds: Amount (+9.4218), V14 (+5.3111), V4 (+2.8909), V12 (+2.7049), V10 (+2.5014).

Top negative SHAP terms in raw log-odds: V20 (-2.6442), V3 (-2.0689), V2 (-1.3414), V1 (-0.5894), V7 (-0.4737).

The separate Isolation Forest ranks this observation at approximately the 99.3% anomaly percentile (Highly unusual); this is not a fraud probability.

### closest_to_frozen_threshold

Validation source row `215953`; label used only for this descriptive validation view: `1`. Calibrated probability: `0.18359214`; frozen threshold: `0.18359214`; status: `flagged_for_review`.

Top positive SHAP terms in raw log-odds: V14 (+8.2266), V4 (+3.6782), V2 (+1.8095), V5 (+1.5551), V12 (+1.3922).

Top negative SHAP terms in raw log-odds: V17 (-2.8484), V16 (-2.0468), V3 (-1.6610), Amount (-0.6832), V22 (-0.5511).

The separate Isolation Forest ranks this observation at approximately the 99.5% anomaly percentile (Highly unusual); this is not a fraud probability.

### median_validation_probability

Validation source row `210271`; label used only for this descriptive validation view: `0`. Calibrated probability: `0.00011480`; frozen threshold: `0.18359214`; status: `not_flagged_by_policy`.

Top positive SHAP terms in raw log-odds: V1 (+0.9822), V17 (+0.4110), V6 (+0.2652), V4 (+0.2602), V24 (+0.2247).

Top negative SHAP terms in raw log-odds: V12 (-0.8922), Time (-0.5047), V3 (-0.4469), V14 (-0.3117), V16 (-0.2643).

The separate Isolation Forest ranks this observation at approximately the 16.9% anomaly percentile (Typical); this is not a fraud probability.
