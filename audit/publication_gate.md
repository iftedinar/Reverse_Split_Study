# CORE / ENRICHED Tiering and Publication Gate Determination

## CORE / ENRICHED tiers

Per the brief, events are tiered by data reliability rather than treated as
a single undifferentiated pool.

- **CORE tier (88/88 events, 100%):** split-adjustment factor validation =
  PASS (audit/split_adjustment_validation.csv, 88/88, mean/max factor_pct_diff
  = 0.0%); data completeness = complete (audit/data_completeness_round2.csv,
  final re-check: 88/88, >=28 pre-event / >=58 post-event trading bars);
  Accuracy Check Pass #2 independent recomputation agrees to <1e-6 for every
  event (audit/accuracy_check_pass_2.csv, 0 mismatches).
- **ENRICHED tier: 0/88.** No event in the final sample required inclusion
  on weaker evidence — every event that could not clear the CORE bar was
  excluded and seeded-replaced during the three completeness-correction
  rounds documented in RESEARCH_LOG.md (blocked/403 events, round-1;
  Polygon's rolling ~2-year historical-depth floor causing silent
  truncation, round-2; a second anomalous-ticker data-gap pattern, rounds
  2-3), rather than kept and downgraded to ENRICHED. This is a stricter
  standard than the brief required but was preferred because it keeps the
  final N=88 fully homogeneous in data quality.

Because CORE = 100% of the sample, every statistic in this study's report
is computed on the full N=88 CORE sample; there is no separate
CORE-vs-ENRICHED comparison to report.

## Publication Gate

| Gate criterion | Requirement | Result |
|---|---|---|
| Sample size | 75-150 events, target ~100 | 88 events, 84 unique companies — PASS (within range) |
| Distinct companies | >=75 | 84 — PASS |
| Split-adjustment validation | Return-independent factor check | 88/88 PASS, 0 WARNING, 0 FAIL |
| Data completeness | Pre/post window coverage | 88/88 complete |
| Accuracy Check Pass #2 | Independent recomputation, halt-and-fix on failure | 0 mismatches across 88 events x 4 metrics — no halt triggered |
| Validation Pass #1 | >=20 events / 20% manual review | 20/88 (22.7%) reviewed, 20/20 PASS |
| External spot checks | >=10 events vs. public sources | 11/88 checked, 11/11 CONFIRMED |
| Median reporting | Mandatory alongside mean | Done throughout (results/tables/) |
| No outcome-based cherry-picking | Selection/replacement blind to returns | Maintained across all 3 correction rounds (documented in RESEARCH_LOG.md) |

**Determination: PASS**, with the following pre-registered limitations
disclosed rather than hidden (see the final report's Limitations section):
this is an exploratory, single-window (2024-01-01 to 2025-12-31) study of a
non-random-in-the-population-sense universe (all 2024-2025 US-listed
reverse splits meeting the eligibility screen, stratified-sampled down to
88); the "universe-adjusted" return series is an explicitly-labeled
best-effort substitute for a true matched-control group, not a full
event-study benchmark; the "extreme momentum" intraday leg uses a
same-day high/open proxy in the absence of intraday minute data; and no
claim of causal or tradable-strategy inference is made from N=88
observational events with a modest and partly overlapping stratified
sample.
