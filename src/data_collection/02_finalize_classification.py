"""
Phase 2, Task B - Fix instrument-type classification and finalize the
reverse-split event universe.

Why this script exists
-----------------------
01_collect_reverse_splits.py classified events by EXCHANGE only. Inspecting
its output turned up leveraged/inverse single-stock ETFs (e.g. a "2X Daily
Target" fund) sitting in the "primary universe" file alongside genuine
common stocks - these funds reverse-split routinely as a NAV-management
mechanic, which is a completely different phenomenon from the small-cap,
compliance-driven reverse splits this study is about. The brief is explicit
that ETFs, ETNs, closed-end funds, preferred shares, warrants, rights,
units, and SPAC units must be excluded or separately classified, never
silently folded into the common-stock population - so this needed fixing
before anything downstream (validation, price collection, statistics) was
built on top of it.

Revision 2 (this version)
--------------------------
The first version of this script shared one per-run lookup budget between
two very different jobs: (a) a one-time backfill of the `type` field onto
the 300 tickers script 01 had already resolved by exchange only, and (b)
resolving brand-new pending tickers. Because both were pulled from one
alphabetically-sorted list and capped together, a run's entire budget could
be consumed by (a) and make almost no progress on (b) - which is exactly
what happened (2,670 pending tickers going into a run, 2,446 still pending
coming out, despite the cap being 300).

Fix: the two jobs are now separate steps. Step 3a does the type backfill
once, to completion, regardless of the main cap (it's bounded by the
original 300 anyway, so it's cheap). Step 3b then spends the FULL
per-run cap on brand-new tickers only.

This version also self-tunes its request rate instead of guessing:
it starts at the same conservative 5-calls/minute default, and speeds up
gradually as long as Polygon keeps returning 200s, backing off immediately
and respecting `Retry-After` the moment a 429 appears. This matters because
nobody here actually knows this Polygon plan's true rate limit, and at a
fixed conservative guess the remaining ~2,446 lookups could take 8+ hours;
if the plan supports more throughput, this finds that out empirically
instead of the researcher having to guess and re-run repeatedly.

Still reuses data/raw/polygon_splits_raw.jsonl as-is (no re-fetch), and
still appends to (never rewrites) the raw ticker-universe and lookup-cache
files - only data/intermediate/*.csv are overwritten, since those are
expected to improve as the pipeline is corrected.
"""

import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

RAW_DIR = REPO_ROOT / "data" / "raw"
INTERMEDIATE_DIR = REPO_ROOT / "data" / "intermediate"

SPLITS_RAW_PATH = RAW_DIR / "polygon_splits_raw.jsonl"
UNIVERSE_V2_PATH = RAW_DIR / "polygon_ticker_universe_active_v2.jsonl"
LOOKUP_CACHE_PATH = RAW_DIR / "polygon_ticker_lookup_cache.jsonl"
EXCLUSION_LOG_PATH = INTERMEDIATE_DIR / "exclusion_log.csv"
MASTER_DRAFT_PATH = INTERMEDIATE_DIR / "reverse_split_events_draft.csv"
ADR_LOG_PATH = INTERMEDIATE_DIR / "adr_events_separate.csv"

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
LISTED_EXCHANGES = {"XNAS": "NASDAQ", "XNYS": "NYSE", "XASE": "NYSE American"}

# Adaptive rate limiter: starts conservative, speeds up on sustained success,
# snaps back to conservative (and further, per Retry-After) on any 429.
FLOOR_CALLS_PER_MIN = int(os.getenv("POLYGON_CALLS_PER_MIN", "5"))
CEILING_CALLS_PER_MIN = int(os.getenv("POLYGON_CALLS_PER_MIN_CEILING", "60"))
_state = {"interval": 60.0 / FLOOR_CALLS_PER_MIN, "streak": 0, "last_call": 0.0}
_MIN_POSSIBLE_INTERVAL = 60.0 / CEILING_CALLS_PER_MIN
_MAX_INTERVAL = 60.0 / FLOOR_CALLS_PER_MIN

# Raised from 300: with ~2,446 tickers still pending, a small cap just means
# many more back-and-forth runs. This is safe to set very high - every result
# is written and flushed immediately, so interrupting the script (Ctrl+C) at
# any point loses nothing already fetched.
MAX_TICKER_LOOKUPS_PER_RUN = int(os.getenv("MAX_TICKER_LOOKUPS_PER_RUN", "5000"))


