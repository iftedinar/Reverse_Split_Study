# Research Log — Study A: Reverse Split Momentum

Every major decision, dated, with rationale, alternatives considered, and
impact on methodology. This is append-only in spirit — past entries are not
edited to look smarter in hindsight; corrections get a new dated entry.

---

## 2026-09-18 — Project kickoff / PHASE 0

**Decision:** Set up project skeleton in `Reverse_Split_Study/` per the
brief's specified directory layout, and produce PHASE 0 (research design)
before writing any collection code.

**Reason:** The brief explicitly requires design-before-code, researcher
participation, and avoidance of look-ahead/survivorship bias baked in from
the start rather than retrofitted.

**Alternatives considered:** Jumping straight to a collection script against
whatever API was fastest to wire up. Rejected — would have anchored on
FMP or Alpha Vantage's per-symbol limitations before checking whether a
proper bulk source (Polygon) was viable, and would have skipped the
explicit-approval step the brief asks for on major methodology calls.

**Impact:** No data collected yet. See PHASE_0_RESEARCH_DESIGN.md §17 for
the six decisions still open.

---

## 2026-09-18 — Data source reality check

**Decision:** Tested every currently-connected financial data tool live
before writing anything in PHASE_0 about data sources, rather than relying
on documentation or memory.

**Finding:** Alpha Vantage's `SPLITS` endpoint works and is per-symbol only
(confirmed against NKLA: effective_date 2024-06-25, split_factor 0.0333).
FMP's calendar, directory, and SEC-filings endpoints are all blocked on the
currently connected account's plan tier (confirmed via three separate
plan-upgrade errors). No connected source provides a bulk, market-wide
reverse-split calendar.

**Reason this matters:** The brief's estimated-event-count and
data-source sections cannot be answered with real numbers without a bulk
source. Polygon.io's `/v3/reference/splits` is recommended as the primary
candidate (PHASE_0 §17-A), pending a human signing up for a free key — an
account-creation step Claude cannot do on the user's behalf.

**Impact:** Phase 1's first human task is a diagnostic script to test
Polygon + SEC EDGAR access, rather than jumping into a real collection
run, because the plan cannot lock in a bulk source until that's confirmed.

---

## 2026-09-18 — Phase 1 complete: data source reconnaissance results

**Decision:** Adopt Polygon.io `/v3/reference/splits` as the primary bulk
event-discovery source, with SEC EDGAR full-text search as a secondary
source for announcement dates and later dilution/financing tracking.

**Reason:** Live probe run by the researcher confirmed Polygon returns rich,
correctly-classified reverse-split events (41 of 50 returned in a 30-day
window were reverse splits, spanning ratios from 1-for-5 to 1-for-1500).
SEC EDGAR's full-text search returned 463 hits for the same window and
query — confirmed working, but too noisy (boilerplate/unrelated mentions)
to serve as the primary event count.

**New issues surfaced, to resolve in Phase 2:**
1. Polygon's response hit its `limit=50` page cap exactly — the real
   collection script must paginate via `next_url`, not trust a single page.
2. Polygon's splits payload has no exchange field. Tickers like PNXPF and
   LECRF (5-letter, F-suffix) look OTC/foreign-private-issuer, not
   NASDAQ/NYSE/NYSE American. A per-ticker exchange lookup is needed before
   the NASDAQ/NYSE/NYSE American universe (and the required OTC exclusion
   log) can be built correctly.
3. `FMP_API_KEY` is present in `.env` (the researcher's own key, untested
   directly) — worth a cheap direct test before finalizing decision 17-B,
   since it wasn't tested via `requests` the way Polygon/EDGAR/AV were.

**Impact:** Decision 17-A (PHASE_0 §17-A) is resolved. Decisions 17-B, 17-C,
17-D, 17-F remain open and were sent back to the researcher for sign-off
before Phase 2 (full historical event collection) begins.

---

## 2026-09-18 — Decisions 17-B/C/D/F locked

