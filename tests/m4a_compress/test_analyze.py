"""Cohort-by-date contrast, containment, floor, attrition bound, classification - on hand-built ledgers."""
import dataclasses

import numpy as np
import pandas as pd
import pytest

from scripts.m4a_compress import analyze as A
from scripts.m4a_compress import classify as CL
from scripts.m4a_compress import cohorts as K
from scripts.m4a_compress import common as C
from scripts.m4a_compress import stats as S
from scripts.m4a_compress.common import P

PT = dataclasses.replace(P, min_normal_names=10, n_boot=200, n_perm=50)
SESS = pd.bdate_range("2018-01-01", periods=60).to_numpy(dtype="datetime64[D]")


@pytest.fixture(autouse=True)
def stage(monkeypatch):
    monkeypatch.setitem(C.STAGES, "VAL", (SESS[0].astype("datetime64[D]").astype(object), SESS[-1].astype("datetime64[D]").astype(object)))


def ledger(n_c=2, n_n=20, n_p=3, e_c=None, e_n=1.0, e_p=1.5, T=60, h=5):
    rows = []
    for t in range(T):
        ec = 2.0 + 0.1 * (t % 4) if e_c is None else e_c
        for i in range(n_c):
            rows.append((f"C{t}_{i}", t, True, False, False, ec))
        for i in range(n_n):
            rows.append((f"N{t}_{i}", t, False, True, False, e_n + 0.01 * (i % 3)))
        for i in range(n_p):
            rows.append((f"P{t}_{i}", t, False, False, True, e_p))
    ev = pd.DataFrame(rows, columns=["entity", "t", "is_C", "is_N", "is_P", f"E_range{h}"])
    ev[f"status{h}"] = K.ST_NORMAL
    ev.loc[ev["t"] + h >= T, f"status{h}"] = K.ST_BEYOND
    ev.loc[ev["t"] + h >= T, f"E_range{h}"] = np.nan
    return ev


def test_vs_normal_d_is_cohort_mean_difference_on_dates_with_both_arms():
    ev = ledger()
    row, ser = A.cell_row(ev, SESS, "VAL", 5, "normal", "E_range", PT, extras=False)
    pair = ser["pair"]
    manual = []
    for t in pair.index:
        c = ev[(ev.t == t) & ev.is_C & ev["E_range5"].notna()]["E_range5"].mean()
        n = ev[(ev.t == t) & ev.is_N & ev["E_range5"].notna()]["E_range5"].mean()
        manual.append(c - n)
    np.testing.assert_allclose(pair["d"].to_numpy(), manual)
    assert row["n_pair_dates"] == 55                              # formations t=0..54 have their window (t+5 <= 59) inside the stage
    assert row["d_mean"] == pytest.approx(np.mean(manual))
    assert row["d_lag"] == 5


def test_newey_west_lag_is_the_horizon_and_matches_the_shared_implementation():
    ev = ledger()
    row, ser = A.cell_row(ev, SESS, "VAL", 5, "normal", "E_range", PT, extras=False)
    pair = ser["pair"]
    ref = S.nw_gap_test(pair["d"].to_numpy(), pair.index.to_numpy(), 5)
    assert row["d_se"] == pytest.approx(ref["se"]) and row["d_p_one"] == pytest.approx(ref["p_one"])
    assert row["d_mde80"] == pytest.approx(S.mde_one_sided(ref["se"], PT.alpha))


def test_dates_with_too_few_normal_names_are_excluded_and_counted_but_persistence_has_no_floor():
    ev = ledger(n_n=20)
    small = (ev["t"] < 10) & ev["is_N"] & (ev["entity"].str[-1].astype(int) >= 4)          # cut N to 8 names (< floor 10) on t<10
    ev = ev[~small]
    row, ser = A.cell_row(ev, SESS, "VAL", 5, "normal", "E_range", PT, extras=False)
    assert row["n_pair_dates"] == 45 and row["n_dates_below_floor"] == 10
    rowp, _ = A.cell_row(ev, SESS, "VAL", 5, "persistence", "E_range", PT, extras=False)
    assert rowp["n_pair_dates"] == 55 and rowp["n_dates_below_floor"] == 0


