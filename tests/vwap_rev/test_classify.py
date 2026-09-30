import pandas as pd
import pytest

from scripts.vwap_rev import classify as K

HZ = (5, 10, 15, 30, 60)


def tab(p_by_cell: dict, mean_by_cell: dict | None = None, nan_share: float = 0.0):
    rows = []
    for side in ("up_disp_short", "down_disp_long"):
        for H in HZ:
            rows.append({"side": side, "H": H, "p_one_nw": p_by_cell.get((side, H), 0.5),
                         "session_mean_bp": (mean_by_cell or {}).get((side, H), 1.0),
                         "nan_share": nan_share})
    return pd.DataFrame(rows)


C1 = ("down_disp_long", 30)
C2 = ("up_disp_short", 15)


def test_c5_when_nothing_confirms_in_val():
    r = K.classify(tab({}), tab({C1: 0.0001}), None, {})
    assert r["label"] == "C5" and r["val_confirmed"] == []


def test_train_or_robustness_never_enter_classifier_signature():
    import inspect
    assert list(inspect.signature(K.classify).parameters)[:4] == ["val_tab", "hold_tab", "delay2_tab", "net_lb"]


def test_holm_over_ten_cells_blocks_a_lone_marginal_val_cell():
    # p=0.03 alone passes uncorrected but Holm over 10 cells -> 0.3
    assert K.val_confirmed(tab({C1: 0.03})) == []
    assert K.val_confirmed(tab({C1: 0.004})) == [C1]


def test_negative_mean_never_confirms_even_with_tiny_p():
    assert K.val_confirmed(tab({C1: 1e-9}, {C1: -3.0})) == []


def test_c7_when_val_and_holdout_confirm_but_no_economics():
    r = K.classify(tab({C1: 0.001}), tab({C1: 0.01}), None, {C1: -2.0})
    assert r["label"] == "C7"


def test_c8_when_economic_gate_passes():
    r = K.classify(tab({C1: 0.001}), tab({C1: 0.01}), None, {C1: 0.4})
    assert r["label"] == "C8"


def test_c6_val_confirmed_holdout_positive_but_insignificant():
    r = K.classify(tab({C1: 0.001}), tab({C1: 0.3}, {C1: 0.8}), None, {})
    assert r["label"] == "C6"


def test_c5_val_confirmed_holdout_reversed():
    r = K.classify(tab({C1: 0.001}), tab({C1: 0.9}, {C1: -0.8}), None, {})
    assert r["label"] == "C5"


def test_holdout_holm_is_over_val_confirmed_cells_only():
    # two VAL-confirmed cells; HOLDOUT p 0.03 and 0.03 -> Holm over 2 -> 0.06 -> neither confirms
    v = tab({C1: 0.0005, C2: 0.0005})
    h = tab({C1: 0.03, C2: 0.03})
    r = K.classify(v, h, None, {})
    assert r["label"] == "C6" and r["holdout_confirmed_clean"] == []
    # one VAL-confirmed cell: p=0.03 confirms (Holm over 1)
    r1 = K.classify(tab({C1: 0.0005}), tab({C1: 0.03}), None, {})
    assert r1["label"] == "C7"


def test_microstructure_qualifier_blocks_h5_h10_when_delay2_mean_nonpositive():
    c = ("down_disp_long", 5)
    v, h = tab({c: 0.0005}), tab({c: 0.001})
    bad = K.classify(v, h, tab({}, {c: -0.1}), {c: 1.0})
    assert bad["label"] == "C6" and bad["microstructure_contaminated"] == [c]
    good = K.classify(v, h, tab({}, {c: 0.3}), {c: 1.0})
    assert good["label"] == "C8"
    # H=30 cells are exempt from the qualifier
    assert K.classify(tab({C1: 0.0005}), tab({C1: 0.001}), None, {C1: 1.0})["label"] == "C8"


def test_c4_on_nan_cap_or_listed_defect_takes_precedence():
    r = K.classify(tab({C1: 0.0005}), tab({C1: 0.001}, nan_share=0.05), None, {C1: 1.0})
    assert r["label"] == "C4"
    r2 = K.classify(tab({C1: 0.0005}), tab({C1: 0.001}), None, {}, defects=["freeze hash mismatch"])
    assert r2["label"] == "C4"
