import dataclasses
import hashlib
import pytest
from governance.rfa.declaration import Declaration, validate, digest_of


def _valid(**overrides):
    base = dict(
        name="TESTC1",
        methodology_version="1.0.0",
        delta_lo=0.02, delta_hi=0.05,
        sd_lo=0.15, sd_hi=0.25,
        delta_provenance="Jegadeesh & Titman (1993) cross-sectional momentum magnitudes.",
        sd_provenance="Dispersion floor from first-principles breadth argument, N=200 names.",
        prior_exposure="Operator has read PSB-1 C5 and PSB-2 C2/C4 reports.",
        n_available=130,
        cadence="monthly",
        window="2012-01-01 to 2022-12-30",
        test_type="two_sided",
        metric="rank_ic",
    )
    base.update(overrides)
    return Declaration(**base)


def test_valid_declaration_passes():
    validate(_valid())


def test_declaration_is_immutable():
    d = _valid()
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.delta_hi = 0.99


@pytest.mark.parametrize("field", ["delta_provenance", "sd_provenance", "prior_exposure"])
def test_empty_provenance_rejected(field):
    with pytest.raises(ValueError, match=field):
        validate(_valid(**{field: "   "}))


def test_inverted_bands_rejected():
    with pytest.raises(ValueError, match="delta_lo"):
        validate(_valid(delta_lo=0.09, delta_hi=0.01))
    with pytest.raises(ValueError, match="sd_lo"):
        validate(_valid(sd_lo=0.9, sd_hi=0.1))


def test_nonpositive_sd_rejected():
    with pytest.raises(ValueError, match="sd_lo"):
        validate(_valid(sd_lo=0.0))


def test_insufficient_formations_rejected():
    with pytest.raises(ValueError, match="n_available"):
        validate(_valid(n_available=1))


def test_unknown_test_type_rejected():
    with pytest.raises(ValueError, match="test_type"):
        validate(_valid(test_type="bayesian"))


def test_unknown_metric_rejected():
    with pytest.raises(ValueError, match="metric"):
        validate(_valid(metric="sharpe"))


def test_digest_covers_entire_file(tmp_path):
    p = tmp_path / "decl.py"
    p.write_bytes(b"DECLARATION = 1\n# trailing content after any notional seal\n")
    expected = hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest_of(str(p)) == expected


def test_digest_changes_when_trailing_bytes_change(tmp_path):
    p = tmp_path / "decl.py"
    p.write_bytes(b"DECLARATION = 1\n")
    first = digest_of(str(p))
    p.write_bytes(b"DECLARATION = 1\n# appended\n")
    assert digest_of(str(p)) != first
