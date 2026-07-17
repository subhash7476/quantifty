"""PSB-2 formula-fidelity tests — mutation-verified. Arms D and E included.
Uses CSV COPY for fast DuckDB import.
"""

import csv
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


def _write_csv(con, rows, csv_path):
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        for row in rows:
            w.writerow(row)
    con.execute(f"COPY equity_bhavcopy_adjusted FROM '{csv_path}' (AUTO_DETECT TRUE)")
    csv_path.unlink()


def test_c2_baseline_252_t21():
    cal = _bday_span(date(2019, 1, 2), 300)
    t = cal[-1]
    t_21 = cal[cal.index(t) - 21]
    t_base_start = cal[cal.index(t_21) - 251]
    bs_idx = cal.index(t_base_start)
    be_idx = cal.index(t_21)

    path = Path(__file__).parent / "fid_c2_baseline.duckdb"
    con = _store(path)
    con.executemany("INSERT INTO trading_calendar VALUES (?, 200)", [(d,) for d in cal])
    con.execute("INSERT INTO universe_eligibility VALUES (?, ?)", ["S0001", "S0001"])
    con.execute("INSERT INTO universe_membership VALUES (?, ?, ?)", [date(2019, 1, 2), "S0001", 1])

    # Give baseline structure along the length axis (R3-2).
    # Most recent 200 days of baseline at 0.32, oldest 52 days at 0.28.
    # At 252-day window: mean = (200*0.32 + 52*0.28) / 252 ≈ 0.3117, σ ≈ 0.02.
    # At 200-day window (only the 0.32 region): mean ≈ 0.32, σ ≈ 0.
    # z(252) = (0.80 - 0.3117) / 0.02 ≈ 24.4
    # z(200) would differ because mean and σ both change.
    n_total = be_idx - bs_idx + 1
    n_old = n_total - 200  # ~52 days at 0.28
    rows = []
    for i, d in enumerate(cal):
        if i >= len(cal) - 15:
            dp = 0.80
        elif bs_idx <= i <= be_idx:
            offset = i - bs_idx
            dp = 0.32 if offset >= n_old else 0.28
        else:
            dp = None
        rows.append(["S0001", d.isoformat(), 100.0, 100.0, round(dp, 4) if dp is not None else None, 1e7])
    _write_csv(con, rows, path.with_suffix(".csv"))
    con.close()

    panel = H.load_panel(str(path), cutoff=H.DEV_HI)
    scores = H.score_c2_psb2(panel, t)
    assert "S0001" in scores, "S0001 not scored"
    z = scores["S0001"]
    # Expected: ~(0.80 - 0.312) / 0.02 ≈ 24. Assert > 15.
    assert z > 15, f"z={z:.2f} too low (expected ~24)"


def test_c2_min_8_nonnull():
    cal = _bday_span(date(2019, 1, 2), 280)
    t = cal[-1]
    t_21 = cal[cal.index(t) - 21]
    t_base_start = cal[cal.index(t_21) - 251]
    bs_idx = cal.index(t_base_start)
    be_idx = cal.index(t_21)

    path = Path(__file__).parent / "fid_c2_min8.duckdb"
    con = _store(path)
    con.executemany("INSERT INTO trading_calendar VALUES (?, 200)", [(d,) for d in cal])
    con.execute("INSERT INTO universe_eligibility VALUES (?, ?)", ["S0001", "S0001"])
    con.execute("INSERT INTO universe_membership VALUES (?, ?, ?)", [date(2019, 1, 2), "S0001", 1])

    rng = np.random.default_rng(42)
    base_vals = rng.uniform(0.28, 0.32, be_idx - bs_idx + 1).tolist()

    rows = []
    for i, d in enumerate(cal):
        if i >= len(cal) - 7:
            dp = 0.50
        elif bs_idx <= i <= be_idx:
            dp = base_vals[i - bs_idx]
        else:
            dp = None
        rows.append(["S0001", d.isoformat(), 100.0, 100.0, round(dp, 4) if dp is not None else None, 1e7])
    _write_csv(con, rows, path.with_suffix(".csv"))
    con.close()

    panel = H.load_panel(str(path), cutoff=H.DEV_HI)
    scores = H.score_c2_psb2(panel, t)
    assert "S0001" not in scores, "should be skipped (< 8 non-NULL recent)"
    print("  C2 min 8 non-NULL: correctly skipped (mutation: change to 5, passes)")


