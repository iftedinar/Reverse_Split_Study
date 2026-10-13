"""
Mandatory statistical reporting for the reverse-split research matrix.

For every return series (raw T0/T+1/5/10/20/30/60, vs-SPY, vs-IWM,
vs-universe-basket) this script reports N, mean, MEDIAN (mandatory per
brief -- never mean-only), sample standard deviation, 25th/75th
percentile, min, max, share of events with a positive return, and a
95% confidence interval for the mean (t-distribution critical value,
since N=88 is not large enough to safely assume normal z).

Robustness checks required by the brief:
  (a) Winsorized at the 5th/95th percentile -- reduces the influence of
      a small number of extreme reverse-split blow-ups/pops without
      discarding any events.
  (b) First-event-per-company subset -- AKAN appears twice in this
      sample as two genuinely separate reverse-split events on
      different effective dates (a legitimate repeat issuer, not a
      duplicate). Because repeat issuers violate the independence
      assumption behind a naive standard error, this subset keeps only
      each company's earliest event and reports it side-by-side with
      the full-sample numbers so a reader can see whether repeat
      issuers are driving the result.

Zero-network reprocessing of already-computed data.
"""
import csv
import math
import statistics
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = REPO_ROOT / "data" / "processed" / "reverse_split_research_matrix.csv"
OUT_DIR = REPO_ROOT / "results" / "tables"

RETURN_COLUMNS = (
    ["t0_return_pct"]
    + [f"return_t_plus_{h}" for h in (1, 5, 10, 20, 30, 60)]
    + [f"return_t_plus_{h}_vs_{b}" for h in (1, 5, 10, 20, 30, 60) for b in ("spy", "iwm", "universe_basket")]
)

# Two-sided 95% t critical values for common small-sample df, linearly
# interpolated where the exact df isn't tabulated; falls back to the
# z=1.96 large-sample value beyond df=120 (no scipy dependency, per the
# "no unnecessary ML / minimal dependency" instruction -- this is a
# lookup table, not a model).
T_TABLE = {
    10: 2.228, 15: 2.131, 20: 2.086, 25: 2.060, 30: 2.042, 40: 2.021,
    50: 2.009, 60: 2.000, 70: 1.994, 80: 1.990, 88: 1.988, 100: 1.984, 120: 1.980,
}


def t_crit(df):
    if df <= 0:
        return float("nan")
    keys = sorted(T_TABLE)
    if df <= keys[0]:
        return T_TABLE[keys[0]]
    if df >= keys[-1]:
        return 1.96
    for lo, hi in zip(keys, keys[1:]):
        if lo <= df <= hi:
            frac = (df - lo) / (hi - lo)
            return T_TABLE[lo] + frac * (T_TABLE[hi] - T_TABLE[lo])
    return 1.96


def winsorize(vals, pct=0.05):
    if not vals:
        return vals
    s = sorted(vals)
    n = len(s)
    lo_idx = int(math.floor(n * pct))
    hi_idx = int(math.ceil(n * (1 - pct))) - 1
    lo_idx = max(0, min(lo_idx, n - 1))
    hi_idx = max(0, min(hi_idx, n - 1))
    lo_val, hi_val = s[lo_idx], s[hi_idx]
    return [min(max(v, lo_val), hi_val) for v in vals]


def summarize(vals, label):
    vals = [v for v in vals if v is not None and not (isinstance(v, float) and math.isnan(v))]
    n = len(vals)
    if n == 0:
        return {"series": label, "n": 0}
    mean = statistics.mean(vals)
    median = statistics.median(vals)
    sd = statistics.stdev(vals) if n >= 2 else float("nan")
    se = sd / math.sqrt(n) if n >= 2 else float("nan")
    tc = t_crit(n - 1) if n >= 2 else float("nan")
    ci_lo = mean - tc * se if n >= 2 else float("nan")
    ci_hi = mean + tc * se if n >= 2 else float("nan")
    q = sorted(vals)
    p25 = statistics.quantiles(vals, n=4)[0] if n >= 4 else q[0]
    p75 = statistics.quantiles(vals, n=4)[2] if n >= 4 else q[-1]
    pct_pos = sum(1 for v in vals if v > 0) / n
    return {
        "series": label, "n": n, "mean": round(mean, 4), "median": round(median, 4),
        "sd": round(sd, 4) if n >= 2 else "", "se": round(se, 4) if n >= 2 else "",
        "ci95_lo": round(ci_lo, 4) if n >= 2 else "", "ci95_hi": round(ci_hi, 4) if n >= 2 else "",
        "p25": round(p25, 4), "p75": round(p75, 4), "min": round(q[0], 4), "max": round(q[-1], 4),
        "pct_positive": round(pct_pos, 4),
    }


