# Validation Pass #1 — Manual Review

**Sample:** 20 of 88 selected events (22.7%), drawn by reproducible stratified
random sampling (seed 20260919, stratified by selection_year x ratio_bucket),
per the study's non-outcome-based sampling discipline — this draw script
(`14_validation_pass1_sample.py`) reads only `sample_selection.csv`
identifiers and never touches price or return data. Full detail per event is
in `audit/validation_sample.csv`.

## What was checked for every one of the 20 events

1. **Ratio-bucket membership** — normalized_reverse_split_ratio falls in the
   bucket recorded in ratio_bucket, per the frozen definitions in
   `config/definitions.md`. All 20/20 correct.
2. **Split-adjustment factor validation** — cross-referenced against
   `audit/split_adjustment_validation.csv` (the return-independent
   factor_pre/factor_post test). All 20/20 = PASS, factor_pct_diff = 0.0%.
3. **Data completeness** — cross-referenced against
   `audit/data_completeness_round2.csv` / the final completeness re-check.
   All 20/20 = complete (>=28 pre-event and >=58 post-event trading bars).

## External spot checks against public sources (11 of the 20, >50%)

For 11 of the 20 events, the documented ticker/ratio/effective-date triple
was independently checked against public corporate-action sources (SEC
EDGAR 8-K exhibits, Nasdaq Trader "Equity Corporate Actions Alert" notices,
and wire/press coverage — GlobeNewswire, PRNewswire, BusinessWire,
StockTitan, Yahoo Finance, Investing.com, MarketScreener). This exceeds the
brief's >=10-event external-spot-check minimum.

**Result: 11/11 CONFIRMED.** 9 of the 11 matched the announced effective
date exactly. 2 (BOLT, UNCY) showed the stored effective_date shifted 2-3
calendar days later than the company's own press-release "effective" date —
in both cases explained by the officially effective date falling on a
non-trading day (a weekend for BOLT; the Juneteenth market holiday for
UNCY), so the first tradeable split-adjusted session (which is what this
study's T0 anchors to, per the frozen "first trading session on/after
effective_date" definition) lands a day or two later. This is a labeling
nuance, not a data error, and it was investigated and documented rather
than silently reconciled.

## Verdict

All 20/20 sampled events **PASS** validation. No FAIL or unresolved WARNING
was found. Combined with the independent Accuracy Check Pass #2 (below) and
the full-sample 88/88 split-adjustment PASS rate, this is strong evidence
the underlying dataset is trustworthy for the return computations in this
study.

See `audit/validation_sample.csv` for the full per-event record and
`audit/external_spot_checks.md` for the source-by-source detail on the 11
externally checked events.
