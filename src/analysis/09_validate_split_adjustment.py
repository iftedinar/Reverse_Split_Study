"""
Validate, for every selected event, that Polygon's internal split-
adjustment factor at the effective date matches this study's documented
reverse-split ratio.

Corrected methodology (v2): the first version of this script compared
raw_close[T-1] to raw_close[T0] directly, and separately compared
adj_close[T-1] to adj_close[T0] -- but that second comparison actually
measures the event's real T-1-to-T0 price *return* (which is expected to
be large and volatile for these stocks -- that IS the phenomenon under
study), not an adjustment error, so it produced a flood of false
"WARNING"/"FAIL" results that had nothing to do with data quality.

The correct, return-independent test isolates the mechanical adjustment
factor at each single day: factor(day) = adj_close(day) / raw_close(day).
For a day before the split, factor_pre should equal the documented ratio
times any subsequent cumulative adjustment; for a day on/after the split,
factor_post should equal that same subsequent cumulative adjustment
alone. Their ratio, factor_pre / factor_post, cancels out any later
adjustment and should equal ONLY the documented ratio for this specific
event -- a pure mechanical check, unaffected by the size of the real
T-1-to-T0 return.

Zero-network reprocessing of already-fetched data.
Output: audit/split_adjustment_validation.csv (one row per event).

Classification:
  PASS    -- factor-implied ratio within 2% of documented ratio (this is
             a mechanical calculation, so it should match almost exactly;
             a few % of slack covers rounding in the source bars)
  WARNING -- within 10% (rounding/data quirk worth a manual glance)
  FAIL    -- >10% off, or T-1/T0 raw or adjusted data missing
"""
import csv
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PATH = REPO_ROOT / "data" / "processed" / "sample_selection.csv"
PANEL_PATH = REPO_ROOT / "data" / "intermediate" / "event_price_panel.csv"
OUT_PATH = REPO_ROOT / "audit" / "split_adjustment_validation.csv"

FIELDNAMES = [
    "event_id", "ticker", "effective_date", "documented_ratio",
    "raw_close_t_minus_1", "raw_close_t0", "raw_close_return_pct",
    "adj_close_t_minus_1", "adj_close_t0", "adj_close_return_pct",
    "factor_pre", "factor_post", "factor_implied_ratio", "factor_pct_diff",
    "classification", "notes",
]


def load_panel_by_event():
    by_event = defaultdict(list)
    with open(PANEL_PATH, newline="") as f:
        for row in csv.DictReader(f):
            by_event[row["event_id"]].append(row)
    for eid in by_event:
        by_event[eid].sort(key=lambda r: r["trading_date"])
    return by_event


def find_offset_rows(rows, target_offsets):
    out = {}
    for r in rows:
        off = r["trading_day_offset"]
        if off == "":
            continue
        off = int(off)
        if off in target_offsets:
            out[off] = r
    return out


def classify(pct_diff):
    if pct_diff is None:
        return "FAIL", "missing T-1 or T0 raw/adjusted data"
    if pct_diff <= 0.02:
        return "PASS", ""
    if pct_diff <= 0.10:
        return "WARNING", "small mismatch between Polygon's adjustment factor and the documented ratio -- worth a manual glance"
    return "FAIL", "Polygon's adjustment factor does not match the documented ratio -- check for a wrong ratio, wrong effective date, or an intervening corporate action"


def main():
    with open(SAMPLE_PATH, newline="") as f:
        sample_rows = [r for r in csv.DictReader(f) if r["selected"] == "True"]

    panel_by_event = load_panel_by_event()
    out_rows = []
    counts = defaultdict(int)

    for s in sample_rows:
        eid = s["event_id"]
        documented_ratio = float(s["normalized_reverse_split_ratio"])
        rows = panel_by_event.get(eid, [])
        offs = find_offset_rows(rows, {-1, 0})

        raw_t1 = offs.get(-1, {}).get("raw_close", "")
        raw_t0 = offs.get(0, {}).get("raw_close", "")
        adj_t1 = offs.get(-1, {}).get("adj_close", "")
        adj_t0 = offs.get(0, {}).get("adj_close", "")

        factor_pre = factor_post = factor_implied_ratio = pct_diff = None
        raw_return_pct = adj_return_pct = None

        try:
            raw_t1_f, raw_t0_f, adj_t1_f, adj_t0_f = (
                float(raw_t1), float(raw_t0), float(adj_t1), float(adj_t0)
            )
            factor_pre = adj_t1_f / raw_t1_f
            factor_post = adj_t0_f / raw_t0_f
            factor_implied_ratio = factor_pre / factor_post
            pct_diff = abs(factor_implied_ratio - documented_ratio) / documented_ratio
            raw_return_pct = (raw_t0_f / raw_t1_f) - 1
            adj_return_pct = (adj_t0_f / adj_t1_f) - 1
        except (ValueError, TypeError, ZeroDivisionError):
            pass

        classification, notes = classify(pct_diff)
        counts[classification] += 1

        out_rows.append({
            "event_id": eid, "ticker": s["ticker"], "effective_date": s["effective_date"],
            "documented_ratio": documented_ratio,
            "raw_close_t_minus_1": raw_t1, "raw_close_t0": raw_t0,
            "raw_close_return_pct": round(raw_return_pct, 4) if raw_return_pct is not None else "",
            "adj_close_t_minus_1": adj_t1, "adj_close_t0": adj_t0,
            "adj_close_return_pct": round(adj_return_pct, 4) if adj_return_pct is not None else "",
            "factor_pre": round(factor_pre, 6) if factor_pre is not None else "",
            "factor_post": round(factor_post, 6) if factor_post is not None else "",
            "factor_implied_ratio": round(factor_implied_ratio, 4) if factor_implied_ratio is not None else "",
            "factor_pct_diff": round(pct_diff, 4) if pct_diff is not None else "",
            "classification": classification, "notes": notes,
        })

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"Validated {len(out_rows)} events (corrected factor-based methodology).")
    print(f"PASS: {counts['PASS']}  WARNING: {counts['WARNING']}  FAIL: {counts['FAIL']}")
    for label in ("FAIL", "WARNING"):
        if counts[label]:
            print(f"\n{label} events:")
            for r in out_rows:
                if r["classification"] == label:
                    print(f"  {r['event_id']}: documented={r['documented_ratio']}, "
                          f"factor_implied={r['factor_implied_ratio']}, pct_diff={r['factor_pct_diff']}, notes={r['notes']}")
    print(f"\nWrote {OUT_PATH}")


if __name__ == "__main__":
    main()
