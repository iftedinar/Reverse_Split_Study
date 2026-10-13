# Researcher Notes — Stage 0: Data Source Reconnaissance

## What we're testing

Whether we actually have a way to find *every* reverse stock split across
NASDAQ/NYSE/NYSE American over the last several years — as opposed to only
being able to look up a split for a ticker we already happen to know about.

## Why it matters

The entire study depends on having a complete, unbiased list of events.
If we can only check splits one ticker at a time, we'd have to already know
which several thousand small-cap tickers to check — which defeats the
purpose of doing a market-wide study rather than a hand-picked one.

## What we found (Phase 0)

- Alpha Vantage can confirm a split for a ticker we already name (it correctly
  reported NKLA's mid-2024 reverse split). It cannot list "every reverse
  split that happened in March 2024," for example.
- FMP, which would otherwise be able to do exactly that (a splits calendar),
  is locked behind a paid plan tier on the connected account.
- Polygon.io almost certainly can do this on its free tier, but nothing here
  is connected to it yet — that's the point of Phase 1's task.

## What the Phase 1 script does, in plain terms

It's a five-minute "does this actually work" check, not a real data pull.
It asks Polygon for a small window of recent splits, asks SEC EDGAR for a
small window of 8-K filings mentioning "reverse stock split," and re-confirms
Alpha Vantage works from your own machine the same way it did here. It
writes one small JSON file summarizing what worked.

## How to interpret the result

- If Polygon comes back with real reverse-split rows for the test window,
  we have our bulk source and can move to Phase 2 (build the full event
  database).
- If Polygon's free tier is more restricted than expected (e.g., no
  historical depth, or reverse-split identification isn't clean from
  `split_from`/`split_to`), we'll know that concretely instead of guessing,
  and can decide between an FMP upgrade, a different vendor, or a
  SEC-EDGAR-only approach (slower, but free and authoritative).
