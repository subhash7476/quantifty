"""W2 — how much close-to-close variance the NiftyShield hold window carries, and
whether afternoons trend or revert.

Pre-analysis note: docs/reports/index_research/NIFTY_SHIELD_AFTERNOON_VARIANCE_PREREG_2026-09-27.md
Spot only (1m NSE_INDEX|Nifty 50 + 1d closes + 13pm DayType facts); reads no options data.

Usage: python afternoon_variance.py [--data-root F:/Nifty/data]
"""
import argparse
import math
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from core.market.bar_labeling import UnknownLabeling, covered_interval, labeling_of  # noqa: E402
from core.market.session_schedule import CAS_EFFECTIVE, SPECIAL_SESSIONS  # noqa: E402

REPORT = ROOT / "docs" / "reports" / "index_research" / "NIFTY_SHIELD_AFTERNOON_VARIANCE_2026-09-27.md"
SYMBOL = "NSE_INDEX|Nifty 50"
START, END = date(2023, 1, 2), date(2026, 9, 25)
ENTRY = time(13, 0)
OPEN = time(9, 15)
BRACKET_SHARE = 2.5 / 6.25
BLOCK, REPS, SEED = 20, 10_000, 20260927
LABEL_OOS_FROM = date(2024, 1, 1)
REGIMES = ("BullTrend", "BearTrend", "Choppy")


def window_end(d):
    return time(15, 15) if d >= CAS_EFFECTIVE else time(15, 30)


def grid(t0, t1, step):
    out, cur = [], datetime.combine(date.min, t0)
    while cur.time() <= t1:
        out.append(cur.time())
        cur += timedelta(minutes=step)
    return out


def boundary_prices(con, d):
    """{boundary time: price at that time} — a bar's close sits at the end of the minute it covers."""
    bars = con.execute("select timestamp, open, close from candles where symbol=? order by timestamp",
                       [SYMBOL]).fetchall()
    if not bars:
        return None, "no index bars"
    try:
        lab = labeling_of(bars[0][0].time(), d, "cash_cat2")
    except UnknownLabeling as exc:
        return None, f"labelling refused: {exc}"
    px = {}
    for ts, o, c in bars:
        start, end = covered_interval(ts.time(), lab)
        px[end] = c
        if start == OPEN:
            px[OPEN] = o
    return px, None


def rv(px, times):
    lp = [math.log(px[t]) for t in times]
    return float(np.sum(np.diff(lp) ** 2))


def load_sessions(data_root):
    d1 = Path(data_root) / "market_data" / "nse" / "candles" / "1d"
    m1 = Path(data_root) / "market_data" / "nse" / "candles" / "1m"
    days = sorted(date.fromisoformat(p.stem) for p in d1.glob("*.duckdb"))
    daily = {}
    for d in days:
        if d < START - timedelta(days=10) or d > END:
            continue
        c = duckdb.connect(str(d1 / f"{d}.duckdb"), read_only=True)
        v = c.execute("select open, close from candles where symbol=?", [SYMBOL]).fetchone()
        c.close()
        if v:
            daily[d] = v
    order = sorted(daily)
    rows, drops = [], {}
    for prev, d in zip(order, order[1:]):
        if d < START:
            continue
        if d in SPECIAL_SESSIONS:
            drops["special session"] = drops.get("special session", 0) + 1
            continue
        f = m1 / f"{d}.duckdb"
        if not f.exists():
            drops["no 1m file"] = drops.get("no 1m file", 0) + 1
            continue
        con = duckdb.connect(str(f), read_only=True)
        px, why = boundary_prices(con, d)
        con.close()
        if px is None:
            drops[why.split(":")[0]] = drops.get(why.split(":")[0], 0) + 1
            continue
        we = window_end(d)
        g5, g1, gd = grid(ENTRY, we, 5), grid(ENTRY, we, 1), grid(OPEN, we, 5)
        if any(t not in px for t in set(g1) | set(gd)):
            drops["missing bars in window"] = drops.get("missing bars in window", 0) + 1
            continue
        c_prev, (o, c) = daily[prev][1], daily[d]
        rows.append(dict(
            session=d, era="post-CAS" if d >= CAS_EFFECTIVE else "pre-CAS",
            hold_rv5=rv(px, g5), hold_rv1=rv(px, g1), day_rv5=rv(px, gd),
            hold_ret2=math.log(px[we] / px[ENTRY]) ** 2,
            rcc2=math.log(c / c_prev) ** 2, ron2=math.log(o / c_prev) ** 2))
    return pd.DataFrame(rows), drops


