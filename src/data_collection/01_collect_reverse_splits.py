"""
Phase 2, Task A - Full historical reverse-split event collection.

Purpose
-------
Build the raw reverse-split event universe for the locked 5-year window
(config/study_scope.md, decision 17-C), classify each event by exchange
(decision 17-D: OTC is logged, not silently dropped), and produce a first
draft master event table. This is RAW DISCOVERY ONLY - no price history,
filings, or float data yet. That's Phase 3 onward.

Design choices, and why
------------------------
- Polygon's /v3/reference/splits is paginated via `next_url`; the code
  follows it rather than trusting a single page (Phase 1 found the probe's
  single-page request hit its cap exactly).
- Exchange classification is two-tiered to keep API usage bounded:
    1. Fetch the full ACTIVE ticker universe for XNAS/XNYS/XASE once
       (a few thousand rows, a handful of pages) and match split-event
       tickers against it - free, one-time cost.
    2. For tickers NOT found in the active universe (likely delisted,
       ticker-changed, or genuinely OTC), do an individual ticker-detail
       lookup - the only per-ticker API calls in this script, and the only
       ones subject to a tight rate limit.
  This avoids one API call per split event (which would be slow) while
  still resolving delisted small-caps correctly instead of mislabeling
  every one of them "unknown."
- Because step 2 can be slow on a free-tier rate limit, it is capped per
  run (MAX_TICKER_LOOKUPS_PER_RUN) and cached to disk - re-running this
  script resumes rather than restarting, and reports how many are left.
- All raw API responses are appended to data/raw/ as-received and never
  edited in place, per the project's raw-data-immutability rule.

Everything here is discovery + classification. No conclusions, no
statistics - that starts in Phase 5+.
"""

import csv
import json
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

RAW_DIR = REPO_ROOT / "data" / "raw"
INTERMEDIATE_DIR = REPO_ROOT / "data" / "intermediate"
RAW_DIR.mkdir(parents=True, exist_ok=True)
INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)

SPLITS_RAW_PATH = RAW_DIR / "polygon_splits_raw.jsonl"
TICKER_UNIVERSE_PATH = RAW_DIR / "polygon_ticker_universe_active.jsonl"
TICKER_LOOKUP_CACHE_PATH = RAW_DIR / "polygon_ticker_lookup_cache.jsonl"
EXCLUSION_LOG_PATH = INTERMEDIATE_DIR / "exclusion_log.csv"
MASTER_DRAFT_PATH = INTERMEDIATE_DIR / "reverse_split_events_draft.csv"
FMP_PROBE_PATH = INTERMEDIATE_DIR / "fmp_probe_result.json"

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
FMP_API_KEY = os.getenv("FMP_API_KEY")

# Study window - locked in config/study_scope.md, decision 17-C.
WINDOW_YEARS = 5
WINDOW_END = date.today()
WINDOW_START = WINDOW_END.replace(year=WINDOW_END.year - WINDOW_YEARS)

LISTED_EXCHANGES = {"XNAS": "NASDAQ", "XNYS": "NYSE", "XASE": "NYSE American"}

# Conservative default for an unverified free-tier key; override in .env if
# you know your actual Polygon plan's rate limit (calls per minute).
POLYGON_CALLS_PER_MIN = int(os.getenv("POLYGON_CALLS_PER_MIN", "5"))
_MIN_INTERVAL = 60.0 / POLYGON_CALLS_PER_MIN
_last_call_ts = [0.0]

# How many individual ticker-detail lookups (the slow, rate-limited path)
# to run in a single invocation. Re-run the script to continue; the cache
# means already-looked-up tickers are never re-fetched.
MAX_TICKER_LOOKUPS_PER_RUN = int(os.getenv("MAX_TICKER_LOOKUPS_PER_RUN", "300"))


def _throttled_get(url: str, params: Optional[dict] = None) -> requests.Response:
    elapsed = time.monotonic() - _last_call_ts[0]
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    for attempt in range(5):
        resp = requests.get(url, params=params, timeout=30)
        _last_call_ts[0] = time.monotonic()
        if resp.status_code == 429:
            wait = float(resp.headers.get("Retry-After", 30))
            print(f"  rate limited (429) - waiting {wait:.0f}s (attempt {attempt + 1}/5)")
            time.sleep(wait)
            continue
        return resp
    return resp  # last attempt's response, even if still failing


def fetch_all_splits() -> list[dict]:
    print(f"Fetching Polygon splits {WINDOW_START} -> {WINDOW_END} ...")
    url = "https://api.polygon.io/v3/reference/splits"
    params = {
        "execution_date.gte": WINDOW_START.isoformat(),
        "execution_date.lte": WINDOW_END.isoformat(),
        "limit": 1000,
        "apiKey": POLYGON_API_KEY,
    }
    all_results = []
    page = 0
    with open(SPLITS_RAW_PATH, "a") as raw_f:
        while url:
            page += 1
            resp = _throttled_get(url, params=params if page == 1 else None)
            if resp.status_code != 200:
                print(f"  ERROR page {page}: HTTP {resp.status_code}: {resp.text[:200]}")
                break
            payload = resp.json()
            results = payload.get("results", [])
            for r in results:
                r["_fetched_at"] = datetime.utcnow().isoformat()
                raw_f.write(json.dumps(r) + "\n")
            all_results.extend(results)
            print(f"  page {page}: {len(results)} events (running total {len(all_results)})")
            next_url = payload.get("next_url")
            if next_url:
                sep = "&" if "?" in next_url else "?"
                url = f"{next_url}{sep}apiKey={POLYGON_API_KEY}"
                params = None
            else:
                url = None
    return all_results


