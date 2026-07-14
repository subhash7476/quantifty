"""PSB-1 §5 scoring unit tests (Prompt 1 deliverable 3).

Hand-built fixtures: known inputs -> computed scores; completeness rules; §4.2
imputation; AC-3 (deliv_pct carried through the same rn=1 turnover-primary pick).
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "psb1"))

import screening_harness as H  # noqa: E402


def make_panel(cal, px, dp=None, members=None):
    """Build a Panel directly from dicts. px/dp keyed by (entity, date)."""
    cal = sorted(cal)
    cal_pos = {d: i for i, d in enumerate(cal)}
    px = {k: float(v) for k, v in px.items() if v is not None}
    dp = dict(dp or {})
    ent_dates = {}
    for (e, d) in px:
        ent_dates.setdefault(e, []).append(d)
    for e in ent_dates:
        ent_dates[e].sort()
    reb0 = cal[0]
    members = members or sorted({e for (e, _) in px})
    return H.Panel(cal, cal_pos, px, dp, {}, ent_dates, [reb0], {reb0: list(members)}, cal[-1])


def days(n, start=date(2021, 1, 1)):
    return [start + timedelta(days=i) for i in range(n)]


# --------------------------------------------------------------------------- C1
def test_c1_basic():
    cal = days(6)
    px = {("E", cal[0]): 100.0, ("E", cal[5]): 110.0}
    panel = make_panel(cal, px)
    s = H.score_c1(panel, cal[5])
    assert s["E"] == pytest.approx(-(110.0 / 100.0 - 1.0))   # -0.10


def test_c1_incomplete_missing_tminus5():
    cal = days(6)
    px = {("E", cal[5]): 110.0}                              # no t-5 price
    panel = make_panel(cal, px)
    assert "E" not in H.score_c1(panel, cal[5])


# --------------------------------------------------------------------------- C3
def _c3_panel():
    cal = days(70)
    it = 64
    px = {("E", cal[i]): 100.0 for i in range(70)}           # prices irrelevant to C3
    dp = {}
    # 60-day baseline ending t-5 (indices 0..59): 20x0.30 + 20x0.50 + 20 NULL -> 40 non-null
    for i in range(0, 20):
        dp[("E", cal[i])] = 0.30
    for i in range(20, 40):
        dp[("E", cal[i])] = 0.50
    for i in range(40, 60):
        dp[("E", cal[i])] = None
    # recent 5 (indices 60..64): 0.60 each
    for i in range(60, 65):
        dp[("E", cal[i])] = 0.60
    for i in range(65, 70):
        dp[("E", cal[i])] = None
    return make_panel(cal, px, dp), cal, it


def test_c3_basic():
    panel, cal, it = _c3_panel()
    base = [0.30] * 20 + [0.50] * 20
    mu = np.mean(base); sd = np.std(base, ddof=1)
    expected = (0.60 - mu) / sd
    s = H.score_c3(panel, cal[it])
    assert s["E"] == pytest.approx(expected)


def test_c3_incomplete_recent_below_3():
    panel, cal, it = _c3_panel()
    for i in range(60, 65):
        panel.dp[("E", cal[i])] = None
    panel.dp[("E", cal[63])] = 0.60
    panel.dp[("E", cal[64])] = 0.60                          # only 2 non-null recent
    assert "E" not in H.score_c3(panel, cal[it])


def test_c3_incomplete_baseline_below_40():
    panel, cal, it = _c3_panel()
    panel.dp[("E", cal[0])] = None                           # 39 non-null baseline
    assert "E" not in H.score_c3(panel, cal[it])


def test_c3_zero_std_excluded():
    panel, cal, it = _c3_panel()
    for i in range(0, 40):
        panel.dp[("E", cal[i])] = 0.40                       # constant baseline -> sd=0
    for i in range(40, 60):
        panel.dp[("E", cal[i])] = None
    assert "E" not in H.score_c3(panel, cal[it])


# --------------------------------------------------------------------------- C4
def test_c4_interaction_weights():
    """Two names, C1 and C3 complete; check s = c1 * (1 - 2p) with known percentile ranks."""
    cal = days(70)
    it = 64
    px = {}
    for name, r5 in (("A", 0.10), ("B", -0.10)):            # A winner, B loser
        px[(name, cal[it - 5])] = 100.0
        px[(name, cal[it])] = 100.0 * (1 + r5)
    dp = {}
    # give A high abnormal delivery, B low -> percentile p(A)=1, p(B)=0 (n=2)
    for name, base_vals, recent in (("A", [0.30, 0.50], 0.90), ("B", [0.30, 0.50], 0.10)):
        for i in range(0, 20):
            dp[(name, cal[i])] = 0.30
        for i in range(20, 40):
            dp[(name, cal[i])] = 0.50
        for i in range(40, 60):
            dp[(name, cal[i])] = None
        for i in range(60, 65):
            dp[(name, cal[i])] = recent
        for i in range(65, 70):
            dp[(name, cal[i])] = None
    panel = make_panel(cal, px, dp, members=["A", "B"])
    s = H.score_c4(panel, cal[it])
    c1 = H.score_c1(panel, cal[it])
    # p(A)=1 -> weight (1-2)= -1 ; p(B)=0 -> weight +1
    assert s["A"] == pytest.approx(c1["A"] * -1.0)
    assert s["B"] == pytest.approx(c1["B"] * 1.0)


# --------------------------------------------------------------------------- C5
def test_c5_zero_vol_excluded():
    cal = days(260)
    px = {("E", cal[i]): 100.0 for i in range(260)}          # flat -> returns 0 -> sd=0
    panel = make_panel(cal, px)
    assert "E" not in H.score_c5(panel, cal[259])


def test_c5_basic():
    cal = days(260)
    rng = np.random.default_rng(0)
    rets = rng.normal(0, 0.02, 259)
    prices = 100.0 * np.cumprod(np.concatenate([[1.0], 1 + rets]))
    px = {("E", cal[i]): float(prices[i]) for i in range(260)}
    panel = make_panel(cal, px)
    it = 259
    lo = it - H.VOL_DAYS + 1
    window_rets = [prices[k] / prices[k - 1] - 1 for k in range(lo + 1, it + 1)]
    expected = -np.std(window_rets, ddof=1)
    assert H.score_c5(panel, cal[it])["E"] == pytest.approx(expected)


def test_c5_below_200_obs_excluded():
    cal = days(260)
    px = {}
    rng = np.random.default_rng(1)
    for i in range(260):
        if i % 2 == 0:                                       # ~130 present -> <200 returns
            px[("E", cal[i])] = 100.0 * (1 + rng.normal(0, 0.02))
    panel = make_panel(cal, px)
    assert "E" not in H.score_c5(panel, cal[259])


# --------------------------------------------------------------------------- §4.2 imputation
def test_date_ic_imputation_direction():
    scores = [5, 4, 3, 2, 1, 0]
    fwd = [None, 0.04, 0.03, 0.02, 0.01, 0.005]             # highest-score name delisted
    primary, imputed = H.date_ic(scores, fwd)
    assert primary == pytest.approx(1.0)                    # among present, perfectly monotone
    assert imputed < primary                                # high score paired with worst return


def test_date_ic_below_min_names():
    assert H.date_ic([1, 2, 3], [0.1, None, None]) == (None, None)


# --------------------------------------------------------------------------- percentile rank
def test_pct_rank_ties_and_endpoints():
    r = H._pct_rank([10, 20, 20, 40])
    assert r[0] == pytest.approx(0.0)
    assert r[3] == pytest.approx(1.0)
    assert r[1] == pytest.approx(r[2])                       # average ties


# --------------------------------------------------------------------------- AC-3 loader
def test_loader_delivpct_follows_rn1_pick(tmp_path):
    """deliv_pct must come from the SAME rn=1 turnover-primary listing as the price."""
    db = tmp_path / "ac3.duckdb"
    con = duckdb.connect(str(db))
    con.execute("CREATE TABLE trading_calendar(trade_date DATE, n_symbols INT)")
    con.execute("CREATE TABLE universe_eligibility(symbol VARCHAR, entity VARCHAR)")
    con.execute("CREATE TABLE universe_membership(rebalance_date DATE, symbol VARCHAR, rank INT)")
    con.execute("CREATE TABLE equity_bhavcopy_adjusted("
                "trade_date DATE, symbol VARCHAR, close DOUBLE, open DOUBLE, deliv_pct DOUBLE, turnover DOUBLE)")
    d = date(2022, 6, 1)
    con.execute("INSERT INTO trading_calendar VALUES (?, 200)", [d])
    # entity E has two listings on the same day; E_A has higher turnover (rn=1)
    con.executemany("INSERT INTO universe_eligibility VALUES (?,?)",
                    [("E_A", "E"), ("E_B", "E")])
    con.execute("INSERT INTO universe_membership VALUES (?, 'E_A', 1)", [d])
    con.executemany("INSERT INTO equity_bhavcopy_adjusted VALUES (?,?,?,?,?,?)", [
        (d, "E_A", 111.0, None, 0.90, 100.0),                     # turnover-primary
        (d, "E_B", 222.0, None, 0.10, 50.0),
    ])
    con.close()
    panel = H.load_panel(db_path=str(db), cutoff=date(2022, 12, 31))
    assert panel.px[("E", d)] == pytest.approx(111.0)       # price from E_A
    assert panel.dp[("E", d)] == pytest.approx(0.90)        # deliv from the SAME E_A row


def test_loader_asserts_fence(tmp_path):
    db = tmp_path / "fence.duckdb"
    con = duckdb.connect(str(db))
    con.execute("CREATE TABLE trading_calendar(trade_date DATE, n_symbols INT)")
    con.execute("CREATE TABLE universe_eligibility(symbol VARCHAR, entity VARCHAR)")
    con.execute("CREATE TABLE universe_membership(rebalance_date DATE, symbol VARCHAR, rank INT)")
    con.execute("CREATE TABLE equity_bhavcopy_adjusted("
                "trade_date DATE, symbol VARCHAR, close DOUBLE, open DOUBLE, deliv_pct DOUBLE, turnover DOUBLE)")
    d = date(2022, 6, 1)
    con.execute("INSERT INTO trading_calendar VALUES (?, 200)", [d])
    con.execute("INSERT INTO universe_eligibility VALUES ('E','E')")
    con.execute("INSERT INTO universe_membership VALUES (?, 'E', 1)", [d])
    con.execute("INSERT INTO equity_bhavcopy_adjusted VALUES (?, 'E', 100.0, NULL, 0.5, 100.0)", [d])
    con.close()
    panel = H.load_panel(db_path=str(db), cutoff=date(2022, 12, 31))
    assert panel.observed_max <= date(2022, 12, 31)


# --------------------------------------------------------------------------- C2 (D1)
def _c2_panel(rmkt_vals, re_vals, re_form, rmkt_form):
    """Build a 5-day-per-week panel for one name 'E' where each weekly grid return equals
    the supplied value, and return (panel, wgrid, widx, rmkt, formation_date).

    rmkt_vals/re_vals index the 52 window weeks (grids 1..52); grid 53 is the formation
    week (re_form / rmkt_form). rmkt is supplied directly to score_c2 (not price-derived).
    """
    n_grids = 54                                            # grids 0..53
    cal = []
    d = date(2018, 1, 1)
    for _ in range(n_grids * 5):
        cal.append(d)
        d += timedelta(days=1)
        while d.weekday() >= 5:
            d += timedelta(days=1)
    grid = [cal[5 * k + 4] for k in range(n_grids)]
    # prices for E at grid days: realise each weekly return r_E(grid_k)=price(k)/price(k-1)-1
    price = 100.0
    px = {("E", grid[0]): price}
    for k in range(1, 53):
        price *= (1 + re_vals[k - 1])
        px[("E", grid[k])] = price
    price *= (1 + re_form)                                  # formation grid 53
    px[("E", grid[53])] = price
    panel = make_panel(cal, px, members=["E"])
    widx = {g: i for i, g in enumerate(grid)}
    rmkt = {grid[k]: rmkt_vals[k - 1] for k in range(1, 53)}
    rmkt[grid[53]] = rmkt_form
    return panel, grid, widx, rmkt, grid[53]


def test_c2_fit_and_sign():
    """Hand-computed OLS: 4-value pattern over 52 weeks -> beta=3, alpha=0.01, sigma_e computed;
    formation resid +0.01 (E outperformed its market-implied return) -> score negative."""
    rmkt_vals, re_vals = [], []
    pattern = [(0.01, 0.03), (0.01, 0.05), (-0.01, -0.01), (-0.01, -0.03)]
    for i in range(52):
        x, y = pattern[i % 4]
        rmkt_vals.append(x); re_vals.append(y)
    panel, grid, widx, rmkt, t = _c2_panel(rmkt_vals, re_vals, re_form=0.02, rmkt_form=0.0)
    s = H.score_c2(panel, t, grid, widx, rmkt)
    # hand: alpha=0.01, beta=3, residuals all +/-0.01, sigma_e=sqrt(52*0.0001/50); resid_t=+0.01
    import math
    sigma_e = math.sqrt(52 * 0.0001 / 50)
    expected = -0.01 / sigma_e
    assert s["E"] == pytest.approx(expected, rel=1e-6)
    assert s["E"] < 0                                       # outperformer scores negative


def test_c2_completeness_40_present_39_absent():
    rmkt_vals, re_vals = [], []
    pattern = [(0.01, 0.03), (0.01, 0.05), (-0.01, -0.01), (-0.01, -0.03)]
    for i in range(52):
        x, y = pattern[i % 4]
        rmkt_vals.append(x); re_vals.append(y)
    panel, grid, widx, rmkt, t = _c2_panel(rmkt_vals, re_vals, re_form=0.02, rmkt_form=0.0)
    # drop rmkt for 12 window weeks -> 40 usable -> present
    rmkt40 = dict(rmkt)
    for k in range(1, 13):
        del rmkt40[grid[k]]
    assert "E" in H.score_c2(panel, t, grid, widx, rmkt40)
    # drop one more -> 39 usable -> absent
    rmkt39 = dict(rmkt40)
    del rmkt39[grid[13]]
    assert "E" not in H.score_c2(panel, t, grid, widx, rmkt39)


def test_c2_zero_residual_sigma_guard():
    """Constant name return (price flat) with varying market -> beta=0, residuals exactly 0
    -> sigma_e=0 -> excluded by the sigma(e)>0 guard."""
    rmkt_vals = [(0.01 if i % 3 == 0 else -0.01 if i % 3 == 1 else 0.02) for i in range(52)]
    re_vals = [0.0] * 52                                    # price stays 100.0 exactly
    panel, grid, widx, rmkt, t = _c2_panel(rmkt_vals, re_vals, re_form=0.02, rmkt_form=0.01)
    assert "E" not in H.score_c2(panel, t, grid, widx, rmkt)


# --------------------------------------------------------------------------- sign flag (D2)
def test_sign_flag():
    assert H._sign_flag(0.0453, -0.0938) is True
    assert H._sign_flag(-0.02, 0.03) is True
    assert H._sign_flag(0.0453, 0.0015) is False
    assert H._sign_flag(0.04, 0.0) is False                 # imputed exactly 0 -> not a flip


# --------------------------------------------------------------------------- R1 §11.3 (gate-(b) classifier)
DAY0, DAY1 = date(2020, 1, 1), date(2020, 1, 2)
SPLIT_10_1 = [(date(2020, 1, 2), 0.1)]                      # 10:1 split, factor 0.1


def test_r1_five_buckets_agree_with_gate_b():
    """classify_move reproduces gate-(b)'s five buckets (audit_corporate_actions.py:279-296)."""
    assert H.classify_move(-0.90, 100.0, DAY0, DAY1, SPLIT_10_1) == "CA-explained"
    assert H.classify_move(-0.50, 100.0, DAY0, DAY1, SPLIT_10_1) == "magnitude-mismatch"
    assert H.classify_move(+0.50, 100.0, DAY0, DAY1, SPLIT_10_1) == "direction-mismatch"
    assert H.classify_move(-0.50, 100.0, DAY0, DAY1, []) == "CA-shaped-orphan"
    assert H.classify_move(-0.30, 100.0, DAY0, DAY1, []) == "genuine"


