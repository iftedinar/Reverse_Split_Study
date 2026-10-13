# Price-Adjustment Convention Validation

**Prepared:** 2026-09-19
**Purpose:** mandated by the project brief's CRITICAL price-adjustment rule ("DO NOT interpret the mechanical split adjustment as an investment return... maintain both RAW/unadjusted and split-adjusted prices... document each provider's adjustment convention... test manually on selected events"). This document records the live testing done on every price-data source available to this session before any was used to build the study's price panel.

## 1. Sources tested, for the 100 selected events

| Source | Tool | Result | Verdict |
|---|---|---|---|
| FMP | `mcp__FMP__chart` (`historical-price-eod-full`, `historical-price-eod-non-split-adjusted`) | Works for large-caps (AAPL confirmed), but returns `ACCESS DENIED — requires a higher plan` for every small/micro-cap reverse-split candidate tested (KTTA, CNEY), regardless of date range. This is a plan-tier restriction on the underlying ticker universe, not a rate limit. | **Not usable** — the study's population is almost entirely micro-caps, which is exactly the segment this plan tier excludes. |
| Alpha Vantage | `TIME_SERIES_DAILY_ADJUSTED`, `TIME_SERIES_DAILY` | Both return `premium endpoint` / `outputsize=full is a premium feature` errors regardless of ticker. `outputsize=compact` is allowed but only returns the last 100 trading days from today (Sept 2026), which does not reach back to any 2024-2025 event window. | **Not usable** for historical data at this plan tier. |
| Stocklake | `get_stock_history` | Returns `history_not_found` for KTTA (and, by extension, likely for other thinly-covered micro-caps). | **Not usable** as a sole source — coverage gaps on exactly the ticker population this study needs. |
| Webull | `get_stock_bars` | Works, with good coverage of micro-caps and OTC-adjacent names. Confirmed via direct testing (see §2) that it returns a **continuously split-adjusted** series — i.e., historical bars are adjusted for every subsequent stock split up to today's date, not only for the studied event. | **Usable with caveats** (see §3) — good for computing within-window returns, NOT a source of true raw/as-traded prices. |

## 2. Manual adjustment-convention tests performed

**Test A — LICN, 1-for-200 reverse split, effective 2025-03-03.** Fetched
daily bars for 2025-02-10 through 2025-03-19. If the series were raw
(unadjusted), price should jump roughly 200x higher on 2025-03-03. It does
not: the close glides continuously from $15.20 (2025-02-10) down to $5.80
(2025-03-03) to $4.05 (2025-03-19), with no discontinuity at the effective
date. **Conclusion: Webull's `get_stock_bars` returns a split-adjusted,
continuous series, not raw as-traded prices.**

**Test B — CISS, reverse split effective 2024-04-12.** Fetched daily bars
spanning 2024-02-20 through 2024-07-15. Prices in this window range from
roughly $93,000 to over $1,000,000 per share — not a plausible traded
price for a NASDAQ common stock at any point. This indicates CISS
underwent one or more **additional** reverse splits after its 2024-04-12
study event and before today (2026-09-19), and Webull's continuous series
retroactively adjusts historical bars for those **later** splits too, not
only for the split being studied. **Conclusion: Webull's adjustment is
"as of today," not "as of the studied event," and stacks every
subsequent corporate action into the historical series.**

## 3. Implication for this study's methodology

A "continuously adjusted as of today" series is mathematically safe for
computing a **return** strictly within one ticker's own T-30..T+60 event
window: any later (post-window) corporate action multiplies every bar in
that window by the same constant factor, which cancels out of a
price(t2)/price(t1) ratio. It is, however, **not safe** to:
- quote it as, or mistake it for, the true raw/as-traded historical price
  (e.g., "the stock traded at $X before the split") — that requires a
  genuinely unadjusted feed;
- compare absolute price *levels* across events, buckets, or against any
  external reference (regulatory halt thresholds, etc.);
- assume no additional corporate action occurred inside the T-30..T+60
  window itself without checking — an in-window split would already be
  correctly reflected by Webull's adjustment, but must still be logged
  per event so it isn't silently conflated with market-driven momentum.

This is exactly the failure mode the project brief's CRITICAL rule warns
against, so this study will **not** rely on Webull's series alone. It
will be used as a secondary/cross-check series once a genuine
raw + point-in-time-adjusted series is obtained from Polygon (already the
project's authoritative source for split and ticker data, with a working
API key, and offering an explicit `adjusted=true/false` toggle).

## 4. Path forward

`src/data_collection/06_fetch_event_prices_polygon.py` (written alongside
this document) fetches, for the 100 selected events only, both
`adjusted=false` (raw/as-traded) and `adjusted=true` daily OHLCV from
Polygon for each event's own T-30..T+60 trading-day window (padded in
calendar days). This is a small, bounded, event-specific operation (100
tickers, one bounded date range each) — not a resumption of the
full-universe ticker-classification backlog, and fully consistent with
the directive's "make additional API calls only when required for a
selected event's completion" instruction. Because `device_bash`'s network
egress is blocked for direct API calls (established earlier in this
project), this script must be run from the researcher's own terminal, as
all prior network-calling scripts have been.

Once raw data is in hand, this document will be updated with: (a) a
side-by-side raw-vs-adjusted comparison for a sample of events spanning
small and large ratios; (b) confirmation that the raw-series price jump
at each event's effective date matches its documented split ratio within
a small tolerance; (c) the final decision on which series feeds the
return calculations (Polygon `adjusted=true`, cross-checked against
Webull, with Polygon raw retained for narrative/validation purposes and
for confirming ratios).
