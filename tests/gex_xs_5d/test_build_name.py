import math
from datetime import date, datetime, timedelta
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from core.analytics.gex_history import RATE
from core.execution.options.nifty_shield_pricing import bs_price
from scripts.gex_xs_5d import panel as P
from scripts.gex_xs_5d import run_stage as R

SIGMA = 0.30
START = date(2024, 1, 1)


def _sessions(n=30):
    out, d = [], START
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def _chain(t, spot, expiries, oi_ce=100, oi_pe=100):
    rows = []
    for exp in expiries:
        T = (exp - t).days / 365
        fwd = spot * math.exp(RATE * T)
        s_star = fwd * math.exp(-RATE * T)
        for k in np.arange(90, 111, 2.0):
            for typ in ("CE", "PE"):
                rows.append({"trade_date": t, "underlying": "ABC", "expiry_dt": exp, "strike": k,
                             "option_type": typ, "close": bs_price(s_star, k, T, RATE, SIGMA, typ),
                             "contracts": 10, "open_int": oi_ce if typ == "CE" else oi_pe})
    return pd.DataFrame(rows), {exp: spot * math.exp(RATE * (exp - t).days / 365) for exp in expiries}


def _sd(sessions, i, expiries, fwd, hl_range=0.02, meetings=()):
    t = sessions[i]
    hl = {("ABC", d): (100 * (1 + hl_range / 2), 100 * (1 - hl_range / 2), 100.0) for d in sessions}
    adj = {("ABC", d): 100.0 * (1.001 ** k) for k, d in enumerate(sessions)}
    return SimpleNamespace(
        sessions=sessions, hl=hl, adj=adj,
        fut={(t, "ABC", e): f for e, f in fwd.items()},
        prefix={"ABC": "INE123A01"}, meetings=P.index_meetings(list(meetings)),
        monthly_expiries=list(expiries),
        symbol_on=lambda s, t0, d: s)


def test_build_name_end_to_end_values():
    s = _sessions()
    i = 20
    t = s[i]
    exps = [s[i + 7], s[i + 7] + timedelta(days=28)]       # near expires after t+5
    chain, fwd = _chain(t, 100.0, exps, oi_ce=300, oi_pe=100)
    rec, why = R.build_name(_sd(s, i, exps, fwd), i, "ABC", chain)
    assert why is None
    assert rec["N"] > 0                                     # call-heavy OI, dealers long calls
    assert math.exp(rec["ln_iv"]) == pytest.approx(SIGMA, abs=2e-3)
    p = P.parkinson(101.0, 99.0)
    assert rec["y"] == pytest.approx(math.log(p * 252 / math.exp(rec["ln_iv"]) ** 2))
    assert rec["ln_rv5"] == pytest.approx(math.log(p * 252))
    assert rec["r_1"] == pytest.approx(math.log(1.001))
    assert rec["r_5"] == pytest.approx(5 * math.log(1.001))
    assert rec["window_expiry"] is False


def test_build_name_iv_expiry_skips_expiry_inside_window():
    s = _sessions()
    i = 20
    t = s[i]
    exps = [s[i + 3], s[i + 3] + timedelta(days=28)]       # near expires inside the window
    chain, fwd = _chain(t, 100.0, exps)
    rec, why = R.build_name(_sd(s, i, exps, fwd), i, "ABC", chain)
    assert why is None and rec["window_expiry"] is True
    assert math.exp(rec["ln_iv"]) == pytest.approx(SIGMA, abs=2e-3)


def test_build_name_drops_on_results_known_by_close():
    s = _sessions()
    i = 20
    t = s[i]
    exps = [s[i + 7], s[i + 7] + timedelta(days=28)]
    chain, fwd = _chain(t, 100.0, exps)
    m = {"isin_prefix": "INE123A01", "symbol": "ABC", "bm_date": s[i + 2],
         "known_ts": datetime.combine(t, datetime.min.time()) + timedelta(hours=10)}
    rec, why = R.build_name(_sd(s, i, exps, fwd, meetings=[m]), i, "ABC", chain)
    assert rec is None and why == "U4_results"


def test_build_name_drops_on_missing_outcome_bar():
    s = _sessions()
    i = 20
    exps = [s[i + 7], s[i + 7] + timedelta(days=28)]
    chain, fwd = _chain(s[i], 100.0, exps)
    sd = _sd(s, i, exps, fwd)
    del sd.hl[("ABC", s[i + 3])]
    assert R.build_name(sd, i, "ABC", chain) == (None, "outcome_missing_bar")


def test_build_name_controls_stay_inside_the_stage():
    s = _sessions()
    i = 10                                                  # rv20 has only 11 sessions in-stage
    exps = [s[i + 7], s[i + 7] + timedelta(days=28)]
    chain, fwd = _chain(s[i], 100.0, exps)
    assert R.build_name(_sd(s, i, exps, fwd), i, "ABC", chain) == (None, "U3_controls")


def test_build_name_drops_forward_too_far_from_spot():
    s = _sessions()
    i = 20
    exps = [s[i + 7], s[i + 7] + timedelta(days=28)]
    chain, fwd = _chain(s[i], 100.0, exps)
    fwd = {e: f * 1.05 for e, f in fwd.items()}
    assert R.build_name(_sd(s, i, exps, fwd), i, "ABC", chain) == (None, "U3_validity")


def test_formation_ic_void_below_80_names_and_negative_when_planted():
    rng = np.random.default_rng(1)
    n = 150
    df = pd.DataFrame({c: rng.normal(size=n) for c in R.CONTROLS})
    df["N"] = rng.uniform(-1, 1, n)
    df["y"] = -0.8 * df["N"] + 0.3 * df["ln_iv"] + rng.normal(scale=0.3, size=n)
    assert R.formation_ic(df) < -0.3
    assert R.formation_ic(df.iloc[:79]) is None
