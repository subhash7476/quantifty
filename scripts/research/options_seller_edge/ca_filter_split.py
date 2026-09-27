"""W6 — split the cycles `ca_in_hold` drops into corporate actions vs pure moves.

Pre-analysis note: docs/reports/strategies/STRADDLE_CA_FILTER_SPLIT_PREREG_2026-09-27.md
Accounting on the spent window: the build and the study scripts are unchanged; the
2026-09-11 parquet is read as-is (its SHA-256 goes into the report).

Usage: python ca_filter_split.py [--data-root F:/Nifty/data]
"""
import argparse
import hashlib
import sys
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.psb1.disposition_register import DEMERGERS  # noqa: E402

REPORT = ROOT / "docs" / "reports" / "strategies" / "STRADDLE_CA_FILTER_SPLIT_2026-09-27.md"
VARIANT = "m10"
SPREAD = 0.02
KINK = -0.03
WINDOWS = {
    "discovery": ("2016-01-01", "2022-12-31"),
    "confirmation": ("2023-01-01", "2026-08-24"),
    "post-reform": ("2024-11-20", "2026-08-24"),
}
# Pinned reproduction targets (study §2.1 / §5.2): (mean, t)
TARGETS = {"discovery": (0.115, 4.98), "confirmation": (0.082, 2.90)}


def prepare(df):
    """cycle_study.load() columns and filters, minus the ca_in_hold filter."""
    df = df.copy()
    df["entry_date"] = pd.to_datetime(df.entry_date)
    df["exit_date"] = pd.to_datetime(df.exit_date)
    df = df[(df.variant == VARIANT) & (df.underlying != "NIFTY")]
    df = df[df.ce_exit.notna() & df.pe_exit.notna() & df.fut_exit.notna()
            & (df.n20 >= 15) & (df.n60 >= 40) & (df.rv20 > 0)].copy()
    df["prem"] = df.ce + df.pe
    df["prem_exit"] = df.ce_exit + df.pe_exit
    df["ret"] = (df.prem - df.prem_exit) / df.prem
    df["pnl_f"] = (df.prem - df.prem_exit) / df.fut_entry
    stt = np.select([df.entry_date < "2023-04-01", df.entry_date < "2024-10-01"],
                    [0.0005, 0.000625], 0.001)
    exch = np.where(df.entry_date < "2024-10-01", 0.00053, 0.000350) * 1.18
    df["fees"] = stt + exch * (1 + df.prem_exit / df.prem) + 0.00003 * df.prem_exit / df.prem + 0.003
    df["net"] = df.ret - df.fees - SPREAD / 2 * (1 + df.prem_exit / df.prem)
    df["dropped"] = df.ca_in_hold.fillna(0) != 0
    return df


def in_window(df, w):
    lo, hi = WINDOWS[w]
    return df[(df.entry_date >= lo) & (df.entry_date <= hi)]


def by_expiry_stat(d):
    x = d.groupby("expiry_dt").net.mean()
    t = x.mean() / x.std() * np.sqrt(len(x)) if len(x) > 2 else np.nan
    return x.mean(), t, len(x)


def classify(dropped, data_root):
    con = duckdb.connect(str(Path(data_root) / "market_data" / "equity_bhavcopy.duckdb"), read_only=True)
    ca = con.execute("""
        select symbol, ex_date, action_type from corporate_actions where action_type in ('SPLIT','BONUS')
        union select symbol, ex_date, action_type from adjustment_factors""").df()
    known = {s for (s,) in con.execute("select distinct symbol from corporate_actions").fetchall()}
    con.close()
    ca = pd.concat([ca, pd.DataFrame([(s, d, "DEMERGER") for s, d in DEMERGERS],
                                     columns=["symbol", "ex_date", "action_type"])])
    ca["ex_date"] = pd.to_datetime(ca.ex_date)
    kinds, events = [], []
    for r in dropped.itertuples():
        hit = ca[(ca.symbol == r.underlying) & (ca.ex_date > r.entry_date) & (ca.ex_date <= r.exit_date)]
        kinds.append("ca_verified" if len(hit) else "pure_move")
        events.append(", ".join(f"{a} {d.date()}" for a, d in zip(hit.action_type, hit.ex_date)))
    out = dropped.copy()
    out["kind"] = kinds
    out["ca_events"] = events
    out["symbol_in_register"] = out.underlying.isin(known)
    return out


