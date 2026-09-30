"""End-to-end dry run on a SYNTHETIC snapshot: the numpy engine and the pure-SQL verifier are two independent
implementations of the same protocol - on random data (with delistings and holes) they must agree exactly.
This is the pre-freeze validation of both code paths; it touches no real price."""
import datetime as dt

import duckdb
import numpy as np
import pandas as pd
import pytest

from scripts.breakout_vol import common as C
from scripts.breakout_vol import run_stage as R
from scripts.breakout_vol import verify_independent as V


@pytest.fixture(scope="module")
def synth(tmp_path_factory):
    out = tmp_path_factory.mktemp("bkv")
    rng = np.random.default_rng(11)
    E, T = 130, 430
    dates = pd.bdate_range("2012-01-02", periods=T)
    rows = []
    for e in range(E):
        drift = rng.normal(0, 0.0004)
        c = 100 * np.exp(np.cumsum(rng.normal(drift, 0.014, T)))
        o = c * np.exp(rng.normal(0, 0.004, T))
        v = np.exp(rng.normal(10, 0.5, T)) * (1 + 6 * (rng.random(T) < 0.03))
        last = T - 1
        if e % 17 == 0:
            last = int(rng.integers(200, 330))                       # delists inside the stage
        holes = set(rng.choice(np.arange(90, last), size=2, replace=False)) if e % 11 == 0 else set()
        for t in range(last + 1):
            if t in holes:
                continue
            rows.append((f"E{e:03d}", dates[t], f"S{e}", "EQ", o[t], max(o[t], c[t]) * 1.003, min(o[t], c[t]) * 0.997,
                         c[t], v[t], v[t] * c[t], 1))
    panel = pd.DataFrame(rows, columns=["entity", "trade_date", "symbol", "series", "open", "high", "low", "close",
                                        "volume", "turnover", "n_listings"])
    cal = pd.DataFrame({"trade_date": dates, "n_symbols": 300, "tot_turnover_eq": 1e9})
    ents_all = [f"E{e:03d}" for e in range(E)]
    ents_even = [f"E{e:03d}" for e in range(0, E, 2)]
    memb = pd.concat([
        pd.DataFrame({"rebalance_date": dates[0] - pd.Timedelta(days=1), "entity": ents_all,
                      "symbol": [x.replace("E", "S") for x in ents_all], "rank": range(1, len(ents_all) + 1)}),
        pd.DataFrame({"rebalance_date": dates[250], "entity": ents_even,
                      "symbol": [x.replace("E", "S") for x in ents_even], "rank": range(1, len(ents_even) + 1)})])
    panel.to_parquet(out / "panel_dev.parquet", index=False)
    cal.to_parquet(out / "calendar_dev.parquet", index=False)
    memb.to_parquet(out / "membership_dev.parquet", index=False)
    raw = out / "raw.duckdb"
    con = duckdb.connect(str(raw))
    # 2:1 splits at session 200 on every 10th name: the snapshot holds ADJUSTED values (prices x0.5, volume x2 before the
    # ex-date, as the certified view produces); the raw table holds the AS-TRADED values.
    ex_date = dates[200]
    ca_ents = {f"E{e:03d}" for e in range(3, E, 10)}
    raw_df = panel.copy()
    pre = raw_df["entity"].isin(ca_ents) & (raw_df["trade_date"] < ex_date)
    for col in ("open", "high", "low", "close"):
        raw_df.loc[pre, col] = raw_df.loc[pre, col] / 0.5
    raw_df.loc[pre, "volume"] = raw_df.loc[pre, "volume"] * 0.5
    con.execute("CREATE TABLE equity_bhavcopy AS SELECT symbol, series, CAST(trade_date AS DATE) trade_date, open, high, low, close, volume, turnover FROM raw_df")
    con.execute("CREATE TABLE adjustment_factors (symbol VARCHAR, ex_date DATE, action_type VARCHAR, factor DOUBLE)")
    for ent in sorted(ca_ents):
        con.execute("INSERT INTO adjustment_factors VALUES (?, ?, 'SPLIT', 0.5)", [f"S{int(ent[1:])}", ex_date.date()])
    con.close()
    old = (C.OUT_DIR, C.EQUITY_DB, C.STAGES["TRAIN"])
    C.OUT_DIR, C.EQUITY_DB = out, raw
    C.STAGES["TRAIN"] = (dt.date(2012, 6, 1), dt.date(2013, 5, 31))
    yield out
    C.OUT_DIR, C.EQUITY_DB = old[0], old[1]
    C.STAGES["TRAIN"] = old[2]


@pytest.fixture(scope="module")
def ran(synth):
    cells = R.execute("TRAIN", "dev")
    return cells, V.run("TRAIN")


def test_pipeline_produces_all_cells_and_events(ran):
    cells, _ = ran
    assert len(cells) == 8
    assert (cells[["n_B", "n_C"]] > 5).all().all()


def test_sql_and_numpy_engines_agree_event_for_event(ran):
    _, ver = ran
    v = ver["vp1_sql"]
    assert v["only_in_ledger"] == 0 and v["only_in_sql"] == 0, v
    assert v["arm_mismatch"] == 0 and v["status_mismatch_H5"] == 0 and v["status_mismatch_H20"] == 0, v
    assert v["f_max_abs_diff_bp_H5"] < 1e-6 and v["f_max_abs_diff_bp_H20"] < 1e-6, v
    assert v["pass"], v
    assert v["ledger_events"] == v["sql_events"] > 1000 and v["n_compared_H20"] > 800, v      # the comparison is not vacuous
    print("VP1", {k: v[k] for k in v if k != "tables"})


def test_independent_paths_pass(ran):
    _, ver = ran
    for k in ("vp2_raw", "vp3_stats", "vp4_accounting", "vp5_volume", "vp6_fee"):
        assert ver[k]["pass"], (k, ver[k])
    assert ver["vp2_raw"]["verified"] >= 10
    assert ver["vp2_raw"]["skipped_ca"] > 0                          # events spanning the ex-date are skipped, not forced
    assert ver["vp2_raw"]["level_differs_by_later_CA_events"] > 0    # levels DO differ before the ex-date; the margin ratio does not
    assert ver["vp5_volume"]["names_with_bonus_or_split"] > 0 and ver["vp5_volume"]["ca_reconstruction_rate"] == 1.0
    print("VP2", ver["vp2_raw"]); print("VP3 diffs", ver["vp3_stats"]["max_abs_diff"]); print("VP5", ver["vp5_volume"])
    assert not ver["stop"]


def test_terminal_and_dropped_windows_are_exercised(synth):
    ev = pd.read_parquet(synth / "results" / "events_TRAIN.parquet")
    assert (ev["status20"] == 1).any() and (ev["status20"] == 2).any()


def test_verifier_detects_a_tampered_ledger(synth, ran):
    path = synth / "results" / "events_TRAIN.parquet"
    ev = pd.read_parquet(path)
    good = ev.copy()
    i = ev.index[ev["status20"] == 0][10]
    ev.loc[i, "f20"] = ev.loc[i, "f20"] + 0.5                       # half a basis point
    ev.loc[ev.index[ev["arm"] == "B"][3], "arm"] = "C"              # and one mislabelled arm
    ev.to_parquet(path, index=False)
    try:
        v = V.vp1_sql_reconcile("TRAIN", "dev")
        assert not v["pass"] and v["arm_mismatch"] == 1 and v["f_max_abs_diff_bp_H20"] > 0.4
    finally:
        good.to_parquet(path, index=False)
