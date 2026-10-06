"""GEX-XS-5D stage runner: DEV (2016-22) then SEALED (2023 -> E_s), each read once.

Spec: docs/reports/GEX_XS_5D_PRE_REGISTRATION.md, FROZEN 2026-10-06, frozen SHA-256
0cd497ab... (LF bytes before the "## 14. Post-freeze change log" line). Guards (§11 P3):
the frozen SHA and the P1 calendar digest must match, DEV refuses 2023+ dates, SEALED
refuses unless the DEV report records PASS, and no report is ever overwritten.

Usage (from the repo root; --data points at the data directory):
    python -m scripts.gex_xs_5d.run_stage --stage dev --data F:/Nifty/data
    python -m scripts.gex_xs_5d.run_stage --stage sealed --data F:/Nifty/data
"""
from __future__ import annotations

import argparse
import hashlib
import math
import re
import subprocess
import time as _time
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from core.analytics.gex_history import day_regime, select_strikes
from core.market.session_schedule import session_window
from scripts.gex_xs_5d import panel as P
from scripts.gex_xs_5d.ingest_board_meetings import calendar_digest

ROOT = Path(__file__).resolve().parents[2]
PREREG = ROOT / "docs" / "reports" / "GEX_XS_5D_PRE_REGISTRATION.md"
FROZEN_SHA = "0cd497ab40535a46be902d2b3add94903c8cabfcc85fb1cb41a2a29ef08f8a29"
CALENDAR_DIGEST = "067fa6880c737571a3216a6898f00178f57bc7e9cc9c7a30ba355e43bdb299f9"
E_S = date(2026, 10, 5)
SEALED_START = date(2023, 1, 1)
STAGES = {"dev": (date(2016, 2, 11), date(2022, 12, 31)), "sealed": (SEALED_START, E_S)}
REPORTS = {s: ROOT / "docs" / "reports" / f"GEX_XS_5D_{s.upper()}.md" for s in STAGES}
SECTION_14 = re.compile(rb"(?m)^## 14\. Post-freeze change log$")
RUNNER_PATHS = ["scripts/gex_xs_5d", "core/analytics/gex_history.py"]
CONTROLS = ["ln_iv", "ln_rv5", "ln_rv20", "r_1", "r_5"]
SPLITS = {"dev": [("physical settlement (2019-10-01)", date(2019, 10, 1))],
          "sealed": [("SEBI F&O reform (2024-11-20)", date(2024, 11, 20)),
                     ("CAS (2026-08-03)", date(2026, 8, 3))]}
MONTHLY_MIN_UNDERLYINGS = 100


class GuardError(RuntimeError):
    pass


# ------------------------------------------------------------------ guards (§11 P3)

def frozen_sha_of_bytes(b: bytes) -> str:
    b = b.replace(b"\r\n", b"\n")
    m = SECTION_14.search(b)
    if m is None:
        raise GuardError("pre-registration has no '## 14. Post-freeze change log' line")
    return hashlib.sha256(b[:m.start()]).hexdigest()


def check_prereg(path: Path):
    got = frozen_sha_of_bytes(path.read_bytes())
    if got != FROZEN_SHA:
        raise GuardError(f"pre-registration frozen SHA {got[:12]}… != pinned {FROZEN_SHA[:12]}…")


def check_stage_dates(stage: str, dates):
    if stage == "dev" and any(d >= SEALED_START for d in dates):
        raise GuardError("DEV stage was handed a date in the sealed window")
    if stage == "sealed" and any(d < SEALED_START for d in dates):
        raise GuardError("SEALED stage was handed a pre-2023 date")


def check_dev_passed(path: Path):
    if not path.exists() or "**DEV verdict: PASS**" not in path.read_text(encoding="utf-8"):
        raise GuardError(f"SEALED requires {path.name} to record '**DEV verdict: PASS**'")


def check_report_absent(path: Path):
    if path.exists():
        raise GuardError(f"{path.name} exists; a stage report is written once and never overwritten")


def check_calendar(db: Path):
    got = calendar_digest(duckdb.connect(str(db), read_only=True), E_S)
    if got != CALENDAR_DIGEST:
        raise GuardError(f"board-meeting calendar digest {got[:12]}… != pinned {CALENDAR_DIGEST[:12]}…")


