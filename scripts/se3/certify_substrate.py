"""SE-3 Phase 1 — Confirmatory substrate certification.

Structural counts ONLY, on the confirmatory window 2016-02-11 -> 2022-12-31
(inclusive). NO return, NO IC, NO P&L is computed here. The module source must
contain no Spearman/IC call and no forward-return construction (asserted by a
test). Variant B is ABSENT: this module never touches the index-options
database.

Every A1-A14 pinned parameter is implemented exactly as pre-registered. The
three resolved ambiguities from SE3_IMPLEMENTATION_PROMPT.md section 3 are
encoded here as module constants so Phase 2 shares them:
  - skip-a-day (double-lag) return convention (section 3.2)
  - L/S direction: long bottom / short top richness quintile (section 3.3)
  - S3_MIN_USABLE_DATES = 756 (section 3.4)

The 2018-05 MCWB gap is resolved by operator decision 2026-08-05: June-2018
trade dates use the 2018-04 bulletin (the Apr-2018 and Jun-2018 rosters are
identical; verified at decision time). A missing month is filled from the
latest valid snapshot before it; the fill is reported in S1.

Phase 2 (run_confirmatory.py) imports the panel builder from here and adds
returns/IC/P&L on top — S3's usable-date count and Phase 2's actual IC dates
then reconcile by construction.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
import zipfile
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from scripts.osc.sd_probe import (
    implied_vol,
    _parity_forward,
)

# ── pinned constants (pre-reg A1-A14, B1-B8; implementation-prompt section 3) ─
FENCE_START = pd.Timestamp("2016-02-11")
FENCE_END = pd.Timestamp("2022-12-31")
DTE_LO = 7
DTE_HI = 60
SETTLE_FLOOR = 0.50
MONEYNESS_BAND = 0.10
MIN_NAMES = 20
RV_WINDOW = 21
RV_MIN_OBS = 18
NW_LAG = 5
ROLLING_WINDOW = 60
POWER_TARGET = 0.80
S3_MIN_USABLE_DATES = 756          # operator decision (pre-reg section 9.4)

# Resolved ambiguity 3.3: long the BOTTOM richness quintile, short the TOP.
LS_DIRECTION = "long_bottom_short_top"

# Resolved ambiguity 3.4: usable-date shortfall below this is a coded stop.
S3_THRESHOLD = S3_MIN_USABLE_DATES

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STOCK_OPTIONS_DB = PROJECT_ROOT / "data" / "market_data" / "stock_options_bhavcopy.duckdb"
FUTURES_DB = PROJECT_ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
EQUITY_DB = PROJECT_ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
REF_DIR = PROJECT_ROOT / "data" / "reference"
MANIFEST_PATH = REF_DIR / "mcwb_manifest.json"
CERT_REPORT = PROJECT_ROOT / "docs" / "reports" / "SE3_SUBSTRATE_CERTIFICATION.md"

DUMMY_SYMBOLS = {"DUMMYREL", "DUMMYTATAM", "DUMMYHDLVR"}


def _dte(expiry, trade_date):
    return (expiry - trade_date).days


def _pick_expiry(expiries, trade_date, lo=DTE_LO, hi=DTE_HI):
    """Nearest expiry with lo <= DTE <= hi. Returns expiry or None."""
    best = None
    best_dte = None
    for exp in expiries:
        d = _dte(exp, trade_date)
        if lo <= d <= hi:
            if best is None or d < best_dte:
                best, best_dte = exp, d
    return best


def _newey_west(x, lag):
    n = len(x)
    if n < 3:
        return np.nan, np.nan
    mean = np.mean(x)
    resid = x - mean
    s0 = np.sum(resid**2) / n
    s = s0
    for j in range(1, min(lag + 1, n - 1)):
        w = 1.0 - j / (lag + 1)
        s += 2.0 * w * np.sum(resid[j:] * resid[:-j]) / n
    se = math.sqrt(max(s, 1e-15) / n)
    return mean, se


def _corr_matrix_stats(panel):
    """Panel: rows=dates, cols=names. Returns rho_bar, N_eff, pc1, N."""
    filled = panel.dropna(axis=1)
    N = filled.shape[1]
    if N < 3:
        return None
    corr = filled.corr().values
    idx_upper = np.triu_indices(N, k=1)
    pairwise = corr[idx_upper]
    rho_bar = float(np.mean(pairwise))
    neff = N / (1 + (N - 1) * rho_bar) if N > 1 else N
    X_std = (filled - filled.mean()) / filled.std(ddof=1)
    cov = np.cov(X_std.values.T)
    eig = np.linalg.eigvalsh(cov)
    pc1 = float(eig[-1] / eig.sum()) if eig.sum() > 0 else np.nan
    return {"rho_bar": rho_bar, "neff": neff, "pc1": pc1, "N": N}


def _rolling_breadth(panel, window=ROLLING_WINDOW):
    rho_list, neff_list, pc1_list, n_list = [], [], [], []
    dates = panel.index.sort_values()
    for i in range(window - 1, len(dates)):
        win = panel.loc[dates[i - window + 1 : i + 1]]
        s = _corr_matrix_stats(win)
        if s:
            rho_list.append(s["rho_bar"])
            neff_list.append(s["neff"])
            pc1_list.append(s["pc1"])
            n_list.append(s["N"])
    return rho_list, neff_list, pc1_list, n_list


def _assert_fence(df):
    obs_min = df["trade_date"].min()
    obs_max = df["trade_date"].max()
    print(f"Fence: observed range [{obs_min.date()}, {obs_max.date()}]")
    assert obs_min >= FENCE_START, f"FENCE VIOLATION: min trade_date {obs_min.date()} < {FENCE_START.date()}"
    assert obs_max <= FENCE_END, f"FENCE VIOLATION: max trade_date {obs_max.date()} > {FENCE_END.date()}"
    return obs_min, obs_max


# ── loaders ──────────────────────────────────────────────────────────────────
def _load_member_dates():
    """All distinct stock-option trade dates in the fence (cheap DISTINCT)."""
    con = duckdb.connect(str(STOCK_OPTIONS_DB), read_only=True)
    rows = con.execute(
        "SELECT DISTINCT trade_date FROM stock_options_bhavcopy "
        "WHERE trade_date >= '2016-02-11' AND trade_date <= '2022-12-31' "
        "ORDER BY trade_date"
    ).fetchall()
    con.close()
    return [pd.Timestamp(r[0]) for r in rows]


def _load_stock_options(member_pairs, traded_only=False):
    """Member option rows in the fence, filtered to the (underlying, trade_date)
    pairs that are PIT members AND F&O-live (A1+A2). Filtering is done inside
    DuckDB so the whole 66M-row store is never materialised. With `traded_only`
    the A5 filter is pushed into SQL, so only the traded subset (~4M rows) is
    ever materialised — required for the confirmatory/audit path under memory
    constraints."""
    pairs = sorted(member_pairs)
    con = duckdb.connect(str(STOCK_OPTIONS_DB), read_only=True)
    con.register("mp", pd.DataFrame(pairs, columns=["underlying", "trade_date"]))
    traded_clause = " AND so.contracts > 0 AND so.open_int > 0" if traded_only else ""
    df = con.execute(
        f"""
        SELECT so.underlying, so.expiry_dt, so.strike, so.option_type, so.settle,
               so.contracts, so.open_int, so.trade_date
        FROM stock_options_bhavcopy so
        JOIN mp ON mp.underlying = so.underlying AND mp.trade_date = so.trade_date
        WHERE so.trade_date >= '2016-02-11' AND so.trade_date <= '2022-12-31'{traded_clause}
        ORDER BY so.trade_date, so.underlying, so.expiry_dt
        """
    ).fetchdf()
    con.close()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df["expiry_dt"] = pd.to_datetime(df["expiry_dt"])
    return df


def _count_member_rows(member_pairs):
    """COUNT of all (traded or not) member-pair option rows in the fence — for
    the attrition table, without materialising the frame."""
    pairs = sorted(member_pairs)
    con = duckdb.connect(str(STOCK_OPTIONS_DB), read_only=True)
    con.register("mp", pd.DataFrame(pairs, columns=["underlying", "trade_date"]))
    n = con.execute(
        """
        SELECT COUNT(*) FROM stock_options_bhavcopy so
        JOIN mp ON mp.underlying = so.underlying AND mp.trade_date = so.trade_date
        WHERE so.trade_date >= '2016-02-11' AND so.trade_date <= '2022-12-31'
        """
    ).fetchone()[0]
    con.close()
    return int(n)


def _load_futures(member_syms):
    ph = ",".join(f"'{s}'" for s in sorted(member_syms))
    con = duckdb.connect(str(FUTURES_DB), read_only=True)
    df = con.execute(
        f"""
        SELECT underlying, expiry_dt, trade_date, inst_type, settle
        FROM futures_bhavcopy
        WHERE underlying IN ({ph})
          AND inst_type = 'FUTSTK'
          AND trade_date >= '2016-02-11'
          AND trade_date <= '2022-12-31'
        """
    ).fetchdf()
    con.close()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df["expiry_dt"] = pd.to_datetime(df["expiry_dt"])
    return df


def _mcwb_rows(raw, filename):
    """Yield {symbol, weight} from an MCWB CSV, columns located by header name."""
    textio = io.StringIO(raw)
    reader = csv.reader(textio)
    header = None
    rows = []
    for line in reader:
        if not line or not line[0].strip():
            continue
        joined = ",".join(line)
        if "Security Symbol" in joined:
            header = line
            continue
        if header is not None:
            rows.append(line)
    if header is None:
        sys.exit(f"FATAL: header not found in {filename}")
    try:
        sym_idx = header.index("Security Symbol")
    except ValueError:
        sys.exit(f"FATAL: Security Symbol column not found in {filename}")
    w_idx = None
    for i, col in enumerate(header):
        if col.strip() in ("Weightage (%)", "Weightage", "Weightage%", "Index Weightage (%)"):
            w_idx = i
            break
    out = []
    for r in rows:
        if len(r) <= sym_idx:
            continue
        sym = r[sym_idx].strip().upper()
        if not sym:
            continue
        w = None
        if w_idx is not None and len(r) > w_idx:
            wstr = r[w_idx].strip()
            if wstr not in ("", "-"):
                try:
                    w = float(wstr.replace("%", ""))
                except ValueError:
                    sys.exit(f"FATAL: unparseable weight {wstr!r} in {filename}")
        out.append({"symbol": sym, "weight": w})
    return out


def _load_mcwb():
    """snapshots: {month_str: {symbol: weight_pct}}; pollution: {symbol: first_month}."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    valid = [r for r in manifest["records"] if r["status"] == "valid"]
    snapshots = {}
    pollution = {}
    for rec in sorted(valid, key=lambda r: r["month"]):
        month = rec["month"]
        with zipfile.ZipFile(REF_DIR / rec["filename"]) as zf:
            if "nifty50_mcwb.csv" not in zf.namelist():
                sys.exit(f"FATAL: nifty50_mcwb.csv missing from {rec['filename']}")
            raw = zf.read("nifty50_mcwb.csv").decode("utf-8", errors="replace")
        members = {}
        for row in _mcwb_rows(raw, rec["filename"]):
            sym = row["symbol"]
            if sym in DUMMY_SYMBOLS or sym.startswith("DUMMY") or sym.startswith("TMPV"):
                if sym not in pollution:
                    pollution[sym] = month
                continue
            if row["weight"] is None:
                sys.exit(
                    f"FATAL: weight column not located in {rec['filename']} layout; "
                    "stopping per A1 (do not substitute equal weights)."
                )
            members[sym] = row["weight"]
        snapshots[month] = members
    return snapshots, pollution


