"""
Fetch RAW (unadjusted) and split-adjusted daily OHLCV from Polygon for the
100 SELECTED events only (data/processed/sample_selection.csv, selected=True).

This is intentionally NOT a resumption of the full-universe ticker
classification backlog. It makes exactly 2 API calls per selected event
(adjusted=false and adjusted=true), ~200 calls total, each for a single
ticker's own bounded T-30..T+60 trading-day window. Per the 2026-09-19
scope-reduction directive, this is the kind of narrowly-scoped,
selected-event API use that IS allowed, in contrast to bulk ticker lookups.

Why this has to run here and not from the Cowork session: this project's
device_bash shell sits behind a proxy that blocks all outbound HTTPS
(confirmed earlier in this project against api.polygon.io and
www.google.com), so any script making real API calls must be run from the
researcher's own terminal, exactly like 01_collect_reverse_splits.py and
02_finalize_classification.py before it.

Output (written under data/raw/ — immutable/append-only, and
data/intermediate/ — regenerable):
  data/raw/polygon_event_prices_raw.jsonl
      One JSON line per (event_id, adjusted flag) API response, exactly as
      returned by Polygon (full aggs payload, not reprocessed). Appended,
      never overwritten, so re-running this script after a partial run
      does not lose prior progress -- it skips (event_id, adjusted) pairs
      already present in this file.
  data/intermediate/event_price_panel.csv
      One row per (event_id, trading_date), with both raw and adjusted
      OHLCV columns, built by 07_build_price_panel.py from the raw file
      (kept as a separate, explicit step so the raw fetch and the
      reshaping are independently auditable).

Requires: requests, python-dotenv, pandas-market-calendars (already in
requirements.txt). Run from the Reverse_Split_Study project root:
    python src/data_collection/06_fetch_event_prices_polygon.py
"""
import csv
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

SAMPLE_PATH = REPO_ROOT / "data" / "processed" / "sample_selection.csv"
RAW_OUT_PATH = REPO_ROOT / "data" / "raw" / "polygon_event_prices_raw.jsonl"

POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY")
if not POLYGON_API_KEY:
    raise SystemExit("POLYGON_API_KEY not found in .env -- aborting.")

# Padding in CALENDAR days around the effective date, generous enough to
# comfortably contain T-30 and T+60 TRADING days including weekends/holidays.
PRE_PAD_CALENDAR_DAYS = 55
POST_PAD_CALENDAR_DAYS = 95

# Same conservative-but-adaptive rate limiting approach as
# 02_finalize_classification.py: start slow, speed up on sustained 200s,
# back off hard and honor Retry-After on 429.
FLOOR_CALLS_PER_MIN = 5
CEILING_CALLS_PER_MIN = 60
_state = {"interval": 60.0 / FLOOR_CALLS_PER_MIN, "streak": 0, "last_call": 0.0}


def _throttle():
    elapsed = time.time() - _state["last_call"]
    if elapsed < _state["interval"]:
        time.sleep(_state["interval"] - elapsed)


def _record_success():
    _state["streak"] += 1
    if _state["streak"] % 20 == 0:
        _state["interval"] = max(60.0 / CEILING_CALLS_PER_MIN, _state["interval"] * 0.85)
    _state["last_call"] = time.time()


def _record_failure(retry_after=None):
    _state["streak"] = 0
    _state["interval"] = 60.0 / FLOOR_CALLS_PER_MIN
    _state["last_call"] = time.time()
    if retry_after:
        time.sleep(float(retry_after))


def load_selected_events():
    with open(SAMPLE_PATH, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["selected"] == "True"]
    return rows


def load_already_fetched():
    done = set()
    if RAW_OUT_PATH.exists():
        with open(RAW_OUT_PATH) as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    done.add((rec["event_id"], rec["adjusted"]))
                except (json.JSONDecodeError, KeyError):
                    continue
    return done


def fetch_aggs(ticker, start_date, end_date, adjusted):
    url = (
        f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/"
        f"{start_date}/{end_date}"
    )
    params = {
        "adjusted": "true" if adjusted else "false",
        "sort": "asc",
        "limit": 50000,
        "apiKey": POLYGON_API_KEY,
    }
    _throttle()
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code == 429:
        retry_after = resp.headers.get("Retry-After", 30)
        _record_failure(retry_after)
        return fetch_aggs(ticker, start_date, end_date, adjusted)
    if resp.status_code != 200:
        _record_failure()
        return {"status": "ERROR", "http_status": resp.status_code, "body": resp.text[:500]}
    _record_success()
    return resp.json()


def main():
    events = load_selected_events()
    already = load_already_fetched()
    print(f"{len(events)} selected events. {len(already)} (event_id, adjusted) pairs already fetched.")

    RAW_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fetched_this_run = 0
    errors = []

    with open(RAW_OUT_PATH, "a") as out_f:
        for i, ev in enumerate(events, 1):
            event_id = ev["event_id"]
            ticker = ev["ticker"]
            eff_date = ev["effective_date"]

            import datetime
            eff = datetime.datetime.strptime(eff_date, "%Y-%m-%d")
            start = (eff - datetime.timedelta(days=PRE_PAD_CALENDAR_DAYS)).strftime("%Y-%m-%d")
            end = (eff + datetime.timedelta(days=POST_PAD_CALENDAR_DAYS)).strftime("%Y-%m-%d")

            for adjusted in (False, True):
                key = (event_id, adjusted)
                if key in already:
                    continue
                print(f"[{i}/{len(events)}] {ticker} ({event_id}) adjusted={adjusted} ...")
                payload = fetch_aggs(ticker, start, end, adjusted)
                record = {
                    "event_id": event_id,
                    "ticker": ticker,
                    "effective_date": eff_date,
                    "adjusted": adjusted,
                    "window_start": start,
                    "window_end": end,
                    "fetched_at": datetime.datetime.utcnow().isoformat(),
                    "response": payload,
                }
                out_f.write(json.dumps(record) + "\n")
                out_f.flush()
                fetched_this_run += 1
                if payload.get("status") not in ("OK", "DELAYED"):
                    errors.append((ticker, event_id, adjusted, payload.get("status")))

    print(f"\nFetched {fetched_this_run} new (event_id, adjusted) pairs this run.")
    if errors:
        print(f"{len(errors)} non-OK responses (see raw file for detail):")
        for t, eid, adj, status in errors[:20]:
            print(f"  {t} {eid} adjusted={adj}: {status}")
    print(f"\nRaw responses appended to: {RAW_OUT_PATH}")
    print("Next step: run src/data_collection/07_build_price_panel.py (zero network calls)")
    print("to reshape this into data/intermediate/event_price_panel.csv.")


if __name__ == "__main__":
    main()