def runner_commit() -> str:
    dirty = subprocess.run(["git", "status", "--porcelain", "--", *RUNNER_PATHS], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    if dirty:
        raise GuardError(f"runner code has uncommitted changes:\n{dirty}")
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                          text=True).stdout.strip()


def verdict(test: dict) -> str:
    return "PASS" if test["mean"] < 0 and test["p_one_sided"] < 0.05 else "FAIL"


# ------------------------------------------------------------------ data

class StageData:
    """Everything one stage reads, restricted to the stage's own sessions (§2)."""

    def __init__(self, stage: str, data: Path):
        start, end = STAGES[stage]
        opt = duckdb.connect(str(data / "market_data" / "stock_options_bhavcopy.duckdb"), read_only=True)
        dates = [r[0] for r in opt.execute(
            "SELECT DISTINCT trade_date FROM stock_options_bhavcopy WHERE trade_date BETWEEN ? AND ?",
            [start, end]).fetchall()]
        opt.close()
        self.sessions = P.session_grid(dates, start, end)
        check_stage_dates(stage, self.sessions)
        self.data = data
        lo, hi = self.sessions[0], self.sessions[-1]

        fut = duckdb.connect(str(data / "market_data" / "futures_bhavcopy.duckdb"), read_only=True)
        f = fut.execute("""SELECT trade_date, underlying, expiry_dt, close FROM futures_bhavcopy
                           WHERE inst_type = 'FUTSTK' AND trade_date BETWEEN ? AND ?""", [lo, hi]).df()
        monthly = fut.execute("""SELECT expiry_dt FROM futures_bhavcopy WHERE inst_type = 'FUTSTK'
                                 GROUP BY 1 HAVING count(DISTINCT underlying) >= ?""",
                              [MONTHLY_MIN_UNDERLYINGS]).fetchall()
        fut.close()
        self.fut = {(r.trade_date.date(), r.underlying, r.expiry_dt.date()): r.close
                    for r in f.itertuples(index=False)}
        self.fut_names = defaultdict(set)
        for (d, u, _e) in self.fut:
            self.fut_names[d].add(u)
        self.monthly_expiries = sorted(r[0] for r in monthly)

        eq = duckdb.connect(str(data / "market_data" / "equity_bhavcopy.duckdb"), read_only=True)
        raw = eq.execute("""SELECT trade_date, symbol, high, low, close FROM equity_bhavcopy
                            WHERE series = 'EQ' AND trade_date BETWEEN ? AND ?""", [lo, hi]).df()
        adj = eq.execute("""SELECT trade_date, symbol, close FROM equity_bhavcopy_adjusted
                            WHERE series = 'EQ' AND trade_date BETWEEN ? AND ?""", [lo, hi]).df()
        intervals = eq.execute("SELECT symbol, valid_from, valid_to, entity FROM symbol_entity_intervals").fetchall()
        isin = eq.execute("SELECT symbol, isin FROM symbol_isin WHERE isin LIKE 'INE%'").fetchall()
        eq.close()
        self.hl = {(r.symbol, r.trade_date.date()): (r.high, r.low, r.close) for r in raw.itertuples(index=False)}
        self.adj = {(r.symbol, r.trade_date.date()): r.close for r in adj.itertuples(index=False)}
        self.entity_rows = defaultdict(list)       # symbol -> [(from, to, entity)]
        self.entity_syms = defaultdict(list)       # entity -> [(from, to, symbol)]
        for s, a, b, e in intervals:
            self.entity_rows[s].append((a, b, e))
            self.entity_syms[e].append((a, b, s))
        self.prefix = {s: i[:9] for s, i in isin}

        bm = duckdb.connect(str(data / "research" / "gex_xs_5d" / "board_meetings.duckdb"), read_only=True)
        rows = bm.execute("""SELECT isin_prefix, symbol, bm_date, known_ts FROM board_meetings
                             WHERE is_results AND bm_date <= ?""", [E_S]).fetchall()
        bm.close()
        self.meetings = P.index_meetings(
            [{"isin_prefix": a, "symbol": b, "bm_date": c, "known_ts": d} for a, b, c, d in rows])

    def symbol_on(self, symbol: str, t: date, d: date) -> str:
        """The symbol carrying `symbol`'s entity (as of t) on date d; time-aware (§3)."""
        ent = next((e for a, b, e in self.entity_rows.get(symbol, []) if a <= t <= b), None)
        if ent is None:
            return symbol
        return next((s for a, b, s in self.entity_syms[ent] if a <= d <= b), symbol)

    def chains(self, month_sessions: list[date]) -> pd.DataFrame:
        opt = duckdb.connect(str(self.data / "market_data" / "stock_options_bhavcopy.duckdb"), read_only=True)
        df = opt.execute("""
            SELECT trade_date, underlying, expiry_dt, strike, option_type, close, contracts, open_int
            FROM stock_options_bhavcopy
            WHERE trade_date BETWEEN ? AND ? AND expiry_dt > trade_date
              AND (contracts > 0 OR open_int > 0)""", [month_sessions[0], month_sessions[-1]]).df()
        opt.close()
        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
        df["expiry_dt"] = pd.to_datetime(df["expiry_dt"]).dt.date
        return df


