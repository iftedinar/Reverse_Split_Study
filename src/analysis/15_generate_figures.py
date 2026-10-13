"""
Generate the 12 publication figures from the research matrix and
statistics tables. Zero-network, matplotlib only (no seaborn/no ML).
Writes to results/figures/publication/.
"""
import csv
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

REPO_ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = REPO_ROOT / "data" / "processed" / "reverse_split_research_matrix.csv"
TABLES_DIR = REPO_ROOT / "results" / "tables"
OUT_DIR = REPO_ROOT / "results" / "figures" / "publication"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HORIZONS = [1, 5, 10, 20, 30, 60]
NAVY = "#1a3a5c"
RED = "#b5322e"
GREY = "#8a8a8a"
GOLD = "#c98a2c"

plt.rcParams.update({
    "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "axes.facecolor": "white",
})


def load_rows():
    with open(MATRIX_PATH, newline="") as f:
        return list(csv.DictReader(f))


def fv(row, col):
    v = row.get(col, "")
    if v in ("", None):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def load_table(name):
    with open(TABLES_DIR / name, newline="") as f:
        return list(csv.DictReader(f))


def savefig(fig, name):
    path = OUT_DIR / name
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {path.name}")


def main():
    rows = load_rows()
    n = len(rows)

    # ---- Fig 1: Median CAR path (raw) with IQR band, T0..T+60 ----
    offsets = [0] + HORIZONS
    med_vals, p25_vals, p75_vals = [], [], []
    for h in offsets:
        col = "t0_return_pct" if h == 0 else f"return_t_plus_{h}"
        vals = [fv(r, col) for r in rows]
        vals = [v for v in vals if v is not None]
        med_vals.append(statistics.median(vals) * 100)
        q = statistics.quantiles(vals, n=4)
        p25_vals.append(q[0] * 100)
        p75_vals.append(q[2] * 100)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.axhline(0, color=GREY, lw=0.8)
    ax.fill_between(offsets, p25_vals, p75_vals, color=NAVY, alpha=0.15, label="IQR (25th-75th pct)")
    ax.plot(offsets, med_vals, marker="o", color=NAVY, lw=2, label="Median cumulative return")
    ax.set_xlabel("Trading days relative to reverse-split effective date (T0)")
    ax.set_ylabel("Cumulative raw return (%)")
    ax.set_title("Fig. 1 — Median Post-Split Cumulative Return, T0 to T+60 (N=88)")
    ax.legend(loc="lower left", frameon=False)
    savefig(fig, "fig01_median_car_path.png")

    # ---- Fig 2: Median return by horizon, three series (raw, vs-SPY/IWM avg, vs-universe) ----
    raw_med, mkt_med, uni_med = [], [], []
    for h in HORIZONS:
        raw = [fv(r, f"return_t_plus_{h}") for r in rows]
        raw = [v for v in raw if v is not None]
        spy = [fv(r, f"return_t_plus_{h}_vs_spy") for r in rows]
        iwm = [fv(r, f"return_t_plus_{h}_vs_iwm") for r in rows]
        mkt = [v for v in spy if v is not None] + [v for v in iwm if v is not None]
        uni = [fv(r, f"return_t_plus_{h}_vs_universe_basket") for r in rows]
        uni = [v for v in uni if v is not None]
        raw_med.append(statistics.median(raw) * 100)
        mkt_med.append(statistics.median(mkt) * 100)
        uni_med.append(statistics.median(uni) * 100)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = range(len(HORIZONS))
    w = 0.26
    ax.bar([i - w for i in x], raw_med, width=w, color=NAVY, label="Raw return")
    ax.bar([i for i in x], mkt_med, width=w, color=RED, label="vs. SPY/IWM (market-adjusted)")
    ax.bar([i + w for i in x], uni_med, width=w, color=GOLD, label="vs. same-sample universe basket")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(list(x)); ax.set_xticklabels([f"T+{h}" for h in HORIZONS])
    ax.set_ylabel("Median return (%)")
    ax.set_title("Fig. 2 — Median Return by Horizon: Raw vs. Market- vs. Universe-Adjusted (N=88)")
    ax.legend(frameon=False, fontsize=8)
    savefig(fig, "fig02_median_return_by_series.png")

    # ---- Fig 3: Distribution of T+30 raw returns (histogram) ----
    t30 = [fv(r, "return_t_plus_30") for r in rows]
    t30 = [v * 100 for v in t30 if v is not None]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.hist(t30, bins=22, color=NAVY, edgecolor="white")
    ax.axvline(statistics.median(t30), color=RED, lw=2, linestyle="--", label=f"Median = {statistics.median(t30):.1f}%")
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("T+30 raw return (%)"); ax.set_ylabel("Number of events")
    ax.set_title("Fig. 3 — Distribution of T+30 Returns (N=88)")
    ax.legend(frameon=False)
    savefig(fig, "fig03_t30_return_histogram.png")

    # ---- Fig 4: Median T+30 return by ratio bucket ----
    rb = load_table("statistics_by_ratio_bucket.csv")
    order = ["1-for-2 to 1-for-5", "1-for-6 to 1-for-10", "1-for-11 to 1-for-20", "1-for-21 to 1-for-50", "greater than 1-for-50"]
    rb_sorted = sorted(rb, key=lambda r: order.index(r["group"]) if r["group"] in order else 99)
    labels = [r["group"] for r in rb_sorted]
    vals = [float(r["median_t_plus_30"]) * 100 if r["median_t_plus_30"] else 0 for r in rb_sorted]
    ns = [r["n"] for r in rb_sorted]
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    colors = [RED if v < 0 else NAVY for v in vals]
    bars = ax.bar(range(len(labels)), vals, color=colors)
    for i, (b, nn) in enumerate(zip(bars, ns)):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() - (2 if b.get_height() < 0 else -1), f"n={nn}",
                ha="center", va="top" if b.get_height() < 0 else "bottom", fontsize=8)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("Median T+30 raw return (%)")
    ax.set_title("Fig. 4 — Median T+30 Return by Reverse-Split Ratio Bucket")
    savefig(fig, "fig04_median_return_by_ratio_bucket.png")

    # ---- Fig 5: Median return by pre-split price bucket ----
    pb = load_table("statistics_by_price_bucket.csv")
    order_p = ["<$1", "$1-$2", "$2-$5", "$5-$10", "$10-$20", ">$20"]
    pb_sorted = sorted(pb, key=lambda r: order_p.index(r["pre_split_price_bucket"]) if r["pre_split_price_bucket"] in order_p else 99)
    labels = [r["pre_split_price_bucket"] for r in pb_sorted]
    vals = [float(r["median_t_plus_30"]) * 100 if r["median_t_plus_30"] else 0 for r in pb_sorted]
    ns = [r["n"] for r in pb_sorted]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    colors = [RED if v < 0 else NAVY for v in vals]
    bars = ax.bar(range(len(labels)), vals, color=colors)
    for i, (b, nn) in enumerate(zip(bars, ns)):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() - (2 if b.get_height() < 0 else -1), f"n={nn}",
                ha="center", va="top" if b.get_height() < 0 else "bottom", fontsize=8)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels)
    ax.set_ylabel("Median T+30 raw return (%)")
    ax.set_title("Fig. 5 — Median T+30 Return by Pre-Split Price Bucket")
    savefig(fig, "fig05_median_return_by_price_bucket.png")

    # ---- Fig 6: Median return by selection year ----
    yr = load_table("statistics_by_year.csv")
    yr_sorted = sorted(yr, key=lambda r: r["group"])
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for r, color in zip(yr_sorted, (NAVY, RED)):
        vals = [float(r[f"median_t_plus_{h}"]) * 100 if r[f"median_t_plus_{h}"] else None for h in HORIZONS]
        ax.plot(HORIZONS, vals, marker="o", label=f"{r['group']} (n={r['n']})", color=color)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xlabel("Trading days post-event (T+h)"); ax.set_ylabel("Median return (%)")
    ax.set_title("Fig. 6 — Median Return by Horizon, Split by Selection Year")
    ax.legend(frameon=False)
    savefig(fig, "fig06_median_return_by_year.png")

    # ---- Fig 7: Continuation/reversal/momentum classification counts ----
    labels = ["extreme_momentum_event", "momentum_continuation", "failed_momentum", "reversal"]
    counts = [sum(1 for r in rows if r[l] == "True") for l in labels]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(range(len(labels)), counts, color=[GOLD, NAVY, GREY, RED])
    for i, c in enumerate(counts):
        ax.text(i, c + 0.5, str(c), ha="center")
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(["Extreme\nmomentum", "Momentum\ncontinuation", "Failed\nmomentum", "Reversal"])
    ax.set_ylabel("Number of events (of 88)")
    ax.set_title("Fig. 7 — Frequency of Frozen Momentum/Reversal Classifications")
    savefig(fig, "fig07_classification_counts.png")

    # ---- Fig 8: Volume ratio distribution (post/pre) ----
    vr = [fv(r, "post_pre_volume_ratio") for r in rows]
    vr = [v for v in vr if v is not None and v < 20]  # trim extreme outlier tail for readability
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.hist(vr, bins=22, color=NAVY, edgecolor="white")
    ax.axvline(1.0, color="black", lw=0.8, linestyle=":", label="No change (ratio = 1)")
    ax.axvline(statistics.median(vr), color=RED, lw=2, linestyle="--", label=f"Median = {statistics.median(vr):.2f}x")
    ax.set_xlabel("Post/pre mean daily raw volume ratio (values >=20x trimmed for display)")
    ax.set_ylabel("Number of events")
    ax.set_title("Fig. 8 — Post-Event vs. Pre-Event Volume Ratio")
    ax.legend(frameon=False)
    savefig(fig, "fig08_volume_ratio_histogram.png")

    # ---- Fig 9: Pre- vs post-event volatility scatter ----
    pre_v = [fv(r, "pre_event_volatility") for r in rows]
    post_v = [fv(r, "post_event_volatility") for r in rows]
    pairs = [(a, b) for a, b in zip(pre_v, post_v) if a is not None and b is not None]
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    xs = [p[0] * 100 for p in pairs]; ys = [p[1] * 100 for p in pairs]
    ax.scatter(xs, ys, color=NAVY, alpha=0.6, edgecolor="white")
    lim = max(max(xs), max(ys)) * 1.05
    ax.plot([0, lim], [0, lim], color=GREY, lw=1, linestyle="--", label="Pre = post (no change)")
    ax.set_xlim(0, lim); ax.set_ylim(0, lim)
    ax.set_xlabel("Pre-event daily return volatility, T-30..T-1 (%)")
    ax.set_ylabel("Post-event daily return volatility, T0..T+30 (%)")
    ax.set_title("Fig. 9 — Pre- vs. Post-Event Volatility (N=88)")
    ax.legend(frameon=False)
    savefig(fig, "fig09_volatility_scatter.png")

    # ---- Fig 10: Max run-up vs max drawdown scatter (T0..T+60) ----
    runup = [fv(r, "max_runup_t0_to_t60") for r in rows]
    dd = [fv(r, "max_drawdown_t0_to_t60") for r in rows]
    pairs = [(a, b) for a, b in zip(runup, dd) if a is not None and b is not None]
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    xs = [p[0] * 100 for p in pairs]; ys = [p[1] * 100 for p in pairs]
    ax.scatter(xs, ys, color=NAVY, alpha=0.6, edgecolor="white")
    ax.axhline(0, color=GREY, lw=0.8); ax.axvline(0, color=GREY, lw=0.8)
    ax.set_xlabel("Max cumulative run-up, T0 to T+60 (%)")
    ax.set_ylabel("Max cumulative drawdown, T0 to T+60 (%)")
    ax.set_title("Fig. 10 — Max Run-Up vs. Max Drawdown per Event (N=88)")
    savefig(fig, "fig10_runup_vs_drawdown_scatter.png")

    # ---- Fig 11: Threshold-crossing frequencies ----
    up_labels = ["crossed_plus_10pct", "crossed_plus_20pct", "crossed_plus_50pct", "crossed_plus_100pct"]
    dn_labels = ["crossed_minus_10pct", "crossed_minus_20pct", "crossed_minus_50pct"]
    up_counts = [sum(1 for r in rows if r[l] == "True") / n * 100 for l in up_labels]
    dn_counts = [sum(1 for r in rows if r[l] == "True") / n * 100 for l in dn_labels]
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.bar([f"+{p}%" for p in (10, 20, 50, 100)], up_counts, color=NAVY, label="Ever ran up >= threshold")
    ax.bar([f"-{p}%" for p in (10, 20, 50)], [-v for v in dn_counts], color=RED, label="Ever drew down <= threshold")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_ylabel("Share of events (%)")
    ax.set_title("Fig. 11 — Share of Events Ever Crossing Return Thresholds, T0-T+60")
    ax.legend(frameon=False)
    savefig(fig, "fig11_threshold_crossing_frequency.png")

    # ---- Fig 12: Sample composition (events per year and per ratio bucket) ----
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    yr_counts = {}
    for r in rows:
        yr_counts[r["selection_year"]] = yr_counts.get(r["selection_year"], 0) + 1
    axes[0].bar(list(yr_counts.keys()), list(yr_counts.values()), color=NAVY)
    axes[0].set_title("By selection year"); axes[0].set_ylabel("N events")
    rb_counts = {}
    for r in rows:
        rb_counts[r["ratio_bucket"]] = rb_counts.get(r["ratio_bucket"], 0) + 1
    rb_order = [o for o in order if o in rb_counts]
    axes[1].bar(range(len(rb_order)), [rb_counts[o] for o in rb_order], color=GOLD)
    axes[1].set_xticks(range(len(rb_order))); axes[1].set_xticklabels(rb_order, rotation=25, ha="right", fontsize=7)
    axes[1].set_title("By ratio bucket")
    fig.suptitle("Fig. 12 — Final Sample Composition (N=88, 84 unique companies)")
    savefig(fig, "fig12_sample_composition.png")

    print(f"\nGenerated 12 publication figures in {OUT_DIR}")


if __name__ == "__main__":
    main()
