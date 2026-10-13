# Locked Study Scope Decisions

Decided 2026-09-18, in response to PHASE_0_RESEARCH_DESIGN.md §17. Changing
any of these after Phase 2 data collection has started must go through
RESEARCH_LOG.md with a dated rationale, not a silent edit here.

## 17-A — Bulk event-discovery source: RESOLVED (Phase 1)
Polygon.io `/v3/reference/splits` is primary. SEC EDGAR full-text search is
secondary (announcement dates, dilution/financing timeline later).

## 17-B — FMP
**Decision: test the existing FMP_API_KEY directly before deciding.**
`01_collect_reverse_splits.py` includes a one-call FMP capability probe
(a basic quote call + the stock-split-history call). If it works at this
key's tier, FMP becomes an optional third cross-check source. If it fails
the same way the MCP connector did in Phase 0, FMP is excluded and no
upgrade is purchased without a separate, explicit decision.

## 17-C — Research window length
**Decision: 5 years.** Window = today (2026-09-18) minus 5 years, i.e.
**2021-09-18 through 2026-09-18**. Revisit only if the resulting sample
size proves too small for the planned subgroup analyses (ratio x float x
price x market cap) — that would be a logged, dated decision, not a
default extension.

## 17-D — OTC-listed reverse splits
**Decision: log but exclude.** Every event is classified by exchange
(NASDAQ / NYSE / NYSE American / OTC / unknown). OTC and unknown-exchange
events are written to `data/intermediate/exclusion_log.csv` with a reason,
and excluded from the primary analysis population. They are never silently
dropped without a row in the exclusion log.

## 17-E — Frozen continuation/reversal definitions
Proceeding as drafted in `config/definitions.md` (extreme momentum,
continuation, failed momentum, reversal). No objection raised.

## 17-F — Intraday minute-data scope
**Decision: stratified subsample.** Once the full daily-event population
exists (Phase 2) and buckets are populated (ratio x float x price), draw
~300-500 events spanning every bucket combination for 1-minute intraday
collection (T-5 through T+10). Exact stratification method to be specified
in Phase 4, before intraday collection begins, and logged.