def max_abs_move(rows, data_root):
    """Largest |daily front-future log return| inside each row's hold."""
    con = duckdb.connect(str(Path(data_root) / "market_data" / "futures_bhavcopy.duckdb"), read_only=True)
    out = []
    for r in rows.itertuples():
        v = con.execute("""
            with c as (select trade_date, close, lag(close) over (order by trade_date) pc
                       from futures_bhavcopy where inst_type='FUTSTK' and underlying=? and expiry_dt=?
                         and trade_date between ? and ?)
            select max(abs(ln(close/pc))) from c where pc > 0 and trade_date > ?""",
            [r.underlying, r.expiry_dt, r.entry_date.date(), r.exit_date.date(), r.entry_date.date()]).fetchone()[0]
        out.append(v)
    con.close()
    return out


def nifty_hold_returns(cycles, data_root):
    """Nifty 50 close-to-close return from entry_date to exit_date, 1d store."""
    d1 = Path(data_root) / "market_data" / "nse" / "candles" / "1d"

    def close(d):
        c = duckdb.connect(str(d1 / f"{d.date().isoformat()}.duckdb"), read_only=True)
        v = c.execute("select close from candles where symbol='NSE_INDEX|Nifty 50'").fetchone()
        c.close()
        if v is None:
            raise RuntimeError(f"no Nifty 50 close in 1d store for {d.date()}")
        return v[0]

    return [close(b) / close(a) - 1 for a, b in zip(cycles.entry_date, cycles.exit_date)]


