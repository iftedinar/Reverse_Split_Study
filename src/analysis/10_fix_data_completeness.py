"""
Round-2 data-completeness correction.

Round 1 (05_replace_blocked_events.py) only caught events where Polygon
returned an outright HTTP 403 for the whole request. Inspecting the
*actual* bars returned (not just the HTTP status) for the resulting
100-event panel reveals a second, more pervasive effect of the same
underlying cause: this Polygon plan provides daily history only from a
rolling ~2-years-before-today floor (empirically pinned at 2024-09-19,
observed as the earliest date returned by ANY request in the fetched
file, regardless of how much earlier window_start asked for). Requests
whose window_start falls before that floor still return HTTP 200 "OK",
but the results are silently clamped to start at the floor -- so an
event dated soon after the floor may have a technically-"OK" response
that is missing most or all of its T-30..T-1 pre-event window (in the
worst case, like VSME_2024-06-18, only 2 bars total, both ~3 months
after the actual effective date). Round 1's HTTP-status-only check could
not see this since it never inspected bar counts, only response status.

A second, unrelated and much rarer pattern also shows up: a handful of
events (independent of date) return zero or near-zero bars across the
*entire* requested window (pre AND post), e.g. GRDX, AVX, BGMS, FGNX --
most likely a ticker that does not match what Polygon has on file for
that date range (delisted immediately, ticker reused/changed, or a
genuine error in the underlying splits source record), or, for a few
2025 cases (DCX, AGPU), a stock with no trading history before its
own event -- i.e. the "reverse split" record likely coincides with a
new listing, which fails this study's implicit assumption of a
pre-existing trader base to measure momentum against.

This script re-derives completeness directly from the fetched bars
(data/intermediate/event_price_panel.csv), not from HTTP status, so it
catches both patterns. It is zero-network reprocessing.

Completeness bar (deliberately a little under the nominal T-30/T+60 to
tolerate market holidays, not to paper over real gaps):
    pre_count  (raw bars strictly before effective_date)  >= 28
    post_count (raw bars on/after effective_date)         >= 58

Any currently-selected event failing this bar is excluded with a reason
that distinguishes the two causes, and replaced with one same-(year,
ratio_bucket)-stratum draw from the remaining eligible-but-unselected
pool, restricted to effective_date >= NEW_SAFE_MIN_EFFECTIVE_DATE (chosen
from the observed transition: pre_count reaches a stable ~35-39 by
effective_date ~2024-11-04 and stays there, so 2024-11-15 leaves comfortable
margin, including a few days' slack for however long it takes to run the
next fetch). Same fixed master seed as every prior draw in this study.

This is Round 2 of the same non-outcome-based, transparent replacement
process as Round 1 -- reads no price/return data to decide which
*replacement* to draw (only completeness of the *currently selected*
event, which is a data-availability fact, not an outcome), same seeding
scheme, same "nothing is deleted, everything stays visible with a reason"
discipline.
"""
import csv
from collections import defaultdict
import random
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PATH = REPO_ROOT / "data" / "processed" / "sample_selection.csv"
PANEL_PATH = REPO_ROOT / "data" / "intermediate" / "event_price_panel.csv"
OUT_REPORT_PATH = REPO_ROOT / "audit" / "data_completeness_round2.csv"

RANDOM_SEED = 20260919
NEW_SAFE_MIN_EFFECTIVE_DATE = "2024-11-15"
PRE_MIN = 28
POST_MIN = 58

FIELDNAMES = [
    "event_id", "ticker", "company", "permanent_identifier", "effective_date",
    "split_from", "split_to", "normalized_reverse_split_ratio", "ratio_bucket",
    "exchange", "security_type", "selection_year", "selection_stratum",
    "random_seed", "selected", "eligibility_status", "inclusion_reason",
    "exclusion_reason",
]


def load_panel_by_event():
    by_event = defaultdict(list)
    with open(PANEL_PATH, newline="") as f:
        for row in csv.DictReader(f):
            by_event[row["event_id"]].append(row)
    return by_event


def completeness(rows, eff_date):
    pre = sum(1 for r in rows if r["trading_date"] < eff_date and r["raw_close"])
    post = sum(1 for r in rows if r["trading_date"] >= eff_date and r["raw_close"])
    return pre, post


