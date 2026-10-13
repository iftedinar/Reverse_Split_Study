# Study A — Reverse Split Momentum

A point-in-time event study of reverse stock splits and subsequent momentum in U.S. equities.

**Status:** PHASE 0 complete. PHASE 1 (data source reconnaissance) complete and confirms Polygon.io as the primary bulk event-discovery source. Awaiting decisions 17-B/C/D/F before PHASE 2 (full event collection) begins.
Start here: `reports/PHASE_0_RESEARCH_DESIGN.md`.

## What this is

This project studies what historically happens, in price, volume, volatility, float
turnover, halts, and financing/dilution, around reverse stock splits on NASDAQ, NYSE,
and NYSE American. It does not assume reverse splits are bullish, bearish, or
predictive. It is built to be reproducible and auditable, with an explicit eye toward
eventual publication, so look-ahead bias, survivorship bias, and multiple-testing risk
are treated as first-class concerns, not afterthoughts.

This study is independent of the 100Stocks / Trade100 project. Nothing here reads
from or writes to that codebase; it happens to live in the same OneDrive tree.

## Two tracks

- **Track A (human-assisted):** you run scripts, inspect output, and approve
  methodology decisions at each major stage. `reports/RESEARCHER_NOTES_*.md` explains
  each stage in plain language before you run it.
- **Track B (autonomous):** Claude builds and runs everything that does not depend on
  a decision only you can make, or on credentials Claude cannot obtain on your behalf
  (see PHASE_0 §14/§15 for the exact split).

## Directory layout

```
Reverse_Split_Study/
  README.md
  requirements.txt
  RESEARCH_LOG.md          <- every major decision, dated, with rationale
  .env.example             <- copy to .env and fill in your own keys (never commit .env)
  config/
    definitions.md         <- frozen definitions: ratio/price/float buckets, continuation/reversal
  data/
    raw/                   <- immutable as downloaded; never edited by hand
    intermediate/          <- cleaned but not yet feature-engineered
    processed/             <- analysis-ready tables
  src/
    data_collection/       <- 00_test_data_sources.py lives here (Phase 1 task)
    cleaning/
    validation/
    features/
    analysis/
    visualization/
  notebooks/
  results/
    tables/
    figures/
  reports/                 <- PHASE_0 design doc, researcher notes, final report
  audit/                   <- lookahead_bias_audit.md, survivorship_bias_audit.csv, etc.
  tests/
```

## Setup

```
python -m venv .venv
.venv\Scripts\activate        (Windows)  or  source .venv/bin/activate  (macOS/Linux)
pip install -r requirements.txt
copy .env.example .env        (Windows)  or  cp .env.example .env
```

Then fill in `.env` with your own API keys (see PHASE_0 §13 for which ones and why).