def test_persistence_contrast_uses_the_high_state_arm():
    ev = ledger()
    row, _ = A.cell_row(ev, SESS, "VAL", 5, "persistence", "E_range", PT, extras=False)
    c_mean = ev[ev.is_C & ev["E_range5"].notna()].groupby("t")["E_range5"].mean().mean()
    assert row["d_mean"] == pytest.approx(c_mean - 1.5)


def test_events_with_window_past_the_stage_or_unresolved_never_enter_the_statistic():
    ev = ledger()
    ev.loc[(ev.t == 3) & ev.is_C, "E_range5"] = 1e6                                         # would dominate if used
    ev.loc[(ev.t == 3) & ev.is_C, "status5"] = K.ST_DROPPED
    row, ser = A.cell_row(ev, SESS, "VAL", 5, "normal", "E_range", PT, extras=False)
    assert 3 not in ser["pair"].index and row["d_mean"] < 5
    assert row["n_dropped_C"] == 2


def test_attrition_bound_is_worst_case_for_the_claim_and_never_above_the_observed_mean():
    ev = ledger()
    ev.loc[(ev.t.isin([3, 4])) & (ev["entity"].str.startswith("C")) & (ev["entity"].str.endswith("_0")), "status5"] = K.ST_DROPPED
    ev.loc[(ev.t.isin([7, 8])) & ev.is_N & (ev["entity"].str.endswith("_1")), "status5"] = K.ST_DROPPED
    ev.loc[ev["status5"] == K.ST_DROPPED, "E_range5"] = np.nan
    row, _ = A.cell_row(ev, SESS, "VAL", 5, "normal", "E_range", PT, extras=True)
    assert row["n_dropped_C"] == 2 and row["n_dropped_X"] == 2
    assert row["bound_d_mean"] < row["d_mean"]


def test_by_year_and_date_concentration_tables():
    ev = ledger()
    _, ser = A.cell_row(ev, SESS, "VAL", 5, "normal", "E_range", PT, extras=False)
    d = ser["pair"]["d"]
    by = A.by_year(d, SESS)
    assert by["n_dates"].sum() == len(d) and set(by.index) == {2018}
    conc = A.concentration(d, SESS, k=5)
    assert conc["d_mean"] == pytest.approx(d.mean())
    assert conc["d_mean_ex_top_k"] < conc["d_mean"] and conc["share_pos_dates"] == pytest.approx((d > 0).mean())
    assert len(conc["top_dates"]) == 5


def test_holm_classification_val_consistent_cell_needs_adjusted_p_positive_mean_and_non_fragile():
    tab = pd.DataFrame({"h": [5, 20, 5, 20], "comparator": ["normal", "normal", "persistence", "persistence"],
                        "d_p_one": [0.001, 0.30, 0.20, 0.5], "d_mean": [0.1, 0.0, -0.1, 0.0],
                        "bound_d_mean": [0.05, -0.1, -0.2, -0.1], "bound_d_p_one": [0.01, 0.8, 0.5, 0.9]})
    res = CL.classify(tab)
    assert res["val_consistent"] == [(5, "normal")] and res["label"].startswith("C6")
    fragile = tab.copy(); fragile["bound_d_mean"] = [-0.01, -0.1, -0.2, -0.1]
    assert CL.classify(fragile)["label"].startswith("C5")
    assert CL.classify(tab.assign(d_p_one=[0.02, 0.3, 0.2, 0.5]))["label"].startswith("C5")     # Holm: 0.02*4 = 0.08
    assert CL.classify(tab, defects=["hash mismatch"])["label"].startswith("C4")
    assert "NON-CONFIRMATORY" in CL.classify(tab)["label"] and "VAL-confirmed" not in CL.classify(tab)["label"]


def test_signed_return_is_descriptive_only_no_pvalues():
    ev = ledger()
    ev["E_sgn5"] = np.where(ev["E_range5"].notna(), 0.1, np.nan)
    tab = A.signed_descriptive(ev, SESS, "VAL", 5, PT)
    assert {"cohort", "mean_evt", "mean_coh", "frac_pos", "n"} <= set(tab.columns)
    assert not any("p_" in c or c.endswith("_t") for c in tab.columns)
