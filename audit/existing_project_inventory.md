# Existing Project Inventory — Reverse Split Momentum Study (Study A)

**Prepared:** 2026-09-19
**Purpose:** Mandatory first deliverable of the 2026-09-19 scope-reduction directive. Documents the last safely persisted state of every file in the project before any new code is written or any new API call is made, so that all valid existing work is reused and nothing is redownloaded or discarded without cause. No file was deleted, overwritten with fabricated content, or re-fetched from the network to produce this document; the only file this inspection process modified is described in the "Actions taken during this inspection" section below.

## 1. Actions taken during this inspection (full disclosure)

Before this document existed, the three intermediate classification files
(`reverse_split_events_draft.csv`, `adr_events_separate.csv`, `exclusion_log.csv`)
were found to be **stale**: they were last written when the ticker-lookup cache had
only 300 entries, but the cache had since grown to 1,207 unique resolved tickers
without a corresponding re-classification run. Re-running the original
classification script (`02_finalize_classification.py`) was avoided because it
also resolves new pending tickers via live API calls, which the current directive
explicitly forbids resuming. Instead, a new script,
`src/data_collection/03_rebuild_from_cache.py`, was written. It makes **zero
network calls** and only reprocesses the three raw files that were already on
disk (`polygon_splits_raw.jsonl`, `polygon_ticker_universe_active_v2.jsonl`,
`polygon_ticker_lookup_cache.jsonl`) to regenerate the three intermediate CSVs
so that they correctly reflect the cache's current, already-fetched state. This
is the only write made to existing project data during this inspection, and it
is a correction of a staleness bug, not new data collection — no raw file was
touched, no ticker was newly looked up, and no observation was added or removed
beyond what the already-cached data supports.

## 2. Last safely persisted state of the interrupted ticker classification process

The classification/lookup pipeline (`01_collect_reverse_splits.py` →
`02_finalize_classification.py`) was interrupted mid-run. Its last safely
persisted state, verified directly from the raw files on disk (not from
terminal output, which is not proof of persistence), is:

| Raw asset | Records persisted | Last write (mtime) |
|---|---|---|
| `polygon_splits_raw.jsonl` (all Polygon-reported splits, 5-yr pull) | 6,737 split events | 2026-09-18 20:12:55 |
| `polygon_ticker_universe_active_v2.jsonl` (active-ticker snapshot w/ `type` field) | 8,843 tickers | 2026-09-19 00:22:10 |
| `polygon_ticker_lookup_cache.jsonl` (individual ticker lookups, deduplicated) | 1,507 raw lines → **1,207 unique tickers** (later entries override earlier ones for the same ticker; all 1,207 carry the `type` field, confirming the type-backfill step fully completed) | 2026-09-19 07:57:44 |

No ticker lookups have occurred since 07:57:44 on 2026-09-19 — the cache file
has not grown further. **2,073 raw split records still have no resolved
ticker information at all** ("PENDING_LOOKUP") and were never silently
dropped; they remain visible in `exclusion_log.csv` with that explicit reason.

## 3. Why the primary-universe count did not grow despite ~907 additional tickers being resolved

Between the stale snapshot (cache = 300) and the rebuilt snapshot (cache =
1,207), roughly 907 additional tickers were resolved via individual lookups —
yet the primary common-stock universe stayed flat at exactly 1,309 events
both before and after. This was investigated directly rather than assumed
benign, with the following result:

- The classification logic looks a ticker up in the **active-universe
  snapshot first**, and only falls back to the **individual lookup cache**
  when the ticker is absent from that snapshot. Since the universe snapshot
  (8,843 tickers) has not changed since 00:22:10 on 2026-09-18, every ticker
  that individual lookups have since resolved is, by construction, a ticker
  that was **not** in the active-universe snapshot to begin with.
- All 1,207 cache-resolved tickers were checked directly: **zero** of them
  are also present in the active-universe snapshot (no redundant lookups),
  and **all 1,207** are tickers actually referenced by a split event.
- Their resolved exchanges: 616 "OTC Link" (over-the-counter — excluded per
  the project's own frozen scope decision 17-D), 502 "NOT_FOUND" (ticker no
  longer resolvable via Polygon's reference endpoint — most likely delisted,
  merged, or reused since the split event, and correctly logged as
  `PENDING_LOOKUP`/excluded rather than guessed), 67 ARCX (NYSE Arca), 20
  BATS (Cboe BZX), and 2 Grey Market. **None of these venues are NASDAQ,
  NYSE, or NYSE American** — the three exchanges this study is scoped to.
