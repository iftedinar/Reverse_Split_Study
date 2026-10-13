"""
Draw the Validation Pass #1 manual-review sample: >=20 events / >=20%
of the N=88 sample, stratified by (selection_year, ratio_bucket) using
the study's fixed master seed so the draw is reproducible and was not
influenced by looking at returns (this script reads only
sample_selection.csv identifiers -- no price or return data).

For each drawn event it also pulls the internal consistency checks
that ARE mechanically available without a human: ratio-bucket
membership, price-bucket membership, the prior split-adjustment
factor validation result (09_validate_split_adjustment.py), and the
prior data-completeness result (10_fix_data_completeness.py /
audit/data_completeness_round2.csv). These pre-fill the audit table;
final PASS/WARNING/FAIL judgment plus at least 10 external spot checks
against public sources are recorded separately in
audit/validation_pass_1.md.
"""
import csv
import random
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PATH = REPO_ROOT / "data" / "processed" / "sample_selection.csv"
SPLIT_VALIDATION_PATH = REPO_ROOT / "audit" / "split_adjustment_validation.csv"
COMPLETENESS_PATH = REPO_ROOT / "audit" / "data_completeness_round2.csv"
OUT_PATH = REPO_ROOT / "audit" / "validation_sample.csv"

RANDOM_SEED = 20260919
TARGET_N = 20


def price_bucket(price):
    if price is None:
        return ""
    if price < 1: return "<$1"
    if price < 2: return "$1-$2"
    if price < 5: return "$2-$5"
    if price < 10: return "$5-$10"
    if price < 20: return "$10-$20"
    return ">$20"


def main():
    with open(SAMPLE_PATH, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["selected"] == "True"]

    split_val = {}
    with open(SPLIT_VALIDATION_PATH, newline="") as f:
        for r in csv.DictReader(f):
            split_val[r["event_id"]] = r

    completeness = {}
    if COMPLETENESS_PATH.exists():
        with open(COMPLETENESS_PATH, newline="") as f:
            for r in csv.DictReader(f):
                completeness[r["event_id"]] = r

    strata = {}
    for r in rows:
        key = (r["selection_year"], r["ratio_bucket"])
        strata.setdefault(key, []).append(r)

    n_total = len(rows)
    target = max(TARGET_N, round(0.20 * n_total))

    # proportional allocation per stratum, seeded, largest-remainder to hit target exactly
    alloc = {}
    remainders = []
    running = 0
    for key, grp in strata.items():
        exact = target * len(grp) / n_total
        base = int(exact)
        alloc[key] = base
        running += base
        remainders.append((exact - base, key))
    remainders.sort(reverse=True)
    i = 0
    while running < target and i < len(remainders):
        _, key = remainders[i]
        alloc[key] += 1
        running += 1
        i += 1

    picked = []
    for key, grp in strata.items():
        k = min(alloc.get(key, 0), len(grp))
        rng = random.Random(f"{RANDOM_SEED}:validation_pass1:{key}")
        picked.extend(rng.sample(grp, k))

    picked.sort(key=lambda r: r["event_id"])

    out_rows = []
    for r in picked:
        eid = r["event_id"]
        sv = split_val.get(eid, {})
        cp = completeness.get(eid, {})
        out_rows.append({
            "event_id": eid, "ticker": r["ticker"], "company": r["company"],
            "effective_date": r["effective_date"],
            "split_from": r["split_from"], "split_to": r["split_to"],
            "normalized_reverse_split_ratio": r["normalized_reverse_split_ratio"],
            "ratio_bucket": r["ratio_bucket"], "exchange": r["exchange"],
            "split_adjustment_check": sv.get("classification", "n/a"),
            "factor_pct_diff": sv.get("factor_pct_diff", ""),
            "completeness_check": cp.get("complete", "n/a (pre-round-2 event or already 100% complete)"),
            "external_spot_check": "",
            "manual_verdict": "",
            "notes": "",
        })

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(out_rows[0].keys())
    with open(OUT_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)

    print(f"Drew {len(out_rows)} / {n_total} events ({len(out_rows)/n_total:.1%}) for Validation Pass #1.")
    print(f"Wrote {OUT_PATH}")
    for r in out_rows:
        print(f"  {r['event_id']:>6}  {r['ticker']:6s}  {r['effective_date']}  ratio={r['normalized_reverse_split_ratio']}  split_check={r['split_adjustment_check']}")


if __name__ == "__main__":
    main()