# ------------------------------------------------------------------ per-session panel (§3-§7)

def _parkinson_mean(sd: StageData, symbol, t, days, minimum):
    vals = []
    for d in days:
        bar = sd.hl.get((sd.symbol_on(symbol, t, d), d))
        if bar is not None and bar[0] > 0 and bar[1] > 0:
            vals.append(P.parkinson(bar[0], bar[1]))
    return (sum(vals) / len(vals)) if len(vals) >= minimum else None


def build_name(sd: StageData, i: int, und: str, chain: pd.DataFrame):
    """One name on session i. Returns (record, None) or (None, drop_reason)."""
    s, t = sd.sessions, sd.sessions[i]
    bar = sd.hl.get((und, t))
    if bar is None:
        return None, "U2_no_eq_row"
    spot = bar[2]
    t5 = s[i + P.STEP]
    by_exp, listed = {}, sorted(chain["expiry_dt"].unique())
    for exp in listed:
        fwd = sd.fut.get((t, und, exp))
        if fwd is None or abs(fwd / spot - 1) > P.MAX_FWD_DEV:
            continue
        by_exp[exp] = select_strikes(chain[chain["expiry_dt"] == exp], fwd, (exp - t).days / 365)
    expiries = [e for e in by_exp.values() if len(e.strikes)]
    if not P.name_valid(expiries):
        return None, "U3_validity"
    n = day_regime(expiries).net_norm
    iv_exp = P.iv_expiry(listed, t5)
    iv = P.atm_iv(by_exp[iv_exp]) if iv_exp in by_exp and len(by_exp[iv_exp].strikes) else None
    if iv is None:
        return None, "U3_atm_iv"
    rv = _parkinson_mean(sd, und, t, s[i + 1:i + P.STEP + 1], P.STEP)
    if rv is None:
        return None, "outcome_missing_bar"
    if rv == 0:
        return None, "outcome_zero_rv"
    rv5 = _parkinson_mean(sd, und, t, s[max(0, i - 4):i + 1], P.RV5_MIN)
    rv20 = _parkinson_mean(sd, und, t, s[max(0, i - 19):i + 1], P.RV20_MIN)
    closes = [sd.adj.get((sd.symbol_on(und, t, s[j]), s[j])) if j >= 0 else None for j in (i, i - 1, i - 5)]
    if not rv5 or not rv20 or any(c is None or c <= 0 for c in closes):
        return None, "U3_controls"
    prefix = sd.prefix.get(und)
    close_dt = datetime.combine(t, session_window("derivatives", t)[1])
    if P.results_excluded(sd.meetings, prefix, und, t, t5, close_dt):
        return None, "U4_results"
    return {
        "i": i, "t": t, "symbol": und, "N": n,
        "y": math.log(rv * 252 / iv ** 2),
        "ln_iv": math.log(iv), "ln_rv5": math.log(rv5 * 252), "ln_rv20": math.log(rv20 * 252),
        "r_1": math.log(closes[0] / closes[1]), "r_5": math.log(closes[0] / closes[2]),
        "posthoc_results": P.results_excluded(sd.meetings, prefix, und, t, t5, close_dt, posthoc=True),
        "window_expiry": any(t < x <= t5 for x in sd.monthly_expiries),
    }, None