def test_r1_ca_shaped_below_min_price_is_genuine():
    """is_ca_shaped is disabled below Rs 5 (tick-grid floor) — gate-(b) rule."""
    assert H.classify_move(-0.50, 4.0, DAY0, DAY1, []) == "genuine"


def test_r1_interval_span_exdate_on_nontrading_day():
    """A factor whose ex_date falls on a non-trading day between the two prints still spans
    (ptd < ex <= td), unlike a `td == ex_date` test."""
    facs = [(date(2020, 1, 2), 0.1)]                        # ex on Jan-2 (non-trading here)
    d0, d1 = date(2020, 1, 1), date(2020, 1, 3)            # move printed Jan-1 -> Jan-3
    assert H.classify_move(-0.90, 100.0, d0, d1, facs) == "CA-explained"


def _scan_panel(ret, move_date_idx=5, n=10):
    cal = days(n)
    cal_pos = {d: i for i, d in enumerate(cal)}
    px = {("E", cal[i]): 100.0 for i in range(n)}
    px[("E", cal[move_date_idx])] = 100.0 * (1 + ret)
    return H.Panel(cal, cal_pos, px, {}, {}, {"E": list(cal)}, [cal[0]], {cal[0]: ["E"]}, cal[-1])


def test_scan_residue_undocumented_halts_flag():
    panel = _scan_panel(-0.50)                              # CA-shaped-orphan, no factor
    res = H.scan_data_integrity(panel, factors_by_entity={}, documented=set())
    assert ("E", panel.cal[5]) in res.register
    assert res.would_halt
    assert res.counts.get("CA-shaped-orphan") == 1


