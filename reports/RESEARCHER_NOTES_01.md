# Researcher Notes — Stage 1: Full Event Collection

## What we're testing

Whether we can turn "Polygon has reverse-split data" (confirmed in Phase 1,
one 30-day sample) into an actual, complete list of every reverse split on
NASDAQ, NYSE, and NYSE American over the last 5 years — correctly separating
those from OTC/foreign-listed tickers that happen to show up in the same
feed, rather than mixing them in.

## Why it matters

Everything downstream — the ratio-bucket analysis, the price/volume study,
the statistics — is only as good as this list. Getting a ticker's exchange
wrong means either polluting the primary NASDAQ/NYSE/NYSE American analysis
with an OTC stock that trades completely differently, or wrongly discarding
a real NASDAQ/NYSE event just because it happened to be delisted by the
time we checked.

## What the script does, in plain terms

1. Quickly tests your FMP key directly (four different endpoint URLs) to
   settle decision 17-B once and for all — does it work or not, and at
   which API version.
2. Pulls every split Polygon recorded between five years ago and today,
   paging through as many pages as it takes (Phase 1's probe only grabbed
   one page and undercounted).
3. Downloads the current roster of every actively-listed NASDAQ/NYSE/NYSE
   American stock once — this is the fast, cheap way to classify most
   events.
4. For any split-event ticker not found on that roster (usually because it
   was delisted, or it's genuinely OTC), it looks the ticker up
   individually. This is the one slow part, so it's capped at 300 lookups
   per run by default and remembers what it already checked — running it
   again continues rather than starting over.
5. Writes two files: the primary-universe draft event table, and an
   exclusion log for everything that isn't NASDAQ/NYSE/NYSE American (with
   a reason), so nothing disappears silently.

## How to interpret the result

- If `reverse_split_events_draft.csv` has a plausible number of rows for
  5 years (order of magnitude: low thousands, per the Phase 1 extrapolation)
  and `exclusion_log.csv` mostly shows OTC-looking tickers, the pipeline is
  working as designed.
- If the script reports remaining ticker lookups at the end, just run it
  again — it picks up where it left off.
- The `fmp_probe_result.json` file settles whether FMP is usable going
  forward; send it back along with the two CSVs.
