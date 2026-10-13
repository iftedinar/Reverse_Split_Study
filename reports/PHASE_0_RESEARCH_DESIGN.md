# PHASE 0 — Research Design
## Study A: Reverse Split Momentum

Date: 2026-09-18
Status: **Draft for approval.** Section 17 lists every decision that needs your
sign-off before Track B autonomous work moves past scaffolding into real data
collection.

---

## 1. Proposed architecture

Two parallel, cross-checked tracks feeding one shared, immutable data layer:

```
                    +----------------------+
                    |  Event Discovery      |  (which stocks reverse-split, when, at what ratio)
                    +-----------+----------+
                                |
                    +-----------v----------+
                    |  Point-in-time Enrichment |  (price, volume, float, filings, news, halts)
                    +-----------+----------+
                                |
              +-----------------+-----------------+
              v                                    v
     +------------------+               +-------------------+
     | Validation Pass 1  |               | Control-Group      |
     | (sample audit)     |               | Construction        |
     +------------------+               +-------------------+
              |                                    |
              +-----------------+------------------+
                                v
                     +---------------------+
                     | Feature Engineering   |  (returns, RVOL, turnover, VWAP, gaps, MFE/MAE)
                     +-----------+---------+
                                v
                     +---------------------+
                     | Statistical Analysis  |  (event study, AR/CAR, group tests, regression)
                     +-----------+---------+
                                v
                     +---------------------+
                     | Validation Pass 2     |  (independent recomputation)
                     +-----------+---------+
                                v
                     +---------------------+
                     | Out-of-sample check   |  (chronological holdout)
                     +-----------+---------+
                                v
                          Final Report
```

Every stage writes to `data/raw` (immutable), `data/intermediate`, or
`data/processed` -- never overwriting a prior stage's output in place. Every
transformation is a script in `src/`, runnable independently, so the whole
pipeline can be rebuilt from `data/raw/` alone.

---

## 2. Proposed data sources

I tested what's actually reachable from the connectors available to me right
now, rather than assuming. Results below are from live calls made today, not
documentation.

| Source | What it's for | Status (tested today) |
|---|---|---|
| **Alpha Vantage** | Per-symbol split history, per-symbol daily adjusted OHLCV | **Works.** Confirmed live: `SPLITS` for NKLA returned `{"effective_date":"2024-06-25","split_factor":"0.0333"}` -- i.e. a real, verifiable 1-for-~30 reverse split. Per-symbol only; no bulk/market-wide endpoint. |
| **Financial Modeling Prep (FMP)** | Would-be bulk splits calendar, SEC filings search, symbol directory | **Blocked on the connected account's current plan.** `calendar` (splits-calendar, splits-company), `secFilings`, and `directory` (even `available-exchanges`) all returned plan-upgrade errors today. FMP is effectively unusable for this study unless the account is upgraded to Starter tier or above. |
| **Polygon.io** `/v3/reference/splits` | **Recommended primary source for bulk event discovery** -- a market-wide, ticker-agnostic splits endpoint that returns `execution_date`, `split_from`, `split_to` for every US-listed split, reverse or forward (`split_from > split_to` identifies a reverse split) | Not connected to this session -- no MCP tool for it. Free tier requires a signup (human task, see Phase 1) but does not require a credit card historically for the free tier; rate limits apply. |
| **SEC EDGAR full-text search** (`efts.sec.gov`) + **EDGAR filing index** | Free, public, no signup. Authoritative for announcement/effective dates (8-K Item 3.03/5.03), and later for the dilution/financing analysis (S-1, S-3, 424B, ATM agreements) | Not testable from this session (no outbound HTTP tool wired to it here), but it is a stable, documented public API. Requires a compliant `User-Agent` header (real name + email) -- SEC will block generic ones. |
| **Nasdaq Trader daily halt files** (`nasdaqtrader.com`) | LULD/trading-halt history, published as free daily CSV archives | Not testable from this session; publicly documented, free, no key. |
| **Stocklake** (connected) | Current fundamentals/technicals/screener -- useful for today's float/market-cap as a *reference point*, not historical point-in-time | Works, but explicitly **not** a point-in-time source -- using it for historical float would violate the study's own point-in-time rule. Will only be used for present-day sanity checks. |
| **Webull, Aiera** (connected) | Webull: quotes/fundamentals/filings-adjacent; Aiera: institutional research/transcripts | No dedicated reverse-split or point-in-time float endpoint found in either. Considered secondary/exploratory only. |