def _throttled_get(url: str, params: Optional[dict] = None) -> requests.Response:
    elapsed = time.monotonic() - _state["last_call"]
    if elapsed < _state["interval"]:
        time.sleep(_state["interval"] - elapsed)
    for attempt in range(5):
        resp = requests.get(url, params=params, timeout=30)
        _state["last_call"] = time.monotonic()
        if resp.status_code == 429:
            wait = float(resp.headers.get("Retry-After", 30))
            print(f"  rate limited (429) - backing off to {FLOOR_CALLS_PER_MIN}/min, waiting {wait:.0f}s")
            _state["interval"] = _MAX_INTERVAL
            _state["streak"] = 0
            time.sleep(wait)
            continue
        # Sustained success: speed up gradually, capped at the ceiling.
        _state["streak"] += 1
        if _state["streak"] >= 20 and _state["interval"] > _MIN_POSSIBLE_INTERVAL:
            _state["interval"] = max(_MIN_POSSIBLE_INTERVAL, _state["interval"] * 0.85)
            _state["streak"] = 0
            print(f"  no rate-limit errors in a while - speeding up to ~{60/_state['interval']:.1f} calls/min")
        return resp
    return resp


def load_raw_splits() -> list[dict]:
    with open(SPLITS_RAW_PATH) as f:
        return [json.loads(line) for line in f]


def fetch_universe_v2() -> dict:
    universe = {}
    if UNIVERSE_V2_PATH.exists() and UNIVERSE_V2_PATH.stat().st_size > 0:
        print(f"Loading cached v2 universe from {UNIVERSE_V2_PATH.name} ...")
        with open(UNIVERSE_V2_PATH) as f:
            for line in f:
                row = json.loads(line)
                universe[row["ticker"]] = row
        return universe

    print("Fetching v2 active ticker universe (with type) for XNAS/XNYS/XASE ...")
    with open(UNIVERSE_V2_PATH, "a") as raw_f:
        for mic in LISTED_EXCHANGES:
            url = "https://api.polygon.io/v3/reference/tickers"
            params = {"market": "stocks", "exchange": mic, "active": "true", "limit": 1000, "apiKey": POLYGON_API_KEY}
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
                    row = {"ticker": r.get("ticker"), "exchange": mic, "name": r.get("name", ""), "type": r.get("type", "UNKNOWN")}
                    raw_f.write(json.dumps(row) + "\n")
                    universe[row["ticker"]] = row
                print(f"  {mic} page {page}: {len(results)} tickers (running total {len(universe)})")
                next_url = payload.get("next_url")
                if next_url:
                    sep = "&" if "?" in next_url else "?"
                    url, params = f"{next_url}{sep}apiKey={POLYGON_API_KEY}", None
                else:
                    url = None
    return universe


def load_lookup_cache() -> dict:
    cache = {}
    if LOOKUP_CACHE_PATH.exists():
        with open(LOOKUP_CACHE_PATH) as f:
            for line in f:
                row = json.loads(line)
                cache[row["ticker"]] = row  # later lines win
    return cache


def lookup_ticker_detail(ticker: str, cache: dict, cache_file) -> dict:
    url = f"https://api.polygon.io/v3/reference/tickers/{ticker}"
    resp = _throttled_get(url, params={"apiKey": POLYGON_API_KEY})
    if resp.status_code == 200:
        r = resp.json().get("results", {}) or {}
        row = {"ticker": ticker, "found": True, "exchange": r.get("primary_exchange", "UNKNOWN"),
               "name": r.get("name", ""), "type": r.get("type", "UNKNOWN"), "active": r.get("active")}
    elif resp.status_code == 404:
        row = {"ticker": ticker, "found": False, "exchange": "NOT_FOUND", "name": "", "type": "NOT_FOUND", "active": None}
    else:
        row = {"ticker": ticker, "found": False, "exchange": f"ERROR_{resp.status_code}", "name": "", "type": "UNKNOWN", "active": None}
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


COMMON_STOCK_TYPES = {"CS"}
ADR_TYPES = {"ADRC", "ADRP", "ADRR", "ADRW", "GDR", "NYRS"}


