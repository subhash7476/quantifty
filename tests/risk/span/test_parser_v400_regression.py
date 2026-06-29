"""MM9.5-S2 — Block M: Regression against real NSE SPAN archive.

These tests are pinned to:
    reference/span/nsccl.20260625.i1/nsccl.20260625.i01.spn

If the reference file is replaced, ALL hardcoded assertion values MUST be
revalidated against the new file.  The test is skipped when the reference
file is absent from the filesystem.
"""

import pathlib

import pytest

SPAN_FILE = (
    pathlib.Path(__file__).resolve().parents[3]
    / "reference"
    / "span"
    / "nsccl.20260625.i1"
    / "nsccl.20260625.i01.spn"
)

pytestmark = pytest.mark.skipif(
    not SPAN_FILE.exists(),
    reason="Real SPAN reference file not present",
)


@pytest.fixture(scope="module")
def real_snapshot():
    from core.risk.span.parser_v400 import parse_span_xml
    return parse_span_xml(SPAN_FILE.read_bytes())


@pytest.fixture(scope="module")
def raw_bytes():
    return SPAN_FILE.read_bytes()


# --------------------------------------------------------------------------- #
# Smoke
# --------------------------------------------------------------------------- #

def test_m1_real_file_parses_without_exception(real_snapshot):
    assert real_snapshot is not None


# --------------------------------------------------------------------------- #
# scan_risk reference values
# --------------------------------------------------------------------------- #

def test_m2_nifty_scan_risk(real_snapshot):
    assert real_snapshot.risk_arrays["NIFTY"].risk_metrics["scan_risk"] == pytest.approx(2244.36, abs=0.01)


def test_m3_banknifty_scan_risk(real_snapshot):
    assert real_snapshot.risk_arrays["BANKNIFTY"].risk_metrics["scan_risk"] == pytest.approx(5513.40, abs=0.01)


# --------------------------------------------------------------------------- #
# Metadata counts
# --------------------------------------------------------------------------- #

def test_m4_underlying_count(real_snapshot):
    assert real_snapshot.metadata["underlying_count"] == 239


def test_m5_option_count(real_snapshot):
    assert real_snapshot.metadata["option_count"] == 158713


# --------------------------------------------------------------------------- #
# price_scan_range
# --------------------------------------------------------------------------- #

def test_m6_nifty_price_scan_range(real_snapshot):
    assert real_snapshot.risk_arrays["NIFTY"].risk_metrics["price_scan_range"] == pytest.approx(2234.01, abs=0.01)


def test_m7_banknifty_price_scan_range(real_snapshot):
    assert real_snapshot.risk_arrays["BANKNIFTY"].risk_metrics["price_scan_range"] == pytest.approx(5488.30, abs=0.01)


# --------------------------------------------------------------------------- #
# Spread charges
# --------------------------------------------------------------------------- #

def test_m8_nifty_intra_spread_charge(real_snapshot):
    assert real_snapshot.risk_arrays["NIFTY"].risk_metrics["intra_spread_charge_rs"] == pytest.approx(425.0, abs=0.01)


def test_m9_banknifty_intra_spread_charge(real_snapshot):
    assert real_snapshot.risk_arrays["BANKNIFTY"].risk_metrics["intra_spread_charge_rs"] == pytest.approx(1029.0, abs=0.01)


# --------------------------------------------------------------------------- #
# cvf
# --------------------------------------------------------------------------- #

def test_m10_cvf_is_one_for_all_underlyings(real_snapshot):
    for symbol, ra in real_snapshot.risk_arrays.items():
        assert ra.risk_metrics["cvf"] == 1.0, f"cvf != 1.0 for {symbol}"


# --------------------------------------------------------------------------- #
# risk_free_rate
# --------------------------------------------------------------------------- #

def test_m11_nifty_risk_free_rate(real_snapshot):
    assert real_snapshot.risk_arrays["NIFTY"].risk_metrics["risk_free_rate"] == pytest.approx(0.07, abs=0.001)


# --------------------------------------------------------------------------- #
# Scenario grid
# --------------------------------------------------------------------------- #

def test_m12_scan_scenarios_has_16_entries(real_snapshot):
    assert len(real_snapshot.metadata["scan_scenarios"]) == 16


# --------------------------------------------------------------------------- #
# Futures contracts
# --------------------------------------------------------------------------- #

def test_m13_nifty_has_futures_contracts(real_snapshot):
    assert len(real_snapshot.futures.get("NIFTY", ())) >= 1


def test_m14_nifty_nearest_futures_ra12_matches_reference(real_snapshot):
    assert real_snapshot.futures["NIFTY"][0].ra[12] == pytest.approx(2244.36, abs=0.01)


# --------------------------------------------------------------------------- #
# Option completeness
# --------------------------------------------------------------------------- #

def test_m15_nifty_has_option_series(real_snapshot):
    assert len(real_snapshot.option_series.get("NIFTY", ())) >= 1


def test_m16_option_contracts_count_equals_metadata_option_count(real_snapshot):
    total = sum(len(v) for v in real_snapshot.option_contracts.values())
    assert total == real_snapshot.metadata["option_count"]


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #

def test_m17_parser_is_deterministic(raw_bytes):
    from core.risk.span.parser_v400 import parse_span_xml
    a = parse_span_xml(raw_bytes)
    b = parse_span_xml(raw_bytes)
    assert a == b
