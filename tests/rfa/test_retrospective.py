from scripts.rfa.retrospective import assess


def _by_name(rows):
    return {r["name"]: r for r in rows}


def test_gate_fires_on_c5_c4_and_f1():
    rows = _by_name(assess())
    for name in ("C5", "C4", "F1_TRAIN"):
        assert rows[name]["decision"] == "ABANDON", name


def test_c2_as_recorded_in_psb2_does_not_fire():
    rows = _by_name(assess())
    assert rows["C2_PSB2"]["decision"] == "PROCEED"
    assert rows["C2_PSB2"]["max_power"] > 0.80


def test_c2_fires_only_on_extended_history_reestimate():
    rows = _by_name(assess())
    assert rows["C2_PHASE0_5"]["decision"] == "ABANDON"
    # Pinned to V2's recorded power (0.6563) so the unfilled placeholder
    # Case(0.0, 0.0, 0) FAILS instead of passing trivially at power 0.0.
    assert 0.60 < rows["C2_PHASE0_5"]["max_power"] < 0.70
    assert rows["C2_PHASE0_5"]["n"] > 0


def test_f1_dispersion_is_flagged_approximate():
    rows = _by_name(assess())
    assert rows["F1_TRAIN"]["sd_is_approximate"] is True
    assert rows["C5"]["sd_is_approximate"] is False
