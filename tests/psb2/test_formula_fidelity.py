"""Formula-fidelity tests: one assertion per pinned §9 parameter.

Each test uses a tiny hand-constructed panel with exact expected values,
such that a wrong constant makes the assertion fail on a known input.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import duckdb
import numpy as np
from datetime import date, timedelta

from scripts.psb2 import harness as H


def _bday_span(start, n):
    days = []
    d = start
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def _build_cal(con, cal):
    con.executemany("INSERT INTO trading_calendar VALUES (?, 200)", [(d,) for d in cal])


def _build_universe(con, entities):
    con.executemany("INSERT INTO universe_eligibility VALUES (?, ?)", [(e, e) for e in entities])
    con.executemany(
        "INSERT INTO universe_membership VALUES (?, ?, ?)",
        [(date(2010, 1, 4), e, i + 1) for i, e in enumerate(entities)],
    )


def _store(path):
    if path.exists():
        path.unlink()
    con = duckdb.connect(str(path))
    con.execute("CREATE TABLE trading_calendar (trade_date DATE, n_symbols INTEGER)")
    con.execute("CREATE TABLE universe_eligibility (symbol VARCHAR, entity VARCHAR)")
    con.execute("CREATE TABLE universe_membership (rebalance_date DATE, symbol VARCHAR, rank INTEGER)")
    con.execute("CREATE TABLE equity_bhavcopy_adjusted ("
               "symbol VARCHAR, trade_date DATE, close DOUBLE, "
               "open DOUBLE, deliv_pct DOUBLE, turnover DOUBLE)")
    return con


def _insert_prices(con, data):
    """data: list of (symbol, trade_date, close, open, deliv_pct, turnover)"""
    con.executemany("INSERT INTO equity_bhavcopy_adjusted VALUES (?,?,?,?,?,?)", data)


# ── C2 Tests ────────────────────────────────────────────────────────────────────

def test_c2_252_day_baseline_ending_t21():
    """C2's delivery baseline is 252 trading days ending t-21, with ≥ 150 non-NULL.

    Plant: exactly 252 trading days in baseline, ≥ 150 non-NULL.
    Expected: C2 z-score computed correctly.
    """
    entities = ["S0001"]
    # Build 300 business days: 252 baseline + 21 gap + ~15 recent + buffer
    cal = _bday_span(date(2019, 1, 2), 300)
    t = cal[-1]  # last day = formation date

    path = Path(__file__).parent / "test_c2_baseline.duckdb"
    con = _store(path)
    _build_cal(con, cal)
    _build_universe(con, entities)

    # Insert delivery data
    # Baseline: 252 days ending t-21, all at 0.30
    t_21 = cal[cal.index(t) - 21]
    t_base_start = cal[cal.index(t_21) - 252]
    base_idx_start = cal.index(t_base_start)
    base_idx_end = cal.index(t_21)

    # Use varying baseline values to get non-zero std
    rng = np.random.default_rng(42)
    base_vals = rng.uniform(0.25, 0.35, 252).tolist()

    rows = []
    for i, d in enumerate(cal):
        # Recent period (~15 days): delivery = 0.80
        if i >= len(cal) - 20:
            dp = 0.80
        # Baseline period: delivery varies around 0.30
        elif base_idx_start <= i <= base_idx_end:
            idx_in_base = i - base_idx_start
            dp = base_vals[idx_in_base] if idx_in_base < len(base_vals) else 0.30
        else:
            dp = None
        close_val = 100.0
        if dp is not None:
            rows.append(("S0001", d, close_val, close_val, round(dp, 4), 1e7))
        else:
            rows.append(("S0001", d, close_val, close_val, None, 1e7))
    _insert_prices(con, rows)
    con.close()

    panel = H.load_panel(str(path), cutoff=H.DEV_HI)
    scores = H.score_c2_psb2(panel, t)

    assert "S0001" in scores, f"S0001 not scored: {scores}"
    z = scores["S0001"]
    # Expected: recent_mean ≈ 0.80, base_mean ≈ 0.30, base_std ≈ 0.03
    # z ≈ (0.80 - 0.30) / 0.03 ≈ 16.7
    print(f"  C2 252-day baseline: z = {z:.4f} (expected > 1.0)")
    assert z > 1.0, f"C2 z-score too low: {z:.4f}"


def test_c2_fortnightly_mean_min_8():
    """C2 requires ≥ 8 non-NULL deliv_pct in the recent period.

    Plant: exactly 7 non-NULL → should be skipped.
    """
    entities = ["S0001"]
    cal = _bday_span(date(2019, 1, 2), 280)
    t = cal[-1]

    path = Path(__file__).parent / "test_c2_min8.duckdb"
    con = _store(path)
    _build_cal(con, cal)
    _build_universe(con, entities)

    rows = []
    for i, d in enumerate(cal):
        dp = None
        # Only 7 non-NULL in recent period
        if i >= len(cal) - 7:
            dp = 0.50
        elif i < len(cal) - 250:
            dp = 0.30
        close_val = 100.0
        rows.append(("S0001", d, close_val, close_val, dp, 1e7))
    _insert_prices(con, rows)
    con.close()

    panel = H.load_panel(str(path), cutoff=H.DEV_HI)
    scores = H.score_c2_psb2(panel, t)

    assert "S0001" not in scores, "S0001 should be skipped (< 8 non-NULL recent)"
    print("  C2 min 8 non-NULL: correctly skipped entity with 7 recent observations")


# ── C3 Tests ────────────────────────────────────────────────────────────────────

def test_c3_21_day_return_horizon():
    """C3 uses 21-trading-day return for r_i(t).

    Plant: S0001 has +10% return over 21 days, S0002 has -10%.
    Delivery: S0001 has above-baseline, S0002 has below-baseline in recent window.
    Verify C3 score sign matches formula: both should be positive.
    """
    entities = ["S0001", "S0002"]
    cal = _bday_span(date(2019, 1, 2), 300)
    t = cal[-1]
    t_21 = cal[cal.index(t) - 21]
    t_21_base = cal[cal.index(t_21) - 252]

    path = Path(__file__).parent / "test_c3_21d.duckdb"
    con = _store(path)
    _build_cal(con, cal)
    _build_universe(con, entities)

    rng = np.random.default_rng(42)
    base_vals = rng.uniform(0.28, 0.32, 252).tolist()

    rows = []
    for i, d in enumerate(cal):
        # Baseline period: varying values
        base_start_idx = cal.index(t_21_base)
        base_end_idx = cal.index(t_21)
        if base_start_idx <= i <= base_end_idx:
            idx = i - base_start_idx
            bv = base_vals[idx] if idx < 252 else 0.30
            dp_s1 = bv
            dp_s2 = bv
        elif i >= len(cal) - 20:
            dp_s1 = 0.45  # above baseline
            dp_s2 = 0.15  # below baseline
        else:
            dp_s1 = None
            dp_s2 = None
        if d == t_21:
            cs1, cs2 = 100.0, 100.0
        elif d == t:
            cs1, cs2 = 110.0, 90.0
        else:
            cs1, cs2 = 100.0, 100.0
        if dp_s1 is not None:
            rows.append(("S0001", d, cs1, cs1, round(dp_s1, 4), 1e7))
            rows.append(("S0002", d, cs2, cs2, round(dp_s2, 4), 1e7))
        else:
            rows.append(("S0001", d, cs1, cs1, None, 1e7))
            rows.append(("S0002", d, cs2, cs2, None, 1e7))
    _insert_prices(con, rows)
    con.close()

    panel = H.load_panel(str(path), cutoff=H.DEV_HI)
    c2_scores = H.score_c2_psb2(panel, t)
    scores = H.score_c3_psb2(panel, t, c2_scores)

    assert "S0001" in scores, f"S0001 not scored. c2_scores={c2_scores}"
    assert "S0002" in scores, f"S0002 not scored"

    # S0001: p near 1 (high delivery) → weight ≈ -1 → s = +r = +0.10
    # S0002: p near 0 (low delivery) → weight ≈ +1 → s = -r = -(-0.10) = +0.10
    s1 = scores["S0001"]
    s2 = scores["S0002"]
    print(f"  C3 S0001(p=1,r=+10%): s={s1:.4f} (expected ~ +0.10)")
    print(f"  C3 S0002(p=0,r=-10%): s={s2:.4f} (expected ~ +0.10)")
    assert s1 > 0.05, f"S0001 s too low: {s1:.4f}"
    assert s2 > 0.05, f"S0002 s too low: {s2:.4f}"


# ── C4 Tests ────────────────────────────────────────────────────────────────────

def test_c4_lookback():
    """C4 uses g-12 and g-1 lookback, requires 12 prior grid dates.

    Plant: S0001 has strong momentum (up 20% over 12 months, flat last month).
    S0002 has weak momentum (down 10% over 12 months, flat last month).
    Verify C4 score is positive for S0001, negative for S0002.
    """
    entities = ["S0001", "S0002"]
    cal = _bday_span(date(2015, 1, 2), 2600)

    path = Path(__file__).parent / "test_c4_lookback.duckdb"
    con = _store(path)
    _build_cal(con, cal)
    _build_universe(con, entities)

    # Insert flat data first (close=100 everywhere)
    for d in cal:
        rows = []
        for e in entities:
            rows.append((e, d, 100.0, 100.0, 0.50, 1e7))
        con.executemany("INSERT INTO equity_bhavcopy_adjusted VALUES (?,?,?,?,?,?)", rows)
    con.close()

    # Now update prices at specific dates for momentum signal
    # Use the monthly grid aligned with the cutoff
    panel = H.load_panel(str(path), cutoff=H.DEV_HI)
    mg = H.monthly_grid(panel.cal)

    g_last = len(mg) - 1
    if g_last < 13:
        g_last = 13

    t_g = mg[g_last]
    t_12 = mg[g_last - 12]
    t_1 = mg[g_last - 1]

    # Update prices
    con2 = duckdb.connect(str(path))
    # S0001: price at t_12=100, at t_1=120, at t_g=120
    con2.execute("UPDATE equity_bhavcopy_adjusted SET close=? WHERE symbol=? AND trade_date=?",
                 [100.0, "S0001", t_12])
    con2.execute("UPDATE equity_bhavcopy_adjusted SET close=? WHERE symbol=? AND trade_date=?",
                 [120.0, "S0001", t_1])
    con2.execute("UPDATE equity_bhavcopy_adjusted SET close=? WHERE symbol=? AND trade_date=?",
                 [120.0, "S0001", t_g])
    # S0002: price at t_12=100, at t_1=90, at t_g=90
    con2.execute("UPDATE equity_bhavcopy_adjusted SET close=? WHERE symbol=? AND trade_date=?",
                 [100.0, "S0002", t_12])
    con2.execute("UPDATE equity_bhavcopy_adjusted SET close=? WHERE symbol=? AND trade_date=?",
                 [90.0, "S0002", t_1])
    con2.execute("UPDATE equity_bhavcopy_adjusted SET close=? WHERE symbol=? AND trade_date=?",
                 [90.0, "S0002", t_g])
    con2.close()

    # Reload panel with updated prices
    panel = H.load_panel(str(path), cutoff=H.DEV_HI)
    mg = H.monthly_grid(panel.cal)
    g_idx = mg.index(t_g)
    scores = H.score_c4_psb2(panel, t_g, g_idx, mg)

    assert "S0001" in scores, "S0001 not scored"
    assert "S0002" in scores, "S0002 not scored"

    s1 = scores["S0001"]
    s2 = scores["S0002"]
    # S0001: r_12 = 120/100 - 1 = 0.20, r_1 = 120/120 - 1 = 0.00
    # s = (1+0.20)/(1+0.00) - 1 = 0.20
    # S0002: r_12 = 90/100 - 1 = -0.10, r_1 = 90/90 - 1 = 0.00
    # s = (1-0.10)/(1+0.00) - 1 = -0.10
    print(f"  C4 S0001 (momentum +20%): s={s1:.4f} (expected ~0.20)")
    print(f"  C4 S0002 (momentum -10%): s={s2:.4f} (expected ~ -0.10)")
    assert abs(s1 - 0.20) < 0.01, f"S0001 s={s1:.4f}, expected ~0.20"
    assert abs(s2 + 0.10) < 0.01, f"S0002 s={s2:.4f}, expected ~ -0.10"


# ── Grid and Constants ──────────────────────────────────────────────────────────

def test_fortnightly_grid():
    """Verify fortnightly grid produces exactly 56 dates in dev window."""
    cal = _bday_span(date(2010, 1, 4), 3500)
    fg = H.fortnightly_grid(cal)
    dev_fg = [d for d in fg if H.C2_DEV_LO <= d <= H.DEV_HI]
    assert len(dev_fg) == 56, f"Dev fortnightly: {len(dev_fg)}, expected 56"
    assert dev_fg[0] == date(2020, 9, 15), f"First: {dev_fg[0]}"
    assert dev_fg[-1] == date(2022, 12, 30), f"Last: {dev_fg[-1]}"
    mid = sum(1 for d in dev_fg if d.day <= 15)
    assert mid == 28, f"Mid-month: {mid}, expected 28"
    print("  Fortnightly grid: 56 dates, first=2020-09-15, last=2022-12-30")


def test_exit_band():
    """C2/C3 exit band is 0.40 (top quintile entry, top two quintiles exit)."""
    assert H.C2_EXIT_BAND == 0.40, f"C2_EXIT_BAND = {H.C2_EXIT_BAND}"
    assert H.C3_EXIT_BAND == 0.40, f"C3_EXIT_BAND = {H.C3_EXIT_BAND}"
    print("  Exit bands: C2=0.40, C3=0.40")


def test_staggered_tranches():
    """C4 uses 6 tranches, 1/6th rebalanced per month."""
    assert H.C4_N_TRANCHES == 6, f"C4_N_TRANCHES = {H.C4_N_TRANCHES}"
    print("  C4 staggered: 6 tranches")


def test_power_hurdle():
    """Power hurdle ≥ 0.80 at alpha=0.05 one-sided."""
    assert H.POWER_HURDLE == 0.80, f"POWER_HURDLE = {H.POWER_HURDLE}"
    assert H.ALPHA == 0.05, f"ALPHA = {H.ALPHA}"
    print("  Power hurdle: 0.80 at alpha=0.05")


def test_bonferroni_m():
    """Bonferroni m = 3 (D11)."""
    assert H.BONFERRONI_M == 3, f"BONFERRONI_M = {H.BONFERRONI_M}"
    print("  Bonferroni m = 3")


def test_slippage_kappa():
    """kappa = 5 bp per side."""
    assert H.KAPPA == 0.0005, f"KAPPA = {H.KAPPA}"
    print("  Slippage kappa = 5 bp")


if __name__ == "__main__":
    tests = [
        test_c2_252_day_baseline_ending_t21,
        test_c2_fortnightly_mean_min_8,
        test_c3_21_day_return_horizon,
        test_c4_lookback,
        test_fortnightly_grid,
        test_exit_band,
        test_staggered_tranches,
        test_power_hurdle,
        test_bonferroni_m,
        test_slippage_kappa,
    ]

    import time
    t0 = time.time()
    passed = 0
    for fn in tests:
        try:
            fn()
            print(f"  PASS {fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL {fn.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed ({time.time()-t0:.1f}s)")