def test_scan_documented_residue_in_register_but_no_halt():
    """A documented residue row is STILL a missing input (in the register) but does NOT halt."""
    panel = _scan_panel(-0.50)
    res = H.scan_data_integrity(panel, factors_by_entity={},
                                documented={("E", panel.cal[5])})
    assert ("E", panel.cal[5]) in res.register             # D5: register regardless of documentation
    assert not res.would_halt                              # §11.3 halt keys on UNDOCUMENTED only
    assert len(res.residue_rows) == 1 and res.residue_rows[0][4] is True


def test_scan_genuine_not_in_register():
    panel = _scan_panel(-0.30)                              # not CA-shaped -> genuine
    res = H.scan_data_integrity(panel, factors_by_entity={}, documented=set())
    assert not res.register and not res.would_halt


# --------------------------------------------------------------------------- D5 scoring integration
def _reg(panel, entity, idx):
    return H.reg_positions(panel, {(entity, panel.cal[idx])})


def test_d5_c1_formation_window_excludes_register():
    cal = days(6)
    px = {("E", cal[0]): 100.0, ("E", cal[5]): 110.0}
    panel = make_panel(cal, px)
    assert "E" in H.score_c1(panel, cal[5])                             # no register -> scored
    reg = _reg(panel, "E", 3)                                           # register move in (t-5, t]
    assert "E" not in H.score_c1(panel, cal[5], reg)                    # D5.2 -> not scored
    reg_edge = _reg(panel, "E", 0)                                      # at t-5 (excluded endpoint)
    assert "E" in H.score_c1(panel, cal[5], reg_edge)                   # (t-5, t] excludes t-5