def kinked(y, x):
    X = sm.add_constant(np.column_stack([x, np.minimum(x - KINK, 0)]))
    fit = sm.OLS(y, X).fit(cov_type="HC1")
    beta, gamma = fit.params[1], fit.params[2]
    cov = fit.cov_params()
    se_down = np.sqrt(cov[1, 1] + cov[2, 2] + 2 * cov[1, 2])
    q = sm.OLS(y, sm.add_constant(np.column_stack([x, x ** 2]))).fit(cov_type="HC1")
    return dict(beta=beta, beta_se=np.sqrt(cov[1, 1]), beta_down=beta + gamma, beta_down_se=se_down,
                n_below=int((x < KINK).sum()), n=len(y), quad=q.params[2], quad_t=q.tvalues[2])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default=str(ROOT / "data"))
    a = ap.parse_args()
    pq = Path(a.data_root) / "scratch" / "options_seller_edge" / "stock_straddles.parquet"
    sha = hashlib.sha256(pq.read_bytes()).hexdigest()
    df = prepare(pd.read_parquet(pq))
    L = [f"# W6 — Stock-Straddle `ca_in_hold` Split and Kinked Beta (generated)\n",
         f"Pre-analysis note: `STRADDLE_CA_FILTER_SPLIT_PREREG_2026-09-27.md`. Script: "
         f"`scripts/research/options_seller_edge/ca_filter_split.py`.\n",
         f"- Parquet: `{pq.name}`, SHA-256 `{sha}`",
         f"- Construct: variant `{VARIANT}`, stock names only, net at {SPREAD:.0%} spread, per-expiry mean then t across expiries\n",
         "## 1. Reproduction gate (filter in place)\n",
         "| window | mean | t | expiries | target mean | target t | pass |", "|---|--:|--:|--:|--:|--:|---|"]
    ok = True
    for w, (tm, tt) in TARGETS.items():
        m, t, n = by_expiry_stat(in_window(df[~df.dropped], w))
        p = abs(m - tm) <= 0.001 and abs(t - tt) <= 0.05
        ok &= p
        L.append(f"| {w} | {m:+.2%} | {t:.2f} | {n} | {tm:+.1%} | {tt:.2f} | {'PASS' if p else 'FAIL'} |")
    L.append("\n(Tolerance pinned in the note: ±0.1 pp in mean, ±0.05 in t.)\n")
    L.append("Erratum to the note: it quotes discovery as \"166 expiries\"; 166 is the study's *names per "
             "expiry* column (§2.1). The gate tests mean and t only, as pinned, so it is unaffected.\n")
    if not ok:
        L.append("**Reproduction gate FAILED — stopping, per the pre-analysis note.**")
        REPORT.write_text("\n".join(L), encoding="utf-8")
        print("\n".join(L))
        return 1

    dropped = classify(df[df.dropped], a.data_root)
    dropped["max_abs_move"] = max_abs_move(dropped, a.data_root)
    pure = dropped[dropped.kind == "pure_move"]
    L += ["## 2. What the filter drops\n",
          "| window | clean rows | dropped | CA-verified | pure move | pure-move share of rows |",
          "|---|--:|--:|--:|--:|--:|"]
    for w in WINDOWS:
        dw, cw = in_window(dropped, w), in_window(df, w)
        npm = (dw.kind == "pure_move").sum()
        L.append(f"| {w} | {len(cw)} | {len(dw)} | {(dw.kind == 'ca_verified').sum()} | {npm} | {npm / len(cw):.3%} |")
    L.append(f"\nDropped symbols absent from the CA register entirely: "
             f"{sorted(set(dropped.loc[~dropped.symbol_in_register, 'underlying'])) or 'none'}\n")

    restored = pd.concat([df[~df.dropped], pure])
    L += ["## 3. Result with pure moves restored (CA-verified stay dropped)\n",
          "| window | filter kept: mean (t, n) | pure moves restored: mean (t, n) | change |", "|---|--:|--:|--:|"]
    res = {}
    for w in WINDOWS:
        m0, t0, n0 = by_expiry_stat(in_window(df[~df.dropped], w))
        m1, t1, n1 = by_expiry_stat(in_window(restored, w))
        res[w] = (m1, t1)
        L.append(f"| {w} | {m0:+.2%} ({t0:.2f}, {n0}) | {m1:+.2%} ({t1:.2f}, {n1}) | {m1 - m0:+.2%} |")
    m1, t1 = res["confirmation"]
    verdict = "SURVIVES its look-ahead (still INSUFFICIENT for a construct)" if (m1 > 0 and t1 >= 1.645) else "CLOSE"
    L.append(f"\n**Pinned decision rule (confirmation, restored): mean {m1:+.2%}, t {t1:.2f} → {verdict}.**\n")

    allw = in_window(restored, "confirmation")
    pw = in_window(pure, "confirmation")
    L += ["## 4. Tail disclosure\n",
          f"- Confirmation window: crash frequency p = {len(pw)} / {len(allw)} = {len(pw) / max(len(allw), 1):.3%} of rows; "
          f"mean net seller return on them {pw.net.mean():+.1%}" if len(pw) else "- Confirmation window: no pure-move rows.",
          f"- Whole sample: {len(pure)} pure-move rows, mean net seller return {pure.net.mean():+.1%}\n" if len(pure) else "",
          "Every pure-move row (for checking by eye):\n",
          "| symbol | entry | exit | max \\|daily move\\| | net seller return | P&L % notional | symbol in CA register |",
          "|---|---|---|--:|--:|--:|---|"]
    for r in pure.sort_values("net").itertuples():
        L.append(f"| {r.underlying} | {r.entry_date.date()} | {r.exit_date.date()} | {r.max_abs_move:.1%} | "
                 f"{r.net:+.1%} | {r.pnl_f:+.2%} | {r.symbol_in_register} |")
    L += ["\nCA-verified rows (kept dropped):\n", "| symbol | entry | exit | events |", "|---|---|---|---|"]
    for r in dropped[dropped.kind == "ca_verified"].sort_values("entry_date").itertuples():
        L.append(f"| {r.underlying} | {r.entry_date.date()} | {r.exit_date.date()} | {r.ca_events} |")

    L += ["\n## 5. Kinked market beta (descriptive)\n",
          f"y = equal-weight mean P&L (% of futures notional) per expiry; x = Nifty 50 entry→exit return; "
          f"kink k = {KINK:.0%}; HC1 standard errors.\n",
          "| sample | n | cycles x < k | β (se) | β_down (se) | x² coef (t) |", "|---|--:|--:|--:|--:|--:|"]
    for label, d in (("filter kept", df[~df.dropped]), ("pure moves restored", restored)):
        cyc = d.groupby("expiry_dt").agg(y=("pnl_f", "mean"), entry_date=("entry_date", "first"),
                                          exit_date=("exit_date", "first")).reset_index()
        cyc["x"] = nifty_hold_returns(cyc, a.data_root)
        k = kinked(cyc.y.to_numpy(), cyc.x.to_numpy())
        L.append(f"| {label} | {k['n']} | {k['n_below']} | {k['beta']:+.3f} ({k['beta_se']:.3f}) | "
                 f"{k['beta_down']:+.3f} ({k['beta_down_se']:.3f}) | {k['quad']:+.2f} ({k['quad_t']:.2f}) |")
    L.append("\nAll windows pooled (2016 → 2026-08). Few cycles fall below the kink, so β_down is imprecise; "
             "it is reported, not used to choose anything.")
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