def main() -> int:
    if not POLYGON_API_KEY:
        print("POLYGON_API_KEY not set in .env - cannot proceed.")
        return 1

    print("--- Step 1: Load existing raw splits (no new API calls) ---")
    splits = load_raw_splits()
    print(f"{len(splits)} raw split events loaded.\n")

    print("--- Step 2: Fetch/load v2 ticker universe (with type) ---")
    universe = fetch_universe_v2()
    print(f"v2 universe size: {len(universe)}\n")

    cache = load_lookup_cache()
    all_tickers = {s["ticker"] for s in splits}

    print("--- Step 3a: One-time type backfill for previously-cached entries ---")
    needing_refresh = [t for t, row in cache.items() if "type" not in row]
    print(f"{len(needing_refresh)} cached tickers still need a type backfill.")
    if needing_refresh:
        with open(LOOKUP_CACHE_PATH, "a") as cache_file:
            for i, t in enumerate(needing_refresh, 1):
                lookup_ticker_detail(t, cache, cache_file)
                if i % 25 == 0:
                    print(f"  backfilled {i}/{len(needing_refresh)}")

    print("\n--- Step 3b: Resolve brand-new pending tickers (full budget) ---")
    still_unresolved = sorted(t for t in all_tickers if t not in universe and t not in cache)
    todo = still_unresolved[:MAX_TICKER_LOOKUPS_PER_RUN]
    remaining = len(still_unresolved) - len(todo)
    print(f"{len(still_unresolved)} tickers unresolved; processing {len(todo)} this run (cap={MAX_TICKER_LOOKUPS_PER_RUN}).")
    if todo:
        with open(LOOKUP_CACHE_PATH, "a") as cache_file:
            for i, t in enumerate(todo, 1):
                lookup_ticker_detail(t, cache, cache_file)
                if i % 50 == 0:
                    print(f"  looked up {i}/{len(todo)} (current rate ~{60/_state['interval']:.1f}/min)")
    if remaining > 0:
        print(f"\n{remaining} tickers still need lookup - re-run this script to continue.")
    else:
        print("\nAll tickers resolved.")

    print("\n--- Step 4: Classify every reverse-split event (exchange + type) ---")
    master_rows, adr_rows, exclusion_rows = [], [], []
    for s in splits:
        ticker = s["ticker"]
        split_from, split_to = s.get("split_from"), s.get("split_to")
        if not split_from or not split_to or split_from <= split_to:
            continue
        ratio = split_from / split_to

        info = universe.get(ticker) or cache.get(ticker)
        if info is None:
            exch_mic, name, sec_type = "PENDING_LOOKUP", "", "PENDING_LOOKUP"
        else:
            exch_mic, name, sec_type = info.get("exchange", "UNKNOWN"), info.get("name", ""), info.get("type", "UNKNOWN")

        record = {
            "polygon_id": s.get("id"), "ticker": ticker, "company_name": name,
            "effective_date": s.get("execution_date"), "split_from": split_from, "split_to": split_to,
            "ratio": round(ratio, 4), "ratio_bucket": classify_ratio_bucket(ratio),
            "exchange_mic": exch_mic, "exchange_name": LISTED_EXCHANGES.get(exch_mic, exch_mic),
            "security_type": sec_type, "source": "polygon",
        }
        is_listed = exch_mic in LISTED_EXCHANGES
        if is_listed and sec_type in COMMON_STOCK_TYPES:
            master_rows.append(record)
        elif is_listed and sec_type in ADR_TYPES:
            adr_rows.append({**record, "note": "ADR/foreign-private-issuer instrument - tracked separately per brief; inclusion decision pending"})
        else:
            if exch_mic == "PENDING_LOOKUP":
                reason = "pending individual ticker lookup (re-run script)"
            elif not is_listed:
                reason = f"not on NASDAQ/NYSE/NYSE American (resolved exchange: {exch_mic})"
            else:
                reason = f"not a common stock (security_type: {sec_type})"
            exclusion_rows.append({**record, "exclusion_reason": reason})

    for path, rows in [(MASTER_DRAFT_PATH, master_rows), (ADR_LOG_PATH, adr_rows), (EXCLUSION_LOG_PATH, exclusion_rows)]:
        if rows:
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)

    print(f"Primary universe (common stock, listed): {len(master_rows)} -> {MASTER_DRAFT_PATH.relative_to(REPO_ROOT)}")
    print(f"ADR/foreign-private-issuer (separate, listed): {len(adr_rows)} -> {ADR_LOG_PATH.relative_to(REPO_ROOT)}")
    print(f"Excluded (OTC/other exchange/non-common-stock/pending): {len(exclusion_rows)} -> {EXCLUSION_LOG_PATH.relative_to(REPO_ROOT)}")
    print("\nClassification pass complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
