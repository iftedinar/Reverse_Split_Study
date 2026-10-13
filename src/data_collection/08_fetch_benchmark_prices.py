"""
Fetch daily benchmark prices (SPY = broad market, IWM = small-cap) spanning
the full range needed to compute market-adjusted returns for every event in
the T-30..T+60 trading-day window, for the CURRENT (post-replacement)
100-event sample.

Only 2 tickers, 1 request each (adjusted=true only -- benchmarks are not
being validated for their own split ratios, so the raw/unadjusted series
is not needed here). This is the smallest additional dataset needed to
compute the market-adjusted return leg of the analysis (raw return,
market-adjusted return, and a same-universe equal-weight basket return are
the three series specified in PHASE_0_RESEARCH_DESIGN.md section 9); it is
not a resumption of the bulk ticker lookup and does not touch any
per-event data.

Date range is derived from the actual current sample (not hardcoded), with
the same 55/95 calendar-day padding used for individual events, so it
covers every event's T-30..T+60 window with room to spare.

Requires network (POLYGON_API_KEY in .env) -- run from your own terminal,
not via any automated shell that cannot reach the internet:
    python src/data_collection/08_fetch_benchmark_prices.py
"""
import csv
import json
import os
import time
import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    raise SystemExit("pip install requests")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PATH = REPO_ROOT / "data" / "processed" / "sample_selection.csv"
OUT_PATH = REPO_ROOT / "data" / "raw" / "polygon_benchmark_prices_raw.jsonl"

API_KEY = os.environ.get("POLYGON_API_KEY")
BASE_URL = "https://api.polygon.io"

BENCHMARK_TICKERS = ["SPY", "IWM"]
PRE_PAD_CALENDAR_DAYS = 55
POST_PAD_CALENDAR_DAYS = 95

FLOOR_CALLS_PER_MIN = 5
CEILING_CALLS_PER_MIN = 60


def load_sample_date_range():
    with open(SAMPLE_PATH, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["selected"] == "True"]
    if not rows:
        raise SystemExit(f"No selected=True rows found in {SAMPLE_PATH}")
    dates = sorted(r["effective_date"] for r in rows)
    return dates[0], dates[-1]


def already_fetched(ticker):
    if not OUT_PATH.exists():
        return False
    with open(OUT_PATH) as f:
        for line in f:
            rec = json.loads(line)
            if rec["ticker"] == ticker:
                return True
    return False


def fetch_one(ticker, window_start, window_end):
    url = (
        f"{BASE_URL}/v2/aggs/ticker/{ticker}/range/1/day/"
        f"{window_start}/{window_end}"
    )
    params = {"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": API_KEY}
    resp = requests.get(url, params=params, timeout=30)
    try:
        payload = resp.json()
    except ValueError:
        payload = {"status": "ERROR", "http_status": resp.status_code, "text": resp.text[:500]}
    if resp.status_code != 200 and "status" not in payload:
        payload["status"] = "ERROR"
        payload["http_status"] = resp.status_code
    return payload


def main():
    if not API_KEY:
        raise SystemExit("POLYGON_API_KEY not found in environment / .env")

    earliest_eff, latest_eff = load_sample_date_range()
    window_start = (
        datetime.date.fromisoformat(earliest_eff) - datetime.timedelta(days=PRE_PAD_CALENDAR_DAYS)
    ).isoformat()
    window_end = (
        datetime.date.fromisoformat(latest_eff) + datetime.timedelta(days=POST_PAD_CALENDAR_DAYS)
    ).isoformat()
    print(f"Sample effective_date range: {earliest_eff} .. {latest_eff}")
    print(f"Benchmark fetch window (with padding): {window_start} .. {window_end}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    calls_per_min = FLOOR_CALLS_PER_MIN
    consecutive_ok = 0

    for ticker in BENCHMARK_TICKERS:
        if already_fetched(ticker):
            print(f"{ticker}: already fetched, skipping.")
            continue

        print(f"Fetching {ticker} ...")
        payload = fetch_one(ticker, window_start, window_end)
        status = payload.get("status")

        rec = {
            "ticker": ticker,
            "window_start": window_start,
            "window_end": window_end,
            "adjusted": True,
            "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
            "response": payload,
        }
        with open(OUT_PATH, "a") as f:
            f.write(json.dumps(rec) + "\n")

        if status == "OK":
            n = payload.get("resultsCount", 0)
            print(f"  OK -- {n} daily bars")
            consecutive_ok += 1
            if consecutive_ok >= 20 and calls_per_min < CEILING_CALLS_PER_MIN:
                calls_per_min = min(CEILING_CALLS_PER_MIN, calls_per_min * 1.15)
                consecutive_ok = 0
        else:
            print(f"  {status}: {json.dumps(payload)[:300]}")
            consecutive_ok = 0
            if resp_is_429(payload):
                time.sleep(60)

        time.sleep(60.0 / calls_per_min)

    print(f"\nDone. Output: {OUT_PATH}")


def resp_is_429(payload):
    return payload.get("http_status") == 429 or payload.get("status") == "ERROR" and "429" in json.dumps(payload)


if __name__ == "__main__":
    main()
