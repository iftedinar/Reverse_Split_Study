# Do Reverse Stock Splits Trigger Momentum, or Mask Decline? Evidence from 88 Events (2024–2025)

*An applied event-study note by Iftekhar Dinar, Data Analytics & Finance, Missouri State University*

## Abstract

Retail-trading discourse often treats a reverse stock split as a potential catalyst for a short-term speculative "pop" — the theory being that a mechanically higher share price and reduced float can attract momentum-driven trading flow. This note reports the results of a reproducible event study designed to test that hypothesis directly. Using a stratified random sample of 88 U.S.-listed reverse-split events (84 distinct companies) effective between January 2024 and December 2025, I measure raw, market-adjusted, and same-universe-adjusted returns from each split's effective date (T0) through 60 trading days later. The evidence points the opposite direction from the popular narrative: median returns are negative at every horizon and worsen over time — from −3.6% at T0 to −24.8% by T+60 — a pattern that survives outlier-robust (winsorized) and repeat-issuer-robust checks. None of the 88 events met a pre-registered "extreme momentum" threshold. The results are consistent with reverse splits functioning, in this sample, as a lagging marker of continued fundamental deterioration in already-distressed micro-cap issuers, rather than as a bullish catalyst.

## 1. Motivation

Nasdaq's minimum bid-price rule (Rule 5550(a)(2)) requires common stock to trade at or above $1.00 to maintain listing; a stock that falls below this threshold for an extended period faces delisting unless it regains compliance, most commonly via a reverse split. That mechanical, largely defensive motivation is well understood. What is less settled — and what circulates persistently in retail-investor communities — is whether the *market's reaction* to a reverse split tends toward short-term appreciation (a "squeeze" or "pop" thesis) or continued decline. This note tests that question with data rather than anecdote.

## 2. Data and Method

The sample is a stratified random draw (fixed seed, stratified by year and reverse-split-ratio bucket) from all eligible U.S. exchange-listed reverse splits effective in 2024–2025, using daily adjusted and unadjusted price data from Polygon.io plus SPY/IWM benchmark data. Eligibility, selection, and every replacement of an excluded event were determined strictly from identifiers (ticker, date, ratio) — never from subsequent price or return data — to rule out outcome-based cherry-picking. The final sample comprises 88 events across 84 companies, all of which passed (a) a return-independent test that Polygon's mechanical split-adjustment factor matches the documented ratio (88/88 clean), and (b) a data-completeness check requiring sufficient pre- and post-event trading history (88/88 complete). An independently coded recomputation of core return metrics matched the primary results exactly (zero discrepancies across 88 events), and a manually reviewed 22.7% subsample — including 11 events cross-checked against SEC filings, Nasdaq corporate-action alerts, and press coverage — confirmed the underlying event data.

Three return series are reported in parallel: raw split-adjusted return; return net of the matching broad-market benchmark (SPY/IWM, matched by calendar date); and return net of an equal-weighted basket of the other sampled reverse-split events, as an explicitly labeled, best-effort substitute for a true matched-control group.

## 3. Findings

**Returns worsen, they don't pop.** Median cumulative raw return is −3.6% on the split's effective date, −8.7% after one week, −10.2% after 30 trading days, and −24.8% after 60 trading days. By T+60, only 22.7% of events show a positive return, and the 95% confidence interval for the mean return excludes zero. Market-adjustment (netting out SPY/IWM) does not explain this away — adjusted medians are, if anything, slightly more negative.

**No extreme-momentum events.** Under a pre-registered definition (a same-day return of at least +50%, or an intraday proxy of at least +100%), zero of the 88 events qualified as "extreme momentum." Only 11.4% showed even a modest one-week continuation pattern; 56.8% were outright same-day reversals.

**The effect is robust, not outlier-driven.** Winsorizing the most extreme 5% of observations at each tail tightens the confidence intervals (they now exclude zero at every mid-to-long horizon) without moving the medians at all. Restricting to each company's first reverse split only (removing one repeat issuer) leaves the same pattern intact.

**Attention rises; buying doesn't.** Trading volume and return volatility both increase, on median, in the month following the event — genuine market attention is present — but that attention correlates with continued selling pressure rather than accumulation, at least in this sample.

## 4. Interpretation and Limits

Ninety-two percent of the sampled events involved stocks trading below $1.00 immediately before the split — this is overwhelmingly a sample of defensive, compliance-driven reverse splits rather than discretionary ones, and the results should be read in that light. The study is observational: it documents an empirical pattern, not a causal mechanism, and a reverse split does not cause underperformance so much as it co-occurs with, and likely follows from, the same fundamental weakness that made the split necessary in the first place. The sample size (N=88, one two-year window) and the use of a same-universe proxy rather than a true matched-control group are limitations that a larger, multi-window follow-up study could address. One descriptive pattern worth flagging for further work: median T+30 returns are not monotonic in reverse-split severity — the moderate 1-for-6-to-1-for-10 bucket (n=25) actually shows a positive median, in contrast to both milder and more severe ratio buckets — a result plausibly worth a dedicated, larger-sample follow-up.

## 5. Conclusion

In this reproducible, non-outcome-based sample of 88 reverse stock splits, the popular "reverse-split momentum" thesis does not hold up: prices decline, on median, at every horizon tested, and the decline deepens over the following quarter of trading. For traders and researchers evaluating reverse splits as a potential signal, this evidence argues for treating them as a marker of continued risk rather than an opportunity signal — at least in the 2024–2025 micro-cap segment studied here.

*Full methodology, validation logs, statistical tables, and figures are available on request. All code and data-provenance documentation follow a fully reproducible, pre-registered, non-outcome-based design.*