def build_panel(sd: StageData):
    """Every session with t+5 inside the stage; all five phases read from this panel."""
    s = sd.sessions
    todo = [i for i in range(len(s)) if i + P.STEP <= len(s) - 1]
    records, drops = [], defaultdict(Counter)
    by_month = defaultdict(list)
    for i in todo:
        by_month[(s[i].year, s[i].month)].append(i)
    t0 = _time.time()
    for k, idx in enumerate(by_month.values()):
        ch = sd.chains([s[idx[0]], s[idx[-1]]])
        for i in idx:
            day = ch[ch["trade_date"] == s[i]]
            for und, chain in day.groupby("underlying"):
                if und not in sd.fut_names[s[i]]:
                    continue
                rec, why = build_name(sd, i, und, chain)
                if rec is None:
                    drops[i][why] += 1
                else:
                    records.append(rec)
        print(f"  {s[idx[0]]:%Y-%m}: {len(records):,} records ({_time.time() - t0:,.0f}s)", flush=True)
    return pd.DataFrame(records), drops


# ------------------------------------------------------------------ statistic and test (§8, §1)

def formation_ic(df: pd.DataFrame, method="spearman", sign=False):
    if len(df) < P.MIN_NAMES:
        return None
    C = np.column_stack([P.winsorize(df[c].to_numpy(float)) for c in CONTROLS])
    y = P.winsorize(df["y"].to_numpy(float))
    n = df["N"].to_numpy(float)
    return P.residual_ic(np.sign(n) if sign else n, y, C, method)


def phase_series(panel: pd.DataFrame, n_sessions: int, phase: int, **kw):
    groups = dict(tuple(panel.groupby("i"))) if len(panel) else {}
    out = []
    for i in P.formation_indices(n_sessions, phase):
        df = groups.get(i, panel.iloc[0:0])
        out.append((i, len(df), formation_ic(df, **kw)))
    return out


def _test(series):
    ics = np.array([ic for _, _, ic in series if ic is not None])
    return P.nw_mean_test(ics) if len(ics) > 2 else {"n": len(ics), "mean": float("nan"),
                                                     "se": float("nan"), "t": float("nan"),
                                                     "p_one_sided": float("nan")}


def analyse(stage: str, sd: StageData, panel: pd.DataFrame, drops) -> dict:
    s, n = sd.sessions, len(sd.sessions)
    main = phase_series(panel, n, 0)
    valid = [(i, k, ic) for i, k, ic in main if ic is not None]
    res = {"stage": stage, "sessions": n, "formations": len(main), "valid": len(valid),
           "void": [s[i] for i, _, ic in main if ic is None], "test": _test(main)}
    res["verdict"] = verdict(res["test"])
    ics = np.array([ic for _, _, ic in valid])
    res["ac1"] = P.ac1(ics)
    res["names"] = [k for _, k, _ in valid]
    res["drops"] = sum((drops[i] for i, _, _ in main), Counter())
    years = defaultdict(list)
    for i, _, ic in valid:
        years[s[i].year].append(ic)
    res["per_year"] = {y: (len(v), float(np.mean(v))) for y, v in sorted(years.items())}
    sub = lambda keep: _test([x for x in main if keep(x)])
    res["splits"] = []
    for label, cut in SPLITS[stage]:
        res["splits"] += [(f"before {label}", sub(lambda x: s[x[0]] < cut)),
                          (f"on/after {label}", sub(lambda x: s[x[0]] >= cut))]
    expiry_i = set(panel.loc[panel["window_expiry"], "i"]) if len(panel) else set()
    res["splits"] += [("window contains a monthly expiry", sub(lambda x: x[0] in expiry_i)),
                      ("window without a monthly expiry", sub(lambda x: x[0] not in expiry_i))]
    res["variants"] = [
        ("post-hoc results exclusion (any results meeting in window)",
         _test(phase_series(panel[~panel["posthoc_results"]] if len(panel) else panel, n, 0))),
        ("sign of N in place of N", _test(phase_series(panel, n, 0, sign=True))),
        ("Pearson in place of Spearman", _test(phase_series(panel, n, 0, method="pearson"))),
    ]
    res["phases"] = [(p, _test(phase_series(panel, n, p))) for p in range(1, P.STEP)]
    return res


# ------------------------------------------------------------------ report

def _fmt(t):
    return (f"{t['n']} | {t['mean']:+.4f} | {t['t']:+.2f} | {t['p_one_sided']:.4f}"
            if t["n"] > 2 else f"{t['n']} | — | — | —")


