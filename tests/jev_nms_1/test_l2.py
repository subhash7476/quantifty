from scipy.stats import binomtest

from scripts.jev_nms_1.l2 import decide
from scripts.jev_nms_1.transport import validate_response


def _rec(year, choice, probs=None, valid=True):
    probs = probs or {y: (0.8 if y == choice else 0.1) for y in ("2023", "2024", "2025")}
    return {"state": f"{year}-06-03|10:00", "true_year": year,
            "validity": {"valid": valid, "choice": choice, "probabilities": probs}}


def _records(correct):
    recs = []
    for i in range(90):
        y = ("2023", "2024", "2025")[i // 30]
        wrong = {"2023": "2024", "2024": "2025", "2025": "2023"}[y]
        recs.append(_rec(y, y if i < correct else wrong))
    return recs


def test_one_sided_binomial_against_one_third():
    d = decide(_records(30), 1 / 3, 0.01)
    assert d["successes"] == 30 and d["p_value"] == binomtest(30, 90, 1 / 3, alternative="greater").pvalue
    assert d["result"] == "PASS"
    assert decide(_records(45), 1 / 3, 0.01)["result"] == "FAIL"


def test_invalid_responses_ties_or_choice_argmax_disagreement_need_a_ruling():
    recs = _records(30)
    recs[0] = _rec("2023", "2023", valid=False)
    assert decide(recs, 1 / 3, 0.01)["needs_ruling"]
    recs = _records(30)
    recs[0] = _rec("2023", "2023", {"2023": 0.4, "2024": 0.4, "2025": 0.2})
    assert decide(recs, 1 / 3, 0.01)["needs_ruling"]
    recs = _records(30)
    recs[0] = _rec("2023", "2023", {"2023": 0.2, "2024": 0.7, "2025": 0.1})
    assert decide(recs, 1 / 3, 0.01)["needs_ruling"]


def test_year_classes_validate():
    import json
    body = json.dumps({"model": "jev-1.13.0", "answers": {"snapshot_year": {
        "choice": "2024", "probabilities": {"2023": 0.2, "2024": 0.5, "2025": 0.3}}}}).encode()
    assert validate_response(body, "snapshot_year", ("2023", "2024", "2025"))["valid"]
    assert not validate_response(body, "snapshot_year")["valid"]
