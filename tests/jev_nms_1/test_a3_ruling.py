import json
from fractions import Fraction

import pytest

from scripts.jev_nms_1.eligibility import load_seal
from scripts.jev_nms_1.rulings import REPO, frozen_argmax, l5_halts, l5_threshold, load_a3
from scripts.jev_nms_1.transport import CLASSES


def _l3_records():
    load_a3()  # verifies l3_step5.json against its A3 reference
    return json.loads((REPO / "data/jev_market_state/l3_step5.json").read_text(encoding="utf-8"))["records"]


ORDER = ["trending_up", "trending_down", "range_bound", "disorderly"]


def test_tie_order_is_the_sealed_f1_class_order():
    config, _ = load_seal()
    a3 = load_a3()
    assert a3["argmax_tie_rule"]["class_order"] == config["labels"]["classes_order"] == ORDER
    assert list(CLASSES) == ORDER


@pytest.mark.parametrize("tied, expected", [
    (("trending_down", "range_bound"), "trending_down"),
    (("range_bound", "disorderly"), "range_bound"),
    (("trending_up", "trending_down"), "trending_up"),
    (("trending_up", "disorderly"), "trending_up"),
    (("trending_down", "disorderly"), "trending_down"),
    (("trending_up", "trending_down", "range_bound", "disorderly"), "trending_up"),
])
def test_exact_tie_resolves_to_first_class_in_frozen_order(tied, expected):
    top = 1 / len(tied) if len(tied) == 4 else 0.42
    rest = (1 - top * len(tied)) / (4 - len(tied)) if len(tied) < 4 else 0
    probs = {c: (top if c in tied else rest) for c in reversed(ORDER)}
    assert frozen_argmax(probs, ORDER) == expected


def test_no_tie_returns_the_maximum_regardless_of_order():
    probs = {"trending_up": 0.06, "trending_down": 0.35, "range_bound": 0.49, "disorderly": 0.10}
    assert frozen_argmax(probs, ORDER) == "range_bound"


def test_l3_tie_state_resolves_to_trending_down_and_disagrees():
    rec = {r["replicate"]: r for r in _l3_records() if r["state"] == "2023-05-02|12:30"}
    tied = rec[1]["validity"]["probabilities"]
    assert tied["trending_down"] == tied["range_bound"] == 0.42
    # the stored JSON keys are alphabetical, so dict order would pick range_bound
    assert max(tied, key=tied.get) == "range_bound"
    assert frozen_argmax(tied, ORDER) == "trending_down"
    assert frozen_argmax(rec[0]["validity"]["probabilities"], ORDER) == "range_bound"


def test_recorded_l3_run_yields_the_frozen_baseline_under_the_tie_rule():
    a3 = load_a3()
    recs = _l3_records()
    by = {(r["state"], r["replicate"]): r["validity"]["probabilities"] for r in recs}
    states = [r["state"] for r in recs if r["replicate"] == 0]
    agree = [frozen_argmax(by[(s, 0)], ORDER) == frozen_argmax(by[(s, 1)], ORDER) for s in states]
    assert (sum(agree), len(agree)) == (46, 50)
    assert (a3["l3_baseline"]["argmax_agreements"], a3["l3_baseline"]["pairs"]) == (46, 50)
    assert (sum(agree[:20]), 20) == (a3["d6_canaries"]["argmax_agreements"], a3["d6_canaries"]["pairs"])


def test_l5_threshold_is_exactly_41_over_50():
    a3 = load_a3()
    b = a3["l3_baseline"]
    t = l5_threshold(b["argmax_agreements"], b["pairs"], a3["l5_halt"]["threshold_pp_below_baseline"])
    assert t == Fraction(41, 50) == Fraction(a3["l5_halt"]["threshold"])
    assert str(float(t)) == a3["l5_halt"]["threshold_decimal"] == "0.82"
    assert Fraction(b["decimal"]) == Fraction(46, 50)


def test_l5_halt_boundary_is_strict_and_exact():
    t = l5_threshold(46, 50, 10)
    assert not l5_halts(41, 50, t)          # exactly 0.82: not "more than 10 pp below"
    assert l5_halts(40, 50, t)
    assert not l5_halts(17, 20, t)          # 0.85
    assert l5_halts(16, 20, t)              # 0.80
    assert 0.92 - 0.10 != 0.82              # why float differences are not used


def test_a3_refuses_a_tampered_addendum(tmp_path, monkeypatch):
    from scripts.jev_nms_1 import rulings
    bad = tmp_path / "a3.json"
    doc = json.loads(rulings.A3_ADDENDUM.read_text(encoding="utf-8"))
    doc["l5_halt"]["threshold"] = "42/50"
    bad.write_text(json.dumps(doc), encoding="utf-8")
    monkeypatch.setattr(rulings, "A3_ADDENDUM", bad)
    with pytest.raises(RuntimeError, match="pinned SHA-256"):
        load_a3()