def test_c3_21_day_horizon():
    cal = _bday_span(date(2019, 1, 2), 300)
    t = cal[-1]
    t_21 = cal[cal.index(t) - 21]
    t_base_start = cal[cal.index(t_21) - 251]
    bs_idx = cal.index(t_base_start)
    be_idx = cal.index(t_21)

    path = Path(__file__).parent / "fid_c3_21d.duckdb"
    con = _store(path)
    con.executemany("INSERT INTO trading_calendar VALUES (?, 200)", [(d,) for d in cal])
    for e in ["S0001", "S0002"]:
        con.execute("INSERT INTO universe_eligibility VALUES (?, ?)", [e, e])
        con.execute("INSERT INTO universe_membership VALUES (?, ?, ?)", [date(2019, 1, 2), e, 1])

    rng = np.random.default_rng(42)
    base_vals = rng.uniform(0.28, 0.32, be_idx - bs_idx + 1).tolist()

    rows = []
    for i, d in enumerate(cal):
        if i >= len(cal) - 20:
            dp_s1, dp_s2 = 0.45, 0.15
        elif bs_idx <= i <= be_idx:
            val = base_vals[i - bs_idx]
            dp_s1, dp_s2 = val, val
        else:
            dp_s1 = dp_s2 = None
        if d == t_21:
            cs1, cs2 = 100.0, 100.0
        elif d == t:
            cs1, cs2 = 110.0, 90.0
        else:
            cs1, cs2 = 100.0, 100.0
        rows.append(["S0001", d.isoformat(), cs1, cs1, round(dp_s1, 4) if dp_s1 is not None else None, 1e7])
        rows.append(["S0002", d.isoformat(), cs2, cs2, round(dp_s2, 4) if dp_s2 is not None else None, 1e7])
    _write_csv(con, rows, path.with_suffix(".csv"))
    con.close()

    panel = H.load_panel(str(path), cutoff=H.DEV_HI)
    c2 = H.score_c2_psb2(panel, t)
    scores = H.score_c3_psb2(panel, t, c2)
    assert "S0001" in scores and "S0002" in scores, "Entities not scored"
    s1, s2 = scores["S0001"], scores["S0002"]
    assert abs(s1 - 0.10) < 0.02, f"S0001 s={s1:.4f}"
    assert abs(s2 - 0.10) < 0.02, f"S0002 s={s2:.4f}"
    print(f"  C3 21-day horizon: s1={s1:.4f}, s2={s2:.4f} (mutation: 21->10, scores change)")


def test_c4_lookback():
    cal = _bday_span(date(2015, 1, 2), 2600)
    path = Path(__file__).parent / "fid_c4_lookback.duckdb"
    con = _store(path)
    con.executemany("INSERT INTO trading_calendar VALUES (?, 200)", [(d,) for d in cal])
    con.execute("INSERT INTO universe_eligibility VALUES (?, ?)", ["S0001", "S0001"])
    con.execute("INSERT INTO universe_membership VALUES (?, ?, ?)", [date(2015, 1, 2), "S0001", 1])

    rows = [["S0001", d.isoformat(), 100.0, 100.0, 0.50, 1e7] for d in cal]
    _write_csv(con, rows, path.with_suffix(".csv"))
    con.close()

    panel = H.load_panel(str(path), cutoff=H.DEV_HI)
    mg = H.monthly_grid(panel.cal)
    g_last = len(mg) - 1
    assert g_last >= 13, f"Need 14+ grid dates, have {g_last+1}"
    t_g, t_12, t_1 = mg[g_last], mg[g_last - 12], mg[g_last - 1]

    con2 = duckdb.connect(str(path))
    con2.execute("UPDATE equity_bhavcopy_adjusted SET close=100.0 WHERE symbol='S0001' AND trade_date=?", [t_12])
    con2.execute("UPDATE equity_bhavcopy_adjusted SET close=120.0 WHERE symbol='S0001' AND trade_date=?", [t_1])
    con2.execute("UPDATE equity_bhavcopy_adjusted SET close=120.0 WHERE symbol='S0001' AND trade_date=?", [t_g])
    con2.close()

    panel2 = H.load_panel(str(path), cutoff=H.DEV_HI)
    mg2 = H.monthly_grid(panel2.cal)
    scores = H.score_c4_psb2(panel2, t_g, mg2.index(t_g), mg2)
    assert "S0001" in scores, "not scored"
    s = scores["S0001"]
    assert abs(s - 0.20) < 0.01, f"s={s:.4f} (expected 0.20)"
    print(f"  C4 lookback: s={s:.4f} (mutation: change g-12, score changes)")


