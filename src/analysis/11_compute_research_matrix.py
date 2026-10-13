"""
Compute all per-event return, momentum, volume and volatility metrics
for the 88 validated events and write the analysis-ready
data/processed/reverse_split_research_matrix.csv.

Methodology notes (see RESEARCH_LOG.md for the full reasoning):

- All RETURN calculations use the split-ADJUSTED close series
  (adj_close), never the raw series, across any window that spans the
  event date. Polygon's adjustment factor was independently verified
  (09_validate_split_adjustment.py, 88/88 PASS) to match this study's
  documented ratio for every event, so the mechanical split jump is
  correctly removed and what remains is genuine price return. The RAW
  series is used only to (a) report actual traded price levels
  (pre/post-split price buckets) and (b) as an input to the volume
  metrics, where raw share volume is what actually traded (adjusted
  volume is raw volume divided by the same factor, i.e. a share-count
  fiction, not a real traded-volume figure).

- "Market-adjusted return" = event's adjusted-price raw return over a
  window MINUS the benchmark's (SPY or IWM) return over the exact same
  CALENDAR dates (not trading-day offsets -- benchmark dates are looked
  up directly, so any single-stock halt day doesn't misalign it).

- "Universe-adjusted return" is this study's practical substitute for a
  full nearest-neighbor matched-control group (which would require
  fetching full price histories for a separate set of non-split control
  stocks -- explicitly out of scope for this exploratory pass; see
  RESEARCH_LOG.md and PHASE_0_RESEARCH_DESIGN.md section 9's "or a
  constructed equal-weight basket of the same universe" alternative).
  It is the event's return MINUS the equal-weighted average return of
  every OTHER selected event at the same trading-day offset. This is
  reported as a third, clearly-labeled series alongside raw and
  market-adjusted returns, per the brief's instruction that divergence
  between return series is a finding, not noise to average away -- it
  is not a substitute for genuine matched-control analysis and is
  labeled as such everywhere it appears.

- Event time T = trading_day_offset 0 (first trading session on/after
  effective_date, already computed in event_price_panel.csv from the
  ticker's own actual trading dates -- never assumed).

- Price buckets (config/definitions.md): <$1, $1-$2, $2-$5, $5-$10,
  $10-$20, >$20, applied separately to the RAW pre-split price (T-1
  close) and RAW post-split price (T0 close).

- Continuation/reversal (config/definitions.md, frozen before any data
  was examined):
    extreme_momentum   : T0 adj return vs T-1 >= +50%  OR  T0 raw high/open - 1 >= +100%
                         (the intraday-run-up leg is a same-day
                         high-vs-open proxy, since no intraday minute
                         data was collected in this reduced-scope study
                         -- documented limitation, not the literal
                         PHASE_0 intraday definition)
    continuation       : T0 return > 0  AND  T+5 adj close >= T0 adj close
    failed_momentum    : T0 return > 0  AND  T+5 adj close <  T0 adj open
    reversal           : T0 return < 0 (vs T-1)
  (not mutually exclusive by design; a flat event can match none)

- Run-up / drawdown: the maximum and minimum cumulative adjusted return
  from T0 close, tracked through T+5/T+10/T+20/T+30/T+60, plus boolean
  flags for whether each pre-registered threshold (+10/+20/+50/+100%,
  -10/-20/-50%) was ever crossed within T0..T+60.

- Volume: ratio of mean RAW daily volume over T0..T+5 to mean RAW daily
  volume over T-10..T-1 ("post/pre volume ratio").

- Volatility: standard deviation of daily adjusted-close returns over
  T-30..T-1 ("pre_volatility") vs T0..T+30 ("post_volatility").

Zero-network reprocessing of already-fetched, already-validated data.
"""
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PATH = REPO_ROOT / "data" / "processed" / "sample_selection.csv"
PANEL_PATH = REPO_ROOT / "data" / "intermediate" / "event_price_panel.csv"
BENCHMARK_RAW_PATH = REPO_ROOT / "data" / "raw" / "polygon_benchmark_prices_raw.jsonl"
OUT_PATH = REPO_ROOT / "data" / "processed" / "reverse_split_research_matrix.csv"

