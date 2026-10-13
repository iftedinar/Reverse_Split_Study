# Frozen Definitions — Study A: Reverse Split Momentum

Written 2026-09-18, BEFORE any market data has been collected or examined,
per the study's own anti-data-mining discipline. Any change to a definition
after data has been seen must be logged in `RESEARCH_LOG.md` with a stated
reason, and results under both the old and new definition reported side by
side (sensitivity analysis), not silently replaced.

## Event window

- T = effective trading date of the reverse split (not announcement date,
  not calendar date).
- Daily analysis window: T-30 through T+60 **trading days** (via
  `pandas_market_calendars`, NYSE calendar — never calendar-day arithmetic).
- Intraday analysis window: T-5 through T+10 trading days, subject to
  data-availability scoping (PHASE_0 §17-F).

## Reverse-split ratio buckets

| Bucket | Ratio range |
|---|---|
| 1 | 1-for-2 through 1-for-5 |
| 2 | 1-for-6 through 1-for-10 |
| 3 | 1-for-11 through 1-for-20 |
| 4 | 1-for-21 through 1-for-50 |
| 5 | greater than 1-for-50 |

Exact ratio is also retained as a continuous numeric variable
(`ratio = 1 / split_factor`, e.g. split_factor 0.0333 -> ratio ≈ 30).

## Price buckets (retained continuously as well)

`<$1`, `$1-$2`, `$2-$5`, `$5-$10`, `$10-$20`, `>$20` — applied separately to
pre-split and post-split price.

## Float buckets (retained continuously as well; see FLOAT_DATA_RELIABILITY)

`<5M`, `5M-10M`, `10M-20M`, `20M-50M`, `50M-100M`, `>100M`.

## Float turnover levels (retained continuously as well)

`0.5x`, `1x`, `2x`, `5x`, `10x`, `20x+` (Float Turnover = Trading Volume / Float).

## Continuation vs. reversal — draft definitions (PHASE_0 §17-E, pending approval)

- **Extreme momentum event**: T close return ≥ +50% vs. T-1 close, OR
  intraday max run-up from the open ≥ +100%.
- **Momentum continuation**: T close return > 0 AND T+5 close ≥ T close.
- **Failed momentum**: T close return > 0 BUT T+5 close < T open.
- **Reversal**: T close return < 0 vs. T-1 close.

These four are not mutually exhaustive by design (a stock can be flat and
match none of them) — that is intentional; forcing every event into a bucket
would itself be a form of manufactured signal.

## Sensitivity analysis commitment

Alternative bucket schemes and alternative continuation/reversal definitions
will be tested explicitly (PHASE_0 §"Robustness Testing"). A conclusion that
only holds under one specific definition is reported as such, not presented
as a general finding.