def _membership_for_date(snapshots, td, fills):
    """Month M's membership applies to trade dates in month M+1 only.

    If the snapshot for the month before td's month is missing, fill from the
    latest valid snapshot before it (operator decision 2026-08-05 for 2018-05).
    The fill is recorded in `fills`.
    """
    if td.month == 1:
        key = f"{td.year - 1:04d}-12-01"
    else:
        key = f"{td.year:04d}-{td.month - 1:02d}-01"
    if key in snapshots:
        return snapshots[key]
    months = sorted(snapshots)
    earlier = [m for m in months if m < key]
    if not earlier:
        sys.exit(f"FATAL: no MCWB snapshot at or before {key} for trade date {td.date()}")
    fill_from = earlier[-1]
    fills[(key, td.date())] = fill_from
    return snapshots[fill_from]


def _load_ca_register():
    """Load the corporate-action register for FUTSTK underlyings.

    Authority: `adjustment_factors` in `equity_bhavcopy.duckdb` (built from the
    NSE CF-CA feed by `scripts/csmp/ingest_corporate_actions.py`). The observed
    futures price jump is CONFIRMATION ONLY — never the ratio source.

    Returns {symbol: {ex_date: product_of_same_day_factors}}, where `symbol` is
    BOTH the register's symbol and every alias of its entity resolved to that
    symbol (via `symbol_entity_intervals`). This makes the map usable against a
    FUTSTK `underlying` that may be a different ticker for the same entity (NSE
    recycles tickers; a CA registered under a legacy ticker must drop the return
    on the current one).
    """
    con = duckdb.connect(str(EQUITY_DB), read_only=True)
    try:
        rows = con.execute(
            "SELECT symbol, ex_date, factor, action_type FROM adjustment_factors "
            "WHERE action_type IN ('SPLIT','BONUS')"
        ).fetchall()
        iv_rows = con.execute(
            "SELECT symbol, valid_from, valid_to, entity FROM symbol_entity_intervals"
        ).fetchall()
    finally:
        con.close()

    # entity -> set of symbols ever trading as it, and symbol -> entity at a date
    entity_syms = {}
    sym_iv = {}
    for sym, vf, vt, ent in iv_rows:
        entity_syms.setdefault(ent, set()).add(sym)
        sym_iv.setdefault(sym, []).append((vf, vt, ent))

    def _entity(sym, on_date):
        for vf, vt, ent in sym_iv.get(sym, []):
            if vf <= on_date < vt:
                return ent
        return sym

    # primary key: raw symbol (matches FUTSTK underlying). For each entity that
    # owns a CA, alias the ex-date onto every symbol the entity has traded as.
    register = {}
    for sym, ex, factor, at in rows:
        if factor is None or factor <= 0:
            continue
        ent = _entity(sym, ex)
        targets = entity_syms.get(ent, {sym})
        for t in targets:
            d = register.setdefault(t, {})
            d[ex] = d.get(ex, 1.0) * float(factor)
    return register