def fetch_active_ticker_universe() -> dict:
    """Returns {ticker: {"exchange": mic, "name": company_name}} for all
    currently-active common stock on XNAS/XNYS/XASE."""
    universe = {}
    if TICKER_UNIVERSE_PATH.exists() and TICKER_UNIVERSE_PATH.stat().st_size > 0:
        print(f"Loading cached active-ticker universe from {TICKER_UNIVERSE_PATH.name} ...")
        with open(TICKER_UNIVERSE_PATH) as f:
            for line in f:
                row = json.loads(line)
                universe[row["ticker"]] = {"exchange": row["exchange"], "name": row.get("name", "")}
        return universe

    print("Fetching active ticker universe for XNAS/XNYS/XASE (one-time cost) ...")
    with open(TICKER_UNIVERSE_PATH, "a") as raw_f:
        for mic in LISTED_EXCHANGES:
            url = "https://api.polygon.io/v3/reference/tickers"
            params = {
                "market": "stocks",
                "exchange": mic,
                "active": "true",
                "limit": 1000,
                "apiKey": POLYGON_API_KEY,
            }
            page = 0
            while url:
                page += 1
                resp = _throttled_get(url, params=params if page == 1 else None)
                if resp.status_code != 200:
                    print(f"  ERROR {mic} page {page}: HTTP {resp.status_code}: {resp.text[:200]}")
                    break
                payload = resp.json()
                results = payload.get("results", [])
                for r in results:
                    row = {"ticker": r.get("ticker"), "exchange": mic, "name": r.get("name", "")}
                    raw_f.write(json.dumps(row) + "\n")
                    universe[row["ticker"]] = {"exchange": mic, "name": row["name"]}
                print(f"  {mic} page {page}: {len(results)} tickers (running total {len(universe)})")
                next_url = payload.get("next_url")
                if next_url:
                    sep = "&" if "?" in next_url else "?"
                    url = f"{next_url}{sep}apiKey={POLYGON_API_KEY}"
                    params = None
                else:
                    url = None
    return universe


def load_lookup_cache() -> dict:
    cache = {}
    if TICKER_LOOKUP_CACHE_PATH.exists():
        with open(TICKER_LOOKUP_CACHE_PATH) as f:
            for line in f:
                row = json.loads(line)
                cache[row["ticker"]] = row
    return cache


def lookup_ticker_detail(ticker: str, cache: dict, cache_file) -> dict:
    if ticker in cache:
        return cache[ticker]
    url = f"https://api.polygon.io/v3/reference/tickers/{ticker}"
    resp = _throttled_get(url, params={"apiKey": POLYGON_API_KEY})
    if resp.status_code == 200:
        r = resp.json().get("results", {}) or {}
        row = {
            "ticker": ticker,
            "found": True,
            "exchange": r.get("primary_exchange", "UNKNOWN"),
            "name": r.get("name", ""),
            "active": r.get("active"),
        }
    elif resp.status_code == 404:
        row = {"ticker": ticker, "found": False, "exchange": "NOT_FOUND", "name": "", "active": None}
    else:
        row = {"ticker": ticker, "found": False, "exchange": f"ERROR_{resp.status_code}", "name": "", "active": None}
    cache[ticker] = row
    cache_file.write(json.dumps(row) + "\n")
    cache_file.flush()
    return row


def classify_ratio_bucket(ratio: float) -> str:
    if ratio <= 5:
        return "1-for-2 to 1-for-5"
    if ratio <= 10:
        return "1-for-6 to 1-for-10"
    if ratio <= 20:
        return "1-for-11 to 1-for-20"
    if ratio <= 50:
        return "1-for-21 to 1-for-50"
    return "greater than 1-for-50"


def test_fmp() -> dict:
    if not FMP_API_KEY:
        return {"status": "skipped", "reason": "FMP_API_KEY not set"}
    probes = {
        "v3_quote_AAPL": "https://financialmodelingprep.com/api/v3/quote/AAPL",
        "v3_stock_split_AAPL": "https://financialmodelingprep.com/api/v3/historical-price-full/stock_split/AAPL",
        "stable_quote_AAPL": "https://financialmodelingprep.com/stable/quote",
        "stable_splits_AAPL": "https://financialmodelingprep.com/stable/splits",
    }
    results = {}
    for name, url in probes.items():
        params = {"apikey": FMP_API_KEY}
        if name.startswith("stable"):
            params["symbol"] = "AAPL"
        try:
            resp = requests.get(url, params=params, timeout=15)
            body_preview = resp.text[:200]
            results[name] = {
                "http_status": resp.status_code,
                "looks_blocked": "requires a higher plan" in resp.text.lower()
                or "not authorized" in resp.text.lower(),
                "body_preview": body_preview,
            }
        except requests.RequestException as exc:
            results[name] = {"error": str(exc)}
    return {"status": "ok", "probes": results}


