# Post-Reverse-Split Price Momentum in U.S. Micro-Cap Equities: An Event-Study Analysis of 88 Reverse Stock Splits, 2024–2025

**Author:** Iftekhar Dinar
**Affiliation:** Data Analytics & Finance (B.S.), Missouri State University
**Study designation:** Study A — Reverse Split Momentum
**Date completed:** September 2026
**Status:** Exploratory event study; Publication Gate = PASS (see Section 8)

---

## Abstract

Reverse stock splits are frequently associated in financial media and retail-trading discourse with short-term speculative price momentum, on the theory that a mechanically reduced share count and higher nominal price can attract algorithmic or retail attention. This study tests that hypothesis directly using a reproducible, non-outcome-based event-study design. We draw a stratified random sample of 88 reverse-split events (84 distinct issuers) from all eligible U.S. exchange-listed reverse stock splits effective between January 1, 2024 and December 31, 2025, and measure raw, market-adjusted (vs. SPY and IWM), and same-universe-adjusted returns from the split's effective date (T0) through 60 trading days later (T+60). Contrary to the "reverse-split momentum" narrative, we find that median cumulative returns are negative at every measured horizon and grow monotonically more negative with time: −3.6% at T0, −8.7% at T+5, −10.2% at T+30, and −24.8% at T+60. The T+60 underperformance is statistically distinguishable from zero (mean −22.4%, 95% CI [−30.7%, −14.1%]) and survives winsorization and a first-event-per-company robustness check. Only 11.4% of events showed positive-return continuation over the first week, and none of the 88 events met this study's frozen definition of "extreme momentum." We interpret these results as evidence that, in this sample and window, reverse splits among predominantly sub-$1 pre-split micro-caps function as a lagging indicator of continued fundamental deterioration rather than a catalyst for speculative appreciation. All data, sampling, and validation code are documented for reproducibility, and two independent accuracy-verification passes (a manual review of 22.7% of the sample and an independently coded recomputation of core return metrics) returned zero discrepancies.

**Keywords:** reverse stock split, price momentum, micro-cap equities, event study, Nasdaq listing compliance, market microstructure, mean reversion

---

## Table of Contents

1. Introduction
2. Institutional Background and Related Literature
3. Data Sources
4. Sample Construction and Selection Methodology
5. Variable Definitions and Methodology
6. Results
7. Robustness Checks
8. Data Quality, Validation, and the Publication Gate
9. Discussion
10. Limitations
11. Conclusion
References and Data Sources
Appendix A: Full Statistical Tables
Appendix B: Figure Index

---

## 1. Introduction

A reverse stock split ("reverse split") is a corporate action in which a company reduces its number of outstanding shares by a fixed ratio (e.g., 1-for-10) while proportionally increasing the per-share price, leaving the aggregate market value of equity mechanically unchanged at the moment of the action. In U.S. equity markets, the overwhelming majority of reverse splits are undertaken defensively: a company trading below an exchange's minimum bid-price requirement (commonly $1.00 on Nasdaq) executes a reverse split to regain or maintain listing compliance, rather than as a signal of improving fundamentals (Nasdaq Listing Rule 5550(a)(2); see also the corporate-action notices cited in Appendix B of this study's source data).

Despite this well-documented defensive motivation, a persistent narrative in retail-trading and financial-media discourse holds that reverse splits can trigger short-term speculative "pops" — the theory being that a higher nominal share price and reduced float can attract short-covering, options-market-maker hedging flows, or algorithmic momentum strategies that key off round-number price thresholds. This study was designed to test that narrative empirically and directly, using a transparent, pre-registered, non-outcome-based methodology, rather than to confirm it.

We construct a stratified random sample of 88 reverse-split events across 84 distinct U.S.-listed companies, effective between January 1, 2024 and December 31, 2025, and measure price behavior from the split's effective date through 60 trading days later along three dimensions: (i) raw split-adjusted returns, (ii) returns net of two broad-market benchmarks (SPY and IWM), and (iii) returns net of a same-sample equal-weighted "universe basket" as a best-effort, explicitly labeled substitute for a full matched-control group. We report median returns as the mandatory primary statistic (per this study's own pre-registered methodology) alongside means, confidence intervals, and distributional detail, because reverse-split return distributions are, as shown below, strongly right-skewed by a small number of extreme single-event outcomes, making the mean an unreliable summary on its own.

## 2. Institutional Background and Related Literature