POST_HORIZONS = [1, 5, 10, 20, 30, 60]
PRE_WINDOWS = {"t_minus_30_to_minus_1": -30, "t_minus_10_to_minus_1": -10, "t_minus_5_to_minus_1": -5}
RUNUP_THRESHOLDS = [0.10, 0.20, 0.50, 1.00]
DRAWDOWN_THRESHOLDS = [-0.10, -0.20, -0.50]


def price_bucket(price):
    if price is None:
        return ""
    if price < 1:
        return "<$1"
    if price < 2:
        return "$1-$2"
    if price < 5:
        return "$2-$5"
    if price < 10:
        return "$5-$10"
    if price < 20:
        return "$10-$20"
    return ">$20"


def load_panel_by_event():
    by_event = defaultdict(dict)  # event_id -> {offset: row}
    with open(PANEL_PATH, newline="") as f:
        for row in csv.DictReader(f):
            off = row["trading_day_offset"]
            if off == "":
                continue
            by_event[row["event_id"]][int(off)] = row
    return by_event


def load_benchmark_by_date():
    # ticker -> {date_str: adj_close}
    out = defaultdict(dict)
    with open(BENCHMARK_RAW_PATH) as f:
        for line in f:
            rec = json.loads(line)
            resp = rec["response"]
            if resp.get("status") != "OK":
                continue
            import datetime
            for bar in resp.get("results") or []:
                d = datetime.datetime.utcfromtimestamp(bar["t"] / 1000).strftime("%Y-%m-%d")
                out[rec["ticker"]][d] = bar["c"]
    return out


def f(row, field):
    try:
        v = row.get(field, "")
        return float(v) if v != "" else None
    except (TypeError, ValueError):
        return None


