"""
Rebuild classification CSVs from whatever is already on disk. Makes ZERO
network calls - this is pure local reprocessing of data/raw/ files that
were already fetched.

Why this exists: the lookup cache (polygon_ticker_lookup_cache.jsonl) grew
from 300 to 1,207 resolved tickers across several runs, but the
data/intermediate/*.csv files were last written when the cache only had
300 entries, so they're stale relative to what's actually been fetched.
Re-running 02_finalize_classification.py would also (correctly) try to
resolve more pending tickers with new API calls - which is NOT wanted
right now (per the 2026-09-19 scope change: stop the full-universe
lookup, work with what's already available). This script does ONLY the
classification/aggregation step, against the current on-disk cache,
with no network access at all.
"""
import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"
INTERMEDIATE_DIR = REPO_ROOT / "data" / "intermediate"

SPLITS_RAW_PATH = RAW_DIR / "polygon_splits_raw.jsonl"
UNIVERSE_V2_PATH = RAW_DIR / "polygon_ticker_universe_active_v2.jsonl"
LOOKUP_CACHE_PATH = RAW_DIR / "polygon_ticker_lookup_cache.jsonl"
EXCLUSION_LOG_PATH = INTERMEDIATE_DIR / "exclusion_log.csv"
MASTER_DRAFT_PATH = INTERMEDIATE_DIR / "reverse_split_events_draft.csv"
ADR_LOG_PATH = INTERMEDIATE_DIR / "adr_events_separate.csv"

LISTED_EXCHANGES = {"XNAS": "NASDAQ", "XNYS": "NYSE", "XASE": "NYSE American"}
COMMON_STOCK_TYPES = {"CS"}
ADR_TYPES = {"ADRC", "ADRP", "ADRR", "ADRW", "GDR", "NYRS"}


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


def main():
    splits = [json.loads(line) for line in open(SPLITS_RAW_PATH)]

    universe = {}
    with open(UNIVERSE_V2_PATH) as f:
        for line in f:
            row = json.loads(line)
            universe[row["ticker"]] = row

    cache = {}
    with open(LOOKUP_CACHE_PATH) as f:
        for line in f:
            row = json.loads(line)
            cache[row["ticker"]] = row  # later lines win

    print(f"Loaded: {len(splits)} raw splits, {len(universe)} universe tickers, {len(cache)} cached lookups.")

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
                reason = "pending individual ticker lookup (not being resumed per 2026-09-19 scope change)"
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

    print(f"Primary universe (common stock, listed): {len(master_rows)}")
    print(f"ADR/foreign-private-issuer (separate, listed): {len(adr_rows)}")
    print(f"Excluded (OTC/other exchange/non-common-stock/pending): {len(exclusion_rows)}")
    still_pending = sum(1 for r in exclusion_rows if r["exclusion_reason"].startswith("pending"))
    print(f"  of which still PENDING_LOOKUP: {still_pending}")


if __name__ == "__main__":
    main()
