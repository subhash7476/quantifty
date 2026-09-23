# GEX Regime Stage A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the EOD NIFTY gamma-regime panel from options bhavcopy and test whether normalized net GEX predicts
next-day realized-vs-implied variance (TRAIN, then one HOLDOUT run), per the approved spec.

**Architecture:** Pure per-expiry / per-day math in `core/analytics/gex_history.py` (forward, IV, gamma, N/S/flip).
A runner `scripts/gex_regime/run_stage_a.py` loads DuckDB stores, builds the daily panel + outcomes, emits the §8
pre-run checks, fits the §6 OLS with Newey–West HAC, and writes a script-generated report. The runner refuses any
date ≥ 2023-01-01.

**Tech Stack:** Python 3.10+, numpy, pandas, scipy (`brentq`), statsmodels (OLS HAC), duckdb, pytest.

**Spec:** `docs/superpowers/specs/2026-09-23-gex-regime-stage-a-design.md`

## Global Constraints

- NIFTY only; TRAIN 2016-02-11 → 2019-12-31; HOLDOUT 2020-01-01 → 2022-12-31; **no read of any date ≥ 2023-01-01**
  (including the t+1 outcome day — an outcome day outside the window drops that t).
- r = 0.065 fixed; T = calendar DTE / 365; expiries with 1 ≤ DTE ≤ 45.
- Strike filter: OTM leg only, `contracts > 0`, close ≥ 0.5, |ln(K/F)| ≤ 0.10; IV kept in [0.01, 3.0].
- Forward sanity |F / Nifty close − 1| ≤ 2 %; day valid only with ≥ 10 kept strikes.
- Sign convention: calls +, puts − (assumption). Only scale-free measures (N, S, D).
- Flip grid x ∈ [−5 %, +5 %], step 0.1 %, sticky strike.
- Primary pass rule: TRAIN b < 0 and NW t ≤ −2.0; HOLDOUT b < 0 and one-sided p < 0.05. HAC lag 5.
- Report numbers are script-generated only. `OptionsAnalytics.calculate_gex` is not modified.
- Deviation from spec §5/§10 recorded in the spec: the hedging branch has no `implied_vol()`, so
  `gex_history.py` carries its own `brentq` solver over the existing `bs_price`. Reports are written per window
  (`GEX_REGIME_STAGE_A_TRAIN.md`, `..._HOLDOUT.md`); HOLDOUT refuses to run unless the TRAIN report says PASS.

---

### Task 1: Core math — `core/analytics/gex_history.py`

**Files:**
- Create: `core/analytics/gex_history.py`
- Test: `tests/analytics/test_gex_history.py`

**Interfaces:**
- Consumes: `core.execution.options.nifty_shield_pricing.bs_price(spot, strike, t_years, rate, iv, option_type)`.
- Produces:
  - `bs_gamma(spot, strike, t_years, rate, iv) -> float | np.ndarray`
  - `implied_vol(price, spot, strike, t_years, rate, option_type) -> float | None`
  - `parity_forward(chain: pd.DataFrame, t_years: float, rate: float = RATE) -> float | None`
    (chain columns: `strike, option_type, close, contracts, open_int`)
  - `ExpiryStrikes(forward, t_years, strikes, iv, oi_ce, oi_pe)` frozen dataclass (np arrays)
  - `select_strikes(chain, forward, t_years, rate=RATE) -> ExpiryStrikes`
  - `DayRegime(n_strikes, net_norm, sign, flip_x, censored)` frozen dataclass
  - `day_regime(expiries: list[ExpiryStrikes]) -> DayRegime`
  - constants `RATE, MAX_DTE, MIN_STRIKES, MAX_FWD_DEV, FLIP_EDGE`

- [ ] **Step 1: Write failing tests** — `tests/analytics/test_gex_history.py`:

