# Recommender Shilling Attack Response

## Detection

Treat abnormal target-item exposure as a symptom, not proof of abuse. Correlate
exposure changes with profile similarity, interaction timing, model releases,
catalog coverage, and group-level exposure. Natural popularity changes should
not normally produce many new accounts with near-identical preference vectors
and synchronized interactions.

## Evidence requirements

Before proposing account isolation, preserve evidence IDs for the affected
item, suspicious profile cohort, interaction burst, and model version. Reject
stale snapshots that predate the incident. A model or feature release should
remain a competing hypothesis until the registry timeline rules it out.

## Safe response

Run a counterfactual simulation before any intervention. If the projected
result is safe, use a small canary cohort and verify target-item exposure,
catalog coverage, suspicious-profile ratio, and group exposure gap. Account
isolation or feature rebuilding requires named human approval. Failed
postconditions require an immediate rollback to the last investigation
checkpoint.

## Recovery conditions

Recovery requires target-item exposure at or below 8 percent, catalog coverage
at or above 65 percent, suspicious profiles below 1 percent, and group exposure
gap at or below 0.10. Continue monitoring delayed feedback after the first
successful verification because recommender effects can reappear over time.