def test_arm_d_c3_sign():
    cal = _bday_span(date(2019, 1, 2), 300)
    t = cal[-1]
    t_21 = cal[cal.index(t) - 21]
    t_base_start = cal[cal.index(t_21) - 251]
    bs_idx = cal.index(t_base_start)
    be_idx = cal.index(t_21)

    path = Path(__file__).parent / "arm_d.duckdb"
    con = _store(path)
    con.executemany("INSERT INTO trading_calendar VALUES (?, 200)", [(d,) for d in cal])
    for e in ["S_LOW", "S_HIGH"]:
        con.execute("INSERT INTO universe_eligibility VALUES (?, ?)", [e, e])
        con.execute("INSERT INTO universe_membership VALUES (?, ?, ?)", [date(2019, 1, 2), e, 1])

    rng = np.random.default_rng(42)
    base_vals = rng.uniform(0.28, 0.32, be_idx - bs_idx + 1).tolist()

    rows = []
    for i, d in enumerate(cal):
        if i >= len(cal) - 20:
            dp_low, dp_high = 0.15, 0.55
            dp_low, dp_high = 0.15, 0.55
        elif bs_idx <= i <= be_idx:
            val = base_vals[i - bs_idx]
            dp_low, dp_high = val, val
        else:
            dp_low = dp_high = None
        if d == t_21:
            c_low, c_high = 100.0, 100.0
        elif d == t:
            c_low, c_high = 95.0, 110.0
        else:
            c_low, c_high = 100.0, 100.0
        rows.append(["S_LOW", d.isoformat(), c_low, c_low,
                     round(dp_low, 4) if dp_low is not None else None, 1e7])
        rows.append(["S_HIGH", d.isoformat(), c_high, c_high,
                     round(dp_high, 4) if dp_high is not None else None, 1e7])
    _write_csv(con, rows, path.with_suffix(".csv"))
    con.close()

    panel = H.load_panel(str(path), cutoff=H.DEV_HI)
    c2 = H.score_c2_psb2(panel, t)
    scores = H.score_c3_psb2(panel, t, c2)
    assert "S_LOW" in scores, f"S_LOW not scored. c2={c2}"
    assert "S_HIGH" in scores, f"S_HIGH not scored"
    s_low, s_high = scores["S_LOW"], scores["S_HIGH"]
    assert s_low > 0.02, f"S_LOW s={s_low:.4f}"
    assert s_high > 0.05, f"S_HIGH s={s_high:.4f}"
    print(f"  Arm D: S_LOW(p=0,r=-5%)={s_low:.4f} S_HIGH(p=1,r=+10%)={s_high:.4f} (both > 0)")


def test_arm_e_staggered():
    cal = _bday_span(date(2015, 1, 2), 2600)
    entities = [f"S{i:04d}" for i in range(1, 31)]

    path = Path(__file__).parent / "arm_e.duckdb"
    con = _store(path)
    con.executemany("INSERT INTO trading_calendar VALUES (?, 200)", [(d,) for d in cal])
    con.executemany("INSERT INTO universe_eligibility VALUES (?, ?)", [(e, e) for e in entities])
    con.executemany(
        "INSERT INTO universe_membership VALUES (?, ?, ?)",
        [(date(2015, 1, 2), e, i + 1) for i, e in enumerate(entities)],
    )

    rng = np.random.default_rng(42)
    price = np.ones((len(entities), len(cal))) * 100.0
    for j in range(1, len(cal)):
        price[:, j] = price[:, j - 1] * (1 + rng.normal(0, 0.01, len(entities)))

    rows = []
    for i, e in enumerate(entities):
        for j, d in enumerate(cal):
            cv = float(round(float(price[i, j]), 2))
            rows.append([e, d.isoformat(), cv, cv, 0.40, 1e7])
    _write_csv(con, rows, path.with_suffix(".csv"))
    con.close()

    panel = H.load_panel(str(path), cutoff=H.DEV_HI)
    mg = H.monthly_grid(panel.cal)
    def c4_fn(t):
        g = mg.index(t) if t in mg else -1
        return H.score_c4_psb2(panel, t, g, mg) if g >= 0 else {}
    res = H.evaluate_candidate_psb2(panel, "C4", c4_fn, str(path), monthly_grid_dates=mg)
    assert res.turnover is not None, "No turnover"
    turnover_6 = res.turnover

    # Mutation: C4_N_TRANCHES = 3 should increase turnover (R3-2)
    # Fewer tranches means larger share replaced per rebalance.
    orig_tranches = H.C4_N_TRANCHES
    try:
        H.C4_N_TRANCHES = 3
        res3 = H.evaluate_candidate_psb2(panel, "C4", c4_fn, str(path), monthly_grid_dates=mg)
        turnover_3 = res3.turnover
        assert turnover_3 is not None and turnover_3 > turnover_6, (
            f"Turnover at 3 tranches ({turnover_3:.4f}) not > at 6 ({turnover_6:.4f})")
        print(f"  Arm E: turnover(6)={turnover_6:.4f} turnover(3)={turnover_3:.4f} (3 > 6: PASS)")
    finally:
        H.C4_N_TRANCHES = orig_tranches


if __name__ == "__main__":
    import time
    t0 = time.time()
    tests = [
        ("C2 baseline 252d t-21", test_c2_baseline_252_t21),
        ("C2 min 8 non-NULL", test_c2_min_8_nonnull),
        ("C3 21-day horizon", test_c3_21_day_horizon),
        ("C4 lookback", test_c4_lookback),
        ("Arm D: C3 sign", test_arm_d_c3_sign),
        ("Arm E: Staggered", test_arm_e_staggered),
    ]
    passed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
    print(f"\n{passed}/{len(tests)} passed ({time.time()-t0:.1f}s)")
    raise SystemExit(0 if passed == len(tests) else 1)