```python
import math

import numpy as np
import pandas as pd
import pytest

from core.analytics.gex_history import (
    FLIP_EDGE, RATE, ExpiryStrikes, bs_gamma, day_regime, implied_vol,
    parity_forward, select_strikes,
)
from core.execution.options.nifty_shield_pricing import bs_price


def _chain(forward, t, iv, strikes, oi_ce=1000, oi_pe=1000, contracts=10):
    spot = forward * math.exp(-RATE * t)
    rows = []
    for k in strikes:
        for opt, oi in (("CE", oi_ce), ("PE", oi_pe)):
            rows.append({"strike": float(k), "option_type": opt,
                         "close": bs_price(spot, k, t, RATE, iv, opt),
                         "contracts": contracts, "open_int": oi})
    return pd.DataFrame(rows)


def test_bs_gamma_matches_hand_value():
    # d1 = 0.1, phi(0.1) = 0.3969525, gamma = phi / (S * sigma * sqrt(T))
    assert bs_gamma(100.0, 100.0, 1.0, 0.0, 0.2) == pytest.approx(0.01984763, rel=1e-6)


def test_implied_vol_round_trips_bs_price():
    price = bs_price(100.0, 105.0, 0.1, RATE, 0.18, "CE")
    assert implied_vol(price, 100.0, 105.0, 0.1, RATE, "CE") == pytest.approx(0.18, abs=1e-5)


def test_implied_vol_rejects_price_below_intrinsic():
    assert implied_vol(1.0, 100.0, 90.0, 0.1, RATE, "CE") is None


def test_parity_forward_recovers_known_forward():
    chain = _chain(20000.0, 20 / 365, 0.15, range(19500, 20501, 50))
    assert parity_forward(chain, 20 / 365) == pytest.approx(20000.0, abs=0.01)


def test_parity_forward_none_without_traded_pair():
    chain = _chain(20000.0, 20 / 365, 0.15, [20000])
    chain.loc[chain.option_type == "PE", "contracts"] = 0
    assert parity_forward(chain, 20 / 365) is None


def test_select_strikes_keeps_only_traded_otm_legs_in_band():
    t = 20 / 365
    chain = _chain(20000.0, t, 0.15, [17000, 19500, 19900, 20100, 20500, 23000])
    chain.loc[(chain.strike == 19900.0) & (chain.option_type == "PE"), "contracts"] = 0
    es = select_strikes(chain, 20000.0, t)
    # 17000 and 23000 are outside |ln(K/F)| <= 0.10; 19900's OTM put is untraded
    assert list(es.strikes) == [19500.0, 20100.0, 20500.0]
    assert np.allclose(es.iv, 0.15, atol=1e-4)
    assert list(es.oi_ce) == [1000, 1000, 1000]


def _es(strikes, oi_ce, oi_pe, forward=100.0, t=20 / 365, iv=0.2):
    n = len(strikes)
    return ExpiryStrikes(forward, t, np.array(strikes, float), np.full(n, iv),
                         np.array(oi_ce, float), np.array(oi_pe, float))


def test_sign_convention_call_only_is_plus_one_put_only_is_minus_one():
    calls = day_regime([_es([95, 100, 105], [10, 10, 10], [0, 0, 0])])
    puts = day_regime([_es([95, 100, 105], [0, 0, 0], [10, 10, 10])])
    assert calls.net_norm == pytest.approx(1.0) and calls.sign == 1
    assert puts.net_norm == pytest.approx(-1.0) and puts.sign == -1


def test_flip_found_between_put_and_call_mass():
    e = _es([97, 103], [0, 10], [10, 0])
    r = day_regime([e])
    assert not r.censored
    assert -0.03 < r.flip_x < 0.03

    def net(x):
        s = e.forward * math.exp(-RATE * e.t_years) * (1 + x)
        g = bs_gamma(s, e.strikes, e.t_years, RATE, e.iv)
        return float((g * (e.oi_ce - e.oi_pe)).sum())

    assert net(r.flip_x - 0.001) * net(r.flip_x + 0.001) < 0


def test_no_crossing_is_censored_at_grid_edge_below_spot_when_positive():
    r = day_regime([_es([95, 100, 105], [10, 10, 10], [0, 0, 0])])
    assert r.censored and r.flip_x == pytest.approx(-FLIP_EDGE)
```

- [ ] **Step 2: Run** `python -m pytest tests/analytics/test_gex_history.py -q` — expect FAIL (module missing).

- [ ] **Step 3: Implement** `core/analytics/gex_history.py`:

