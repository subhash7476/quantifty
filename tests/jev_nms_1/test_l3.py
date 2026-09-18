import json

import pytest

from scripts.jev_nms_1 import l3
from scripts.jev_nms_1.l3 import decide, record_id, verify_pool

CLASSES = ("trending_up", "trending_down", "range_bound", "disorderly")


def _probs(top, p=0.55):
    rest = (1 - p) / 3
    return {c: (p if c == top else rest) for c in CLASSES}


def _rec(state, rep, top, p=0.55, valid=True):
    probs = _probs(top, p)
    return {"state": state, "replicate": rep, "key": f"k-{state}-{rep}",
            "validity": {"valid": valid, "choice": top if valid else None,
                         "probabilities": probs if valid else None}}


def _run(tops0, tops1, p1=0.55):
    states = [f"2024-06-{i + 1:02d}|10:00" for i in range(len(tops0))]
    return ([_rec(s, 0, t) for s, t in zip(states, tops0)]
            + [_rec(s, 1, t, p1) for s, t in zip(states, tops1)])


def test_record_id_keeps_replicate_0_on_the_canonical_hash():
    assert record_id("abc", "L3-X", 0) == "abc"
    assert record_id("abc", "L3-X", 1) == "abc+L3-X+1"


def test_agreement_and_max_abs_difference_over_all_and_canary_subset():
    tops0 = ["trending_up"] * 50
    tops1 = ["range_bound"] * 5 + ["trending_up"] * 45
    d = decide(_run(tops0, tops1, p1=0.60))
    assert d["all_50"]["argmax_agreements"] == 45
    assert d["all_50"]["argmax_agreement"] == pytest.approx(0.9)
    assert d["canary_d6_first_20"]["n_pairs"] == 20
    assert d["canary_d6_first_20"]["argmax_agreements"] == 15
    assert d["all_50"]["max_abs_probability_difference"] == pytest.approx(0.60 - 0.15)
    assert len(d["canary_baseline_rep0"]) == 20
    assert not d["needs_ruling"]


def test_canary_subset_is_first_20_in_seed_order_of_replicate_0():
    tops = ["trending_up"] * 50
    recs = _run(tops, tops)
    d = decide(recs)
    assert [c["state"] for c in d["canary_baseline_rep0"]] == [r["state"] for r in recs[:20]]


def test_invalid_response_is_excluded_from_pairs_and_flagged():
    recs = _run(["trending_up"] * 50, ["trending_up"] * 50)
    recs[60] = _rec(recs[60]["state"], 1, "trending_up", valid=False)
    d = decide(recs)
    assert d["all_50"]["n_pairs"] == 49
    assert d["n_valid"] == 99 and d["needs_ruling"]


def test_argmax_tie_is_flagged_for_ruling():
    recs = _run(["trending_up"] * 50, ["trending_up"] * 50)
    recs[0]["validity"]["probabilities"] = {c: 0.25 for c in CLASSES}
    assert decide(recs)["argmax_ties"] == [recs[0]["state"]]
    assert decide(recs)["needs_ruling"]


def test_decide_has_no_pass_fail_result():
    d = decide(_run(["trending_up"] * 50, ["disorderly"] * 50))
    assert "result" not in d and d["all_50"]["argmax_agreements"] == 0


def test_frozen_d5_pool_verifies_against_its_population():
    elig = l3._artifact("eligibility_step1.json")
    draws = l3._artifact("draws_step2.json")
    c = verify_pool(elig, draws)
    assert (c["all_states"], c["excluded"], c["population"]) == (6850, 1069, 5781)
    assert c["output_disjoint_s0_l2_dev"] and c["d6_is_first_20"]


def test_pool_verification_refuses_an_output_overlapping_l2():
    elig = l3._artifact("eligibility_step1.json")
    draws = json.loads(json.dumps(l3._artifact("draws_step2.json")))
    draws["draws"]["d5_l3"]["output"][0] = draws["draws"]["d4t_l2_timestamps"]["output"][0]
    with pytest.raises(RuntimeError, match="D5 pool verification failed"):
        verify_pool(elig, draws)