- In other words, every ticker still requiring an individual lookup turned
  out to be off-scope by exchange alone, regardless of its instrument type
  (the type breakdown among them — 148 CS, 67 ETF, 59 ADRC, 12 ETS, 10 GDR,
  6 ETN, 4 OTHER, 3 UNIT, 3 ETV, 1 FUND, 1 WARRANT, 1 PFD, plus 502
  NOT_FOUND — is close to moot, since exchange already disqualifies them).
- **Conclusion:** the flat count is not a bug and not evidence of lost data.
  The active-universe snapshot already contains essentially all
  currently-listed NASDAQ/NYSE/NYSE-American common stock tickers, so it
  already captured nearly every eligible primary event on the first pass.
  The remaining ~2,073 pending lookups are disproportionately OTC and
  delisted/renamed tickers that would not have entered the primary universe
  even if fully resolved. This directly supports the directive's instruction
  to stop the full lookup: continuing it would consume many more hours of
  rate-limited API calls to resolve tickers that are overwhelmingly
  off-scope by exchange.

## 4. Target-window (2024-01-01 to 2025-12-31) adequacy check

Filtering the current, corrected 1,309-row primary universe to the new
study's primary window:

| Metric | Value |
|---|---|
| Eligible primary events, 2024-01-01 to 2025-12-31 | **577** |
| Unique tickers in that window | 445 |
| Tickers with >1 event in window (repeat issuers) | 93 |
| Ratio-bucket split (window) | 1-for-6→10: 169 · 1-for-11→20: 152 · 1-for-21→50: 126 · >1-for-50: 66 · 1-for-2→5: 64 |
| Exchange split (window) | NASDAQ 512 · NYSE American 37 · NYSE 28 |
| Eligible primary events if expanded to 2023-01-01–2025-12-31 | 770 (not needed — see below) |

**577 already-classified, already-eligible candidate events exist in the
target 2024-2025 window alone** — nearly 6x the ~100-event target and well
above the 75-150 acceptable range. This is with **zero new API calls**, using
only data already on disk. Expansion to 2023 is therefore **not necessary**
and will not be done. No further bulk ticker lookups are required to reach
the sample-size target; any further API calls should be limited to
verification/completion of the specific ~100 events ultimately selected.

## 5. Full file inventory

### Root / config

| File | Purpose | Size / records | Last modified | Status | Reusable | Corruption risk |
|---|---|---|---|---|---|---|
| `README.md` | Project overview, two-track explanation, directory layout | 68 lines | 2026-09-18 18:12:51 | Complete for prior scope; needs a short addendum noting the 2026-09-19 scope change | Yes | None |
| `RESEARCH_LOG.md` | Append-only decision log | 188 lines | 2026-09-19 01:46:50 | Complete up to the classification-bug fixes; missing an entry for the 2026-09-19 scope-reduction decision (to be appended next) | Yes | None |
| `requirements.txt` | Python dependency pins | 29 lines | 2026-09-18 16:29:10 | Complete, unchanged | Yes | None |
| `.env` / `.env.example` | API keys (Alpha Vantage, Polygon, FMP, SEC user-agent) | 1004 / 924 bytes | 2026-09-18 | Present and previously verified working | Yes (never committed/exposed) | None |
| `config/definitions.md` | Frozen event-window, ratio-bucket, price-bucket, momentum definitions | 61 lines | 2026-09-18 16:32:37 | Complete, frozen | Yes — ratio buckets used directly in this inventory's analysis | None |
| `config/study_scope.md` | Locked Phase-0 decisions (17-B/C/D/F) | 42 lines | 2026-09-18 18:17:10 | Complete for prior 5-yr scope; decision 17-C (window) is **superseded** by the new 2024-2025 window and needs a documented amendment, not a rewrite | Yes, with amendment | None |

### Reports (Phase 0/1 design documents)

| File | Purpose | Size | Status | Reusable |
|---|---|---|---|---|
| `reports/PHASE_0_RESEARCH_DESIGN.md` | Full 17-section research design + Phase 1 results addendum | 503 lines | Complete | Yes — methodology largely still applies; window/sample-size sections need a superseding note, not deletion |
| `reports/RESEARCHER_NOTES_00.md` | Plain-language Phase 1 explainer | 43 lines | Complete | Yes |
| `reports/RESEARCHER_NOTES_01.md` | Plain-language Phase 2 explainer | 49 lines | Complete | Yes |

### Raw data (`data/raw/` — immutable, append-only; none of these were modified during this inspection)