The mechanical mathematics of a reverse split are well understood and non-controversial: a 1-for-N reverse split multiplies the pre-split share price by N and divides share count by N, with no change to firm value, assuming frictionless markets and no simultaneous corporate action. The empirical finance literature on reverse splits, going back to Woolridge and Chambers (1983) and reprised in numerous subsequent studies of the "reverse split penalty," has generally found that reverse splits are associated with negative abnormal returns in the months and years following the event — the opposite of the "momentum pop" narrative — largely because the decision to reverse-split is itself endogenous to already-poor fundamentals (a company trading below $1 is, by construction, one the market has already substantially devalued).

This study's own results below are broadly consistent with that literature's negative-drift finding, while extending it with a modern (2024–2025) sample, a shorter and more granular event window (T0 through T+60 trading days, rather than multi-year windows), and three parallel return-adjustment methodologies (raw, market-adjusted, and universe-adjusted) so that the reader can see how much of the effect survives after controlling for the fact that a basket of "already-reverse-split" stocks is itself likely a below-market-beta, high-idiosyncratic-risk universe.

## 3. Data Sources

- **Corporate-action identification (ticker, ratio, effective date):** sourced from the study's original 2024–2025 reverse-split universe compilation (documented separately in this project's Phase 0 research design and sample-construction logs).
- **Daily price and volume data:** Polygon.io's stock aggregates API, retrieved with both `adjusted=true` (split-adjusted) and `adjusted=false` (raw/unadjusted) parameters for every event, per this study's governing rule that both series must be retained and never conflated.
- **Benchmark data:** SPY (S&P 500 ETF) and IWM (Russell 2000 ETF) daily adjusted closes from Polygon.io, covering the full study window plus padding.
- **External corporate-action verification:** SEC EDGAR 8-K exhibits, Nasdaq Trader "Equity Corporate Actions Alert" notices, and wire/press coverage (GlobeNewswire, PRNewswire, BusinessWire, StockTitan, Yahoo Finance, Investing.com, MarketScreener), used in Validation Pass #1 (Section 8).

A material data-provider limitation was discovered and corrected during this study: Polygon.io's plan tier enforces a rolling historical-depth floor of approximately two years before the fetch date (empirically pinned at 2024-09-19 during this project's data-collection window), which manifests not only as an outright HTTP 403 error for entirely out-of-range requests, but — more dangerously — as an HTTP 200 "success" response with silently truncated data for windows that only partially precede the floor. This was caught by inspecting actual returned bar-date ranges rather than trusting HTTP status codes alone, and it drove a full re-derivation of this study's data-completeness check (Section 8) and two rounds of non-outcome-based sample replacement (Section 4).

## 4. Sample Construction and Selection Methodology

**Eligibility universe:** all U.S. exchange-listed common-stock reverse stock splits with a documented effective date between 2024-01-01 and 2025-12-31.

**Sampling procedure:** a reproducible stratified random sample was drawn from the eligible universe, stratified jointly by (effective-date year) x (reverse-split ratio bucket: 1-for-2 to 1-for-5, 1-for-6 to 1-for-10, 1-for-11 to 1-for-20, 1-for-21 to 1-for-50, greater than 1-for-50), using a fixed master random seed (20260919) so the draw is exactly reproducible. Target sample size was ~100 events with an acceptable range of 75–150 and a minimum of 75 distinct companies.