**Decision:** Recorded in `config/study_scope.md`:
- 17-B: test the existing FMP_API_KEY directly before any purchase decision.
- 17-C: 5-year window, 2021-09-18 through 2026-09-18.
- 17-D: OTC-listed events logged in an exclusion log, excluded from primary
  analysis.
- 17-F: intraday minute data limited to a stratified subsample (~300-500
  events across all buckets), specified in Phase 4.

**Reason:** User confirmed the recommended option on each, following the
Phase 1 evidence (Polygon confirmed viable, OTC-pattern tickers observed
in the sample, FMP key present but untested, intraday cost/storage
concerns raised in PHASE_0 §16).

**Impact:** Phase 2 (full historical event collection) can now proceed
against a fixed window and a fixed exchange-classification policy, rather
than an open-ended one.

---

## 2026-09-18 — Phase 2 results reviewed, instrument-type bug found and fixed, and a hard technical constraint discovered

**What the Phase 2 run actually produced:** 6,737 raw split events over the
5-year window; after removing forward splits, 4,675 reverse splits. Of
those, the exchange-only classification put 1,549 in the "primary universe"
(NASDAQ/NYSE/NYSE American) and 3,126 in the exclusion log — but only 274
of those exclusions were actually resolved (OTC Link, NOT_FOUND, BATS,
ARCX, Grey Market); the remaining 2,852 were still `PENDING_LOOKUP` because
the per-run lookup cap (300) was hit.

**Bug found:** manually inspecting the "primary universe" file turned up
leveraged/inverse single-stock ETFs (e.g. a "2X Daily Target" fund) sitting
alongside genuine small-cap common stock. The original script classified by
exchange only, never by instrument type — so an ETF that happens to be
listed on NASDAQ was being counted as a qualifying event. This directly
contradicts the brief's explicit requirement to exclude or separately
classify ETFs/ETNs/funds/preferred/warrants/rights/units, never fold them
into the common-stock population.

**Fix:** wrote `02_finalize_classification.py`, which reuses the already-
fetched raw splits (no re-fetch needed) and adds Polygon's `type` field to
both the ticker-universe pull and the individual lookups, then reclassifies
every event into three buckets: primary universe (type=CS, listed),
ADR/foreign-private-issuer (tracked separately per the brief's own
instruction on ADRs, not auto-excluded), and excluded (OTC, other exchange,
non-common-stock type, or still-pending), each with an explicit reason.
Nothing is silently dropped.

**Hard constraint discovered:** attempted to run this fix myself, directly
on the connected device, to avoid asking for another manual step. Every
outbound request — even a plain `curl` to google.com — was rejected by a
mandatory proxy with `403 Forbidden`. This is an organizational egress
allowlist on the sandboxed shell Cowork uses to reach the connected
device; it is separate from, and stricter than, the user's own terminal
(which reached Polygon and SEC EDGAR fine when run directly). Conclusion:
any step that makes outbound API calls must continue to be run by the
researcher directly in their own terminal — this is a technical wall, not
a workflow preference, and it applies to every future data-collection
script in this project, not just this one.

**Impact:** `reverse_split_events_draft.csv` and `exclusion_log.csv` as
they stand are provisional and should not be used for anything downstream
until `02_finalize_classification.py` has been run to completion (it may
need more than one run, same as script 01, given the per-run lookup cap).

---

## 2026-09-18 — Type-fix results reviewed; second bug found and fixed; projection of true final count

**Results from the first corrected run:** 88 ETFs, 11 closed-end funds, 5
warrants, and 1 preferred share were correctly caught and excluded that had
previously been miscounted as common stock. 136 genuine ADR events were
correctly separated into `adr_events_separate.csv` (real companies:
DouYu, 17 Education, Trinity Biotech, Unilever, GSK, NatWest, etc. — this
list looks right on inspection). Primary universe stood at 1,309 rows.