def main():
    with open(SAMPLE_PATH, newline="") as f:
        rows = list(csv.DictReader(f))
    by_id = {r["event_id"]: r for r in rows}
    panel_by_event = load_panel_by_event()

    selected_ids = [eid for eid, r in by_id.items() if r["selected"] == "True"]
    report_rows = []
    failing = []

    for eid in selected_ids:
        r = by_id[eid]
        eff = r["effective_date"]
        panel_rows = panel_by_event.get(eid, [])
        pre, post = completeness(panel_rows, eff)
        complete = pre >= PRE_MIN and post >= POST_MIN
        cause = ""
        if not complete:
            if eff < NEW_SAFE_MIN_EFFECTIVE_DATE:
                cause = "polygon_2yr_clamp"
            else:
                cause = "anomalous_ticker_data_gap"
            failing.append((eid, cause, pre, post))
        report_rows.append({
            "event_id": eid, "effective_date": eff, "pre_count": pre, "post_count": post,
            "complete": complete, "cause": cause,
        })

    OUT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_REPORT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["event_id", "effective_date", "pre_count", "post_count", "complete", "cause"])
        writer.writeheader()
        writer.writerows(report_rows)

    print(f"Checked {len(selected_ids)} currently-selected events.")
    print(f"Complete: {len(selected_ids) - len(failing)}   Failing: {len(failing)}")
    clamp_n = sum(1 for _, c, _, _ in failing if c == "polygon_2yr_clamp")
    anomaly_n = sum(1 for _, c, _, _ in failing if c == "anomalous_ticker_data_gap")
    print(f"  -- polygon_2yr_clamp: {clamp_n}")
    print(f"  -- anomalous_ticker_data_gap: {anomaly_n}")

    # Build replacement pool: currently-unselected eligible rows with
    # effective_date >= the new safe threshold.
    pool_by_stratum = defaultdict(list)
    for r in rows:
        if r["selected"] == "False" and r["effective_date"] >= NEW_SAFE_MIN_EFFECTIVE_DATE:
            pool_by_stratum[r["selection_stratum"]].append(r)

    replaced = []
    unfillable = []
    for eid, cause, pre, post in sorted(failing):
        row = by_id[eid]
        stratum = row["selection_stratum"]
        row["selected"] = "False"
        row["inclusion_reason"] = ""
        if cause == "polygon_2yr_clamp":
            row["exclusion_reason"] = (
                "excluded after selection (round 2): this Polygon plan provides daily "
                "history only from a rolling ~2-years-before-fetch floor (empirically "
                f"~2024-09-19 at fetch time); this event's effective_date ({row['effective_date']}) "
                f"is too close to or before that floor to have a complete T-30 pre-event window "
                f"(only {pre} of a needed ~30 pre-event trading days were returned) -- a data-access "
                "limitation discovered by inspecting actual returned bars (round 1's HTTP-status-only "
                "check missed this because Polygon returns HTTP 200 with silently truncated data, not "
                "an error, when window_start precedes the floor), not related to this event's outcome"
            )
        else:
            row["exclusion_reason"] = (
                "excluded after selection (round 2): Polygon returned little or no usable "
                f"trading data for this ticker across the whole requested window ({pre} pre-event, "
                f"{post} post-event raw trading days), for reasons unrelated to the plan's date floor "
                "-- most likely a ticker/data mismatch in the source record, or (for events shortly "
                "after this ticker's own listing date) no pre-existing trading history to measure "
                "momentum against; flagged as a data-quality issue, not related to this event's outcome"
            )

        candidates = [
            r for r in pool_by_stratum.get(stratum, [])
            if r["event_id"] != eid and r["selected"] == "False"
        ]
        if not candidates:
            unfillable.append(eid)
            continue

        rng = random.Random(f"{RANDOM_SEED}:replacement_r2:{stratum}:{eid}")
        replacement = rng.choice(candidates)
        replacement["selected"] = "True"
        replacement["inclusion_reason"] = (
            "stratified random replacement (round 2) for "
            f"{eid} (excluded for Polygon data-completeness reasons: {cause}); drawn from the "
            "same (year, ratio_bucket) stratum, restricted to effective_date >= "
            f"{NEW_SAFE_MIN_EFFECTIVE_DATE} (empirically confirmed safe re: the plan's historical "
            "depth floor), fixed seed, before any outcome data for the replacement was examined"
        )
        replacement["exclusion_reason"] = ""
        # Remove the replacement from the pool for this stratum so it can't be drawn twice.
        pool_by_stratum[stratum] = [r for r in pool_by_stratum[stratum] if r["event_id"] != replacement["event_id"]]
        replaced.append((eid, replacement["event_id"]))

    with open(SAMPLE_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nReplaced {len(replaced)} events (round 2):")
    for old, new in replaced:
        print(f"  {old}  ->  {new}")
    if unfillable:
        print(f"\nCould not find a same-stratum replacement for: {unfillable}")

    n_selected = sum(1 for r in rows if r["selected"] == "True")
    unique_companies = len(set(r["ticker"] for r in rows if r["selected"] == "True"))
    print(f"\nFinal selected count: {n_selected}")
    print(f"Unique companies: {unique_companies}")
    print(f"\nUpdated {SAMPLE_PATH}")
    print(f"Wrote {OUT_REPORT_PATH}")
    print("\nNext: re-run src/data_collection/06_fetch_event_prices_polygon.py")
    print("(fetches only the new round-2 replacement tickers; everything else is already cached)")
    print("then src/data_collection/07_build_price_panel.py, then re-run this script once more")
    print("to confirm the new replacements are themselves complete (iterate if any anomalies recur).")


if __name__ == "__main__":
    main()
