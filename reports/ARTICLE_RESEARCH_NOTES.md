# Article Research Notes / Talking Points (backup reference, not for publication)

## One-line finding
Reverse splits in this 2024-2025 sample are followed by WORSENING negative
median returns through T+60 (-3.6% -> -24.8%), the opposite of the
"momentum pop" retail narrative -- and the finding is robust to outlier
trimming and to dropping the one repeat issuer.

## Key numbers to have on hand for questions/comments
- N = 88 events, 84 unique companies, 2024-01-01 to 2025-12-31 window.
- Median return: T0 -3.6%, T+1 -5.5%, T+5 -8.7%, T+10 -7.7%, T+20 -8.8%,
  T+30 -10.2%, T+60 -24.8%.
- T+60 mean = -22.4%, 95% CI [-30.7%, -14.1%] -- excludes zero.
- Winsorized T+30 mean CI [-18.2%, -3.4%]; T+60 mean CI [-31.0%, -16.5%] --
  both exclude zero after trimming outliers.
- First-event-per-company (N=84, drops AKAN's 2nd event): T+60 median
  -22.4%, CI [-28.5%, -11.7%] -- same conclusion holds.
- 0/88 events met the "extreme momentum" threshold (T0 return >=+50% or
  intraday high/open proxy >=+100%).
- 10/88 (11.4%) showed "momentum continuation"; 50/88 (56.8%) were same-day
  "reversals."
- 92% (81/88) of events were sub-$1 pre-split -- overwhelmingly defensive,
  Nasdaq-Rule-5550(a)(2)-compliance-driven splits, not discretionary ones.
- Post-event volume and volatility both rise vs. pre-event on median.
- Non-monotonic ratio-bucket pattern: the 1-for-6-to-1-for-10 bucket (n=25)
  shows a POSITIVE median T+30 return (+20.7%), unlike every other bucket
  -- flagged as a follow-up research question, not a confirmed effect
  (modest per-bucket N).

## Data quality talking points (if asked "how do you know this is right?")
- Split-adjustment factor validated via a return-independent mechanical
  test: 88/88 PASS, 0% average discrepancy from documented ratios.
- Data completeness: 88/88 events have full pre/post trading windows.
- Independent Accuracy Check Pass #2 (separately coded from scratch):
  0 mismatches across 88 events x 4 metrics.
- Validation Pass #1: 20/88 events (22.7%) manually reviewed, all PASS;
  11 of those cross-checked against SEC EDGAR / Nasdaq corporate-action
  alerts / press coverage, all CONFIRMED.
- Sample selection was non-outcome-based throughout: every exclusion and
  replacement during data collection was decided from ticker/date/ratio
  identifiers only, never from price or return data -- full audit trail
  preserved, nothing deleted.

## Honest limitations to mention if pressed
- Observational, not causal: a reverse split doesn't "cause" the decline
  so much as co-occur with the same distress that made it necessary.
- "Universe-adjusted" return is a same-sample basket proxy, not a true
  matched-control group.
- No intraday minute data; "extreme momentum" intraday leg is a daily-bar
  proxy.
- N=88 over one two-year window -- modest for subgroup claims (e.g. the
  ratio-bucket pattern above).

## Source documents for anyone who wants to dig in
- reports/Reverse_Split_Momentum_Study_FINAL.md (full academic report)
- results/tables/*.csv (all statistics)
- results/figures/publication/*.png (12 figures)
- audit/*.md and audit/*.csv (validation, accuracy check, publication gate)
- RESEARCH_LOG.md (full decision history)