**Bug found:** the per-run lookup cap (300) was being split between two
different jobs — backfilling `type` onto the original 300 already-resolved
tickers, and resolving brand-new pending tickers — with almost the entire
budget consumed by the backfill. Result: 2,670 pending tickers going in,
2,446 still pending coming out, despite "processing 300."

**Projection check:** of 1,823 tickers fully resolved so far, 72% turned
out to be genuine primary-universe events, 7% ADRs, 21% excluded. Applying
that ratio to the 2,446 still-pending tickers projects roughly 1,756 MORE
primary events once they resolve — a final total near **3,065**, not 1,309.
The current draft is explicitly NOT being treated as final; no statistics
or validation sampling will be run against it until resolution completes.

**Fix:** rewrote `02_finalize_classification.py` (revision 2) to run the
type-backfill and new-ticker resolution as separate steps, raised the
per-run cap from 300 to 5,000 (safe — every result is flushed to disk
immediately, so interrupting the script loses nothing), and added a
self-tuning rate limiter that starts at the same conservative 5 calls/min
and speeds up automatically as long as Polygon keeps returning 200s,
backing off instantly on any 429. This replaces guessing the plan's real
rate limit with finding it out empirically.

**Impact:** researcher needs to re-run `02_finalize_classification.py`
(same command as before) — ideally once, since the new cap should cover
all ~2,446 remaining tickers if the adaptive rate limiter finds meaningful
headroom above 5/min; if not, it remains safely resumable.

---

## 2026-09-19 — Scope reduced to a ~100-event exploratory study (2024-2025); full-universe ticker lookup stopped

**Decision:** the researcher directed a scope change away from resolving
the full 3,000+ ticker backlog and running a full 5-year census, toward a
smaller, higher-quality exploratory event study prioritizing data accuracy,
point-in-time integrity, correct corporate-action handling, and independent
verification over sample size. New parameters: primary study window
2024-01-01 to 2025-12-31 (expand to 2023 only if insufficient, which turned
out not to be necessary — see below); target sample ~100 validated events
from ≥75 distinct companies, acceptable range 75-150; no cherry-picking on
outcome; reproducible stratified random sampling by year x ratio bucket
with a fixed seed; two-tier CORE/ENRICHED design; mandatory median
reporting; mandatory Validation Pass #1 (manual, ≥20 events/20%) and
independent Accuracy Check Pass #2 (separate calculation path); no
unnecessary machine learning. Full detail in `audit/existing_project_inventory.md`.

**Why the previous "~3,065 final events" projection was wrong:** the
2026-09-18 log entry projected the final primary-universe size by applying
a 72%-primary conversion rate (observed across 1,823 resolved tickers) to
the remaining ~2,446 pending tickers. That projection assumed the
remaining tickers would resolve similarly to the ones resolved so far. They
did not. Rebuilding the classification from the current cache state (1,207
individually-resolved tickers, up from 300, with zero new API calls — see
`src/data_collection/03_rebuild_from_cache.py`) shows the primary-universe
count is **unchanged at 1,309**. Investigation showed why: every ticker
that requires an *individual* lookup (as opposed to being found in the
bulk active-ticker snapshot) is, by definition, a ticker the bulk snapshot
did not already know about — and those tickers turned out to be
overwhelmingly off-scope by exchange: 616 OTC Link, 502 not resolvable at
all (likely delisted/renamed since their split event), 67 NYSE Arca, 20
Cboe BZX, 2 Grey Market — zero of the 1,207 are on NASDAQ/NYSE/NYSE
American. The earlier 72% figure was measured over a mix dominated by
easy, bulk-snapshot matches; the remaining backlog is systematically
harder and systematically more likely to be excluded. This is not a data
loss or a bug — it means the bulk active-ticker snapshot already captured
essentially all currently-eligible primary events, and continuing the
individual-lookup backlog would mostly resolve tickers that were never
going to qualify.

**Decision — do not resume the bulk lookup.** Per the researcher's
explicit instruction, `02_finalize_classification.py` will not be run in
full-universe/auto-resume mode. `03_rebuild_from_cache.py` (zero network
calls) is now the standard way to regenerate `reverse_split_events_draft.csv`,
`adr_events_separate.csv`, and `exclusion_log.csv` from whatever is
currently on disk.

