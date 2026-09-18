import random
from datetime import date, timedelta

from scripts.jev_nms_1.draws import SLOTS, make_draws, population_hash


def _elig():
    def recs(lo, hi, drop=()):
        out, d = [], lo
        while d <= hi:
            if d.weekday() < 5:
                ok = d.isoformat() not in drop
                out.append({"date": d.isoformat(), "eligible": ok, "otherwise_eligible": ok})
            d += timedelta(days=1)
        return out
    return {"sessions": {"d_fit": recs(date(2023, 3, 1), date(2024, 12, 31), {"2023-03-01"}),
                         "d_eval": recs(date(2025, 1, 1), date(2025, 12, 31))}}


def test_draw_sizes_and_derived_prefixes():
    d = make_draws(_elig())
    assert len(d["d1_dev"]["output"]) == 100 and d["d2_dev_secondary"]["output"] == d["d1_dev"]["output"][:30]
    assert len(d["d3_s0"]["output"]) == 5 and len(d["d3_s0"]["states"]) == 10
    assert all(len(d[f"d4_l2_{y}"]["output"]) == 30 for y in (2023, 2024, 2025))
    assert len(d["d4t_l2_timestamps"]["output"]) == 90
    assert len(d["d5_l3"]["output"]) == 50 and d["d6_canaries"]["output"] == d["d5_l3"]["output"][:20]


def test_each_draw_is_its_own_seed_42_stream_over_the_sorted_population():
    elig = _elig()
    pop = sorted(r["date"] for r in elig["sessions"]["d_eval"] if r["otherwise_eligible"])
    assert make_draws(elig)["d1_dev"]["output"] == random.Random(42).sample(pop, 100)


def test_l2_years_stay_inside_their_year_and_the_dev_sets():
    d = make_draws(_elig())
    for y in (2023, 2024, 2025):
        assert all(x.startswith(f"{y}-") for x in d[f"d4_l2_{y}"]["output"])
    assert "2023-03-01" not in d["d4_l2_2023"]["output"]  # ineligible
    assert min(d["d4_l2_2023"]["output"]) >= "2023-03-01"


def test_l3_excludes_s0_l2_and_development_states():
    d = make_draws(_elig())
    l3 = set(d["d5_l3"]["output"])
    dev = {f"{x}|{s}" for x in d["d1_dev"]["output"] for s in SLOTS}
    assert not l3 & set(d["d3_s0"]["states"])
    assert not l3 & set(d["d4t_l2_timestamps"]["output"])
    assert not l3 & dev


def test_draws_are_deterministic_and_population_hash_is_order_sensitive():
    assert make_draws(_elig()) == make_draws(_elig())
    assert population_hash(["a", "b"]) != population_hash(["b", "a"])
