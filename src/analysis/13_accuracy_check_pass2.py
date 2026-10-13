"""
Independent Accuracy Check Pass #2.

Per the brief's mandatory two-pass accuracy control, this script
recomputes a subset of core metrics (t0_return_pct and
return_t_plus_{10,30,60}) via a SEPARATE calculation path from
11_compute_research_matrix.py:
  - reads event_price_panel.csv with the plain csv.reader (not
    DictReader) and does its own column-index lookup and its own
    offset-to-row indexing, rather than reusing any helper function
    from script 11;
  - recomputes each ratio directly from raw adj_close strings without
    importing or calling anything from script 11.

If this independent path agrees with the research matrix to within
floating-point rounding (tolerance 1e-6) for every event, that is
strong evidence the original computation is correct rather than a
lucky bug. Any mismatch is reported by event_id with both values so it
can be hand-checked, and per the brief's halt-and-fix rule, a mismatch
found here would stop and get fixed before the results are used in the
report; it never gets quietly patched into a matching number.

Zero-network. Reads only already-fetched, already-validated files.
"""
import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = REPO_ROOT / "data" / "processed" / "reverse_split_research_matrix.csv"
PANEL_PATH = REPO_ROOT / "data" / "intermediate" / "event_price_panel.csv"
OUT_PATH = REPO_ROOT / "audit" / "accuracy_check_pass_2.csv"

CHECK_HORIZONS = [10, 30, 60]


def main():
    with open(PANEL_PATH, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        idx = {name: i for i, name in enumerate(header)}
        panel_raw_rows = list(reader)

    # independent index: event_id -> {offset(int): adj_close(float)}
    independent_index = {}
    for raw_row in panel_raw_rows:
        off_str = raw_row[idx["trading_day_offset"]]
        if off_str == "":
            continue
        eid = raw_row[idx["event_id"]]
        off = int(off_str)
        adj_close_str = raw_row[idx["adj_close"]]
        if adj_close_str == "":
            continue
        independent_index.setdefault(eid, {})[off] = float(adj_close_str)

    with open(MATRIX_PATH, newline="") as f:
        matrix_rows = list(csv.DictReader(f))

    out_rows = []
    mismatches = 0
    for m in matrix_rows:
        eid = m["event_id"]
        series = independent_index.get(eid, {})
        t1 = series.get(-1)
        t0 = series.get(0)

        indep_t0_return = None
        if t1 and t0 is not None and t1 != 0:
            indep_t0_return = (t0 / t1) - 1.0
        reported_t0_return = float(m["t0_return_pct"]) if m["t0_return_pct"] not in ("", None) else None

        row = {
            "event_id": eid, "ticker": m["ticker"],
            "reported_t0_return": reported_t0_return, "independent_t0_return": indep_t0_return,
            "t0_diff": (abs(reported_t0_return - indep_t0_return)
                        if reported_t0_return is not None and indep_t0_return is not None else ""),
        }

        for h in CHECK_HORIZONS:
            th = series.get(h)
            indep_ret = (th / t0 - 1.0) if (t0 and th is not None and t0 != 0) else None
            col = f"return_t_plus_{h}"
            reported = float(m[col]) if m[col] not in ("", None) else None
            row[f"reported_t_plus_{h}"] = reported
            row[f"independent_t_plus_{h}"] = indep_ret
            diff = abs(reported - indep_ret) if reported is not None and indep_ret is not None else None
            row[f"diff_t_plus_{h}"] = diff
            if diff is not None and diff > 1e-6:
                mismatches += 1

        if row["t0_diff"] not in ("", None) and row["t0_diff"] > 1e-6:
            mismatches += 1

        out_rows.append(row)

    fieldnames = ["event_id", "ticker", "reported_t0_return", "independent_t0_return", "t0_diff"]
    for h in CHECK_HORIZONS:
        fieldnames += [f"reported_t_plus_{h}", f"independent_t_plus_{h}", f"diff_t_plus_{h}"]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)

    print(f"Accuracy Check Pass #2: checked {len(out_rows)} events x (t0 + {len(CHECK_HORIZONS)} horizons).")
    print(f"Mismatches (> 1e-6 abs diff): {mismatches}")
    print(f"Result: {'PASS - independent path agrees with primary computation' if mismatches == 0 else 'FAIL - see ' + str(OUT_PATH)}")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