def render(res: dict, commit: str, elapsed: float) -> str:
    st = res["stage"].upper()
    t = res["test"]
    names = res["names"]
    lines = [
        f"# GEX-XS-5D — {st} read",
        "",
        "Script-generated by `scripts/gex_xs_5d/run_stage.py` — do not hand-edit.",
        f"Pre-registration `docs/reports/GEX_XS_5D_PRE_REGISTRATION.md`, frozen SHA-256 `{FROZEN_SHA}` · "
        f"calendar digest `{CALENDAR_DIGEST}` · runner commit `{commit}` · E_s {E_S} · run "
        f"{datetime.now():%Y-%m-%d %H:%M} ({elapsed / 60:,.1f} min)",
        "",
        f"**{st} verdict: {res['verdict']}**",
        "",
        "Rule (§1): mean IC < 0 and one-sided Newey–West (lag 4) p < 0.05.",
        "",
        "| formations | valid | mean IC | NW se | t | one-sided p |",
        "|--:|--:|--:|--:|--:|--:|",
        f"| {res['formations']} | {res['valid']} | {t['mean']:+.5f} | {t['se']:.5f} | {t['t']:+.3f} | {t['p_one_sided']:.6f} |",
        "",
        f"Sessions {res['sessions']}. Void formations (< {P.MIN_NAMES} names): {len(res['void'])} "
        f"{[str(d) for d in res['void']]}. Names per valid formation: min {min(names) if names else '—'}, "
        f"median {int(np.median(names)) if names else '—'}, max {max(names) if names else '—'}. "
        f"IC series AC1 {res['ac1']:+.3f} (the RFA's power assumed independence; §9 tabulates AC1 0.3).",
        "",
        "## Drops on formation sessions, by reason",
        "",
        "| reason | name-sessions |",
        "|---|--:|",
        *[f"| {k} | {v:,} |" for k, v in sorted(res["drops"].items())],
        "",
        "`outcome_missing_bar` uses information after t (a suspension or delisting in t+1..t+5); "
        "reported as §5 requires.",
        "",
        "## Descriptive — not part of any pass rule (§10)",
        "",
        "| subset | n | mean IC | NW t | one-sided p |",
        "|---|--:|--:|--:|--:|",
        *[f"| {label} | {_fmt(x)} |" for label, x in res["splits"]],
        *[f"| {label} | {_fmt(x)} |" for label, x in res["variants"]],
        *[f"| formation phase {p} | {_fmt(x)} |" for p, x in res["phases"]],
        "",
        "| year | formations | mean IC |",
        "|---|--:|--:|",
        *[f"| {y} | {k} | {m:+.4f} |" for y, (k, m) in res["per_year"].items()],
        "",
        "A non-rejection is NOT DEMONSTRATED, never falsified (§9). A PASS is a state-variable "
        "finding, not a trade.",
    ]
    if res["stage"] == "dev":
        lines += ["", "DEV PASS authorizes the one-shot SEALED read; DEV FAIL ends the construct and "
                      "leaves SEALED unread (§1)."]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=list(STAGES), required=True)
    ap.add_argument("--data", type=Path, default=ROOT / "data")
    a = ap.parse_args()
    report = REPORTS[a.stage]
    check_report_absent(report)
    check_prereg(PREREG)
    check_calendar(a.data / "research" / "gex_xs_5d" / "board_meetings.duckdb")
    if a.stage == "sealed":
        check_dev_passed(REPORTS["dev"])
    commit = runner_commit()
    t0 = _time.time()
    sd = StageData(a.stage, a.data)
    print(f"{a.stage}: {len(sd.sessions)} sessions {sd.sessions[0]} -> {sd.sessions[-1]}")
    panel, drops = build_panel(sd)
    out = a.data / "research" / "gex_xs_5d" / f"panel_{a.stage}.duckdb"
    con = duckdb.connect(str(out))
    con.execute("CREATE OR REPLACE TABLE panel AS SELECT * FROM panel")
    con.close()
    res = analyse(a.stage, sd, panel, drops)
    check_report_absent(report)
    report.write_text(render(res, commit, _time.time() - t0), encoding="utf-8")
    print(f"{a.stage.upper()} verdict: {res['verdict']} -> {report}")


if __name__ == "__main__":
    main()