```python
"""EOD NIFTY gamma-exposure regime from options bhavcopy.

Implements §4 of docs/superpowers/specs/2026-09-23-gex-regime-stage-a-design.md.
Sign convention (an assumption): dealers long calls, short puts.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from core.execution.options.nifty_shield_pricing import bs_price

RATE = 0.065
MAX_DTE = 45
MIN_PRICE = 0.5
MONEYNESS_BAND = 0.10
IV_MIN, IV_MAX = 0.01, 3.0
MAX_FWD_DEV = 0.02
MIN_STRIKES = 10
FLIP_EDGE = 0.05
FLIP_GRID = np.round(np.arange(-FLIP_EDGE, FLIP_EDGE + 1e-9, 0.001), 6)


def bs_gamma(spot, strike, t_years, rate, iv):
    vol_t = iv * np.sqrt(t_years)
    d1 = (np.log(spot / strike) + (rate + 0.5 * iv * iv) * t_years) / vol_t
    return np.exp(-0.5 * d1 * d1) / math.sqrt(2 * math.pi) / (spot * vol_t)


def implied_vol(price, spot, strike, t_years, rate, option_type):
    def err(v):
        return bs_price(spot, strike, t_years, rate, v, option_type) - price
    if err(IV_MIN) > 0 or err(IV_MAX) < 0:
        return None
    return brentq(err, IV_MIN, IV_MAX, xtol=1e-7)


def parity_forward(chain: pd.DataFrame, t_years: float, rate: float = RATE):
    traded = chain[chain["contracts"] > 0]
    wide = traded.pivot_table(index="strike", columns="option_type", values="close", aggfunc="first")
    if "CE" not in wide.columns or "PE" not in wide.columns:
        return None
    wide = wide.dropna(subset=["CE", "PE"])
    if wide.empty:
        return None
    diff = wide["CE"] - wide["PE"]
    k = diff.abs().idxmin()
    return float(k + diff[k] * math.exp(rate * t_years))


@dataclass(frozen=True)
class ExpiryStrikes:
    forward: float
    t_years: float
    strikes: np.ndarray
    iv: np.ndarray
    oi_ce: np.ndarray
    oi_pe: np.ndarray


def select_strikes(chain: pd.DataFrame, forward: float, t_years: float, rate: float = RATE) -> ExpiryStrikes:
    oi = (chain.pivot_table(index="strike", columns="option_type", values="open_int",
                            aggfunc="sum", fill_value=0)
          .reindex(columns=["CE", "PE"], fill_value=0))
    spot_star = forward * math.exp(-rate * t_years)
    kept = []
    for r in chain.sort_values("strike").itertuples(index=False):
        otm = "PE" if r.strike < forward else "CE"
        if r.option_type != otm or r.contracts <= 0 or r.close < MIN_PRICE:
            continue
        if abs(math.log(r.strike / forward)) > MONEYNESS_BAND:
            continue
        iv = implied_vol(r.close, spot_star, r.strike, t_years, rate, otm)
        if iv is None:
            continue
        kept.append((r.strike, iv, oi.at[r.strike, "CE"], oi.at[r.strike, "PE"]))
    arr = np.array(kept, float).reshape(-1, 4)
    return ExpiryStrikes(forward, t_years, arr[:, 0], arr[:, 1], arr[:, 2], arr[:, 3])


@dataclass(frozen=True)
class DayRegime:
    n_strikes: int
    net_norm: float
    sign: int
    flip_x: float
    censored: bool


def _exposure(e: ExpiryStrikes, x: float):
    spot = e.forward * math.exp(-RATE * e.t_years) * (1 + x)
    fwd = e.forward * (1 + x)
    g = bs_gamma(spot, e.strikes, e.t_years, RATE, e.iv) * fwd * fwd * 0.01
    return g * (e.oi_ce - e.oi_pe), g * (e.oi_ce + e.oi_pe)


def _flip(expiries):
    net = np.array([sum(_exposure(e, x)[0].sum() for e in expiries) for x in FLIP_GRID])
    idx = np.where(np.sign(net[:-1]) * np.sign(net[1:]) < 0)[0]
    if idx.size == 0:
        at_spot = net[len(net) // 2]
        return (-FLIP_EDGE if at_spot > 0 else FLIP_EDGE), True
    i = idx[np.argmin(np.abs(FLIP_GRID[idx] + FLIP_GRID[idx + 1]))]
    x0, x1, g0, g1 = FLIP_GRID[i], FLIP_GRID[i + 1], net[i], net[i + 1]
    return float(x0 - g0 * (x1 - x0) / (g1 - g0)), False


def day_regime(expiries: list[ExpiryStrikes]) -> DayRegime:
    signed = sum(_exposure(e, 0.0)[0].sum() for e in expiries)
    gross = sum(_exposure(e, 0.0)[1].sum() for e in expiries)
    flip_x, censored = _flip(expiries)
    return DayRegime(
        n_strikes=int(sum(len(e.strikes) for e in expiries)),
        net_norm=float(signed / gross),
        sign=int(np.sign(signed)),
        flip_x=flip_x,
        censored=censored,
    )
```

