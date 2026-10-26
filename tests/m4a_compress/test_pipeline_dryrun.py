"""End-to-end dry run on a SYNTHETIC snapshot: the numpy engine and the pure-SQL verifier are two independent
implementations of the same protocol - on random data (regime-switching volatility, delistings, holes, splits, a
rename chain) they must agree exactly. Pre-freeze validation of both code paths; touches no real price."""
import dataclasses
import datetime as dt

import duckdb
import numpy as np
import pandas as pd
import pytest

from scripts.m4a_compress import common as C
from scripts.m4a_compress import run_stage as R
from scripts.m4a_compress import verify_independent as V

PD = dataclasses.replace(C.P, fast=3, slow=8, pct_window=20, quiet=5, base_window=20, horizons=(3, 6),
                         min_normal_names=30, n_boot=100, n_perm=50)
E_N, T_N = 150, 430


@pytest.fixture(scope="module")
def synth(tmp_path_factory):
    out = tmp_path_factory.mktemp("m4a")
    rng = np.random.default_rng(21)
    dates = pd.bdate_range("2012-01-02", periods=T_N)
    rows = []
    for e in range(E_N):
        sig = np.where(rng.random(T_N) < 0.5, 0.008, 0.02)
        sig = np.repeat(sig[:: 12], 12)[:T_N]                                # regimes of 12 sessions
        c = 100 * np.exp(np.cumsum(rng.normal(0, 1, T_N) * sig))
        o = c * np.exp(rng.normal(0, 0.004, T_N))
        wid = np.abs(rng.normal(0.004, 0.003, T_N)) + sig * 0.5
        v = np.exp(rng.normal(10, 0.5, T_N))
        last = T_N - 1
        if e % 17 == 0:
            last = int(rng.integers(230, 330))                              # delists inside the stages
        holes = set(rng.choice(np.arange(110, last), size=2, replace=False)) if e % 11 == 0 else set()
        for t in range(last + 1):
            if t in holes:
                continue
            rows.append((f"E{e:03d}", dates[t], f"S{e}", "EQ", o[t], max(o[t], c[t]) * (1 + wid[t]),
                         min(o[t], c[t]) * (1 - wid[t]), c[t], v[t], v[t] * c[t], 1))
    panel = pd.DataFrame(rows, columns=["entity", "trade_date", "symbol", "series", "open", "high", "low", "close",
                                        "volume", "turnover", "n_listings"])
    cal = pd.DataFrame({"trade_date": dates, "n_symbols": 300, "tot_turnover_eq": 1e9})
    ents_all = [f"E{e:03d}" for e in range(E_N)]
    ents_even = [f"E{e:03d}" for e in range(0, E_N, 2)]
    memb = pd.concat([
        pd.DataFrame({"rebalance_date": dates[0] - pd.Timedelta(days=1), "entity": ents_all,
                      "symbol": [x.replace("E", "S") for x in ents_all], "rank": range(1, len(ents_all) + 1)}),
        pd.DataFrame({"rebalance_date": dates[280], "entity": ents_even,
                      "symbol": [x.replace("E", "S") for x in ents_even], "rank": range(1, len(ents_even) + 1)})])
    ex_date = dates[260]
    ca_ents = {f"E{e:03d}" for e in range(3, E_N, 10)}
    ren = panel["entity"].eq("E003") & (panel["trade_date"] >= dates[100])
    panel.loc[ren, "symbol"] = "S3B"                                          # rename chain inside the panel
    raw_df = panel.copy()
    pre = raw_df["entity"].isin(ca_ents) & (raw_df["trade_date"] < ex_date)
    for col in ("open", "high", "low", "close"):
        raw_df.loc[pre, col] = raw_df.loc[pre, col] / 0.5                     # snapshot holds ADJUSTED, raw holds AS-TRADED
    panel.to_parquet(out / "panel_dev.parquet", index=False)
    cal.to_parquet(out / "calendar_dev.parquet", index=False)
    memb.to_parquet(out / "membership_dev.parquet", index=False)
    con = duckdb.connect(str(out / "raw.duckdb"))
    con.execute("CREATE TABLE equity_bhavcopy AS SELECT symbol, series, CAST(trade_date AS DATE) trade_date, open, high, low, close, volume, turnover FROM raw_df")
    con.execute("CREATE TABLE adjustment_factors (symbol VARCHAR, ex_date DATE, action_type VARCHAR, factor DOUBLE)")
    for ent in sorted(ca_ents):
        sym = "S3B" if ent == "E003" else f"S{int(ent[1:])}"                  # E003's factor is keyed to its NEW symbol
        con.execute("INSERT INTO adjustment_factors VALUES (?, ?, 'SPLIT', 0.5)", [sym, ex_date.date()])
    con.execute("CREATE TABLE symbol_entity_intervals (symbol VARCHAR, valid_from DATE, valid_to DATE, entity VARCHAR)")
    for e in range(E_N):
        con.execute("INSERT INTO symbol_entity_intervals VALUES (?, DATE '2000-01-01', DATE '2100-01-01', ?)", [f"S{e}", f"E{e:03d}"])
    con.execute("INSERT INTO symbol_entity_intervals VALUES ('S3B', DATE '2000-01-01', DATE '2100-01-01', 'E003')")
    con.close()
    from scripts.m4a_compress import panel as PL
    old = (C.OUT_DIR, C.SNAPSHOT_DIR, C.EQUITY_DB, C.BKV_PANEL_SHA256, dict(C.STAGES))
    C.OUT_DIR, C.SNAPSHOT_DIR, C.EQUITY_DB = out, out, out / "raw.duckdb"
    C.BKV_PANEL_SHA256 = PL.sha256_file(out / "panel_dev.parquet")
    C.STAGES.clear()
    C.STAGES.update({"TRAIN": (dt.date(2012, 12, 3), dt.date(2013, 6, 28)), "VAL": (dt.date(2013, 7, 1), dt.date(2013, 12, 31))})
    yield out
    C.OUT_DIR, C.SNAPSHOT_DIR, C.EQUITY_DB, C.BKV_PANEL_SHA256 = old[:4]
    C.STAGES.clear(); C.STAGES.update(old[4])