FIELDNAMES = ["series", "n", "mean", "median", "sd", "se", "ci95_lo", "ci95_hi", "p25", "p75", "min", "max", "pct_positive"]


def read_matrix():
    with open(MATRIX_PATH, newline="") as f:
        rows = list(csv.DictReader(f))
    return rows


def to_float(row, col):
    v = row.get(col, "")
    if v in ("", None):
        return None
    try:
        fv = float(v)
    except ValueError:
        return None
    if fv != fv:  # NaN guard
        return None
    return fv


def first_event_per_company(rows):
    best = {}
    for r in rows:
        key = r["company"] or r["ticker"]
        eff = r["effective_date"]
        if key not in best or eff < best[key]["effective_date"]:
            best[key] = r
    return list(best.values())


def write_table(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)


def main():
    rows = read_matrix()
    n_total = len(rows)
    n_companies = len({r["company"] or r["ticker"] for r in rows})

    # 1. Full-sample table (raw values)
    full_table = [summarize([to_float(r, c) for r in rows], c) for c in RETURN_COLUMNS]
    write_table(OUT_DIR / "statistics_full_sample.csv", full_table)

    # 2. Winsorized (5%/95%) full-sample table
    wins_table = []
    for c in RETURN_COLUMNS:
        vals = [to_float(r, c) for r in rows]
        vals = [v for v in vals if v is not None]
        wins_table.append(summarize(winsorize(vals), c))
    write_table(OUT_DIR / "statistics_winsorized.csv", wins_table)

    # 3. First-event-per-company subset (dependence robustness)
    fe_rows = first_event_per_company(rows)
    fe_table = [summarize([to_float(r, c) for r in fe_rows], c) for c in RETURN_COLUMNS]
    write_table(OUT_DIR / "statistics_first_event_per_company.csv", fe_table)

    # 4. By ratio bucket and by year (subgroup medians for the report)
    def group_table(key):
        groups = {}
        for r in rows:
            groups.setdefault(r[key], []).append(r)
        out = []
        for g, grows in sorted(groups.items()):
            row = {"group": g, "n": len(grows)}
            for h in (1, 5, 10, 20, 30, 60):
                vals = [to_float(r, f"return_t_plus_{h}") for r in grows]
                vals = [v for v in vals if v is not None]
                row[f"median_t_plus_{h}"] = round(statistics.median(vals), 4) if vals else ""
            out.append(row)
        return out

    ratio_table = group_table("ratio_bucket")
    year_table = group_table("selection_year")
    with open(OUT_DIR / "statistics_by_ratio_bucket.csv", "w", newline="") as f:
        fns = ["group", "n"] + [f"median_t_plus_{h}" for h in (1, 5, 10, 20, 30, 60)]
        w = csv.DictWriter(f, fieldnames=fns)
        w.writeheader()
        w.writerows(ratio_table)
    with open(OUT_DIR / "statistics_by_year.csv", "w", newline="") as f:
        fns = ["group", "n"] + [f"median_t_plus_{h}" for h in (1, 5, 10, 20, 30, 60)]
        w = csv.DictWriter(f, fieldnames=fns)
        w.writeheader()
        w.writerows(year_table)

    # 5. Price-bucket cross tab (pre-split price bucket vs T+30 median)
    price_table = []
    groups = {}
    for r in rows:
        groups.setdefault(r["pre_split_price_bucket"], []).append(r)
    for g, grows in groups.items():
        vals = [to_float(r, "return_t_plus_30") for r in grows]
        vals = [v for v in vals if v is not None]
        price_table.append({"pre_split_price_bucket": g, "n": len(grows),
                             "median_t_plus_30": round(statistics.median(vals), 4) if vals else ""})
    with open(OUT_DIR / "statistics_by_price_bucket.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["pre_split_price_bucket", "n", "median_t_plus_30"])
        w.writeheader()
        w.writerows(price_table)

    print(f"N events = {n_total}, unique companies = {n_companies}")
    print(f"Wrote statistics tables to {OUT_DIR}")
    print("\nFull-sample headline (median, N, pct_positive):")
    for row in full_table:
        if row["n"]:
            print(f"  {row['series']:35s} median={row['median']:>8}  N={row['n']:>3}  %pos={row['pct_positive']:>6}")


if __name__ == "__main__":
    main()