- [ ] **Step 4: Run** the tests — expect all PASS.
- [ ] **Step 5: Commit** `feat: GEX history core math for Stage A (forward, IV, gamma, N/S/flip)`.

### Task 2: Runner — panel, outcomes, checks, fit, report

**Files:**
- Create: `scripts/gex_regime/__init__.py` (empty), `scripts/gex_regime/run_stage_a.py`
- Test: `tests/gex_regime/test_run_stage_a.py`

**Interfaces:**
- Consumes: everything Task 1 produces.
- Produces (CLI): `python scripts/gex_regime/run_stage_a.py --window train|holdout [--checks-only]` →
  `docs/reports/GEX_REGIME_STAGE_A_{TRAIN|HOLDOUT}.md`.
  Pure helpers tested: `check_window(start, end)`, `build_outcomes(daily, expiry_dates, window_start, window_end)`.

- [ ] **Step 1: Write failing tests** — `tests/gex_regime/test_run_stage_a.py`:

```python
import math
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.gex_regime.run_stage_a import build_outcomes, check_window  # noqa: E402


def test_check_window_refuses_sealed_dates():
    with pytest.raises(ValueError):
        check_window(date(2022, 1, 1), date(2023, 1, 1))
    check_window(date(2020, 1, 1), date(2022, 12, 31))


def _daily():
    dates = pd.bdate_range("2019-11-01", "2020-01-03")
    return pd.DataFrame({"date": dates.date, "high": 101.0, "low": 99.0,
                         "close": 100.0, "vix": 16.0})


def test_outcome_uses_next_day_and_drops_t_whose_next_day_leaves_window():
    out = build_outcomes(_daily(), {date(2019, 12, 26)}, date(2019, 12, 1), date(2019, 12, 31))
    assert out["date"].max() == date(2019, 12, 30)       # its t+1 (12-31) is in window
    assert date(2019, 12, 31) not in set(out["date"])     # t+1 = 2020-01-01 is outside
    rv = math.log(101 / 99) ** 2 / (4 * math.log(2))
    ivd = (16 / 100) ** 2 / 252
    row = out.set_index("date").loc[date(2019, 12, 24)]
    assert row["y"] == pytest.approx(math.log(rv / ivd))
    assert row["exp_next"] == 0
    assert out.set_index("date").loc[date(2019, 12, 25), "exp_next"] == 1
```

- [ ] **Step 2: Run** `python -m pytest tests/gex_regime -q` — expect FAIL (module missing).

- [ ] **Step 3: Implement** `scripts/gex_regime/run_stage_a.py` (full file):

