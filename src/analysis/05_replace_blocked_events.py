"""
Replace the events that a genuine data-access limitation makes unusable,
using the SAME deterministic, pre-registered methodology as the original
draw -- never chosen by looking at outcomes.

Discovery: after fetching Polygon daily aggregates for all 100 originally
selected events (06_fetch_event_prices_polygon.py), 18 of them returned
HTTP 403 "NOT_AUTHORIZED ... your plan doesn't include this data
timeframe" for BOTH adjusted and unadjusted requests. Inspecting the
boundary precisely: every event whose padded window started on or before
2024-03-29 failed, and every event whose padded window started on or
after 2024-04-24 succeeded. Since the window start is effective_date minus
55 calendar days, this means events with effective_date before
~2024-06-18 cannot be fetched at this Polygon plan's historical depth.
This is a plan-tier limitation, not a per-ticker data problem (it affects
every ticker in that date range regardless of size or exchange) and is
identical for both adjusted=true and adjusted=false requests.

This script:
  1. Reads which event_ids actually failed from
     data/raw/polygon_event_prices_raw.jsonl (the ground truth -- it does
     not hardcode the list), so it stays correct if the fetch is ever
     redone with a different plan or window.
  2. Marks those events selected=False with an explicit, non-outcome
     exclusion_reason (they remain in the file as eligible-but-unselected,
     per the brief's requirement -- nothing is deleted).
  3. For each excluded event, draws exactly one replacement from the SAME
     (year, ratio_bucket) stratum, restricted to events with
     effective_date >= 2024-06-18 (so the replacement is guaranteed
     fetchable), using a seeded RNG derived from the master seed plus the
     stratum -- deterministic and reproducible, decided purely by data
     availability and never by looking at any return/outcome data (this
     script reads no price or return data at all).
  4. Rewrites data/processed/sample_selection.csv in place (regenerable
     intermediate artifact) with the updated selected/reason columns for
     both the excluded originals and the new replacements.

Run with zero network calls, from the project root:
    python src/analysis/05_replace_blocked_events.py
"""
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PATH = REPO_ROOT / "data" / "processed" / "sample_selection.csv"
RAW_PRICES_PATH = REPO_ROOT / "data" / "raw" / "polygon_event_prices_raw.jsonl"

RANDOM_SEED = 20260919  # same master seed as 04_select_sample.py
REPLACEMENT_MIN_EFFECTIVE_DATE = "2024-06-18"  # empirically confirmed safe boundary

FIELDNAMES = [
    "event_id", "ticker", "company", "permanent_identifier", "effective_date",
    "split_from", "split_to", "normalized_reverse_split_ratio", "ratio_bucket",
    "exchange", "security_type", "selection_year", "selection_stratum",
    "random_seed", "selected", "eligibility_status", "inclusion_reason",
    "exclusion_reason",
]


def find_blocked_event_ids():
    if not RAW_PRICES_PATH.exists():
        raise SystemExit(f"{RAW_PRICES_PATH} not found -- run the price fetch first.")
    blocked = set()
    ok = set()
    with open(RAW_PRICES_PATH) as f:
        for line in f:
            rec = json.loads(line)
            resp = rec["response"]
            status = resp.get("status") if isinstance(resp, dict) else "NON_DICT"
            (ok if status == "OK" else blocked).add(rec["event_id"])
    # An event only counts as blocked if NEITHER fetch (raw or adjusted)
    # succeeded for it, i.e. it never appears in `ok`.
    return blocked - ok


def main():
    with open(SAMPLE_PATH, newline="") as f:
        rows = list(csv.DictReader(f))
    by_id = {r["event_id"]: r for r in rows}

    blocked_ids = find_blocked_event_ids()
    currently_selected_blocked = [
        eid for eid in blocked_ids if by_id[eid]["selected"] == "True"
    ]
    print(f"{len(blocked_ids)} event_ids returned no usable Polygon response.")
    print(f"{len(currently_selected_blocked)} of those were in the current selected set.")

    # Build the unselected-eligible pool, indexed by stratum, restricted to
    # the safe date range, excluding anything already selected.
    pool_by_stratum = defaultdict(list)
    for r in rows:
        if (
            r["selected"] == "False"
            and r["effective_date"] >= REPLACEMENT_MIN_EFFECTIVE_DATE
        ):
            pool_by_stratum[r["selection_stratum"]].append(r)

    replaced = []
    unfillable = []
    for eid in sorted(currently_selected_blocked):
        row = by_id[eid]
        stratum = row["selection_stratum"]
        row["selected"] = "False"
        row["inclusion_reason"] = ""
        row["exclusion_reason"] = (
            "excluded after selection: Polygon plan tier returned "
            "NOT_AUTHORIZED for this event's historical window "
            "(effective_date before ~2024-06-18 is outside this plan's "
            "historical depth) -- a data-access limitation discovered "
            "after the blind draw, not related to this event's outcome"
        )

        candidates = [
            r for r in pool_by_stratum.get(stratum, [])
            if r["event_id"] != eid and r["selected"] == "False"
        ]
        if not candidates:
            unfillable.append(eid)
            continue

        rng = random.Random(f"{RANDOM_SEED}:replacement:{stratum}:{eid}")
        replacement = rng.choice(candidates)
        replacement["selected"] = "True"
        replacement["inclusion_reason"] = (
            "stratified random replacement for "
            f"{eid} (excluded for Polygon data-access reasons); drawn "
            "from the same (year, ratio_bucket) stratum, restricted to "
            "dates with confirmed data availability, fixed seed, before "
            "any outcome data was examined"
        )
        replacement["exclusion_reason"] = ""
        replaced.append((eid, replacement["event_id"]))

    with open(SAMPLE_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nReplaced {len(replaced)} events:")
    for old, new in replaced:
        print(f"  {old}  ->  {new}")
    if unfillable:
        print(f"\nCould not find a same-stratum replacement for: {unfillable}")

    n_selected = sum(1 for r in rows if r["selected"] == "True")
    unique_companies = len(set(r["ticker"] for r in rows if r["selected"] == "True"))
    print(f"\nFinal selected count: {n_selected}")
    print(f"Unique companies: {unique_companies}")
    print(f"\nUpdated {SAMPLE_PATH}")
    print("Next: re-run src/data_collection/06_fetch_event_prices_polygon.py")
    print("(it skips already-fetched pairs, so this only fetches the new replacement tickers)")
    print("then src/data_collection/07_build_price_panel.py")


if __name__ == "__main__":
    main()