**Bottom line:** no connector currently available to me provides a bulk,
market-wide, point-in-time reverse-split calendar. That is the single
biggest open dependency in this design (see section 6, 15, 17-A).

---

## 3. Free vs. paid

| Source | Tier needed | Cost |
|---|---|---|
| Alpha Vantage | Free tier sufficient for per-symbol verification; a paid tier is needed only if extended-history intraday minute bars are pulled from AV specifically (see section 5) | Free / $ for premium |
| Polygon.io | Free tier likely sufficient for splits discovery + EOD daily bars; paid tier ("Stocks Starter" or above) needed for full historical 1-minute intraday coverage across many symbols | Free for discovery; $29-$199+/mo if minute-level intraday at scale is required |
| SEC EDGAR | Free, always | Free |
| Nasdaq Trader halt files | Free, always | Free |
| FMP | Blocked at current tier; would need "Starter" (~$22/mo tier at last public pricing, verify current pricing before paying) to unlock calendar/directory/filings | Optional -- see 17-B |

---

## 4. Exact variables available from each source

- **Alpha Vantage `SPLITS`**: `effective_date`, `split_factor` (decimal; <1 = reverse, e.g. 0.0333 = approx 1-for-30; >1 = forward). No announcement date, no ratio-as-integers, no company metadata.
- **Alpha Vantage `TIME_SERIES_DAILY_ADJUSTED`**: date, open, high, low, close, adjusted close, volume, dividend amount, split coefficient -- per symbol, full history back to listing (free tier, per published docs; to be confirmed empirically in Phase 1).
- **Polygon `/v3/reference/splits`** (per Polygon's public API reference -- to be confirmed once a key is obtained): `ticker`, `execution_date`, `split_from`, `split_to`, `id`. No announcement date or company metadata either -- will need to be joined against a symbol/company reference table.
- **SEC EDGAR full-text search**: filing accession numbers, form type, filing date, company name, CIK -- used to recover **announcement date** (8-K) and to build the dilution/financing timeline later (S-1/S-3/424B/etc.).
- **Nasdaq Trader halt files**: halt date, halt time, resume time, reason code, market -- daily CSV archives.

None of the above provides historical point-in-time **float** or **shares outstanding**. That is flagged explicitly in section 5.

---

## 5. Point-in-time data limitations

This is the most important limitation in the entire design, and the user's
original brief specifically anticipated it.

- **Float / shares outstanding**: no source identified so far (free or on the
  connectors available to me) provides *historical, point-in-time* float.
  Vendors that do (e.g., Sharadar via Nasdaq Data Link, Bloomberg, FactSet)
  are paid and not currently available. Absent a paid point-in-time
  fundamentals feed, every event's `FLOAT_DATA_RELIABILITY` field will be set
  to `LOW`, and float-based conclusions will be presented as directional/
  exploratory only, never as precise. This is a hard constraint, not a
  temporary gap -- flagging it now rather than silently using today's float.
- **Market capitalization**: same issue, one level less severe -- shares
  outstanding changes less frequently than float, and some of it can be
  reconstructed from 10-Q/10-K cover-page share counts on EDGAR (which *are*
  point-in-time and free), at the cost of significant manual/semi-automated
  filing parsing per event.
- **Intraday minute data**: free tiers of both Alpha Vantage and Polygon
  restrict historical intraday depth/coverage. Getting 1-minute bars for
  T-5 through T+10 for every event in a multi-year sample may require a paid
  tier or a scoped-down subsample (see 17-F).
- **News/catalyst timestamps**: free news APIs rarely give the exact
  intraday timestamp of first publication with enough historical depth;
  catalyst classification may end up coarser (date-level, not minute-level)
  for older events.

---

## 6. Estimated number of reverse-split events obtainable

I have not yet run a bulk query (no bulk source is connected here yet --
see section 2), so this is a reasoned order-of-magnitude estimate, not a
measurement, and should be treated as such until Phase 2 produces an actual
count:

- U.S. small-cap reverse splits are common and have been *unusually*
  frequent since 2022, driven heavily by Nasdaq's $1 minimum-bid-price
  listing requirement during a prolonged small-cap/biotech bear market.
- A reasonable planning estimate is on the order of **several hundred to
  roughly a thousand-plus reverse-split events per year** across NASDAQ +
  NYSE American small-caps in 2022-2025, versus a much lower baseline
  (perhaps 100-300/year) in calmer years before that.
- Over a 5-year window (2021-2026): plausibly **1,500-3,500 events**. Over a
  10-year window (2016-2026): plausibly **2,500-5,000+ events**, skewed
  heavily toward the more recent years.
- **This must be replaced with an actual count from Polygon/EDGAR before any
  methodology decision relies on it.** I am flagging the estimate as
  exploratory precisely so it never quietly hardens into a fact.

---

## 7. Data-quality risks

- FMP inaccessible at current tier -- single point of failure if relied upon; mitigated by treating Polygon + EDGAR as primary.
- No bulk point-in-time float/shares source -- see section 5.
- Free-tier rate limits (Alpha Vantage: historically 5 req/min, 25-500 req/day depending on tier) make thousands of per-symbol calls slow; needs disciplined batching/caching in `data/raw/` so nothing is re-fetched.
- OTC-listed reverse splits (common among the smallest names) have materially worse data quality across every source -- per the brief, these are tracked separately, not silently dropped.
- Ticker reuse/collision: small-cap tickers get recycled after delisting; every event must be keyed by CIK (from EDGAR) wherever possible, not ticker alone.
- Multiple-source disagreement on ratio or effective date (e.g., Alpha Vantage vs. Polygon vs. EDGAR 8-K) will be logged, not silently resolved by picking one (per `data_source_registry.csv`, "Reproducibility" section of the original brief).

---

## 8. Proposed statistical methodology

- **Event-study framework**: standard AR/CAR methodology. Actual Return
  minus Expected Return, where Expected Return comes from a market model
  estimated over a pre-event clean window (see benchmark model below).
- **Descriptive statistics**: for every major variable -- N, mean, median,
  SD, 25th/75th percentile, min, max, and a 95% CI on the mean (and on the
  median via bootstrap, since small-cap returns are heavy-tailed and a
  normal-theory CI on the median is inappropriate).
- **Group comparisons**: distributions here are expected to be strongly
  right-skewed with extreme outliers (small-cap gap-up days), so
  **Mann-Whitney U** (two groups) and **Kruskal-Wallis** (3+ groups, e.g.
  ratio buckets) are the primary tests, with Welch's t-test / one-way ANOVA
  reported alongside as a robustness cross-check, not the headline number.
- **Categorical outcomes** (e.g., halt yes/no by ratio bucket): chi-square
  test of independence, or Fisher's exact test where any expected cell count
  is below 5.
- **Multiple testing**: every subgroup cross-tabulation (ratio x float x
  price x market cap, etc.) inflates false-positive risk. Benjamini-Hochberg
  FDR correction will be applied within each pre-specified family of tests,
  and anything found only by looking across many subgroups after the fact is
  labeled `EXPLORATORY` and excluded from the headline findings until
  independently re-tested.
- **Regression**: OLS with HC3 heteroskedasticity-robust standard errors as
  the base case; reported alongside a Huber-robust regression given expected
  outliers. Multicollinearity checked via VIF; influential points via
  Cook's distance. No causal language -- explicitly observational.

---

## 9. Proposed control-group methodology

For each reverse-split event, a matched control is selected from
**non-reverse-split** stocks in the same universe, using only information
available **before** the event date (no look-ahead in matching):

- Match variables: pre-event price level, market cap (where obtainable),
  exchange, sector, trailing 60-day realized volatility, trailing 20-day
  average dollar volume, and calendar month (to control for market regime).
- Matching method: nearest-neighbor on a standardized distance across the
  above variables (a lightweight, transparent alternative to full propensity
  scoring, appropriate given the moderate variable count and the priority on
  auditability over sophistication).
- Three return series will be reported side by side for every headline
  result: **raw return**, **market-adjusted return** (vs. an equal-weighted
  small-cap benchmark, e.g. a Russell Microcap proxy or a constructed
  equal-weight basket of the same universe), and **matched-control-adjusted
  return**. Divergence between these three is itself a finding, not noise
  to be averaged away.
- Controls are drawn from the same survivorship-inclusive universe, i.e. a
  control that later delisted is not excluded -- the same survivorship-bias
  discipline applies to the control group as to the treatment group.

---

## 10. Proposed validation methodology

- **Validation Pass 1** (pre-analysis): random sample of >=30 events or ~5%
  (whichever is larger), manually cross-checked against SEC EDGAR / exchange
  notices for correct ratio, correct effective date, correct forward/reverse
  classification.
- **Validation Pass 2** (post-analysis, pre-conclusion): independent
  recomputation of every headline statistic in a separate script (not a
  re-run of the same code path), diffed against the primary result with an
  explicit PASS/FAIL tolerance table.
- **Out-of-sample check**: chronological 70/30 split (earlier ~70% =
  development, most recent ~30% = holdout). Any pattern used to draw a
  conclusion must be specified in the development period before being
  checked against the holdout -- never the reverse.
- **Robustness**: every headline result re-run under at least one
  alternative bucket scheme, with/without winsorization, and mean vs.
  median, before being called durable.

---

## 11. Proposed project directory

Already created on disk at `Reverse_Split_Study/` (see `README.md` for the
full tree). Matches the structure specified in the brief, with `.gitkeep`
placeholders so empty directories survive if this is later put under git.

---

## 12. Expected dependencies

See `requirements.txt` (already written): pandas, numpy, pyarrow, scipy,
statsmodels, requests, python-dotenv, tenacity, matplotlib, seaborn, tqdm,
python-dateutil, pandas-market-calendars (for correct NYSE/NASDAQ
trading-day arithmetic, since the brief is explicit that trading days != 
calendar days), pytest.

---

## 13. Expected API credentials

See `.env.example` (already written):

- `ALPHAVANTAGE_API_KEY` -- confirm whether you already have one from
  Trade100, or sign up free.
- `POLYGON_API_KEY` -- new, free signup recommended (see Phase 1, Task A).
- `FMP_API_KEY` -- only if you decide to upgrade FMP (17-B); otherwise leave
  blank and FMP is excluded from this study.
- `SEC_USER_AGENT` -- no signup, but SEC requires a real name + email in the
  header on every request; pre-filled with your name/email as the default.

---

## 14. What I (Claude) can complete autonomously right now

- All reproducible scaffolding: directory structure, config, requirements,
  frozen definitions, audit-log templates -- done today.
- Writing every pipeline script (collection, cleaning, validation, feature
  engineering, statistics, matching, visualization, report generation) as
  the data sources are confirmed.
- Using my own currently-connected tools (Alpha Vantage, and Stocklake/Webull
  for present-day reference checks) for small-scale exploratory spot-checks
  and cross-validation of a sample of events -- e.g. verifying a handful of
  ratios/dates the way I did for NKLA above.
- Drafting all reports, audits, and researcher notes as each stage completes.

## 15. What you need to do manually

- Sign up for a free Polygon.io API key (I cannot create accounts on your
  behalf).
- Decide whether to pursue an FMP plan upgrade (17-B) -- this is a real
  money decision, not mine to make.
- Run local scripts I provide (starting with Phase 1's diagnostic script)
  and send back their output, since bulk historical pulls are far more
  efficient run from your machine with your own keys/rate limits than
  relayed through this conversation one API call at a time.
- Approve the methodology decisions in section 17 before Track B moves past
  scaffolding into real bulk data collection.

---

## 16. Estimated computational/storage requirements

- Daily-only master dataset (T-30..T+60 daily bars, ~1,500-5,000 events):
  low tens of MB -- trivial.
- Point-in-time filings/news/halt tables: low tens of MB -- trivial.
- 1-minute intraday for T-5..T+10 (approx 15 trading days x ~390 bars/day =
  ~5,850 bars/event): if pulled for **every** event, this could reach
  several hundred MB to low single-digit GB depending on final event count
  and whether a full quote/trade tape or just OHLCV bars are stored. This is
  the one part of the plan where scoping down to a stratified subsample
  (17-F) may be the pragmatic choice rather than a data-availability problem
  per se.
- Compute: everything here (pandas-scale stats, matching, event-study math)
  runs comfortably on a laptop; no GPU or cluster needed.

---

## 17. Major methodological decisions that need your approval

**A. Bulk event-discovery source.** Recommend: sign up for Polygon.io free
tier as the primary bulk source, cross-validated against SEC EDGAR
full-text search. Alternative: proceed with a smaller, manually-curated
event list if you'd rather not create another account. **Your call.**

**B. FMP plan upgrade.** FMP's calendar/directory/filings endpoints are
paywalled on the current connected plan. Recommend: skip it -- Polygon +
EDGAR cover the same ground for free. Only worth paying for if you want FMP
specifically for some other reason. **Your call.**

**C. Research window length.** 5 years (cleaner data, fewer events) vs. 10
years (more events, weaker point-in-time float/data quality in the older
years). Recommend starting with 5 years (~2021-2026) and only extending
back if the resulting sample size is too small for the subgroup analyses
the brief wants. **Your call.**

**D. OTC inclusion.** Brief says exclude or separately classify OTC
securities. Recommend: track them in the exclusion log but exclude from the
primary analysis, given materially worse data quality across every source
tested. **Your call -- confirm or override.**

**E. Frozen definitions**, proposed now, before any data is seen (full text
in `config/definitions.md`, written today):
  - *Extreme momentum event*: T close return >= +50% vs. T-1 close, **or**
    intraday max run-up from the open >= +100%.
  - *Momentum continuation*: T close return > 0 **and** T+5 close >= T close.
  - *Failed momentum*: T close return > 0 **but** T+5 close < T open.
  - *Reversal*: T close return < 0 vs. T-1 close.
  These are drafts for your approval -- sensitivity analysis with alternative
  reasonable definitions is planned regardless (per the brief's own
  requirement).

**F. Intraday minute-data scope.** Full population vs. a stratified random
subsample (e.g. 300-500 events spanning all ratio/float/price buckets), to
keep intraday data volume and API cost manageable. Recommend the
stratified subsample for intraday, full population for daily. **Your call.**

None of these blocks starting Phase 1 (below) -- Phase 1 is designed to
produce the information needed to make decision A concretely (does Polygon's
free tier actually deliver what's needed) before locking anything in.

---

# PHASE 1 -- First Human Researcher Task

## Why we're doing this

Before writing a single line of the real collection pipeline, we need to know
what our actual, working data access looks like -- not what the docs claim.
Today I confirmed Alpha Vantage works and FMP is blocked at the connected
plan tier, from inside this session. What I *can't* test from here is
Polygon.io (no connector) or SEC EDGAR (no outbound HTTP tool wired to it in
this session) -- both need to be checked from your machine.

## Exact commands to run

```
cd Reverse_Split_Study
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Then open `.env` and fill in:
- `ALPHAVANTAGE_API_KEY` (reuse an existing one if you have it, or get a free one at https://www.alphavantage.co/support/#api-key)
- `POLYGON_API_KEY` -- sign up free at https://polygon.io/dashboard/signup and paste the key
- Leave `FMP_API_KEY` blank for now (pending decision 17-B)
- `SEC_USER_AGENT` is pre-filled with your name/email; leave as is unless you'd rather use a different contact

Then run:

```
python src\data_collection\00_test_data_sources.py
```

## What the command does

`00_test_data_sources.py` (already written, in `src/data_collection/`) will:
1. Confirm your `.env` loads and report which keys are present/missing.
2. Call Polygon's `/v3/reference/splits` for a small recent date window and
   report how many reverse splits it finds, with two or three example rows.
3. Call SEC EDGAR full-text search for 8-K filings mentioning "reverse
   stock split" in the same window, with a compliant User-Agent, and report
   how many hits it finds.
4. Re-verify Alpha Vantage's per-symbol `SPLITS` call still works from your
   machine (same call I ran successfully here against NKLA).
5. Write everything to `data/intermediate/data_source_probe_result.json`.

## Expected runtime

Under a minute -- this is a handful of API calls, not a bulk pull.

## Files this will create

- `data/intermediate/data_source_probe_result.json`

## What successful output looks like

A JSON file with four sections (`env`, `polygon`, `sec_edgar`, `alpha_vantage`),
each showing `"status": "ok"` and a small sample of real data. If Polygon's
free tier turns out to have historical depth restrictions, `polygon.status`
will say so explicitly rather than silently returning nothing.

## Common errors

- `POLYGON_API_KEY not set` -- you skipped the .env step, or the key hasn't
  activated yet (can take a couple of minutes after signup).
- SEC EDGAR `403` -- the User-Agent header is missing or looks like a bot's
  default; `SEC_USER_AGENT` must be a real name + email.
- Alpha Vantage rate-limit message in the JSON body instead of data -- free
  tier is 5 requests/minute; harmless here since we only make one call.

## What to send back

Just the contents of `data/intermediate/data_source_probe_result.json` --
paste it back or attach the file. That tells us definitively whether
Polygon's free tier is sufficient for bulk event discovery (decision 17-A)
before we build the real collection pipeline around it.

## How to verify it worked

The script exits with code 0 and prints `Probe complete -- see
data/intermediate/data_source_probe_result.json` as its last line. If it
exits with a traceback instead, send that back too.

---

# PHASE 1 — Results (2026-09-18)

You ran `00_test_data_sources.py`. All four sources returned `"status": "ok"`.
Full raw JSON preserved at `data/intermediate/data_source_probe_result.json`
(already on your machine from the run) — findings below are read directly
from it, not re-asserted from memory.

## What this confirms

- **Polygon `/v3/reference/splits` works and is rich.** In a single 30-day
  window (2026-08-19 to 2026-09-18) it returned 50 events, 41 of them
  reverse splits, including a 1-for-1500 (PSRU), a 1-for-10 (LECRF), and a
  1-for-5 (PNXPF). **Decision 17-A is resolved: Polygon is the primary bulk
  discovery source**, cross-checked against SEC EDGAR.
- **The `limit=50` request hit its cap exactly (50 of 50 returned).** This
  means the 30-day window almost certainly contains *more* than 50 reverse
  splits and the probe undercounted. The real collection script must follow
  Polygon's `next_url` cursor to page through results instead of trusting a
  single page — noted as a required fix for Phase 2, not a data problem.
- **41 reverse splits in 30 days annualizes to roughly 500/year at the
  current rate**, from this one snapshot alone. That's within the upper half
  of the §6 planning estimate, but §6 was speculative and this is one month
  — Phase 2's real historical pull replaces the estimate with a measured
  count across the full study window.
- **Exchange is not in Polygon's splits payload.** PNXPF and LECRF (5-letter,
  "F"-suffixed tickers) are patterns typically associated with OTC/foreign
  private issuers, not NASDAQ/NYSE/NYSE American primary listings. Polygon's
  splits endpoint alone cannot tell us which — Phase 2 needs a follow-up
  join against Polygon's `/v3/reference/tickers` (or another ticker-detail
  source) per symbol to read `primary_exchange`, both to build the
  NASDAQ/NYSE/NYSE American universe and to populate the OTC exclusion log
  the brief requires, rather than silently dropping or keeping ambiguous
  tickers.
- **SEC EDGAR full-text search works but is noisy, not a clean event
  count.** 463 hits for "reverse stock split" in the same 30-day window vs.
  Polygon's 41 actual reverse splits — most hits are boilerplate risk-factor
  language, unrelated prior filings, or announcements without an executed
  split yet. EDGAR is confirmed useful for **recovering announcement dates**
  and for the later **dilution/financing filing timeline**, but is not being
  used as the primary event-count source — that role stays with Polygon.
- **`FMP_API_KEY` is present in your `.env`** (your own key, used directly
  via `requests`, not through the connector that was blocked in Phase 0).
  This hasn't been tested yet — worth a quick check in the next script, since
  if this key is on a plan tier above what was tested in Phase 0, it could
  reopen FMP's calendar/directory/filings endpoints for free, changing the
  answer to decision 17-B.

## Decision status after Phase 1

- **17-A (bulk source): RESOLVED — Polygon primary, EDGAR secondary.**
- 17-B, 17-C, 17-D, 17-F: still open, asked back to you alongside this
  update.
- 17-E (frozen definitions): proceeding as drafted in `config/definitions.md`
  unless you object.