```python
"""GEX regime Stage A runner — EOD NIFTY gamma regime vs next-day RV / implied variance.

Spec: docs/superpowers/specs/2026-09-23-gex-regime-stage-a-design.md
Usage: python scripts/gex_regime/run_stage_a.py --window train|holdout [--checks-only]
Refuses any date >= 2023-01-01 (unread window).
"""
from __future__ import annotations

import argparse
import math
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.analytics.gex_history import (  # noqa: E402
    MAX_DTE, MAX_FWD_DEV, MIN_STRIKES, day_regime, parity_forward, select_strikes,
)

SEALED_START = date(2023, 1, 1)
WINDOWS = {"train": (date(2016, 2, 11), date(2019, 12, 31)),
           "holdout": (date(2020, 1, 1), date(2022, 12, 31))}
OPTIONS_DB = ROOT / "data/market_data/options_bhavcopy.duckdb"
DAILY_DIR = ROOT / "data/market_data/nse/candles/1d"
REPORT_DIR = ROOT / "docs/reports"
NIFTY, VIX = "NSE_INDEX|Nifty 50", "NSE_INDEX|India VIX"
WARMUP_DAYS = 45
HAC_LAGS = 5
CONTROLS = ["ln_vix", "ln_rv5", "ln_rv20", "exp_next"]


def check_window(start: date, end: date) -> None:
    if end >= SEALED_START or start >= SEALED_START:
        raise ValueError(f"window {start}..{end} touches the unread window (>= {SEALED_START})")


def load_daily(start: date, end: date) -> pd.DataFrame:
    rows = []
    for path in sorted(DAILY_DIR.glob("*.duckdb")):
        d = date.fromisoformat(path.stem)
        if not start <= d <= end:
            continue
        con = duckdb.connect(str(path), read_only=True)
        got = dict((s, (h, lo, c)) for s, h, lo, c in con.execute(
            "SELECT symbol, high, low, close FROM candles WHERE symbol IN (?, ?)", [NIFTY, VIX]).fetchall())
        con.close()
        if NIFTY in got and VIX in got:
            h, lo, c = got[NIFTY]
            rows.append({"date": d, "high": h, "low": lo, "close": c, "vix": got[VIX][2]})
    return pd.DataFrame(rows)


def load_options(start: date, end: date) -> tuple[pd.DataFrame, set]:
    con = duckdb.connect(str(OPTIONS_DB), read_only=True)
    df = con.execute(
        """SELECT trade_date, expiry_dt, strike, option_type, close, contracts, open_int
           FROM option_bhavcopy
           WHERE symbol = 'NIFTY' AND trade_date BETWEEN ? AND ?
             AND expiry_dt > trade_date AND date_diff('day', trade_date, expiry_dt) <= ?""",
        [start, end, MAX_DTE]).df()
    expiries = {r[0] for r in con.execute(
        "SELECT DISTINCT expiry_dt FROM option_bhavcopy WHERE symbol = 'NIFTY' AND expiry_dt < ?",
        [SEALED_START]).fetchall()}
    con.close()
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
    df["expiry_dt"] = pd.to_datetime(df["expiry_dt"]).dt.date
    return df, expiries


def build_regimes(options: pd.DataFrame, close_by_date: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, drops = [], []
    for t, day in options.groupby("trade_date"):
        spot = close_by_date.get(t)
        if spot is None:
            drops.append({"date": t, "reason": "no_index_bar"})
            continue
        expiries, fwd_ratios = [], []
        for exp, chain in day.groupby("expiry_dt"):
            t_years = (exp - t).days / 365
            fwd = parity_forward(chain, t_years)
            if fwd is None:
                drops.append({"date": t, "reason": "expiry_no_pair"})
                continue
            if abs(fwd / spot - 1) > MAX_FWD_DEV:
                drops.append({"date": t, "reason": "expiry_fwd_dev"})
                continue
            fwd_ratios.append(fwd / spot)
            es = select_strikes(chain, fwd, t_years)
            if len(es.strikes):
                expiries.append(es)
        n = sum(len(e.strikes) for e in expiries)
        if n < MIN_STRIKES:
            drops.append({"date": t, "reason": "few_strikes"})
            continue
        r = day_regime(expiries)
        rows.append({"date": t, "n_strikes": r.n_strikes, "n_expiries": len(expiries),
                     "net_norm": r.net_norm, "sign": r.sign, "flip_x": r.flip_x,
                     "censored": r.censored, "fwd_ratio": float(np.median(fwd_ratios))})
    return pd.DataFrame(rows), pd.DataFrame(drops, columns=["date", "reason"])


def build_outcomes(daily: pd.DataFrame, expiry_dates: set, window_start: date, window_end: date) -> pd.DataFrame:
    d = daily.sort_values("date").reset_index(drop=True).copy()
    d["rv"] = np.log(d["high"] / d["low"]) ** 2 / (4 * math.log(2))
    d["rv"] = d["rv"].where(d["rv"] > 0)
    d["ivd"] = (d["vix"] / 100) ** 2 / 252
    d["ln_vix"] = np.log(d["vix"])
    d["ln_rv5"] = np.log(d["rv"].rolling(5).mean())
    d["ln_rv20"] = np.log(d["rv"].rolling(20).mean())
    d["next_date"] = d["date"].shift(-1)
    d["rv_next"] = d["rv"].shift(-1)
    r2 = np.log(d["close"].shift(-1) / d["close"]) ** 2
    d["y"] = np.log(d["rv_next"] / d["ivd"])
    d["y_cc"] = np.log(r2.where(r2 > 0) / d["ivd"])
    d["exp_next"] = d["next_date"].isin(expiry_dates).astype(int)
    keep = (d["date"] >= window_start) & d["next_date"].notna()
    keep &= d["next_date"].apply(lambda x: pd.notna(x) and x <= window_end)
    return d[keep].reset_index(drop=True)


def fit(panel: pd.DataFrame, regressor: str, outcome: str = "y"):
    d = panel.dropna(subset=[outcome, regressor] + CONTROLS)
    X = sm.add_constant(d[[regressor] + CONTROLS].astype(float))
    return sm.OLS(d[outcome].astype(float), X).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})


def _fmt(x, p=4):
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{p}f}"


def checks_section(regimes: pd.DataFrame, drops: pd.DataFrame, n_days: int) -> list[str]:
    out = ["## §8 Pre-run checks (no outcome read)", "",
           f"Trading days in window (index store): {n_days}", "",
           "| year | days computed | kept strikes / day (median) | expiries / day (median) | "
           "fwd/close p1 · median · p99 | flip censored | N p10 · median · p90 |",
           "|---|--:|--:|--:|---|--:|---|"]
    reg = regimes.assign(year=[d.year for d in regimes["date"]])
    for y, g in reg.groupby("year"):
        fr, nn = g["fwd_ratio"], g["net_norm"]
        out.append(f"| {y} | {len(g)} | {g['n_strikes'].median():.0f} | {g['n_expiries'].median():.0f} | "
                   f"{fr.quantile(.01):.4f} · {fr.median():.4f} · {fr.quantile(.99):.4f} | "
                   f"{g['censored'].mean():.1%} | {nn.quantile(.1):+.3f} · {nn.median():+.3f} · "
                   f"{nn.quantile(.9):+.3f} |")
    out += ["", "**Drops by reason** (expiry-level reasons count expiries, not days):", ""]
    if drops.empty:
        out.append("none")
    else:
        dr = drops.assign(year=[d.year for d in drops["date"]])
        tab = dr.pivot_table(index="year", columns="reason", values="date", aggfunc="count", fill_value=0)
        out.append("| year | " + " | ".join(tab.columns) + " |")
        out.append("|---|" + "--:|" * len(tab.columns))
        for y, row in tab.iterrows():
            out.append(f"| {y} | " + " | ".join(str(int(v)) for v in row) + " |")
    return out + [""]


def fit_section(panel: pd.DataFrame, window: str) -> tuple[list[str], bool]:
    m = fit(panel, "net_norm")
    b, t, p = m.params["net_norm"], m.tvalues["net_norm"], m.pvalues["net_norm"]
    p_one = p / 2 if b < 0 else 1 - p / 2
    passed = (b < 0 and t <= -2.0) if window == "train" else (b < 0 and p_one < 0.05)
    q10, q90 = panel["net_norm"].quantile(.1), panel["net_norm"].quantile(.9)
    effect = math.exp(b * (q90 - q10)) - 1
    rho = panel[["net_norm", "ln_vix"]].corr().iloc[0, 1]
    out = ["## §6 Primary fit — y = ln(RV_{t+1} / IVd_t) on N_t + controls (NW HAC lag 5)", "",
           f"n = {int(m.nobs)} · R² = {m.rsquared:.4f}", "",
           "| term | coef | NW t | p (two-sided) |", "|---|--:|--:|--:|"]
    for k in m.params.index:
        out.append(f"| {k} | {m.params[k]:+.4f} | {m.tvalues[k]:+.2f} | {m.pvalues[k]:.4g} |")
    out += ["", f"- **b (net_norm) = {b:+.4f}, NW t = {t:+.2f}, one-sided p (b<0) = {p_one:.4g}**",
            f"- Effect of N p10→p90 ({q10:+.3f}→{q90:+.3f}): {effect:+.1%} in RV_{{t+1}}/IVd_t",
            f"- corr(N, ln VIX) = {rho:+.3f}", ""]
    out += ["## Descriptive (not part of the pass rule)", "",
            "| model | coef | NW t | n |", "|---|--:|--:|--:|"]
    panel = panel.assign(dist=-np.log1p(panel["flip_x"]) / (panel["vix"] / 100 / math.sqrt(252)))
    for label, reg, outc, sub in [
        ("S_t (sign), Parkinson", "sign", "y", panel),
        ("D_t (flip distance, σ units), Parkinson", "dist", "y", panel),
        ("N_t, close-to-close outcome", "net_norm", "y_cc", panel),
    ] + ([("N_t, Parkinson, 2016–2018", "net_norm", "y", panel[[d.year <= 2018 for d in panel["date"]]]),
          ("N_t, Parkinson, 2019", "net_norm", "y", panel[[d.year == 2019 for d in panel["date"]]])]
         if window == "train" else []):
        mm = fit(sub, reg, outc)
        out.append(f"| {label} | {mm.params[reg]:+.4f} | {mm.tvalues[reg]:+.2f} | {int(mm.nobs)} |")
    rule = "b < 0 and NW t ≤ −2.0" if window == "train" else "b < 0 and one-sided p < 0.05"
    out += ["", f"## Verdict", "", f"Rule: {rule}.", "",
            f"**{window.upper()} verdict: {'PASS' if passed else 'FAIL'}**", ""]
    return out, passed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", choices=list(WINDOWS), required=True)
    ap.add_argument("--checks-only", action="store_true")
    args = ap.parse_args()
    start, end = WINDOWS[args.window]
    check_window(start, end)
    if args.window == "holdout":
        train_report = REPORT_DIR / "GEX_REGIME_STAGE_A_TRAIN.md"
        if not train_report.exists() or "**TRAIN verdict: PASS**" not in train_report.read_text(encoding="utf-8"):
            raise SystemExit("HOLDOUT refused: TRAIN report missing or not PASS (spec §7)")

    daily = load_daily(start - timedelta(days=WARMUP_DAYS), end)
    options, expiry_dates = load_options(start, end)
    close_by_date = dict(zip(daily["date"], daily["close"]))
    regimes, drops = build_regimes(options, close_by_date)
    n_days = int(((daily["date"] >= start) & (daily["date"] <= end)).sum())

    rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                         capture_output=True, text=True).stdout.strip()
    lines = [f"# GEX Regime Stage A — {args.window.upper()} ({start} → {end})", "",
             "Script-generated by `scripts/gex_regime/run_stage_a.py` — do not hand-edit.",
             f"Spec: `docs/superpowers/specs/2026-09-23-gex-regime-stage-a-design.md` · code rev `{rev}`", "",
             "Sign convention (assumption): dealers long calls, short puts. "
             "N = Σ signed / Σ gross gamma exposure.", ""]
    lines += checks_section(regimes, drops, n_days)
    if not args.checks_only:
        outcomes = build_outcomes(daily, expiry_dates, start, end)
        panel = outcomes.merge(regimes, on="date", how="inner")
        body, _ = fit_section(panel, args.window)
        lines += body
    suffix = "_CHECKS" if args.checks_only else ""
    path = REPORT_DIR / f"GEX_REGIME_STAGE_A_{args.window.upper()}{suffix}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run** `python -m pytest tests/gex_regime tests/analytics/test_gex_history.py -q` — expect PASS.
- [ ] **Step 5: Commit** `feat: GEX regime Stage A runner with sealed-window guard`.

### Task 3: Pre-run checks (TRAIN), then TRAIN fit

- [ ] **Step 1:** `python scripts/gex_regime/run_stage_a.py --window train --checks-only` → read
  `GEX_REGIME_STAGE_A_TRAIN_CHECKS.md`. Stop and investigate if: > 10 % of trading days dropped, fwd/close
  median outside [0.995, 1.01], or median kept strikes < 15. Fixes to *data handling bugs* are allowed here
  (no outcome has been read); spec parameters are not changed.
- [ ] **Step 2: Commit** the checks report.
- [ ] **Step 3:** `python scripts/gex_regime/run_stage_a.py --window train` → `GEX_REGIME_STAGE_A_TRAIN.md`.
- [ ] **Step 4: Commit** the TRAIN report. HOLDOUT runs only after the operator reviews TRAIN.