def attach_regime(df, data_root):
    c = duckdb.connect(str(Path(data_root) / "features" / "day_type" / "day_type_facts.duckdb"), read_only=True)
    f = c.execute("select session_date, regime from day_type_facts where checkpoint='13pm'").df()
    c.close()
    f["session_date"] = pd.to_datetime(f.session_date).dt.date
    return df.merge(f.rename(columns={"session_date": "session"}), on="session", how="left")


def block_indices(n, rng):
    nb = math.ceil(n / BLOCK)
    starts = rng.integers(0, n - BLOCK + 1, size=(REPS, nb))
    idx = (starts[:, :, None] + np.arange(BLOCK)).reshape(REPS, -1)[:, :n]
    return idx


def ratio_ci(num, den, idx):
    boot = num[idx].sum(1) / den[idx].sum(1)
    return num.sum() / den.sum(), np.percentile(boot, 2.5), np.percentile(boot, 97.5)


def group_ratio_ci(num, den, mask, idx):
    m = mask[idx]
    boot = (num[idx] * m).sum(1) / (den[idx] * m).sum(1)
    return num[mask].sum() / den[mask].sum(), np.nanpercentile(boot, 2.5), np.nanpercentile(boot, 97.5)


def fmt(t):
    return f"{t[0]:.3f} [{t[1]:.3f}, {t[2]:.3f}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default=str(ROOT / "data"))
    a = ap.parse_args()
    df, drops = load_sessions(a.data_root)
    df = attach_regime(df, a.data_root)
    rng = np.random.default_rng(SEED)
    L = ["# W2 — NiftyShield Afternoon Variance and Trend Term (generated)\n",
         "Pre-analysis note: `NIFTY_SHIELD_AFTERNOON_VARIANCE_PREREG_2026-09-27.md`. "
         "Script: `scripts/research/nifty_shield_diag/afternoon_variance.py`.\n",
         f"- Sessions used: {len(df)} ({(df.era == 'pre-CAS').sum()} pre-CAS, {(df.era == 'post-CAS').sum()} post-CAS), "
         f"{START} → {END}",
         f"- Dropped: {drops or 'none'}",
         f"- Moving-block bootstrap over sessions: block {BLOCK}, {REPS:,} reps, seed {SEED}; 95% percentile intervals; "
         "every statistic is a ratio of sums\n"]
    res = {}
    for era in ("pre-CAS", "post-CAS"):
        e = df[df.era == era].reset_index(drop=True)
        if len(e) < BLOCK + 1:
            continue
        idx = block_indices(len(e), rng)
        H5 = ratio_ci(e.hold_rv5.to_numpy(), e.rcc2.to_numpy(), idx)
        H1 = ratio_ci(e.hold_rv1.to_numpy(), e.rcc2.to_numpy(), idx)
        intra = ratio_ci(e.hold_rv5.to_numpy(), e.day_rv5.to_numpy(), idx)
        on = ratio_ci(e.ron2.to_numpy(), e.rcc2.to_numpy(), idx)
        VR5 = ratio_ci(e.hold_ret2.to_numpy(), e.hold_rv5.to_numpy(), idx)
        VR1 = ratio_ci(e.hold_ret2.to_numpy(), e.hold_rv1.to_numpy(), idx)
        T = (e.hold_ret2 - e.hold_rv5).to_numpy() * 1e8
        Tb = T[idx].mean(1)
        res[era] = dict(H5=H5, VR5=VR5, e=e, idx=idx)
        L += [f"## {era}\n", "| statistic | estimate [95% CI] | reference |", "|---|--:|--:|",
              f"| **H**: hold-window share of close-to-close variance (5-min) | {fmt(H5)} | bracket assumes {BRACKET_SHARE:.2f} |",
              f"| H at 1-min (robustness) | {fmt(H1)} | {BRACKET_SHARE:.2f} |",
              f"| hold share of 09:15→window-end variance (5-min) | {fmt(intra)} | uniform {(2.5 if era == 'pre-CAS' else 2.25) / (6.25 if era == 'pre-CAS' else 6.0):.2f} |",
              f"| overnight share of close-to-close variance | {fmt(on)} | bracket assumes 0 |",
              f"| **VR**: (S_end/S_13)² ÷ Σ D² (5-min) | {fmt(VR5)} | 1 = no autocorrelation |",
              f"| VR at 1-min (robustness) | {fmt(VR1)} | 1 |",
              f"| mean trend term T, bp² per session (5-min) | {T.mean():+.2f} [{np.percentile(Tb, 2.5):+.2f}, {np.percentile(Tb, 97.5):+.2f}] | 0 |",
              f"\nf = √(H/0.40) = **{math.sqrt(H5[0] / BRACKET_SHARE):.3f}** (bracket σ ÷ what the window actually carries, if f < 1 the bracket is too wide).\n"]

    pre = res["pre-CAS"]
    e, idx = pre["e"], pre["idx"]
    L += ["## VR by 13:00 DayType label (pre-CAS)\n",
          "| label | 2024+ (out of sample): n, VR [95% CI] | 2023 (in-sample model): n, VR |", "|---|--:|--:|"]
    grp = {}
    oos = (e.session >= LABEL_OOS_FROM).to_numpy()
    for r in REGIMES:
        m = ((e.regime == r).to_numpy()) & oos
        m23 = ((e.regime == r).to_numpy()) & ~oos
        g = group_ratio_ci(e.hold_ret2.to_numpy(), e.hold_rv5.to_numpy(), m, idx)
        grp[r] = g
        v23 = e.hold_ret2[m23].sum() / e.hold_rv5[m23].sum() if m23.any() else float("nan")
        L.append(f"| {r} | {m.sum()}, {fmt(g)} | {m23.sum()}, {v23:.3f} |")
    L.append(f"\nSessions with no 13pm fact: {e.regime.isna().sum()} (excluded from this table only).\n")

    H5, VR5 = pre["H5"], pre["VR5"]
    f = math.sqrt(H5[0] / BRACKET_SHARE)
    q1 = (f"√t bracket misstates the hold move by factor f = {f:.3f}. A corrected-σ bracket is a v2 candidate for the "
          "promotion pipeline; E008 is unchanged."
          if (not H5[1] <= BRACKET_SHARE <= H5[2]) and abs(f - 1) >= 0.10
          else "√t scaling is adequate for the bracket; no v2 item from this question.")
    if VR5[1] > 1:
        q2a = "Afternoons trend (VR > 1): the unhedged book pays trend on top of variance."
    elif VR5[2] < 1:
        q2a = "Afternoons revert (VR < 1): the unhedged book gains from mean reversion beyond variance."
    else:
        q2a = "No detectable afternoon autocorrelation (VR CI contains 1)."
    ch = grp["Choppy"]
    q2b = ("The DayType gate has a mechanical rationale: Choppy VR lies entirely below both trend labels."
           if ch[2] < grp["BullTrend"][1] and ch[2] < grp["BearTrend"][1]
           else "No detectable path difference by label; the gate's value, if any, must come from elsewhere.")
    L += ["## Pinned conclusions (pre-analysis note §5, pre-CAS)\n", f"- **Q1:** {q1}", f"- **Q2 (pooled):** {q2a}",
          f"- **Q2 (by label):** {q2b}",
          "\nPost-CAS is descriptive only (few sessions). Nothing here changes an E008 rule."]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