def _front_month_rv(g, ca_ex_dates=None):
    """Per-underlying FUTSTK frame -> trailing 21-day annualized RV series.
    Front-month = nearest expiry with DTE >= 7; roll-gap returns dropped, and
    (with `ca_ex_dates`) returns spanning a corporate-action ex-date are dropped
    too — a split changes the price basis without changing the contract, so the
    roll-gap guard alone is blind to it (SE3_CA_CONTAMINATION_REVIEW §7)."""
    g = g.sort_values("trade_date")
    fronts = []
    for td, gg in g.groupby("trade_date"):
        best = _pick_expiry(gg["expiry_dt"].unique(), td, lo=DTE_LO, hi=10_000)
        if best is None:
            continue
        row = gg[gg["expiry_dt"] == best].iloc[0]
        fronts.append({"trade_date": td, "expiry_dt": best, "settle": row["settle"]})
    if not fronts:
        return None
    fdf = pd.DataFrame(fronts).sort_values("trade_date").reset_index(drop=True)
    fdf["prev_exp"] = fdf["expiry_dt"].shift(1)
    fdf["prev_settle"] = fdf["settle"].shift(1)
    fdf["ret"] = np.log(fdf["settle"] / fdf["prev_settle"])
    fdf.loc[fdf["expiry_dt"] != fdf["prev_exp"], "ret"] = np.nan
    if ca_ex_dates:
        ca_dates = pd.DatetimeIndex(sorted(pd.Timestamp(d) for d in ca_ex_dates))
        fdf.loc[fdf["trade_date"].isin(ca_dates), "ret"] = np.nan
    fdf["rv"] = fdf["ret"].rolling(RV_WINDOW, min_periods=RV_MIN_OBS).std(ddof=1) * math.sqrt(252)
    fdf["n_obs"] = fdf["ret"].rolling(RV_WINDOW, min_periods=RV_MIN_OBS).count()
    fdf.loc[fdf["n_obs"] < RV_MIN_OBS, "rv"] = np.nan
    return fdf