**Target-window adequacy — confirmed sufficient without expansion.**
Filtering the current (corrected) primary universe to 2024-01-01–2025-12-31
yields **577 eligible candidate events** across 445 unique tickers — well
above the 100-event target and the 75-150 acceptable range. Expansion to
2023 is therefore not necessary and will not be performed. Any further API
calls will be narrowly scoped to verifying/completing the specific ~100
selected events, never to resuming the general classification backlog.

**Next step:** construct the reproducible stratified random sample
(fixed seed, stratified by year x ratio bucket) from the 577 eligible
2024-2025 primary events, per `audit/existing_project_inventory.md` §6.

---

## 2026-09-19 — Sample selection executed (zero new API calls)

Ran `src/analysis/04_select_sample.py` against the 2024-2025 eligible
population (577 primary-universe events, from `reverse_split_events_draft.csv`,
no new data fetched). Method: stratified by (year, ratio bucket) — 10
strata — with quotas allocated proportional to stratum size via
largest-remainder rounding to hit exactly 100, then a fixed-seed
(`random_seed = 20260919`) randomized draw within each stratum that
prefers spreading across distinct tickers before allowing a repeat
issuer. No outcome/performance data is read anywhere in this script, so
outcome-based cherry-picking is structurally impossible, not merely
avoided by discipline.

**Result:** 100 events selected, from **97 unique companies** (3
repeat-issuer tickers among the selected set), well above the ≥75-company
target. Exchange representation emerged naturally rather than being
forced: 94 NASDAQ / 3 NYSE / 3 NYSE American, matching the underlying
population's skew. Ratio-bucket spread: 29 (1-for-6→10), 26
(1-for-11→20), 22 (1-for-21→50), 12 (>1-for-50), 11 (1-for-2→5). Year
split: 58 from 2025, 42 from 2024. All 577 eligible events (selected and
not) are preserved in `data/processed/sample_selection.csv` with the
required columns, including a `permanent_identifier` column currently set
to `PENDING_VERIFICATION` for every row — no CIK/FIGI field exists in the
already-fetched Polygon data, and it will be filled per-event only during
the upcoming SEC EDGAR verification / external spot-check steps, not via
a bulk lookup.

**Next step:** per-event verification of the 100 selected events (ticker,
company identity, security type, exchange, effective date, ratio,
corporate-action treatment) against authoritative sources, then price-data
acquisition for the CORE sample only.

---

## 2026-09-19 — Price-data source investigation: three sources ruled out, one flagged, one path forward

Tested every price-data source reachable directly from this session
(no `device_bash` network calls involved -- these are Claude's own MCP
connectors, a separate channel from the blocked device proxy) against
the 100 selected events:

- **FMP** (`historical-price-eod-full`, `historical-price-eod-non-split-adjusted`):
  works for large caps (AAPL confirmed) but returns `ACCESS DENIED --
  requires a higher plan` for every micro-cap tested (KTTA, CNEY),
  regardless of date range. Ruled out -- this study's population is
  almost entirely micro-caps.
- **Alpha Vantage** (`TIME_SERIES_DAILY_ADJUSTED`, `TIME_SERIES_DAILY`):
  both premium-gated for historical (`outputsize=full`) data at any
  ticker; `compact` only reaches back ~100 trading days from today
  (Sept 2026), not into 2024-2025. Ruled out for this study's date range.
- **Stocklake** (`get_stock_history`): `history_not_found` for KTTA.
  Ruled out as a sole source given coverage gaps on this exact ticker
  population.
- **Webull** (`get_stock_bars`): works, with real micro-cap coverage.
  BUT confirmed (see `audit/price_adjustment_validation.md` for the full
  test) to return a series continuously split-adjusted **as of today**,
  not as of the studied event -- e.g. CISS shows implied per-share
  prices over $1,000,000 in mid-2024 because it underwent further
  reverse splits after its 2024-04-12 study event, and Webull's series
  bakes those later adjustments into the historical bars too. This is
  safe for within-window return ratios but not a substitute for a true
  raw/as-traded series, which the brief's CRITICAL price-adjustment rule
  requires this study to maintain.