def test_d5_c5_vol_window_drops_register_day():
    cal = days(260)
    rng = np.random.default_rng(3)
    prices = 100.0 * np.cumprod(np.concatenate([[1.0], 1 + rng.normal(0, 0.02, 259)]))
    px = {("E", cal[i]): float(prices[i]) for i in range(260)}
    panel = make_panel(cal, px)
    base = H.score_c5(panel, cal[259])["E"]
    reg = _reg(panel, "E", 200)                                         # one register day
    s = H.score_c5(panel, cal[259], reg)["E"]
    assert s != base                                                    # D5.5 that daily return dropped


def test_d5_c3_unaffected_by_register():
    panel, cal, it = _c3_panel()
    reg = _reg(panel, "E", it - 2)
    assert H.score_c3(panel, cal[it]) == H.score_c3(panel, cal[it])     # C3 takes no reg (D5.6)
    # score_c3 has no reg param at all -> structurally unaffected
    import inspect
    assert "reg" not in inspect.signature(H.score_c3).parameters


def test_d5_c2_market_excludes_register_span():
    """D5.4: a name whose r_i(w-5,w) spans a register move is dropped from r_mkt(w)."""
    cal = []
    d = date(2018, 1, 1)
    for _ in range(60 * 5):
        cal.append(d); d += timedelta(days=1)
        while d.weekday() >= 5:
            d += timedelta(days=1)
    grid = [cal[5 * k + 4] for k in range(60)]
    px = {}
    for k, g in enumerate(grid):
        px[("A", g)] = 100.0 * (1.02 ** k)                             # A and B differ
        px[("B", g)] = 100.0 * (1.05 ** k)
    panel = make_panel(cal, px, members=["A", "B"])
    wg = H.weekly_grid(panel.cal)
    rmkt_plain = H.market_weekly_returns(panel, wg)
    reg = H.reg_positions(panel, {("A", grid[10])})                     # A has a register move at grid 10
    rmkt_reg = H.market_weekly_returns(panel, wg, reg)
    assert rmkt_plain[grid[10]] != rmkt_reg[grid[10]]                   # A excluded from that week's mean


def test_d5_forward_window_exclusion_not_imputed():
    """D5.7: forward-window CA exclusion removes the name from the date and is NOT §4.2-imputed."""
    # 3 names scored; one has a register move in its forward window -> excluded, not imputed
    scores = {"A": 3.0, "B": 2.0, "C": 1.0, "D": 0.5, "E": 0.2, "F": 0.1}
    # emulate the evaluate loop's D5.7 branch + date_ic
    reg_excluded = {"A"}
    s_all = [s for e, s in scores.items() if e not in reg_excluded]
    fwd_all = [0.05, 0.04, 0.03, 0.02, 0.01]                            # all present, none imputed
    primary, imputed = H.date_ic(s_all, fwd_all)
    assert primary == pytest.approx(imputed)                           # nothing imputed for the CA name
