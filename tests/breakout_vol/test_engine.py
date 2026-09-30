import dataclasses

import numpy as np
import pandas as pd
import pytest

from scripts.breakout_vol import engine as G
from scripts.breakout_vol.common import P

P5 = dataclasses.replace(P, range_n=(5,), horizons=(3,), onset_quiet=5, vol_window=5, lookback_required=11,
                         min_bench_names=3, terminal_guard=5)


def make_frames(E=12, T=140, seed=0, cut=None):
    """cut: {entity: last_session_index} to end a series early."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2015-01-05", periods=T)
    rows = []
    for e in range(E):
        c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, T)))
        o = c * np.exp(rng.normal(0, 0.003, T))
        v = np.exp(rng.normal(10, 0.3, T))
        for t in range(T):
            if cut and e in cut and t > cut[e]:
                break
            rows.append((f"E{e:02d}", dates[t], f"S{e}", "EQ", o[t], max(o[t], c[t]) * 1.002, min(o[t], c[t]) * 0.998,
                         c[t], v[t], v[t] * c[t], 1))
    panel = pd.DataFrame(rows, columns=["entity", "trade_date", "symbol", "series", "open", "high", "low", "close",
                                        "volume", "turnover", "n_listings"])
    cal = pd.DataFrame({"trade_date": dates, "n_symbols": 300, "tot_turnover_eq": 1e9})
    memb = pd.DataFrame({"rebalance_date": [dates[0] - pd.Timedelta(days=1)] * E,
                         "entity": [f"E{e:02d}" for e in range(E)], "symbol": [f"S{e}" for e in range(E)],
                         "rank": range(1, E + 1)})
    return panel, cal, memb, dates


def build(panel, cal, memb, p=P5):
    return G.build_panel(panel, cal, memb, p)


def test_close_based_breakout_excludes_today_and_uses_closes():
    panel, cal, memb, dates = make_frames()
    pn = build(panel, cal, memb)
    m = G.detect_masks(pn, 5, P5)
    e, t = 3, 60
    prior_max = pn.C[e, t - 5:t].max()
    assert m["up"][e, t] == (pn.C[e, t] > prior_max)
    assert m["mx"][e, t] == pytest.approx(prior_max)               # window is t-5..t-1, today excluded
    assert m["dn"][e, t] == (pn.C[e, t] < pn.C[e, t - 5:t].min())


def test_signal_is_causal_events_up_to_t0_ignore_everything_after():
    panel, cal, memb, dates = make_frames(seed=1)
    pn = build(panel, cal, memb)
    ev = G.detect_events(pn, P5)
    t0 = 90
    p2 = panel.copy()
    late = p2["trade_date"] > dates[t0]
    rng = np.random.default_rng(9)
    for col in ("open", "high", "low", "close", "volume", "turnover"):
        p2.loc[late, col] = p2.loc[late, col] * np.exp(rng.normal(0, 0.5, late.sum()))
    ev2 = G.detect_events(build(p2, cal, memb), P5)
    a = ev[ev["t"] <= t0].sort_values(["e", "t", "kind"]).reset_index(drop=True)
    b = ev2[ev2["t"] <= t0].sort_values(["e", "t", "kind"]).reset_index(drop=True)
    cols = ["entity", "t", "kind", "close", "vol", "med_vol", "av", "abn", "arm"]
    pd.testing.assert_frame_equal(a[cols], b[cols])
    assert len(a) > 0


def test_volume_baseline_excludes_today():
    panel, cal, memb, dates = make_frames(seed=2)
    pn = build(panel, cal, memb)
    med, av, abn = G.volume_state(pn, P5)
    e, t = 4, 70
    assert med[e, t] == pytest.approx(np.median(pn.V[e, t - 5:t]))
    p2 = panel.copy()
    mask = (p2["entity"] == "E04") & (p2["trade_date"] == dates[t])
    p2.loc[mask, "volume"] *= 1000
    pn2 = build(p2, cal, memb)
    med2, av2, abn2 = G.volume_state(pn2, P5)
    assert med2[e, t] == pytest.approx(med[e, t])                   # today's volume never enters its own baseline
    assert av2[e, t] == pytest.approx(av[e, t] * 1000)
    assert med2[e, t + 1] != med[e, t + 1]                          # but it does enter tomorrow's


def test_onset_only_first_breakout_then_quiet_period():
    panel, cal, memb, dates = make_frames(E=1, T=140, seed=3)
    # deterministic ramp: every session from 50 makes a new closing high
    panel.loc[panel["trade_date"] < dates[50], "close"] = 100.0            # flat base: no breakout inside it
    panel.loc[panel["trade_date"] >= dates[50], "close"] = 101 + np.arange(140 - 50) * 1.0
    panel["open"] = panel["close"]; panel["high"] = panel["close"]; panel["low"] = panel["close"] * 0.99
    memb = memb.iloc[:1]
    pn = build(panel, cal, memb)
    ev = G.detect_events(pn, P5)
    up = ev[ev["kind"] == "up"]
    assert list(up["t"]) == [50]                                    # one onset, the rest of the run is not re-flagged


def test_arms_are_a_partition_and_D_has_no_breakout():
    panel, cal, memb, dates = make_frames(E=20, T=200, seed=4)
    pn = build(panel, cal, memb)
    ev = G.detect_events(pn, P5)
    assert not ev.duplicated(["entity", "date", "N", "kind"]).any()
    brk = ev[ev["kind"].isin(["up", "dn"])]
    assert set(brk["arm"]) <= {"B", "C"}
    assert ((brk["arm"] == "B") == brk["abn"]).all()
    m = G.detect_masks(pn, 5, P5)
    d = ev[ev["kind"].isin(["dup", "ddn"])]
    assert not m["up"][d["e"], d["t"]].any() and not m["dn"][d["e"], d["t"]].any()
    assert d["abn"].all() and (d["arm"] == "D").all()


def test_membership_is_strictly_prior_rebalance():
    panel, cal, memb, dates = make_frames(E=2, T=40)
    memb = pd.DataFrame({"rebalance_date": [dates[0] - pd.Timedelta(days=1), dates[10]],
                         "entity": ["E00", "E01"], "symbol": ["S0", "S1"], "rank": [1, 1]})
    pn = build(panel, cal, memb)
    e1 = pn.entities.index("E01")
    assert not pn.member[e1, 10] and pn.member[e1, 11]              # the rebalance day itself is NOT yet a member day
    assert pn.member[pn.entities.index("E00"), 5] and not pn.member[pn.entities.index("E00"), 11]


def test_forward_window_entry_open_t_plus_1_exit_close_t_plus_h():
    panel, cal, memb, dates = make_frames(seed=5)
    pn = build(panel, cal, memb)
    wr = G.window_returns(pn, 3, P5)
    e, t = 2, 50
    assert wr["R"][e, t] == pytest.approx(pn.C[e, t + 3] / pn.O[e, t + 1] - 1)
    assert wr["gap"][e, t] == pytest.approx(pn.O[e, t + 1] / pn.C[e, t] - 1)
    assert wr["status"][e, t] == G.ST_NORMAL


def test_window_status_dropped_terminal_and_hole():
    panel, cal, memb, dates = make_frames(E=6, T=140, seed=6, cut={1: 60})
    hole = (panel["entity"] == "E02") & (panel["trade_date"] == dates[52])
    panel = panel[~hole]
    pn = build(panel, cal, memb)
    wr = G.window_returns(pn, 3, P5)
    e1, e2 = pn.entities.index("E01"), pn.entities.index("E02")
    assert wr["status"][e1, 58] == G.ST_TERMINAL                    # ends at 60 with 79 sessions of data after: guard ok
    assert wr["R"][e1, 58] == pytest.approx(pn.C[e1, 60] / pn.O[e1, 59] - 1)
    assert wr["status"][e1, 60] == G.ST_DROPPED                     # no entry session
    assert wr["status"][e2, 50] == G.ST_DROPPED                     # hole at 52 inside 51..53, series resumes
    assert wr["status"][e2, 40] == G.ST_NORMAL


def test_benchmark_identity_sum_of_excess_is_zero():
    panel, cal, memb, dates = make_frames(E=15, T=140, seed=7)
    pn = build(panel, cal, memb)
    wr = G.window_returns(pn, 3, P5)
    rm, cnt = G.benchmark(pn, wr, P5)
    for t in (30, 60, 100):
        ok = pn.member[:, t] & np.isfinite(wr["R"][:, t])
        assert cnt[t] == ok.sum()
        assert (wr["R"][ok, t] - rm[t]).sum() == pytest.approx(0.0, abs=1e-12)


def test_attach_outcomes_signs_and_stage_containment():
    panel, cal, memb, dates = make_frames(E=20, T=200, seed=8)
    pn = build(panel, cal, memb)
    ev = G.detect_events(pn, P5)
    ev, bench = G.attach_outcomes(pn, ev, P5)
    r = ev.iloc[0]
    sign = G.KIND_SIGN[r["kind"]]
    assert r["f3"] == pytest.approx(1e4 * sign * (r["R3"] - r["Rm3"]))
    assert r["raw3"] == pytest.approx(1e4 * sign * r["R3"])
    assert ev[ev["kind"].isin(["dn", "ddn"])]["f3"].notna().any()
    has = ev["entry_date"].notna()
    assert (pd.to_datetime(ev.loc[has, "entry_date"]) > pd.to_datetime(ev.loc[has, "date"])).all()   # entry strictly after the signal session