def main() -> int:
    if not POLYGON_API_KEY:
        print("POLYGON_API_KEY not set in .env - cannot proceed.")
        return 1

    print(f"=== Study window: {WINDOW_START} to {WINDOW_END} (5 years, decision 17-C) ===\n")

    print("--- Step 0: FMP direct probe (decision 17-B) ---")
    fmp_result = test_fmp()
    FMP_PROBE_PATH.write_text(json.dumps(fmp_result, indent=2))
    print(f"FMP probe written to {FMP_PROBE_PATH.relative_to(REPO_ROOT)}\n")

    print("--- Step 1: Fetch all splits in window ---")
    splits = fetch_all_splits()
    print(f"Total split events fetched: {len(splits)}\n")

    print("--- Step 2: Build/load active ticker universe ---")
    universe = fetch_active_ticker_universe()
    print(f"Active ticker universe size: {len(universe)}\n")

    print("--- Step 3: Classify each event's exchange ---")
    lookup_cache = load_lookup_cache()
    tickers_needing_lookup = sorted(
        {s["ticker"] for s in splits if s["ticker"] not in universe and s["ticker"] not in lookup_cache}
    )
    print(
        f"{len(splits)} events; "
        f"{sum(1 for s in splits if s['ticker'] in universe)} matched active universe directly; "
        f"{len(tickers_needing_lookup)} need an individual lookup "
        f"({len(lookup_cache)} already cached from a prior run)."
    )

    todo = tickers_needing_lookup[:MAX_TICKER_LOOKUPS_PER_RUN]
    remaining = len(tickers_needing_lookup) - len(todo)
    if todo:
        print(f"Looking up {len(todo)} tickers this run (cap={MAX_TICKER_LOOKUPS_PER_RUN}) ...")
        with open(TICKER_LOOKUP_CACHE_PATH, "a") as cache_file:
            for i, t in enumerate(todo, 1):
                lookup_ticker_detail(t, lookup_cache, cache_file)
                if i % 25 == 0:
                    print(f"  looked up {i}/{len(todo)}")
    if remaining > 0:
        print(
            f"\n{remaining} tickers still need lookup - re-run this script to continue "
            f"(already-fetched tickers are cached and will be skipped)."
        )

    print("\n--- Step 4: Write master draft + exclusion log ---")
    master_rows = []
    exclusion_rows = []
    for s in splits:
        ticker = s["ticker"]
        split_from, split_to = s.get("split_from"), s.get("split_to")
        if not split_from or not split_to or split_from <= split_to:
            continue  # forward split or malformed row - not in scope for this study
        ratio = split_from / split_to

        if ticker in universe:
            exch_mic, name = universe[ticker]["exchange"], universe[ticker]["name"]
        elif ticker in lookup_cache:
            row = lookup_cache[ticker]
            exch_mic, name = row["exchange"], row["name"]
        else:
            exch_mic, name = "PENDING_LOOKUP", ""

        is_listed = exch_mic in LISTED_EXCHANGES
        record = {
            "polygon_id": s.get("id"),
            "ticker": ticker,
            "company_name": name,
            "effective_date": s.get("execution_date"),
            "split_from": split_from,
            "split_to": split_to,
            "ratio": round(ratio, 4),
            "ratio_bucket": classify_ratio_bucket(ratio),
            "exchange_mic": exch_mic,
            "exchange_name": LISTED_EXCHANGES.get(exch_mic, exch_mic),
            "in_primary_universe": is_listed,
            "source": "polygon",
        }
        if is_listed:
            master_rows.append(record)
        else:
            reason = (
                "pending individual ticker lookup (re-run script)"
                if exch_mic == "PENDING_LOOKUP"
                else f"not on NASDAQ/NYSE/NYSE American (resolved exchange: {exch_mic})"
            )
            exclusion_rows.append({**record, "exclusion_reason": reason})

    if master_rows:
        with open(MASTER_DRAFT_PATH, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(master_rows[0].keys()))
            writer.writeheader()
            writer.writerows(master_rows)
    if exclusion_rows:
        with open(EXCLUSION_LOG_PATH, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(exclusion_rows[0].keys()))
            writer.writeheader()
            writer.writerows(exclusion_rows)

    print(f"Primary-universe reverse-split events: {len(master_rows)} -> {MASTER_DRAFT_PATH.relative_to(REPO_ROOT)}")
    print(f"Excluded/pending events: {len(exclusion_rows)} -> {EXCLUSION_LOG_PATH.relative_to(REPO_ROOT)}")
    print("\nCollection pass complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