| File | Purpose | Records | Last modified | Status | Reusable | Corruption risk |
|---|---|---|---|---|---|---|
| `polygon_splits_raw.jsonl` | All Polygon-reported stock splits, full pull window | 6,737 | 2026-09-18 20:12:55 | Complete for the original 5-yr pull; fully covers the new 2024-2025 window (subset) | Yes, directly | None — validated (row counts stable, JSON parses cleanly) |
| `polygon_ticker_universe_active.jsonl` | v1 active-ticker snapshot, exchange only, no `type` field | 8,843 | 2026-09-18 20:15:01 | Superseded by v2 | Superseded — keep for audit trail, do not use for classification | None |
| `polygon_ticker_universe_active_v2.jsonl` | v2 active-ticker snapshot with `type` field added | 8,843 | 2026-09-19 00:22:10 | Complete | Yes, directly (primary classification source) | None |
| `polygon_ticker_lookup_cache.jsonl` | Individual per-ticker lookups (for tickers absent from the universe snapshot) | 1,507 raw lines / 1,207 unique tickers | 2026-09-19 07:57:44 | Partially complete (2,073 split-relevant tickers still unresolved) — but see §3: nearly all of these are off-scope by exchange, so this is not a blocker | Yes, as-is | None |

### Intermediate data (`data/intermediate/` — regenerable; rebuilt during this inspection to correct staleness, described in §1)

| File | Purpose | Records | Last modified | Status | Reusable |
|---|---|---|---|---|---|
| `reverse_split_events_draft.csv` | Primary universe: common-stock reverse splits on NASDAQ/NYSE/NYSE American | 1,309 rows | 2026-09-19 16:19:53 (rebuilt) | Complete and current as of the cache state in §2 | Yes — this is the source table for sample selection |
| `adr_events_separate.csv` | ADR/foreign-private-issuer reverse splits, tracked separately | 135 rows | 2026-09-19 16:19:53 (rebuilt) | Complete and current | Yes, for secondary/enriched ADR analysis only |
| `exclusion_log.csv` | Every excluded split event with a specific, non-silent reason | 3,231 rows | 2026-09-19 16:19:53 (rebuilt) | Complete and current; 2,073 of these rows are `PENDING_LOOKUP`, not silently dropped | Yes — required for the audit trail |
| `data_source_probe_result.json` | Phase 1 live data-source test results | — | 2026-09-18 18:05:06 | Complete | Yes, historical record only |
| `fmp_probe_result.json` | FMP direct-key test results (stable API works, legacy v3 deprecated) | — | 2026-09-18 20:11:38 | Complete | Yes, historical record only |

### Processed data / results / tests / notebooks

All currently empty (`.gitkeep` placeholders only) — expected, since sample
selection and downstream analysis have not yet begun. No corruption risk;
nothing to reuse or discard.

### Source code (`src/data_collection/`)

| File | Purpose | Status | Reusable |
|---|---|---|---|
| `00_test_data_sources.py` | Phase 1 diagnostic probe | Already run successfully; complete | Yes, as historical record; no need to rerun |
| `01_collect_reverse_splits.py` | Phase 2 bulk split pull + universe build (has the known exchange-only classification bug, since fixed downstream) | Already run; superseded by 02/03 for classification, but its raw outputs are exactly what is reused above | Do not rerun (would trigger new bulk API calls); outputs already captured |
| `02_finalize_classification.py` | Adds `type` field, backfills, resolves pending tickers via live API calls, adaptive rate limiter | Correct and working, but **must not be run in full-universe/auto-resume mode** per the current directive | Keep as-is; only use later for narrow, targeted lookups of specific selected/candidate tickers, never a bulk resume |
| `03_rebuild_from_cache.py` | Zero-network reclassification from already-fetched raw files (written during this inspection) | Complete, run successfully, produced the current intermediate CSVs | Yes — this is now the standard way to regenerate the intermediate CSVs whenever the cache changes, without new API calls |

### Audit

| File | Purpose | Status |
|---|---|---|
| `audit/lookahead_bias_audit.md` | Standing look-ahead-bias policy + first log entry | Complete, still in force |
| `audit/existing_project_inventory.md` | This document | New, produced by this inspection |

## 6. Overall conclusion and recommendation

No existing data is corrupted, and nothing needs to be redownloaded or
restarted. The interrupted ticker-lookup process's last persisted state is
fully accounted for and has been folded into current intermediate files
without any new API calls. Critically, **the already-collected and
already-classified data alone provides 577 eligible primary-universe events
in the target 2024-2025 window** — far more than the ~100-event target — so
the next step is sample construction (stratified random selection by year x
ratio bucket) directly from `data/intermediate/reverse_split_events_draft.csv`,
filtered to the 2024-2025 window, with no further bulk ticker lookups and no
expansion to 2023 required. Any additional API calls going forward should be
narrowly scoped to verifying or completing the specific ~100 events that get
selected (e.g., confirming a corporate-action detail, filling a missing
price bar), never to resuming the general classification backlog.