**Non-outcome-based replacement discipline:** during data collection, 18 initially selected events returned HTTP 403 (entirely outside Polygon's historical-depth floor) and were excluded and replaced, within the same (year x ratio bucket) stratum, using seeded random draws restricted to a corrected safe effective-date threshold — a procedure that reads only ticker/date/ratio identifiers and sample-selection metadata, never price or return data, so that no replacement decision could be influenced by how an event's stock subsequently performed. A second and more subtle problem, the silent-truncation issue described in Section 3, required a further two rounds of the identical non-outcome-based exclude-and-replace procedure (41 events excluded and re-drawn in round 2; 3 further anomalous tickers excluded in round 3 and left unreplaced rather than triggering a fourth network round-trip, since the sample was already comfortably within the acceptable range). Every excluded event's exclusion reason and every replacement's provenance is preserved in `data/processed/sample_selection.csv` with a full, non-destructive audit trail — no row was ever deleted.

**Final sample:** N = 88 events, 84 distinct companies (one company, AKAN, appears twice as two genuinely separate reverse-split events on different effective dates — a legitimate repeat-issuer case, not a duplicate, and explicitly addressed in the dependence-robustness check in Section 7).

## 5. Variable Definitions and Methodology

**Event time (T):** T0 is defined as the first trading session on or after the documented effective date, computed from each ticker's own actual observed trading calendar (never assumed from a generic calendar), which correctly absorbs weekends and market holidays; this definition was independently confirmed by 2 of the 11 externally spot-checked events in Section 8, where the officially announced effective date fell on a non-trading day.

**Return series (three, reported in parallel, per this study's pre-registered design):**
- *Raw return*: the event's own split-adjusted-price return over a window, with no benchmark subtraction.
- *Market-adjusted return*: the event's raw return over a window minus the matching benchmark's (SPY or IWM) return over the exact same calendar dates (not trading-day offsets, so that a single-stock trading halt cannot misalign the comparison).
- *Universe-adjusted return*: the event's raw return minus the equal-weighted average return, at the same trading-day offset, of every *other* selected event in the sample. This is an explicitly labeled best-effort substitute for a full nearest-neighbor matched-control group (which would require fetching complete price histories for a separate universe of non-split control stocks — out of scope for this exploratory pass) and is never treated as equivalent to genuine matched-control analysis.

All return calculations use the split-ADJUSTED close series; the raw (unadjusted) series is used only to (a) report actual traded price levels for price-bucket classification and (b) compute raw share volume, since adjusted volume is a share-count fiction rather than a real traded-volume figure.

**Price buckets** (applied to the raw, pre-split T-1 close): <$1, $1–$2, $2–$5, $5–$10, $10–$20, >$20.

**Frozen continuation/reversal definitions** (fixed in `config/definitions.md` before any price data was examined, and not mutually exclusive by design):
- *Extreme momentum*: T0 adjusted return ≥ +50%, OR a same-day high-vs-open proxy ≥ +100% (this intraday leg is a documented proxy for true intraday momentum, since no intraday minute-level data was collected in this reduced-scope study).
- *Momentum continuation*: T0 return > 0 AND T+5 adjusted close ≥ T0 adjusted close.
- *Failed momentum*: T0 return > 0 AND T+5 adjusted close < T0 adjusted open.
- *Reversal*: T0 return < 0 (relative to T-1).

**Run-up / drawdown:** the maximum and minimum cumulative adjusted return from the T0 close through T+60, tracked at T+5/10/20/30/60, with boolean flags for whether each of six pre-registered thresholds (+10%, +20%, +50%, +100%, −10%, −20%, −50%) was ever crossed within the window.

**Volume:** the ratio of mean raw daily volume over T0..T+5 to mean raw daily volume over T-10..T-1.

**Volatility:** the population standard deviation of daily adjusted-close returns, compared over T-30..T-1 ("pre") versus T0..T+30 ("post").

## 6. Results

### 6.1 Headline return path

Table 1 (full detail in Appendix A / `results/tables/statistics_full_sample.csv`) reports the full statistical profile of the raw return series at every horizon. Figure 1 plots the median cumulative return path with its interquartile band.

**Table 1 — Raw Return Summary Statistics (N=88)**

| Horizon | Mean | Median | SD | 95% CI (mean) | % Positive |
|---|---:|---:|---:|---:|---:|
| T0 (day of split) | −1.97% | **−3.56%** | 16.02% | [−5.37%, 1.42%] | 43.2% |
| T+1 | −1.77% | **−5.54%** | 16.59% | [−5.28%, 1.75%] | 35.2% |
| T+5 | −6.69% | **−8.70%** | 22.76% | [−11.52%, −1.87%] | 35.2% |
| T+10 | −5.60% | **−7.66%** | 30.84% | [−12.14%, 0.93%] | 31.8% |
| T+20 | −3.94% | **−8.79%** | 42.05% | [−12.85%, 4.97%] | 37.5% |
| T+30 | −7.44% | **−10.23%** | 50.57% | [−18.16%, 3.27%] | 31.8% |
| T+60 | −22.43% | **−24.79%** | 39.18% | [−30.74%, −14.13%] | 22.7% |

Every horizon's median return is negative, and the median deteriorates roughly monotonically from T0 through T+60. By T+60, fewer than one in four sampled events (22.7%) shows a positive return, and the mean's 95% confidence interval excludes zero — the underperformance at this horizon is not attributable to sampling noise alone. At shorter horizons (T+10, T+20, T+30) the mean's confidence interval technically spans zero, driven by a small number of extreme positive outliers (maximum single-event return at T+30 was +327.8%); the median, which is far more robust to this skew, remains clearly and consistently negative at every horizon, which is precisely why this study's own methodology mandates median reporting rather than mean-only reporting.

### 6.2 Market- and universe-adjusted returns

Figure 2 compares median raw, market-adjusted, and universe-adjusted returns side by side. Market-adjusted medians (net of SPY/IWM) are, if anything, slightly more negative than raw medians at most horizons (e.g., T+30 vs-SPY median = −13.15%, vs-IWM median = −11.70%, versus a raw median of −10.23%), confirming the underperformance is not simply a reflection of a weak broad market over this window. Universe-adjusted medians (net of the same-sample basket) are considerably smaller in magnitude (e.g., T+30 universe-adjusted median = −2.82%) — as expected, since the "universe" itself is composed entirely of other reverse-split stocks that are, on average, also underperforming; this comparison should be read as "underperformance relative to other recently-reverse-split stocks," not "underperformance relative to the broad market," and the gap between the two adjustment methods is itself informative about how much of the effect is common to the reverse-split universe as a whole versus idiosyncratic to market conditions generally.

### 6.3 Subgroup patterns

**By pre-split price bucket:** 81 of 88 events (92%) traded below $1.00 immediately before the split — confirming that this sample is overwhelmingly a study of defensive, listing-compliance-driven splits rather than higher-priced, discretionary ones. The small number of higher-priced-bucket events (7 total) is too sparse to support a separate reliable comparison (Table, Appendix A / `statistics_by_price_bucket.csv`).

**By reverse-split ratio severity:** median T+30 returns vary non-monotonically across ratio buckets (Figure 4): the 1-for-6-to-1-for-10 bucket (n=25) shows a positive median of +20.7% at T+30, in contrast to every other bucket, which is negative (1-for-2-to-5, n=9: −17.6%; 1-for-11-to-20, n=21: −10.8%; 1-for-21-to-50, n=22: −33.2%; greater-than-1-for-50, n=11: −20.6%). Given the modest per-bucket sample sizes, this divergence should be treated as a descriptive pattern worth further study rather than a confirmed effect — a t-test or bootstrap comparison across buckets was outside this exploratory pass's scope, but the raw event-level data in `data/processed/reverse_split_research_matrix.csv` supports that follow-up directly.

**By year:** 2024 events (n=33) show a more severe T+60 median decline (−38.7%) than 2025 events (n=55, −20.1%), while 2025 events show somewhat worse T+10–T+30 medians than 2024 (Table, Appendix A / `statistics_by_year.csv`). This may reflect differing market regimes across the two years or simply sampling variation within a modest per-year N; it is reported transparently rather than smoothed over.

### 6.4 Momentum/reversal classification

Of the 88 events (Figure 7): **0 (0.0%)** met the frozen "extreme momentum" threshold; **10 (11.4%)** showed "momentum continuation" (a positive T0 day followed by a higher T+5 close); and **50 (56.8%)** were classified as a "reversal" (a negative T0-day return). No event in this sample produced the explosive, sustained upward move that the "reverse-split pump" narrative predicts.

### 6.5 Volume and volatility

Post-event mean daily raw volume was, on median, meaningfully elevated relative to the pre-event window (Figure 8) — consistent with a genuine increase in trading attention around the event — even though that attention did not translate into sustained positive price momentum. Post-event return volatility was also elevated relative to pre-event volatility for the large majority of events (Figure 9), indicating that reverse splits are followed by a more turbulent, not calmer, trading regime, at least over the following month.

## 7. Robustness Checks

**Winsorization (5th/95th percentile):** trimming the influence of extreme single-event outcomes tightens the T+30 mean to −10.79% (95% CI [−18.17%, −3.42%], now excluding zero) and the T+60 mean to −23.75% (95% CI [−31.00%, −16.51%]) without moving the medians at all (T+30 median unchanged at −10.23%; T+60 median unchanged at −24.79%) — demonstrating that the negative-drift finding is not an artifact of a handful of extreme blow-ups, and that once those extremes are capped, even the mean-based confidence intervals confirm the same conclusion the medians already supported.

**First-event-per-company subset (dependence robustness):** restricting to each company's earliest event only (N=84, dropping AKAN's second event) leaves the core finding intact: T0 median −3.34% (vs. −3.56% full sample), T+30 median −9.58% (vs. −10.23%), T+60 median −22.38% with a 95% mean CI of [−28.45%, −11.74%] that still excludes zero. The one repeat issuer in this sample is not driving the result.

**Independent Accuracy Check Pass #2:** a completely separately coded recomputation of T0, T+10, T+30, and T+60 returns — reading the underlying price panel with a different parsing method and no shared helper functions — reproduced the primary computation's values to within numerical rounding (tolerance 1e-6) for all 88 events with **zero mismatches** (`audit/accuracy_check_pass_2.csv`).

## 8. Data Quality, Validation, and the Publication Gate

This study applies a two-pass validation discipline plus an independent accuracy check, summarized here and detailed in the `audit/` directory.

1. **Split-adjustment factor validation** (`audit/split_adjustment_validation.csv`): a return-independent test comparing the ratio of Polygon's adjustment factor immediately before versus immediately after each event's effective date against the documented reverse-split ratio. Result: **88/88 PASS**, 0 WARNING, 0 FAIL, with a mean and maximum factor discrepancy of 0.0%.
2. **Data completeness** (`audit/data_completeness_round2.csv`): every event has at least 28 pre-event and 58 post-event trading bars. Result: **88/88 complete**.
3. **Validation Pass #1** (manual review, `audit/validation_pass_1.md` and `audit/validation_sample.csv`): a reproducibly-drawn stratified sample of 20/88 events (22.7%, exceeding the 20%/20-event minimum) was checked for internal consistency (ratio-bucket assignment, split-adjustment result, completeness result) — **20/20 PASS**. Eleven of the twenty (55%, exceeding the ≥10-event external-check minimum) were further verified against public sources outside this study's own dataset — SEC EDGAR 8-K exhibits, Nasdaq Trader corporate-action alerts, and wire/press coverage — and all 11 were **CONFIRMED** (`audit/external_spot_checks.md`). Two of the eleven showed a 2–3 calendar-day gap between the press-release "effective date" and this study's stored date; both were investigated and fully explained by the officially announced effective date falling on a non-trading day (a weekend for one event, the Juneteenth market holiday for the other), which is exactly consistent with this study's own T0 definition rather than a data error.
4. **Accuracy Check Pass #2:** see Section 7 — 0 mismatches across 88 events x 4 core metrics via an independently coded calculation path.

**CORE/ENRICHED tiering:** every one of the 88 events in the final sample cleared all of the above checks and is classified CORE tier. No event was retained on weaker (ENRICHED-tier) evidence; every event that could not clear the CORE bar during data collection was excluded and non-outcome-based-replaced instead (Section 4).

**Publication Gate: PASS.** Sample size (88, within the pre-registered 75–150 acceptable range), distinct-company count (84, above the 75 minimum), both validation passes, the independent accuracy check, and mandatory median reporting are all satisfied. See `audit/publication_gate.md` for the full gate checklist.

## 9. Discussion

The results of this study run directly counter to the "reverse-split momentum pop" narrative. Rather than serving as a catalyst for speculative appreciation, a reverse split in this sample is followed by continued, and generally worsening, price decline over the subsequent quarter of trading. This is consistent with the interpretation that a reverse split is, in the overwhelming majority of cases in this 2024–2025 sample (92% of events were sub-$1 pre-split), a defensive act taken by an already-distressed micro-cap to preserve its exchange listing, and that the underlying fundamental deterioration that necessitated the split in the first place continues to weigh on the stock afterward. The elevated post-event volume and volatility documented in Section 6.5 suggest genuine incremental trading interest around these events — so the "attention" component of the popular narrative is not entirely absent — but that attention appears, in this sample, to have been net-selling rather than net-buying pressure.

The non-monotonic pattern across ratio-severity buckets (Section 6.3) — where the moderate 1-for-6-to-1-for-10 bucket outperformed both milder and more severe buckets — is a genuinely interesting descriptive finding that this exploratory pass is not powered to explain, and it is flagged here explicitly as a candidate for follow-up research with a larger, ratio-bucket-targeted sample.

## 10. Limitations

This study is explicitly exploratory and observational, and several limitations should guide how its results are read:

- **Sample size and window.** N=88 events over a single two-year window (2024–2025) is a modest sample for subgroup analysis, and results may not generalize to other market regimes or time periods.
- **No true matched-control group.** The "universe-adjusted" return series is a same-sample equal-weighted-basket substitute, not a genuine nearest-neighbor matched-control benchmark constructed from non-split comparison firms; it is reported and labeled as such throughout, and should not be read as equivalent to a proper matched-control event study.
- **Intraday "extreme momentum" proxy.** No intraday minute-level price data was collected in this reduced-scope study; the "extreme momentum" definition's intraday leg uses a same-day high-vs-open ratio from daily bars as a documented proxy, which likely understates true intraday volatility around these events.
- **Selection is not causal identification.** This is an observational event study of realized reverse splits; it does not and cannot establish that the reverse split itself causes the subsequent underperformance, as opposed to reflecting the same underlying distress that triggered the split in the first place. No claim of a tradable strategy or causal mechanism is made.
- **Repeat issuers and stratum overlap.** One company (AKAN) contributes two events; while the dependence-robustness check in Section 7 shows this does not drive the headline result, formal cluster-robust or bootstrap standard errors accounting for issuer-level dependence were judged unnecessary given this single instance, but would be advisable in a larger future sample with more repeat issuers.
- **Data-provider constraints.** All price data derives from a single provider (Polygon.io); the provider's rolling historical-depth floor (Section 3) required non-outcome-based sample correction in three rounds, and while every correction is fully documented and none was outcome-based, a reader should be aware the final sample's composition was shaped by this data-access constraint, not solely by the original eligibility screen.

## 11. Conclusion

Using a reproducible, non-outcome-based stratified sample of 88 U.S.-listed reverse stock splits effective in 2024–2025, this study finds no evidence of the popularly discussed "reverse-split momentum" effect. Instead, median returns are negative at every horizon from the split's effective date through 60 trading days later, worsening from −3.6% at T0 to −24.8% at T+60, a result that is robust to winsorization, to a first-event-per-company dependence check, and to an independently coded accuracy-verification pass. Elevated post-event trading volume and volatility indicate genuine market attention around these events, but that attention is associated with continued price deterioration rather than the speculative appreciation the narrative predicts. These findings are consistent with reverse splits functioning, in this sample, primarily as a defensive listing-compliance mechanism for already-distressed micro-cap issuers rather than as a bullish catalyst.

---

## References and Data Sources

- Polygon.io Stock Aggregates API (daily OHLCV, adjusted and unadjusted), accessed 2026.
- SEC EDGAR full-text filing system (8-K exhibits), sec.gov/edgar.
- Nasdaq Trader Equity Corporate Actions Alerts, nasdaqtrader.com.
- Woolridge, J. R., and Chambers, D. R. (1983). "Reverse Splits and Shareholder Wealth." *Financial Management*, 12(3).
- Nasdaq Listing Rule 5550(a)(2) — minimum bid price requirement.
- Wire/press sources cited per-event in `audit/external_spot_checks.md` (GlobeNewswire, PRNewswire, BusinessWire, StockTitan, Yahoo Finance, Investing.com, MarketScreener).

## Appendix A: Full Statistical Tables

Full machine-readable tables underlying every figure and headline number in this report are in `results/tables/`:
`statistics_full_sample.csv`, `statistics_winsorized.csv`, `statistics_first_event_per_company.csv`, `statistics_by_ratio_bucket.csv`, `statistics_by_year.csv`, `statistics_by_price_bucket.csv`.

## Appendix B: Figure Index

All figures are in `results/figures/publication/`:

1. `fig01_median_car_path.png` — Median cumulative return path, T0–T+60, with interquartile band.
2. `fig02_median_return_by_series.png` — Median return by horizon: raw vs. market-adjusted vs. universe-adjusted.
3. `fig03_t30_return_histogram.png` — Distribution of T+30 raw returns.
4. `fig04_median_return_by_ratio_bucket.png` — Median T+30 return by reverse-split ratio bucket.
5. `fig05_median_return_by_price_bucket.png` — Median T+30 return by pre-split price bucket.
6. `fig06_median_return_by_year.png` — Median return by horizon, split by selection year.
7. `fig07_classification_counts.png` — Frequency of frozen momentum/reversal classifications.
8. `fig08_volume_ratio_histogram.png` — Post/pre event volume ratio distribution.
9. `fig09_volatility_scatter.png` — Pre- vs. post-event volatility scatter.
10. `fig10_runup_vs_drawdown_scatter.png` — Max run-up vs. max drawdown per event.
11. `fig11_threshold_crossing_frequency.png` — Share of events crossing pre-registered return thresholds.
12. `fig12_sample_composition.png` — Final sample composition by year and ratio bucket.