# ── panel builder (structural: NO returns, NO IC, NO P&L) ────────────────────
def build_panel():
    """Return the structural panel + S1-S6 tallies. Nothing return-like is
    computed. The panel carries richness (A11) and the per-row ingredients Phase
    2 needs to build the skip-a-day return, plus a structural `dh_ok` flag for
    the usable-date waterfall (cell + forward existence at the next two panel
    rows of that name — existence checks only, no return value)."""

    snapshots, pollution = _load_mcwb()
    print(f"MCWB snapshots: {len(snapshots)} valid; pollution findings: {pollution}")

    # Snapshot months that feed the fence (month M applies to M+1).
    fence_snap_months = set()
    for td in pd.date_range(FENCE_START, FENCE_END, freq="MS"):
        if td.month == 1:
            fence_snap_months.add(f"{td.year - 1:04d}-12-01")
        else:
            fence_snap_months.add(f"{td.year:04d}-{td.month - 1:02d}-01")
    member_syms = set()
    for month, m in snapshots.items():
        if month in fence_snap_months:
            member_syms |= set(m.keys())
    member_syms.difference_update(DUMMY_SYMBOLS)
    print(f"Union of member symbols across fence window: {len(member_syms)}")

    all_dates = _load_member_dates()
    fills = {}
    membership = {}
    for td in all_dates:
        membership[td] = set(_membership_for_date(snapshots, td, fills).keys())

    # --- S1 cardinality (MEDIUM-2, lead review): membership must resolve to the
    #     source roster's own cardinality, not just "some set". Nifty 50 snapshots
    #     are 50 symbols, except the DVR era (2016-2017) where TATAMTRDVR is
    #     double-listed -> 51. Any other count is a collision to report. ---
    roster_size = {}
    card_issues = []
    for td in all_dates:
        snap = _membership_for_date(snapshots, td, fills)
        n = len(snap)
        key = td.strftime("%Y-%m")
        roster_size[key] = n
        if n not in (50, 51):
            card_issues.append((td.date(), n, sorted(snap)))
    # The only legitimate 51 is the DVR double-listing (TATAMTRDVR).
    dvr_issue = []
    for td in all_dates:
        snap = _membership_for_date(snapshots, td, fills)
        if "TATAMTRDVR" in snap and "TATAMOTORS" in snap:
            dvr_issue.append(td.date())
    for td in all_dates:
        snap = _membership_for_date(snapshots, td, fills)
        assert len(snap) in (50, 51), (
            f"S1 CARDINALITY VIOLATION: {td.date()} membership has {len(snap)} symbols "
            f"(expected 50, or 51 only in the DVR era) — {sorted(snap)}"
        )
    s1_cardinality = {
        "sizes": sorted({(k, v) for k, v in roster_size.items()}),
        "issues": card_issues,
        "dvr_months": sorted(set(dvr_issue)),
        "n_members_50_or_51": all(len(_membership_for_date(snapshots, td, fills)) in (50, 51) for td in all_dates),
    }

    # --- F&O-live guard (A2): pairs where the name is a member AND has a FUTSTK
    #     row on that date.  Futures are small (<=1M rows) so loaded in full. ---
    raw_fut = _load_futures(member_syms)
    obs_fut = _assert_fence(raw_fut)
    fut_stk = raw_fut[raw_fut["inst_type"] == "FUTSTK"]
    fo_live = set(zip(fut_stk["underlying"], fut_stk["trade_date"]))
    member_pairs = set()
    for td, syms in membership.items():
        for s in syms:
            if (s, td) in fo_live:
                member_pairs.add((s, td))

    raw_stock = None
    rows_member = _count_member_rows(member_pairs)
    # Load only the traded subset (A5 pushed into SQL); the panel builder needs
    # traded cells only. The all-rows count for attrition comes from the COUNT.
    traded = _load_stock_options(member_pairs, traded_only=True)
    obs_stock = _assert_fence(traded)
    rows_traded = len(traded)

    fut_stk_settle = fut_stk.set_index(["underlying", "expiry_dt", "trade_date"])["settle"]

    def _stock_forward(td, underlying, expiry, cells=None):
        try:
            f = fut_stk_settle.loc[(underlying, expiry, td)]
            if np.isfinite(f) and f > 0:
                return float(f)
        except KeyError:
            pass
        if cells is None:
            return np.nan
        g = cells[cells["expiry_dt"] == expiry]
        calls = g[g["option_type"] == "CE"][["strike", "settle"]]
        puts = g[g["option_type"] == "PE"][["strike", "settle"]]
        return _parity_forward(calls, puts, expiry, td)

    records = []
    attrit = {
        "rows_loaded": None,
        "rows_member": rows_member,
        "rows_traded": rows_traded,
        "dropped_no_expiry": 0,
        "dropped_no_forward": 0,
        "dropped_no_atm": 0,
        "iv_attempted": 0,
        "iv_discard": 0,
    }
    iv_by_year = {}
    names_by_year = {}

    traded = traded.sort_values(["trade_date", "underlying"])
    n_groups = traded.groupby(["trade_date", "underlying"]).ngroups
    print(f"Processing {n_groups:,} (date, underlying) groups ...")
    for gi, ((td, underlying), grp) in enumerate(
            traded.groupby(["trade_date", "underlying"])):
        if gi % 20000 == 0 and gi > 0:
            print(f"  group {gi:,}/{n_groups:,}")
        expiries = sorted(grp["expiry_dt"].unique())
        expiry = _pick_expiry(expiries, td)
        if expiry is None:
            attrit["dropped_no_expiry"] += 1
            continue
        F = _stock_forward(td, underlying, expiry, grp)
        if not np.isfinite(F) or F <= 0:
            attrit["dropped_no_forward"] += 1
            continue

        g = grp[grp["expiry_dt"] == expiry]
        gs = g[g["settle"] >= SETTLE_FLOOR]
        gm = gs[np.abs(np.log(gs["strike"] / F)) <= MONEYNESS_BAND]

        calls = gm[gm["option_type"] == "CE"]
        puts = gm[gm["option_type"] == "PE"]
        iv_call_cell = iv_put_cell = None
        T = _dte(expiry, td) / 365.0
        yr = td.year
        iv_by_year.setdefault(yr, {"attempted": 0, "discarded": 0})
        if len(calls):
            c = calls[calls["strike"] >= F]
            if len(c):
                c = c.loc[c["strike"].idxmin()]
                attrit["iv_attempted"] += 1
                iv_by_year[yr]["attempted"] += 1
                iv = implied_vol(c["settle"], F, c["strike"], T, "CE")
                if np.isnan(iv):
                    attrit["iv_discard"] += 1
                    iv_by_year[yr]["discarded"] += 1
                else:
                    iv_call_cell = (c["strike"], "CE", iv, c["settle"])
        if len(puts):
            p = puts[puts["strike"] < F]
            if len(p):
                p = p.loc[p["strike"].idxmax()]
                attrit["iv_attempted"] += 1
                iv_by_year[yr]["attempted"] += 1
                iv = implied_vol(p["settle"], F, p["strike"], T, "PE")
                if np.isnan(iv):
                    attrit["iv_discard"] += 1
                    iv_by_year[yr]["discarded"] += 1
                else:
                    iv_put_cell = (p["strike"], "PE", iv, p["settle"])
        if iv_call_cell is None and iv_put_cell is None:
            attrit["dropped_no_atm"] += 1
            continue

        sigmas = [c[2] for c in (iv_call_cell, iv_put_cell) if c]
        records.append({
            "trade_date": td,
            "underlying": underlying,
            "expiry_dt": expiry,
            "F_t": F,
            "sigma": float(np.mean(sigmas)),
            "iv_call": iv_call_cell,
            "iv_put": iv_put_cell,
        })
        names_by_year.setdefault(yr, set()).add(underlying)

    stock_df = pd.DataFrame(records) if records else pd.DataFrame(
        columns=["trade_date", "underlying", "expiry_dt", "F_t", "sigma", "iv_call", "iv_put"]
    )

    # --- A10 realized vol ---
    ca_register = _load_ca_register()
    rv_map = {}
    for underlying, g in fut_stk.groupby("underlying"):
        fdf = _front_month_rv(g, ca_ex_dates=ca_register.get(underlying))
        if fdf is None or fdf.empty:
            continue
        rv_map[underlying] = fdf[["trade_date", "rv"]].dropna(subset=["rv"]).set_index("trade_date")["rv"]

    rv_series = pd.Series(np.nan, index=stock_df.index)
    for i, (u, td) in enumerate(zip(stock_df["underlying"], stock_df["trade_date"])):
        m = rv_map.get(u)
        if m is not None and td in m.index:
            rv_series.iloc[i] = m.loc[td]
    stock_df["rv"] = rv_series.values

    # --- A11 richness (variant A): per-date OLS sigma ~ rv, residual ---
    richness = pd.Series(np.nan, index=stock_df.index)
    for td, grp in stock_df.groupby("trade_date"):
        gg = grp.dropna(subset=["sigma", "rv"])
        if len(gg) < MIN_NAMES:
            continue
        X = np.column_stack([np.ones(len(gg)), gg["rv"].values])
        y = gg["sigma"].values
        try:
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        except np.linalg.LinAlgError:
            continue
        richness.loc[gg.index] = y - (X @ beta)
    stock_df["richness"] = richness

    # --- structural pairing (usable-date waterfall): the skip-a-day IC at t
    #     pairs richness(t) with the name's NEXT panel row's return over
    #     t1 -> t2, where t1 = next row's date. That return needs the next
    #     row's ATM cell (expiry, strike, option_type) to be TRADED at t2 and
    #     the forward for that expiry to exist at t2. Existence checks only —
    #     no return value computed here. This mirrors exactly what Phase 2's
    #     `dh_skip` shift will require, so S3's usable-date count reconciles
    #     with Phase 2's IC dates by construction. ---
    stock_df = stock_df.sort_values(["underlying", "trade_date"]).reset_index(drop=True)
    # traded cell existence: (date, underlying, expiry, strike, ot)
    traded_keys = set(zip(traded["trade_date"], traded["underlying"],
                          traded["expiry_dt"], traded["strike"], traded["option_type"]))
    # parity-capable (date, underlying, expiry): BOTH a CE and a PE traded.
    # Forward exists at (date, underlying, expiry): FUTSTK settle present, or
    # both legs traded at that (date, underlying, expiry).
    fut_keys = set(zip(fut_stk_settle.index.get_level_values(0),
                       fut_stk_settle.index.get_level_values(1),
                       fut_stk_settle.index.get_level_values(2)))
    ce_keys = {(d, u, e) for (d, u, e, s, ot) in traded_keys if ot == "CE"}
    pe_keys = {(d, u, e) for (d, u, e, s, ot) in traded_keys if ot == "PE"}
    parity_ok = ce_keys & pe_keys

    def _forward_exists(td, underlying, expiry):
        if (underlying, expiry, td) in fut_keys:
            return True
        return (td, underlying, expiry) in parity_ok

    # can_form_return on a panel row (date d): next calendar trading day d2
    # exists in the fence, the row's ATM call or put cell is traded at d2, and
    # the forward for that expiry exists at d2.
    next_cal = {d: all_dates[i + 1] for i, d in enumerate(all_dates[:-1])}
    can_form = np.zeros(len(stock_df), dtype=bool)
    for i, r in enumerate(stock_df.itertuples(index=False)):
        d2 = next_cal.get(r.trade_date)
        if d2 is None:
            continue
        ok = False
        for cell in (r.iv_call, r.iv_put):
            if cell is None:
                continue
            strike, ot, _iv, _v = cell
            if (d2, r.underlying, r.expiry_dt, strike, ot) in traded_keys:
                ok = True
                break
        if ok and _forward_exists(d2, r.underlying, r.expiry_dt):
            can_form[i] = True
    stock_df["can_form_return"] = can_form

    # paired at t = richness at t AND the name's NEXT panel row can form a return.
    next_row_can = stock_df.groupby("underlying")["can_form_return"].shift(-1)
    stock_df["dh_ok"] = stock_df["richness"].notna().to_numpy() & (
        next_row_can.fillna(False).to_numpy().astype(bool)
    )

    # --- S2 / S3: names/day and usable-date waterfall ---
    names_per_day = stock_df[stock_df["richness"].notna()].groupby("trade_date").size()
    paired_per_day = stock_df[stock_df["dh_ok"]].groupby("trade_date").size()

    first_usable = None
    if len(all_dates) >= RV_WINDOW:
        # A10's binding warmup is the first date with >= MIN_NAMES names having a
        # complete 21-trading-day RV window (>=18 observations inside the fence).
        # A flat `all_dates[RV_WINDOW - 1]` would over-skip by one: the >=18-obs
        # floor is reached one trading day before a full 21-day window completes.
        # Use the actual names-per-day from the panel so Phase 1's certified
        # usable-date count reconciles with Phase 2's consumed count (lead review
        # B-2 / MEDIUM-1).
        rich_dates = names_per_day[names_per_day >= MIN_NAMES].index
        if len(rich_dates):
            first_usable = min(rich_dates)
        else:
            first_usable = None

    def _waterfall():
        """Waterfall of survivors — each line is the count REMAINING after that
        exclusion. Not independent subtractions."""
        total = len(all_dates)
        remaining = all_dates

        # 1. pre-warmup: dates before the first usable formation date
        if first_usable is not None:
            after_warmup = [d for d in remaining if d >= first_usable]
        else:
            after_warmup = []
        pre_warmup = total - len(after_warmup)

        # 2. tail: dates with no t+1 / t+2 pair inside the fence.
        #    A formation at d needs d+1 and d+2 in the calendar (fence).
        cal_pos = {d: i for i, d in enumerate(all_dates)}
        after_tail = [d for d in after_warmup if cal_pos[d] + 2 < len(all_dates)]
        tail = len(after_warmup) - len(after_tail)

        # 3. dates with < MIN_NAMES names surviving A1-A11 (richness computable)
        rich_ok = set(names_per_day[names_per_day >= MIN_NAMES].index)
        after_rich = [d for d in after_tail if d in rich_ok]
        lt20_richness = len(after_tail) - len(after_rich)

        # 4. dates with < MIN_NAMES PAIRED names for the IC (A13)
        pair_ok = set(paired_per_day[paired_per_day >= MIN_NAMES].index)
        after_pair = [d for d in after_rich if d in pair_ok]
        lt20_paired = len(after_rich) - len(after_pair)

        return {
            "total": total,
            "pre_warmup": pre_warmup,
            "after_warmup": len(after_warmup),
            "tail": tail,
            "after_tail": len(after_tail),
            "lt20_richness": lt20_richness,
            "after_richness": len(after_rich),
            "lt20_paired": lt20_paired,
            "usable": len(after_pair),
        }

    waterfall = _waterfall()
    s3_pass = waterfall["usable"] >= S3_THRESHOLD

    return {
        "snapshots": snapshots,
        "pollution": pollution,
        "member_syms": member_syms,
        "fills": fills,
        "obs_stock": obs_stock,
        "obs_fut": obs_fut,
        "attrit": attrit,
        "panel": stock_df,
        "names_per_day": names_per_day,
        "paired_per_day": paired_per_day,
        "first_usable": first_usable,
        "all_dates": all_dates,
        "waterfall": waterfall,
        "s3_pass": s3_pass,
        "s3_threshold": S3_THRESHOLD,
        "iv_by_year": iv_by_year,
        "names_by_year": names_by_year,
        "s1_cardinality": s1_cardinality,
    }