@pytest.fixture(scope="module")
def ran(synth):
    cells = {st: R.execute(st, PD) for st in ("TRAIN", "VAL")}
    return cells, {st: V.run(st, PD) for st in ("TRAIN", "VAL")}


def test_pipeline_produces_all_primary_cells_with_dates_in_every_cohort(ran):
    cells, _ = ran
    for st, tab in cells.items():
        prim = tab[(tab["variant"] == "D2") & (tab["outcome"] == "E_range")]
        assert len(prim) == 4 and set(prim["comparator"]) == {"normal", "persistence"}
        assert (prim["n_C"] > 20).all() and (prim["n_pair_dates"] > 10).all(), prim[["h", "comparator", "n_C", "n_pair_dates"]]


def test_sql_and_numpy_engines_agree_row_for_row(ran):
    _, ver = ran
    for st, v in ver.items():
        for var in ("D2", "D1"):
            x = v["vp1_sql"][var]
            assert x["only_in_ledger"] == 0 and x["only_in_sql"] == 0, (st, var, x)
            assert x["flag_mismatch"] == 0 and x["status_mismatch"] == 0, (st, var, x)
            assert x["pct_max_abs_diff"] < 1e-12 and x["E_max_abs_diff"] < 1e-9, (st, var, x)
            assert x["ledger_rows"] == x["sql_rows"] > 2000 and x["n_compared_values"] > 2000     # not vacuous
            assert x["pass"]


def test_independent_paths_pass(ran):
    _, ver = ran
    for st, v in ver.items():
        for k in ("vp2_raw", "vp3_stats", "vp4_accounting", "vp5_prices"):
            assert v[k]["pass"], (st, k, v[k])
        assert v["vp2_raw"]["verified"] >= 8
        assert v["vp5_prices"]["entities_with_bonus_or_split"] > 0 and v["vp5_prices"]["ca_reconstruction_rate"] == 1.0
        assert not v["stop"]


def test_raw_check_skips_events_spanning_a_corporate_action_instead_of_forcing_them(synth, ran):
    x = V.vp2_raw_sample("TRAIN", PD, n_per_cohort=60)
    assert x["skipped_ca"] > 0 and x["verified"] > 20 and x["pass"], x


def test_terminal_and_dropped_windows_are_exercised(synth):
    ev = pd.read_parquet(synth / "results" / "events_D2_TRAIN.parquet")
    assert (ev["status6"] == 2).any() and (ev["status6"] == 0).any()


def test_verifier_detects_a_tampered_ledger(synth, ran):
    path = synth / "results" / "events_D2_TRAIN.parquet"
    ev = pd.read_parquet(path)
    good = ev.copy()
    i = ev.index[ev["status6"] == 0][10]
    ev.loc[i, "E_range6"] = ev.loc[i, "E_range6"] + 0.01
    j = ev.index[ev["is_C"]][3]
    ev.loc[j, "is_C"] = False
    ev.to_parquet(path, index=False)
    try:
        x = V.vp1_sql_reconcile("TRAIN", PD)["D2"]
        assert not x["pass"] and x["E_max_abs_diff"] > 0.005 and x["flag_mismatch"] >= 1
    finally:
        good.to_parquet(path, index=False)


def test_rerun_reproduces_the_cell_table_byte_for_byte(synth, ran):
    cells, _ = ran
    again = R.execute("VAL", PD)
    pd.testing.assert_frame_equal(cells["VAL"].reset_index(drop=True), again.reset_index(drop=True))


def test_percentile_differences_are_accepted_only_when_a_documented_float_tie_explains_them():
    diff = np.array([0.0, 1 / 20, 1 / 20, 3 / 20, 0.01])
    ties = np.array([0, 1, 0, 1, 5])
    explained, unexplained = V.classify_pct_diffs(diff, ties, 20)
    assert list(explained) == [False, True, False, False, False]      # 1/20 with one tie in the window
    assert list(unexplained) == [False, False, True, True, True]      # no tie / diff larger than the ties allow / not a multiple


def test_verifier_flags_a_tampered_percentile(synth, ran):
    path = synth / "results" / "events_D2_TRAIN.parquet"
    ev = pd.read_parquet(path)
    good = ev.copy()
    ev.loc[ev.index[100], "pct"] = ev.loc[ev.index[100], "pct"] + 0.05
    ev.to_parquet(path, index=False)
    try:
        x = V.vp1_sql_reconcile("TRAIN", PD, variants=("D2",))["D2"]
        assert not x["pass"] and x["pct_unexplained"] >= 1
    finally:
        good.to_parquet(path, index=False)