def main():
    with open(SAMPLE_PATH, newline="") as fh:
        sample = [r for r in csv.DictReader(fh) if r["selected"] == "True"]

    panel = load_panel_by_event()
    bench = load_benchmark_by_date()

    # First pass: compute each event's own adjusted-return series by offset,
    # needed both for its own row and for the universe-basket benchmark.
    event_returns = {}  # event_id -> {offset: adj_close}
    for s in sample:
        eid = s["event_id"]
        rows = panel.get(eid, {})
        event_returns[eid] = {off: f(r, "adj_close") for off, r in rows.items()}

    # universe basket: for each offset, the set of (event, adj_close) pairs,
    # used to compute each OTHER event's average return at that offset.
    def event_return_from_t0(eid, offset):
        series = event_returns.get(eid, {})
        t0 = series.get(0)
        val = series.get(offset)
        if t0 is None or val is None or t0 == 0:
            return None
        return (val / t0) - 1

    all_event_ids = [s["event_id"] for s in sample]

    def universe_avg_return(offset, exclude_eid):
        vals = []
        for eid in all_event_ids:
            if eid == exclude_eid:
                continue
            r = event_return_from_t0(eid, offset)
            if r is not None:
                vals.append(r)
        return statistics.mean(vals) if vals else None

    out_rows = []
    fieldnames = None

    for s in sample:
        eid = s["event_id"]
        ticker = s["ticker"]
        eff = s["effective_date"]
        rows = panel.get(eid, {})

        r_t1 = rows.get(-1)  # T-1
        r_t0 = rows.get(0)   # T0
        r_t5 = rows.get(5)

        raw_t1 = f(r_t1, "raw_close") if r_t1 else None
        raw_t0 = f(r_t0, "raw_close") if r_t0 else None
        adj_t1 = f(r_t1, "adj_close") if r_t1 else None
        adj_t0 = f(r_t0, "adj_close") if r_t0 else None
        t0_open = f(r_t0, "adj_open") if r_t0 else None
        t0_high_raw = f(r_t0, "raw_high") if r_t0 else None
        t0_open_raw = f(r_t0, "raw_open") if r_t0 else None
        t5_adj = f(r_t5, "adj_close") if r_t5 else None
        t0_date = r_t0["trading_date"] if r_t0 else None

        row = {
            "event_id": eid, "ticker": ticker, "company": s["company"],
            "effective_date": eff, "trading_date_t0": t0_date,
            "selection_year": s["selection_year"], "ratio_bucket": s["ratio_bucket"],
            "normalized_reverse_split_ratio": s["normalized_reverse_split_ratio"],
            "exchange": s["exchange"], "security_type": s["security_type"],
            "pre_split_price_raw": raw_t1, "pre_split_price_bucket": price_bucket(raw_t1),
            "post_split_price_raw": raw_t0, "post_split_price_bucket": price_bucket(raw_t0),
        }

        # T0 day return (adjusted, vs T-1)
        t0_return = None
        if adj_t1 and adj_t0 is not None and adj_t1 != 0:
            t0_return = (adj_t0 / adj_t1) - 1
        row["t0_return_pct"] = t0_return

        # Pre-event window returns (adjusted)
        for label, off in PRE_WINDOWS.items():
            r_start = rows.get(off)
            start_px = f(r_start, "adj_close") if r_start else None
            if start_px and adj_t1 is not None and start_px != 0:
                row[f"pre_return_{label}"] = (adj_t1 / start_px) - 1
            else:
                row[f"pre_return_{label}"] = None

        # Post-event returns at each horizon: raw, market-adjusted (SPY, IWM), universe-adjusted
        for h in POST_HORIZONS:
            r_h = rows.get(h)
            px_h = f(r_h, "adj_close") if r_h else None
            raw_ret = None
            if adj_t0 and px_h is not None and adj_t0 != 0:
                raw_ret = ((px_h / adj_t0) - 1)
            row[f"return_t_plus_{h}"] = raw_ret

            # market-adjusted, by matching actual calendar dates
            for bench_ticker in ("SPY", "IWM"):
                col = f"return_t_plus_{h}_vs_{bench_ticker.lower()}"
                if raw_ret is None or not t0_date or r_h is None:
                    row[col] = None
                    continue
                date_h = r_h["trading_date"]
                b0 = bench.get(bench_ticker, {}).get(t0_date)
                bh = bench.get(bench_ticker, {}).get(date_h)
                if b0 and bh:
                    bench_ret = (bh / b0) - 1
                    row[col] = raw_ret - bench_ret
                else:
                    row[col] = None

            # universe-adjusted (best-effort substitute for a matched control;
            # see module docstring)
            uni_avg = universe_avg_return(h, eid)
            row[f"return_t_plus_{h}_vs_universe_basket"] = (
                raw_ret - uni_avg if raw_ret is not None and uni_avg is not None else None
            )

        # Run-up / drawdown from T0 close through T+60, and threshold flags
        max_cum = None
        min_cum = None
        crossed = {th: False for th in RUNUP_THRESHOLDS}
        crossed_dd = {th: False for th in DRAWDOWN_THRESHOLDS}
        if adj_t0:
            for off in range(0, 61):
                r_off = rows.get(off)
                px = f(r_off, "adj_close") if r_off else None
                if px is None:
                    continue
                cum = (px / adj_t0) - 1
                max_cum = cum if max_cum is None else max(max_cum, cum)
                min_cum = cum if min_cum is None else min(min_cum, cum)
                for th in RUNUP_THRESHOLDS:
                    if cum >= th:
                        crossed[th] = True
                for th in DRAWDOWN_THRESHOLDS:
                    if cum <= th:
                        crossed_dd[th] = True
        row["max_runup_t0_to_t60"] = max_cum
        row["max_drawdown_t0_to_t60"] = min_cum
        for th in RUNUP_THRESHOLDS:
            row[f"crossed_plus_{int(th*100)}pct"] = crossed[th]
        for th in DRAWDOWN_THRESHOLDS:
            row[f"crossed_minus_{abs(int(th*100))}pct"] = crossed_dd[th]

        # Continuation / reversal classification (frozen definitions)
        intraday_runup_proxy = None
        if t0_open_raw and t0_high_raw is not None and t0_open_raw != 0:
            intraday_runup_proxy = (t0_high_raw / t0_open_raw) - 1
        row["t0_intraday_high_vs_open_pct"] = intraday_runup_proxy

        extreme_momentum = bool(
            (t0_return is not None and t0_return >= 0.50)
            or (intraday_runup_proxy is not None and intraday_runup_proxy >= 1.00)
        )
        continuation = bool(
            t0_return is not None and t0_return > 0
            and t5_adj is not None and adj_t0 is not None and t5_adj >= adj_t0
        )
        failed_momentum = bool(
            t0_return is not None and t0_return > 0
            and t5_adj is not None and t0_open is not None and t5_adj < t0_open
        )
        reversal = bool(t0_return is not None and t0_return < 0)
        row["extreme_momentum_event"] = extreme_momentum
        row["momentum_continuation"] = continuation
        row["failed_momentum"] = failed_momentum
        row["reversal"] = reversal

        # Volume: post (T0..T+5) vs pre (T-10..T-1) mean raw volume
        pre_vols = [f(rows.get(o), "raw_volume") for o in range(-10, 0) if rows.get(o)]
        post_vols = [f(rows.get(o), "raw_volume") for o in range(0, 6) if rows.get(o)]
        pre_vols = [v for v in pre_vols if v is not None]
        post_vols = [v for v in post_vols if v is not None]
        pre_vol_mean = statistics.mean(pre_vols) if pre_vols else None
        post_vol_mean = statistics.mean(post_vols) if post_vols else None
        row["pre_event_mean_volume"] = pre_vol_mean
        row["post_event_mean_volume"] = post_vol_mean
        row["post_pre_volume_ratio"] = (
            post_vol_mean / pre_vol_mean if pre_vol_mean and post_vol_mean is not None and pre_vol_mean != 0 else None
        )

        # Volatility: stdev of daily adjusted returns, pre (T-30..T-1) vs post (T0..T+30)
        def daily_returns(offsets):
            closes = []
            for o in offsets:
                r_o = rows.get(o)
                px = f(r_o, "adj_close") if r_o else None
                if px is not None:
                    closes.append(px)
            rets = []
            for i in range(1, len(closes)):
                if closes[i - 1]:
                    rets.append((closes[i] / closes[i - 1]) - 1)
            return rets

        pre_rets = daily_returns(range(-30, 0))
        post_rets = daily_returns(range(0, 31))
        row["pre_event_volatility"] = statistics.pstdev(pre_rets) if len(pre_rets) >= 2 else None
        row["post_event_volatility"] = statistics.pstdev(post_rets) if len(post_rets) >= 2 else None

        out_rows.append(row)
        if fieldnames is None:
            fieldnames = list(row.keys())

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"Computed research matrix for {len(out_rows)} events, {len(fieldnames)} columns.")
    print(f"Wrote {OUT_PATH}")

    # quick sanity summary
    def med(vals):
        vals = [v for v in vals if v is not None]
        return statistics.median(vals) if vals else None

    print("\nQuick sanity check (median returns):")
    print("  T0 day return:", med([r["t0_return_pct"] for r in out_rows]))
    for h in POST_HORIZONS:
        print(f"  T+{h} return:", med([r[f"return_t_plus_{h}"] for r in out_rows]))
    print("  extreme_momentum_event count:", sum(1 for r in out_rows if r["extreme_momentum_event"]))
    print("  momentum_continuation count:", sum(1 for r in out_rows if r["momentum_continuation"]))
    print("  reversal count:", sum(1 for r in out_rows if r["reversal"]))


if __name__ == "__main__":
    main()
