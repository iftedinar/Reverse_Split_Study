"""
Construct the reproducible stratified random sample for the 2024-2025
exploratory reverse-split event study.

Design (per the 2026-09-19 scope-reduction directive):
  - Eligible population: primary-universe (common stock, NASDAQ/NYSE/NYSE
    American) reverse-split events with effective_date in
    [2024-01-01, 2025-12-31], drawn from the already-classified
    data/intermediate/reverse_split_events_draft.csv. No new API calls.
  - Stratified by (selection_year, ratio_bucket) -> up to 10 strata.
  - Allocation across strata is proportional to stratum size (largest-
    remainder rounding to hit the target total exactly), so naturally rare
    strata are not forced up to equal size.
  - Within a stratum, selection is randomized with a FIXED seed and
    prefers spreading across distinct companies: a shuffled pass first
    takes at most one event per ticker; only if a stratum's unique-ticker
    count is smaller than its quota does a second shuffled pass allow a
    second event from an already-picked ticker. This is a selection-order
    rule, not a filter - it never removes a repeated company from the
    eligible pool, and it is applied identically regardless of any event's
    subsequent performance (no outcome data is consulted at any point in
    this script).
  - ALL eligible events (selected or not) are written to
    data/processed/sample_selection.csv, per the requirement to preserve
    eligible-but-unselected events, not just the sample.

Eligibility here means: already resolved to primary universe (security_type
CS, listed on NASDAQ/NYSE/NYSE American) with a plausible ratio
(split_from > split_to, computed ratio > 1). No outcome/performance data of
any kind is read, computed, or referenced anywhere in this script - by
construction, cherry-picking on results is impossible here.
"""
import csv
import random
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DRAFT_PATH = REPO_ROOT / "data" / "intermediate" / "reverse_split_events_draft.csv"
OUT_PATH = REPO_ROOT / "data" / "processed" / "sample_selection.csv"

WINDOW_START = "2024-01-01"
WINDOW_END = "2025-12-31"
TARGET_N = 100
RANDOM_SEED = 20260919  # fixed; documented in RESEARCH_LOG.md

FIELDNAMES = [
    "event_id", "ticker", "company", "permanent_identifier", "effective_date",
    "split_from", "split_to", "normalized_reverse_split_ratio", "ratio_bucket",
    "exchange", "security_type", "selection_year", "selection_stratum",
    "random_seed", "selected", "eligibility_status", "inclusion_reason",
    "exclusion_reason",
]


def load_eligible_rows():
    with open(DRAFT_PATH, newline="") as f:
        rows = list(csv.DictReader(f))
    eligible = []
    for r in rows:
        d = r.get("effective_date", "")
        if not (WINDOW_START <= d <= WINDOW_END):
            continue
        eligible.append(r)
    return eligible


def build_strata(eligible_rows):
    strata = defaultdict(list)
    for r in eligible_rows:
        year = r["effective_date"][:4]
        stratum = f"{year}|{r['ratio_bucket']}"
        strata[stratum].append(r)
    return strata


def allocate_quotas(strata, target_n):
    total = sum(len(v) for v in strata.values())
    raw_quota = {k: len(v) * target_n / total for k, v in strata.items()}
    floor_quota = {k: int(v) for k, v in raw_quota.items()}
    allocated = sum(floor_quota.values())
    remainder = target_n - allocated
    # largest-remainder method distributes the leftover seats
    remainders = sorted(
        strata.keys(), key=lambda k: raw_quota[k] - floor_quota[k], reverse=True
    )
    for k in remainders[:remainder]:
        floor_quota[k] += 1
    # never allocate more than a stratum actually has
    for k in floor_quota:
        floor_quota[k] = min(floor_quota[k], len(strata[k]))
    return floor_quota


def select_within_stratum(rows, quota, rng):
    if quota <= 0:
        return set()
    by_ticker = defaultdict(list)
    for r in rows:
        by_ticker[r["ticker"]].append(r)

    tickers = list(by_ticker.keys())
    rng.shuffle(tickers)

    selected_ids = []
    # Pass 1: at most one event per ticker (pick the earliest-effective-date
    # event for that ticker within the stratum, for determinism once the
    # ticker order itself has been randomized).
    for t in tickers:
        if len(selected_ids) >= quota:
            break
        candidates = sorted(by_ticker[t], key=lambda r: r["effective_date"])
        selected_ids.append(candidates[0]["event_id"])

    # Pass 2 (only if the stratum has fewer unique tickers than its quota):
    # allow additional events, still randomized, from tickers' remaining
    # (not-yet-selected) events.
    if len(selected_ids) < quota:
        leftovers = []
        for t in tickers:
            already = {selected_ids[i] for i in range(len(selected_ids))}
            for r in sorted(by_ticker[t], key=lambda r: r["effective_date"])[1:]:
                leftovers.append(r["event_id"])
        rng.shuffle(leftovers)
        for eid in leftovers:
            if len(selected_ids) >= quota:
                break
            selected_ids.append(eid)

    return set(selected_ids)


