# Look-Ahead Bias Audit — Study A: Reverse Split Momentum

This file is a living log, started 2026-09-18 (Phase 0, before any data
collection). Every entry below documents a decision point where "could a
trader have known this at this timestamp?" was asked, and what was done
about it. This file grows as the pipeline is built — it is not meant to be
complete on day one.

## Standing policy

1. Any variable used as a **predictive feature** (in matching, bucketing, or
   regression) must be computable using only information dated strictly
   before the timestamp it's attached to.
2. Any variable that is only knowable after the fact (e.g. T+5 return, the
   fact that a halt occurred on T+2, financing announced on T+10) may be
   used as an **outcome**, never as an input to a feature used to explain an
   earlier outcome.
3. News/catalyst classification must record its own timestamp and be
   excluded from any "what did the trader know at T" feature if that
   timestamp is after the relevant decision point.
4. Point-in-time float/shares data, where obtainable at all (see PHASE_0
   §5), must carry the filing date it came from — never today's float
   substituted for a historical date.

## Entries

- **2026-09-18** — Decision: `SPLITS` ratio and `effective_date` are treated
  as known exactly as of T (the effective date is definitionally public and
  mechanical — the split ratio is set in the company's own filed amendment).
  Announcement date (from 8-K) is captured separately and is the correct
  reference point for any "market reaction to the announcement" analysis,
  which is distinct from "market behavior around the effective date."
