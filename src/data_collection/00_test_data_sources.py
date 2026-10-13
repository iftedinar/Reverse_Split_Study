"""
Phase 1, Task A - Data source reconnaissance.

Purpose
-------
Before building the real reverse-split collection pipeline, confirm which
data sources are actually usable from THIS machine, with YOUR API keys.
This makes exactly a handful of API calls - it is a connectivity/capability
probe, not a bulk data pull.

What it checks
--------------
1. .env loads and reports which keys are present.
2. Polygon.io /v3/reference/splits - can we get a market-wide list of
   reverse splits for a small recent window? (candidate primary bulk source)
3. SEC EDGAR full-text search - can we find 8-K filings mentioning
   "reverse stock split" in the same window? (free, always-available
   cross-check / backfill source)
4. Alpha Vantage SPLITS - re-confirms the per-symbol lookup that was
   already verified working from Claude's session, this time from your
   own machine with your own key.

Output
------
Writes data/intermediate/data_source_probe_result.json and prints a summary.
Exits 0 on completion (even if individual sources fail - failures are
recorded in the JSON, not treated as fatal, since finding out a source
doesn't work is exactly the point of this script).
"""

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = REPO_ROOT / "data" / "intermediate" / "data_source_probe_result.json"

# A small, recent, fixed window - large enough to plausibly contain a few
# reverse splits, small enough to stay well within any free-tier rate limit.
WINDOW_DAYS = 30


def check_env() -> dict:
    load_dotenv(REPO_ROOT / ".env")
    keys = ["ALPHAVANTAGE_API_KEY", "POLYGON_API_KEY", "FMP_API_KEY", "SEC_USER_AGENT"]
    present = {k: bool(os.getenv(k)) for k in keys}
    return {"status": "ok", "keys_present": present}


def check_polygon() -> dict:
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        return {"status": "skipped", "reason": "POLYGON_API_KEY not set in .env"}

    end = date.today()
    start = end - timedelta(days=WINDOW_DAYS)
    url = "https://api.polygon.io/v3/reference/splits"
    params = {
        "execution_date.gte": start.isoformat(),
        "execution_date.lte": end.isoformat(),
        "limit": 50,
        "apiKey": api_key,
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
    except requests.RequestException as exc:
        return {"status": "error", "reason": f"request failed: {exc}"}

    if resp.status_code != 200:
        return {"status": "error", "reason": f"HTTP {resp.status_code}: {resp.text[:300]}"}

    payload = resp.json()
    results = payload.get("results", [])
    reverse_splits = [r for r in results if r.get("split_from", 0) > r.get("split_to", 0)]
    forward_splits = [r for r in results if r.get("split_from", 0) < r.get("split_to", 0)]

    return {
        "status": "ok",
        "window": {"from": start.isoformat(), "to": end.isoformat()},
        "total_events_returned": len(results),
        "reverse_split_count": len(reverse_splits),
        "forward_split_count": len(forward_splits),
        "sample_reverse_splits": reverse_splits[:3],
        "note": "If total_events_returned is 0, widen WINDOW_DAYS or check "
        "whether the free tier restricts this endpoint's date range.",
    }


def check_sec_edgar() -> dict:
    user_agent = os.getenv("SEC_USER_AGENT")
    if not user_agent or "@" not in user_agent:
        return {
            "status": "skipped",
            "reason": "SEC_USER_AGENT missing or does not look like 'Name email@example.com'",
        }

    end = date.today()
    start = end - timedelta(days=WINDOW_DAYS)
    url = "https://efts.sec.gov/LATEST/search-index"
    params = {
        "q": '"reverse stock split"',
        "forms": "8-K",
        "dateRange": "custom",
        "startdt": start.isoformat(),
        "enddt": end.isoformat(),
    }
    headers = {"User-Agent": user_agent}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
    except requests.RequestException as exc:
        return {"status": "error", "reason": f"request failed: {exc}"}

    if resp.status_code != 200:
        return {
            "status": "error",
            "reason": f"HTTP {resp.status_code}: {resp.text[:300]}",
            "hint": "403 usually means SEC_USER_AGENT was rejected - it must "
            "look like a real name + email, not a generic string.",
        }

    payload = resp.json()
    hits = payload.get("hits", {}).get("hits", [])
    sample = []
    for h in hits[:3]:
        src = h.get("_source", {})
        sample.append(
            {
                "display_names": src.get("display_names"),
                "file_date": src.get("file_date"),
                "form": src.get("root_forms") or src.get("form"),
            }
        )

    return {
        "status": "ok",
        "window": {"from": start.isoformat(), "to": end.isoformat()},
        "total_hits": payload.get("hits", {}).get("total", {}).get("value"),
        "sample_hits": sample,
    }


def check_alpha_vantage() -> dict:
    api_key = os.getenv("ALPHAVANTAGE_API_KEY")
    if not api_key:
        return {"status": "skipped", "reason": "ALPHAVANTAGE_API_KEY not set in .env"}

    # NKLA is used only because Claude already confirmed, live, on 2026-09-18,
    # that it has a real recorded reverse split (2024-06-25, split_factor
    # 0.0333) - this call re-verifies the SAME source is reachable from your
    # machine, it does not assert any new fact about NKLA.
    test_symbol = "NKLA"
    url = "https://www.alphavantage.co/query"
    params = {"function": "SPLITS", "symbol": test_symbol, "apikey": api_key}
    try:
        resp = requests.get(url, params=params, timeout=15)
    except requests.RequestException as exc:
        return {"status": "error", "reason": f"request failed: {exc}"}

    if resp.status_code != 200:
        return {"status": "error", "reason": f"HTTP {resp.status_code}: {resp.text[:300]}"}

    payload = resp.json()
    if "Note" in payload or "Information" in payload:
        return {"status": "rate_limited", "raw": payload}

    return {"status": "ok", "test_symbol": test_symbol, "raw": payload}


def main() -> int:
    result = {
        "generated_at": date.today().isoformat(),
        "env": check_env(),
        "polygon": check_polygon(),
        "sec_edgar": check_sec_edgar(),
        "alpha_vantage": check_alpha_vantage(),
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, indent=2, default=str))

    print(json.dumps(result, indent=2, default=str))
    print(f"\nProbe complete - see {OUT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