**Decision:** fetch true raw (`adjusted=false`) and point-in-time
adjusted (`adjusted=true`) daily OHLCV from **Polygon** -- the project's
existing, already-authenticated, already-proven data source -- for the
100 selected events only, each with its own bounded T-30..T+60
trading-day window (`src/data_collection/06_fetch_event_prices_polygon.py`,
~200 total API calls). Webull's series will be retained as a
secondary cross-check, not the primary source. Because this requires
outbound HTTPS and `device_bash`'s proxy blocks that (established
earlier in this project), this script must be run in the researcher's
own terminal, exactly like the original split/ticker collection scripts.
A companion zero-network script, `07_build_price_panel.py`, reshapes the
raw responses into `data/intermediate/event_price_panel.csv` once fetched.

**Next step, once the researcher runs `06_fetch_event_prices_polygon.py`
and `07_build_price_panel.py`:** validate the raw-series price jump at
each event's effective date against its documented split ratio (a subset
manually, per Validation Pass #1), then compute returns, run-up/drawdown,
and volume metrics for the CORE sample.

## 2026-09-19 (cont.) — Polygon plan-tier blocker diagnosed and resolved via seeded replacement

The researcher ran `06_fetch_event_prices_polygon.py`, producing
`data/raw/polygon_event_prices_raw.jsonl` (200 lines: 100 events x 2
adjusted flags). Diagnostic pass over the raw file found 164 `OK`
responses and 36 `ERROR` responses. Every error was HTTP 403
`NOT_AUTHORIZED: ... your plan doesn't include this data timeframe`, and
the failures were precisely bounded: every request with a padded window
start on or before 2024-03-29 failed, and every request with a window
start on or after 2024-04-24 succeeded (window start = effective_date -
55 calendar days). This implies **events with effective_date before
~2024-06-18 cannot be fetched at this Polygon plan's historical depth**
-- a plan-tier limitation affecting every ticker in that date range
regardless of size or exchange, identical for `adjusted=true` and
`adjusted=false`. Confirmed on the boundary pair AKAN (window start
2024-03-29, ERROR) vs. VSME (window start 2024-04-24, OK). This
translated to exactly 18 of the 100 originally-selected events (all in
`year=2024`, spread across all 5 ratio buckets) being unfetchable.

**Decision:** rather than accepting a reduced N=82 (which would
non-randomly under-represent early 2024) or attempting some workaround
of the plan restriction, each blocked event was excluded with an
explicit, transparent, non-outcome-based reason and replaced with one
same-(year, ratio_bucket)-stratum event drawn from the remaining
eligible-but-unselected pool, restricted to `effective_date >=
2024-06-18` (the confirmed-fetchable boundary), using a seeded RNG
derived from the same master seed (`20260919`) plus the stratum and the
excluded event's id -- deterministic, reproducible, and decided purely
by data availability, before any return/outcome data was read for any
event (`src/analysis/05_replace_blocked_events.py`, reads only the
sample CSV and the raw fetch-status file, never price data). All 18
excluded originals remain in `sample_selection.csv` as
eligible-but-unselected with `exclusion_reason` populated -- nothing was
deleted.

Result: `data/processed/sample_selection.csv` updated in place. Final
selected count: 100. Unique companies: 98 (one previously-excluded
ticker, AKAN, was drawn back in via a *different* event_id/effective_date
as a replacement for CIM, which is a legitimate repeat-issuer case, not
a duplicate of the excluded AKAN event). Full list of the 18
substitutions is in the script's run output and reproducible by
re-running `05_replace_blocked_events.py` (idempotent given the same
raw-prices file).