def write_certification(path, d):
    """Script-generated certification report. NO hand-edited numbers."""
    att = d["attrit"]
    wf = d["waterfall"]
    lines = []
    l = lines.append
    l("# SE-3 — Confirmatory Substrate Certification (Phase 1)")
    l("")
    l("**Window:** 2016-02-11 -> 2022-12-31 (inclusive) | **Run:** script-generated, no hand-edited numbers")
    l("**Variant A only.** NIFTY index-option leg 2016-02-11 -> 2022-12-31 is NOT read by this run and remains unread.")
    l("")
    l("## 1. Fence proof (S6)")
    l("")
    l(f"- stock options: observed `trade_date` range [{d['obs_stock'][0].date()}, {d['obs_stock'][1].date()}]")
    l(f"- stock futures: observed `trade_date` range [{d['obs_fut'][0].date()}, {d['obs_fut'][1].date()}]")
    l("- Hard assertion per source: `assert FENCE_START <= min and max <= FENCE_END` — **PASSED**")
    l("")
    l("## 2. Window ledger (post-run)")
    l("")
    l("| Leg | Window | State entering this run | State after |")
    l("|---|---|---|---|")
    l("| **OPTSTK stock options** | **2016-02-11 -> 2022-12-31** | Skew-exposed 2016-07->2020-12; **unspent** 2021-01->2022-12 | **SPENT — this is the confirmatory read** |")
    l("| NIFTY index options | 2016-02-11 -> 2022-12-31 | Unread, 1,701 dates | **Unread — variant A does not touch the index leg** |")
    l("| OPTSTK stock options | 2023-01-02 -> 2025-12-31 | **Spent** by the breadth probe | Unchanged — out of bounds here |")
    l("| NIFTY index options | 2023-01-02 -> 2025-12-31 | Already burned | Unchanged — out of bounds here |")
    l("| Both legs | 2026-01-01 -> 2026-07 | Unread | **Preserved — deliberately reserved** |")
    l("")
    l("## 3. S1 — PIT membership")
    l("")
    l(f"- Valid MCWB snapshots: {len(d['snapshots'])} | Union of member symbols in fence: {len(d['member_syms'])}")
    l(f"- Pollution findings (DUMMY*/TMPV* excluded, reported by symbol and first-seen month): {d['pollution'] or 'none'}")
    if d["fills"]:
        l("- MCWB fill(s) applied (month M missing -> latest valid snapshot before it):")
        distinct = {}
        for key, src in d["fills"].items():
            distinct.setdefault(key[0], set()).add(src)
        for needed, srcs in sorted(distinct.items()):
            l(f"  - needed snapshot {needed}; filled from {sorted(srcs)[0]} (applied to {len([k for k in d['fills'] if k[0] == needed])} trade dates)")
    else:
        l("- MCWB fills: none required")
    l("- Membership resolves for every date in span: **PASS**")
    sc = d["s1_cardinality"]
    l(f"- S1 cardinality (lead review MEDIUM-2): every date's membership is 50 or 51 symbols — **{'PASS' if sc['n_members_50_or_51'] else 'FAIL'}**")
    l(f"  - distinct roster sizes seen: {sc['sizes']}")
    l(f"  - the 51-symbol case is the DVR era — TATAMTRDVR double-listed alongside TATAMOTORS (2016-2017); months: {sc['dvr_months']}")
    l(f"  - cardinality issues (any count outside {{50, 51}}): {sc['issues'] or 'none'}")
    l("")
    l("## 4. Attrition (absolute row counts)")
    l("")
    l("| Stage | Rows |")
    l("|---|---|")
    l(f"| Rows in fence, member universe | {att['rows_member']:,} |")
    l(f"| Traded (contracts>0, OI>0) | {att['rows_traded']:,} |")
    l(f"| §3.2 no expiry in [7,60] (date-name) | {att['dropped_no_expiry']} |")
    l(f"| §3.3 no forward (date-name) | {att['dropped_no_forward']} |")
    l(f"| §3.4 no ATM IV cell (date-name) | {att['dropped_no_atm']} |")
    l(f"| IV inversion discard (A9) | {att['iv_discard']}/{att['iv_attempted']} ({att['iv_discard']/max(att['iv_attempted'],1):.1%}) |")
    l("")
    l("## 5. S5 — IV inversion discard rate by year")
    l("")
    l("| Year | attempted | discarded | rate |")
    l("|---|---|---|---|")
    for yr in sorted(d["iv_by_year"]):
        a = d["iv_by_year"][yr]["attempted"]
        dd = d["iv_by_year"][yr]["discarded"]
        l(f"| {yr} | {a} | {dd} | {dd/max(a,1):.1%} |")
    l("")
    l("## 6. S2 — names/day surviving A1-A11, by year")
    l("")
    l("| Year | median names/day | p10 | p90 |")
    l("|---|---|---|---|")
    _s = d["names_per_day"]
    for yr in sorted(set(_s.index.year)):
        grp = _s[_s.index.year == yr]
        l(f"| {yr} | {grp.median():.0f} | {grp.quantile(0.1):.0f} | {grp.quantile(0.9):.0f} |")
    l("")
    l("## 7. S3 — usable-date waterfall vs 1,701")
    l("")
    l("| Line | Count |")
    l("|---|---|")
    l(f"| trading dates 2016-02-11 .. 2022-12-31 (stock-options store) | {wf['total']} |")
    l(f"|   - dates before first usable formation date (A10 RV warmup: {d['first_usable'].date()}) | -{wf['pre_warmup']} |")
    l(f"|   - tail dates with no t+1 / t+2 pair inside the fence | -{wf['tail']} |")
    l(f"|   - dates with < {MIN_NAMES} names surviving A1-A11 (richness computable) | -{wf['lt20_richness']} |")
    l(f"|   - dates with < {MIN_NAMES} PAIRED names for the IC (A13) | -{wf['lt20_paired']} |")
    l(f"| **= USABLE CONFIRMATORY FORMATION DATES** | **{wf['usable']}** |")
    l("")
    verdict = "PASS" if d["s3_pass"] else "FAIL"
    l(f"**S3: {verdict}** — usable dates {wf['usable']} vs `S3_MIN_USABLE_DATES = {d['s3_threshold']}`.")
    if d["s3_pass"]:
        l("At or above 756: every claim about the declared band's central case survives; the run proceeds with the shortfall reported.")
    else:
        l("**Below 756: the frozen `n_available` is wrong in a way that matters. STOP. The declaration must be re-approved at the true n before any IC is computed.**")
    l("")
    l("## 8. Implementation notes")
    l("")
    l("- Reuses `implied_vol`, `_parity_forward` from `scripts/osc/sd_probe.py` (A14). No reimplementation.")
    l("- Variant B absent; no index-options database reference anywhere in this module (tested).")
    l("- 2018-05 MCWB fill per operator decision 2026-08-05 (April and June 2018 rosters verified identical).")
    l("- Nothing under `data/` is written (read-only).")
    l("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")
    return verdict


def main():
    parser = argparse.ArgumentParser(description="SE-3 Phase 1 — substrate certification")
    parser.add_argument("--out", default=str(CERT_REPORT))
    args = parser.parse_args()
    d = build_panel()
    verdict = write_certification(args.out, d)
    print(f"S3: {verdict}")
    print(f"Report written to {args.out}")


if __name__ == "__main__":
    main()
