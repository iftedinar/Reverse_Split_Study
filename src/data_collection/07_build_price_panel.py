"""
Deshape the raw Polygon per-event responses (data/raw/polygon_event_prices_raw.jsonl,
produced by 06_fetch_event_prices_polygon.py) into a clean, one-row-per-
(event, trading-day) panel with both raw and adjusted OHLCV side by side.

Zero network calls -- pure local reprocessing, same pattern as
03_rebuild_from_cache.py. Safe to re-run any time after the fetch script
adds more data; always rebuilds the full panel from the current raw file.

Output: data/intermediate/event_price_panel.csv with columns:
  event_id, ticker, effective_date, trading_date,
  raw_open, raw_high, raw_low, raw_close, raw_volume,
  adj_open, adj_high, adj_low, adj_close, adj_volume,
  trading_day_offset  (signed integer, 0 = first session on/after
    effective_date, negative = pre-event, positive = post-event; this is
    what the brief calls "event time T", computed here rather than
    assumed, since Polygon's calendar already reflects weekends/holidays)
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = REPO_ROOT / "data" / "raw" / "polygon_event_prices_raw.jsonl"
OUT_PATH = REPO_ROOT / "data" / "intermediate" / "event_price_panel.csv"

FIELDNAMES = [
    "event_id", "ticker", "effective_date", "trading_date",
    "raw_open", "raw_high", "raw_low", "raw_close", "raw_volume",
    "adj_open", "adj_high", "adj_low", "adj_close", "adj_volume",
    "trading_day_offset",
]


def bars_by_date(response):
    """Polygon aggs response -> {date_str: bar_dict}. Empty dict on any
    non-OK / missing-results response (never fabricates a bar)."""
    if not isinstance(response, dict) or response.get("resultsCount", 0) in (0, None):
        return {}
    results = response.get("results") or []
    out = {}
    import datetime
    for bar in results:
        # Polygon 't' is epoch ms UTC for the start of the aggregate window
        date_str = datetime.datetime.utcfromtimestamp(bar["t"] / 1000).strftime("%Y-%m-%d")
        out[date_str] = bar
    return out


def main():
    if not RAW_PATH.exists():
        raise SystemExit(
            f"{RAW_PATH} not found -- run 06_fetch_event_prices_polygon.py "
            "from your terminal first (it needs network access this session doesn't have)."
        )

    # event_id -> {"raw": response, "adjusted": response, "ticker":..., "effective_date":...}
    events = defaultdict(dict)
    with open(RAW_PATH) as f:
        for line in f:
            rec = json.loads(line)
            key = "adjusted" if rec["adjusted"] else "raw"
            events[rec["event_id"]][key] = rec["response"]
            events[rec["event_id"]]["ticker"] = rec["ticker"]
            events[rec["event_id"]]["effective_date"] = rec["effective_date"]

    out_rows = []
    incomplete = []
    for event_id, data in events.items():
        if "raw" not in data or "adjusted" not in data:
            incomplete.append(event_id)
            continue
        raw_bars = bars_by_date(data["raw"])
        adj_bars = bars_by_date(data["adjusted"])
        all_dates = sorted(set(raw_bars) | set(adj_bars))
        eff_date = data["effective_date"]

        # trading_day_offset: 0 = first date >= effective_date among dates
        # actually present in this ticker's own fetched series (so it is
        # never fabricated for a date with no data).
        dates_on_or_after = [d for d in all_dates if d >= eff_date]
        t0 = dates_on_or_after[0] if dates_on_or_after else None
        t0_idx = all_dates.index(t0) if t0 else None

        for idx, d in enumerate(all_dates):
            rb = raw_bars.get(d, {})
            ab = adj_bars.get(d, {})
            offset = (idx - t0_idx) if t0_idx is not None else ""
            out_rows.append({
                "event_id": event_id,
                "ticker": data["ticker"],
                "effective_date": eff_date,
                "trading_date": d,
                "raw_open": rb.get("o", ""), "raw_high": rb.get("h", ""),
                "raw_low": rb.get("l", ""), "raw_close": rb.get("c", ""),
                "raw_volume": rb.get("v", ""),
                "adj_open": ab.get("o", ""), "adj_high": ab.get("h", ""),
                "adj_low": ab.get("l", ""), "adj_close": ab.get("c", ""),
                "adj_volume": ab.get("v", ""),
                "trading_day_offset": offset,
            })

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"{len(events)} events found in raw file ({len(incomplete)} incomplete -- missing raw or adjusted fetch).")
    if incomplete:
        print("Incomplete event_ids (re-run the fetch script to complete):")
        for eid in incomplete[:20]:
            print(f"  {eid}")
    print(f"Wrote {len(out_rows)} (event, trading_date) rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