def main():
    eligible_rows = load_eligible_rows()
    # Assign a stable event_id (ticker + effective_date + split ratio is
    # unique in this dataset; the polygon split id is also unique and is
    # reused directly where present).
    for r in eligible_rows:
        r["event_id"] = f"{r['ticker']}_{r['effective_date']}_{r['split_from']}to{r['split_to']}"

    strata = build_strata(eligible_rows)
    quotas = allocate_quotas(strata, TARGET_N)

    rng = random.Random(RANDOM_SEED)
    selected_ids = set()
    for stratum_key, rows in strata.items():
        # give each stratum its own child-seed derived from the master seed
        # and the stratum key, so results are reproducible per-stratum too
        stratum_rng = random.Random(f"{RANDOM_SEED}:{stratum_key}")
        selected_ids |= select_within_stratum(rows, quotas[stratum_key], stratum_rng)

    out_rows = []
    for r in eligible_rows:
        year = r["effective_date"][:4]
        stratum = f"{year}|{r['ratio_bucket']}"
        is_selected = r["event_id"] in selected_ids
        out_rows.append({
            "event_id": r["event_id"],
            "ticker": r["ticker"],
            "company": r["company_name"],
            "permanent_identifier": "PENDING_VERIFICATION",  # no CIK/FIGI in
            # already-fetched data; to be filled during per-event SEC EDGAR
            # verification (Validation Pass #1 / external spot checks), not
            # via a bulk lookup.
            "effective_date": r["effective_date"],
            "split_from": r["split_from"],
            "split_to": r["split_to"],
            "normalized_reverse_split_ratio": r["ratio"],
            "ratio_bucket": r["ratio_bucket"],
            "exchange": r["exchange_name"],
            "security_type": r["security_type"],
            "selection_year": year,
            "selection_stratum": stratum,
            "random_seed": RANDOM_SEED,
            "selected": is_selected,
            "eligibility_status": "ELIGIBLE",
            "inclusion_reason": (
                "stratified random draw (year x ratio bucket), fixed seed, "
                "selected before any outcome data was examined"
            ) if is_selected else "",
            "exclusion_reason": "" if is_selected else "eligible but not drawn in this sample round",
        })

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(out_rows)

    # ---- summary stats, printed for the log, no file outcome data used ----
    n_selected = sum(1 for r in out_rows if r["selected"])
    unique_companies = len(set(r["ticker"] for r in out_rows if r["selected"]))
    ticker_counts = defaultdict(int)
    for r in out_rows:
        if r["selected"]:
            ticker_counts[r["ticker"]] += 1
    repeat_issuers = sum(1 for t, c in ticker_counts.items() if c > 1)

    print(f"Eligible population (2024-2025 primary universe): {len(eligible_rows)}")
    print(f"Strata: {len(strata)}")
    for k in sorted(strata.keys()):
        print(f"  {k}: pool={len(strata[k])} quota={quotas[k]}")
    print(f"\nSelected events: {n_selected}")
    print(f"Unique companies among selected: {unique_companies}")
    print(f"Repeat-issuer tickers among selected (>1 event): {repeat_issuers}")

    exch_counts = defaultdict(int)
    bucket_counts = defaultdict(int)
    year_counts = defaultdict(int)
    for r in out_rows:
        if r["selected"]:
            exch_counts[r["exchange"]] += 1
            bucket_counts[r["ratio_bucket"]] += 1
            year_counts[r["selection_year"]] += 1
    print(f"\nSelected by exchange: {dict(exch_counts)}")
    print(f"Selected by ratio bucket: {dict(bucket_counts)}")
    print(f"Selected by year: {dict(year_counts)}")
    print(f"\nWrote {len(out_rows)} total rows (eligible + selected flag) to {OUT_PATH}")


if __name__ == "__main__":
    main()