**Next step:** the researcher needs to re-run
`06_fetch_event_prices_polygon.py` once more in their own terminal --
it will skip the 82 already-successfully-fetched event/adjusted pairs
and fetch only the 18 new replacement tickers (36 requests: 18 events x
2 adjusted flags), all with effective_date >= 2024-06-18 and therefore
within the confirmed-fetchable range. Then `07_build_price_panel.py`
(zero network calls) builds the full 100-event price panel.

## 2026-09-20 — Round-1 fix was incomplete: true cause was a rolling ~2-year historical-depth floor, not a fixed date cutoff

Building the price panel and running the split-ratio validation check
(`09_validate_split_adjustment.py`) surfaced two more problems, one much
more serious than round 1's fix:

**1. The real boundary is a rolling ~2-years-before-fetch floor, not a
fixed ~2024-06-18 cutoff.** Round 1 diagnosed the blocker purely from
HTTP status (403 vs 200) and concluded events with `effective_date >=
2024-06-18` were safe. Inspecting the *actual bars returned* for the
resulting panel shows this was wrong: many "OK" (HTTP 200) responses
were silently truncated -- Polygon does not error when `window_start`
precedes this plan's historical floor, it just returns data starting at
the floor instead. The floor itself is empirically pinned at
**2024-09-19** (the earliest date returned by any request in the fetched
file, regardless of how far back `window_start` asked for), and behaves
like a rolling "trailing ~2 years from whenever the request is made"
limit rather than a fixed date -- consistent with "today" in this
project's timeline being ~2026-09-19/20. The practical effect: an
event's *pre-event* T-30 window is only fully intact once its
effective_date is far enough past 2024-09-19 to fit 30 real trading
days before it -- empirically, `pre_count` climbs from single digits
just past the floor to a stable ~35-39 by `effective_date` ~2024-11-04
and stays there. 30 of the 100 currently-selected events (all with
`effective_date` between 2024-06-18 and ~2024-10-18, including several
of round 1's own replacements) failed a completeness check of `pre_count
>= 28` trading days -- most severely VSME_2024-06-18 with only 2 total
raw bars fetched, both ~3 months after its own effective date.

**2. A second, unrelated pattern:** 11 events (independent of date, e.g.
GRDX, AVX, BGMS, FGNX, DCX, AGPU, BTTC, GOAI, PPCB, SPRB, GITS) returned
little or no usable data across their *entire* requested window, pre and
post alike -- most likely a ticker/data mismatch in the source splits
record, or (for a couple of the 2025 cases) a stock with no pre-existing
trading history because its "reverse split" record appears to coincide
with its own listing date, which doesn't fit this study's premise of
measuring momentum against an established trading base.

**A smaller, unrelated bug was also caught and fixed in the same pass:**
`09_validate_split_adjustment.py`'s raw-ratio check had pre/post-split
closes swapped (computed `raw_close[T-1] / raw_close[T0]` instead of
`raw_close[T0] / raw_close[T-1]`), which would have shown every correct
event as a false ratio mismatch. Corrected before drawing any conclusions
from that script's output.

**Fix (round 2, same non-outcome-based methodology as round 1):**
`10_fix_data_completeness.py` re-derives completeness directly from the
fetched bars in `data/intermediate/event_price_panel.csv` (not from HTTP
status), classifies each failing event's cause, excludes it with a
specific transparent reason (kept visible in `sample_selection.csv`,
nothing deleted), and draws one same-(year, ratio_bucket)-stratum
replacement per exclusion from the remaining eligible pool, now
restricted to `effective_date >= 2024-11-15` (the empirically-confirmed
safe floor, with ~11 trading days of margin over the bare minimum, and
slack for however long the next fetch takes to run) -- same fixed master
seed (20260919), same seeded-per-stratum-and-event draw scheme as every
prior replacement in this study, reading no price or return data to pick
which replacement to draw.

**Result:** 41 events excluded (30 for the historical-depth floor, 11
for anomalous ticker data gaps), 32 successfully replaced. **9 could not
be replaced** -- their specific (year, ratio_bucket) stratum had no
remaining eligible-but-unselected candidate with `effective_date >=
2024-11-15` (all 9 are thin 2024 strata largely exhausted by rounds 1
and 2 combined: DLPN, LUCY, MGRX, SBFM, SNTI, TCRT, VMAR (x2), VSME).
Rather than force a cross-stratum substitution (which would itself be a
methodology choice made after seeing which strata ran short, and a new
source of debate), these 9 slots are left unfilled and the final sample
is accepted at **N=91, 86 unique companies** -- still comfortably within
the brief's acceptable range (75-150, target ~100) and only modestly
short of the 100 target. Year split: 58 (2025) / 33 (2024). All 5 ratio
buckets remain represented (10-25 events each).

**Next step:** the researcher needs to run, in their own terminal,
`06_fetch_event_prices_polygon.py` once more (fetches only the 32 new
round-2 replacement tickers; skips everything already cached) and, for
the first time, `08_fetch_benchmark_prices.py` (2 tickers, SPY and IWM,
needed for the market-adjusted return leg of the analysis -- see the
2026-09-19 log entry on price-source investigation). After that,
`07_build_price_panel.py` rebuilds the full panel and
`10_fix_data_completeness.py` is re-run once to confirm the round-2
replacements are themselves complete (a further, smaller round-3 fix is
possible if any of the 32 hit the same rare anomalous-ticker pattern,
but not the historical-depth floor, since all were drawn from dates
safely past it).

## 2026-09-20 (cont.) — Sample finalized at N=88 after a third small completeness check

After the round-2 replacement fetch, re-running `10_fix_data_completeness.py`
found the 32 round-2 replacements themselves clean except 3 (BMNR, JXG,
QCLS) hitting the same rare anomalous-ticker-data-gap pattern as before
(unrelated to the historical-depth floor, since all were drawn from
`effective_date >= 2024-11-15`). Rather than run a fourth data-fetch
round for 3 tickers -- diminishing value against an unpredictable,
low-rate anomaly -- the sample was deliberately finalized at **N=88, 84
unique companies** without replacing them, comfortably inside the
brief's acceptable range (75-150). The 3 draws that were selected but
never fetched are marked `selected=False` with an explicit
"not fetched, stopping decision" reason in `sample_selection.csv`; they
remain visible, nothing was deleted. All 88 currently-selected events
now pass the full completeness bar (>=28 pre-event, >=58 post-event raw
trading days) with zero remaining anomalies. Benchmark data (SPY, IWM,
adjusted daily closes) fetched successfully for the full study window.

**Sample is now final.** Proceeding to price-adjustment validation,
return/momentum computation, statistics, the two validation passes, and
the final report.

## Return/momentum computation, statistics, and both validation passes complete

- `11_compute_research_matrix.py` ran clean on the final N=88 CORE sample:
  61-column research matrix at
  `data/processed/reverse_split_research_matrix.csv`. Headline sanity check
  (median returns): T0 = -3.6%, T+1 = -5.5%, T+5 = -8.7%, T+10 = -7.7%,
  T+20 = -8.8%, T+30 = -10.2%, T+60 = -24.8%. Every post-event horizon's
  median is negative and the magnitude grows with horizon length -- the
  opposite of a "momentum continuation" pattern. reversal count = 50/88,
  momentum_continuation = 10/88, extreme_momentum_event = 0/88 (T0 return
  never reached the frozen +50% threshold in this sample; recall the
  intraday-high-vs-open leg of that definition is a documented proxy, not
  true intraday minute data).
- `12_compute_statistics.py` produced the full mandated statistical
  reporting (N, mean, MEDIAN, SD, 95% CI via a small-sample t-table, p25/p75,
  min/max, % positive) for every return series (raw, vs-SPY, vs-IWM,
  vs-universe-basket) at every horizon, plus a winsorized (5%/95%) robustness
  table, a first-event-per-company (dependence-robustness) table, and
  cross-tabs by ratio bucket, year, and pre-split price bucket. All in
  `results/tables/`.
- `13_accuracy_check_pass2.py`: independent recomputation of t0_return_pct
  and T+10/30/60 returns via a completely separate code path (plain
  csv.reader + its own indexing, no shared helper functions with script 11).
  Result: **0 mismatches** across 88 events x 4 metrics (tolerance 1e-6) --
  PASS, no halt triggered.
- Validation Pass #1 (`14_validation_pass1_sample.py` +
  `audit/validation_sample.csv` + `audit/validation_pass_1.md`): drew 20/88
  events (22.7%) by the same seeded stratified method used for the original
  sample. All 20/20 passed internal consistency (ratio bucket, split-factor
  validation, completeness). 11 of the 20 were further checked against
  public sources (SEC EDGAR, Nasdaq Trader corporate-action alerts, wire
  press) -- exceeding the >=10-event external-check minimum -- and all 11
  were CONFIRMED (`audit/external_spot_checks.md`). Two (BOLT, UNCY) showed
  a 2-3 calendar-day gap between the press-release "effective date" and our
  stored date; investigated and explained by the officially effective date
  falling on a non-trading day (a weekend / the Juneteenth holiday), which
  is exactly what this study's "first trading session on/after
  effective_date" T0 definition predicts -- documented as a labeling
  nuance, not corrected as an error, since the underlying T0 anchor is
  already right.
- Publication Gate (`audit/publication_gate.md`): **PASS**. CORE tier =
  88/88 (100%) -- no event needed to be kept on weaker ENRICHED-tier
  evidence; every event that failed a reliability check was excluded and
  seeded-replaced during the sample-correction rounds instead.
- Proceeding to publication figures and the final report / LinkedIn
  article, per the user's explicit standing instruction to complete the
  remainder of the pipeline autonomously.

## Study complete: final report, 12 publication figures, and LinkedIn materials delivered

Per the user's explicit standing instruction to complete the remainder of
the pipeline autonomously and produce a scholarly final article, this
session completed the full remaining pipeline end to end:

- `15_generate_figures.py`: all 12 pre-specified publication figures
  generated (results/figures/publication/), covering the median return
  path, raw/market/universe-adjusted comparison, return distribution,
  ratio-bucket and price-bucket and year subgroup breakdowns, momentum/
  reversal classification counts, volume and volatility patterns, run-up
  vs. drawdown, threshold-crossing frequencies, and sample composition.
- `reports/Reverse_Split_Momentum_Study_FINAL.md`: full academic-format
  report (Abstract, Introduction, Institutional Background/Related
  Literature, Data, Sample Construction, Methodology, Results, Robustness,
  Data Quality/Validation/Publication Gate, Discussion, Limitations,
  Conclusion, References, Appendices) written from the actual computed
  N=88 results -- no placeholder or illustrative numbers anywhere in it.
- `reports/LINKEDIN_ARTICLE.md`, `reports/LINKEDIN_POST.md`,
  `reports/ARTICLE_RESEARCH_NOTES.md`: the requested LinkedIn deliverables,
  written in a scholarly/academic register per the user's explicit request
  for "very academic style and academic format," using the same verified
  figures as the full report.

**Headline result (stands on its own, independent of any narrative
framing):** median returns are negative at every horizon from the split's
effective date through T+60, and worsen over time (T0 -3.6% -> T+60
-24.8%), robust to winsorization and to a first-event-per-company check --
directly contradicting the popular "reverse-split momentum pop" narrative
this study was designed to test.

This closes out Study A - Reverse Split Momentum: sample construction,
three-round non-outcome-based correction, split-adjustment validation
(88/88 PASS), data completeness (88/88), return/momentum computation,
mandatory statistical reporting (median + mean + CI + robustness), two
independent validation passes (manual review + accuracy-check recomputation,
both clean), 11 external corporate-action spot checks (all confirmed),
Publication Gate determination (PASS), 12 publication figures, the final
academic report, and the LinkedIn article/post/notes are all complete and
on disk under this project folder.
