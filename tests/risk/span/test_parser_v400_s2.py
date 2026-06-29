"""MM9.5-S2 — ParserV400 completeness test suite (Blocks H-L)."""

import hashlib
from datetime import date
from dataclasses import FrozenInstanceError

import pytest

from core.risk.span.span_snapshot import (
    SpanSnapshot,
    SpanRiskArray,
    SpanFutureContract,
    SpanOptionSeries,
    SpanOptionContract,
    UnsupportedSpanSchema,
)
from core.risk.span.parser_v400 import parse_span_xml, SEGMENT_FO
from core.risk.span.span_parser import ParserRegistry

# --------------------------------------------------------------------------- #
# Synthetic PC-SPAN 4.00 XML fixture (S2 extended)
# --------------------------------------------------------------------------- #

S2_FIXTURE_XML = """<?xml version="1.0"?>
<spanFile>
<fileFormat>4.00</fileFormat>
<created>202601010900</created>
<definitions/>
<pointInTime>
<date>20260101</date>
<isSetl>0</isSetl>
<clearingOrg>
<ec>NSCCL</ec>
<pointDef>
<scanPointDef>
<point>1</point><pairedPoint>2</pairedPoint>
<priceScanDef><numerator>0</numerator><denominator>1</denominator></priceScanDef>
<volScanDef><numerator>1</numerator><denominator>1</denominator></volScanDef>
<weight>1.0</weight>
</scanPointDef>
<scanPointDef>
<point>2</point><pairedPoint>1</pairedPoint>
<priceScanDef><numerator>0</numerator><denominator>1</denominator></priceScanDef>
<volScanDef><numerator>-1</numerator><denominator>1</denominator></volScanDef>
<weight>1.0</weight>
</scanPointDef>
<scanPointDef>
<point>3</point><pairedPoint>4</pairedPoint>
<priceScanDef><numerator>1</numerator><denominator>3</denominator></priceScanDef>
<volScanDef><numerator>1</numerator><denominator>1</denominator></volScanDef>
<weight>1.0</weight>
</scanPointDef>
<scanPointDef>
<point>4</point><pairedPoint>3</pairedPoint>
<priceScanDef><numerator>1</numerator><denominator>3</denominator></priceScanDef>
<volScanDef><numerator>-1</numerator><denominator>1</denominator></volScanDef>
<weight>1.0</weight>
</scanPointDef>
<scanPointDef>
<point>5</point><pairedPoint>6</pairedPoint>
<priceScanDef><numerator>-1</numerator><denominator>3</denominator></priceScanDef>
<volScanDef><numerator>1</numerator><denominator>1</denominator></volScanDef>
<weight>1.0</weight>
</scanPointDef>
<scanPointDef>
<point>6</point><pairedPoint>5</pairedPoint>
<priceScanDef><numerator>-1</numerator><denominator>3</denominator></priceScanDef>
<volScanDef><numerator>-1</numerator><denominator>1</denominator></volScanDef>
<weight>1.0</weight>
</scanPointDef>
<scanPointDef>
<point>7</point><pairedPoint>8</pairedPoint>
<priceScanDef><numerator>2</numerator><denominator>3</denominator></priceScanDef>
<volScanDef><numerator>1</numerator><denominator>1</denominator></volScanDef>
<weight>1.0</weight>
</scanPointDef>
<scanPointDef>
<point>8</point><pairedPoint>7</pairedPoint>
<priceScanDef><numerator>2</numerator><denominator>3</denominator></priceScanDef>
<volScanDef><numerator>-1</numerator><denominator>1</denominator></volScanDef>
<weight>1.0</weight>
</scanPointDef>
<scanPointDef>
<point>9</point><pairedPoint>10</pairedPoint>
<priceScanDef><numerator>-2</numerator><denominator>3</denominator></priceScanDef>
<volScanDef><numerator>1</numerator><denominator>1</denominator></volScanDef>
<weight>1.0</weight>
</scanPointDef>
<scanPointDef>
<point>10</point><pairedPoint>9</pairedPoint>
<priceScanDef><numerator>-2</numerator><denominator>3</denominator></priceScanDef>
<volScanDef><numerator>-1</numerator><denominator>1</denominator></volScanDef>
<weight>1.0</weight>
</scanPointDef>
<scanPointDef>
<point>11</point><pairedPoint>12</pairedPoint>
<priceScanDef><numerator>1</numerator><denominator>1</denominator></priceScanDef>
<volScanDef><numerator>1</numerator><denominator>1</denominator></volScanDef>
<weight>1.0</weight>
</scanPointDef>
<scanPointDef>
<point>12</point><pairedPoint>11</pairedPoint>
<priceScanDef><numerator>1</numerator><denominator>1</denominator></priceScanDef>
<volScanDef><numerator>-1</numerator><denominator>1</denominator></volScanDef>
<weight>1.0</weight>
</scanPointDef>
<scanPointDef>
<point>13</point><pairedPoint>14</pairedPoint>
<priceScanDef><numerator>-1</numerator><denominator>1</denominator></priceScanDef>
<volScanDef><numerator>1</numerator><denominator>1</denominator></volScanDef>
<weight>1.0</weight>
</scanPointDef>
<scanPointDef>
<point>14</point><pairedPoint>13</pairedPoint>
<priceScanDef><numerator>-1</numerator><denominator>1</denominator></priceScanDef>
<volScanDef><numerator>-1</numerator><denominator>1</denominator></volScanDef>
<weight>1.0</weight>
</scanPointDef>
<scanPointDef>
<point>15</point><pairedPoint>15</pairedPoint>
<priceScanDef><numerator>3</numerator><denominator>1</denominator></priceScanDef>
<volScanDef><numerator>0</numerator><denominator>1</denominator></volScanDef>
<weight>0.3</weight>
</scanPointDef>
<scanPointDef>
<point>16</point><pairedPoint>16</pairedPoint>
<priceScanDef><numerator>-3</numerator><denominator>1</denominator></priceScanDef>
<volScanDef><numerator>0</numerator><denominator>1</denominator></volScanDef>
<weight>0.3</weight>
</scanPointDef>
</pointDef>
<ccDef>
<cc>NIFTY</cc>
<name>NIFTY</name>
<somTiers>
<tier><tn>0</tn><rate><val>0</val></rate></tier>
</somTiers>
<dSpread>
<spread>1</spread><rate><val>425.0</val></rate>
</dSpread>
<dSpread>
<spread>2</spread><rate><val>500.0</val></rate>
</dSpread>
</ccDef>
<ccDef>
<cc>WIDGET</cc>
<name>WIDGET</name>
<somTiers>
<tier><tn>0</tn><rate><val>15.0</val></rate></tier>
</somTiers>
</ccDef>
<exchange>
<exch>NSE</exch>
<phyPf>
<pfId>1</pfId><pfCode>NIFTY</pfCode><name>NIFTY</name>
<cvf>1.00</cvf>
</phyPf>
<phyPf>
<pfId>2</pfId><pfCode>WIDGET</pfCode><name>WIDGET</name>
<cvf>1.00</cvf>
</phyPf>
<futPf>
<pfId>3</pfId><pfCode>NIFTY</pfCode><name>NIFTY</name>
<fut>
<cId>1</cId><pe>20260130</pe>
<scanRate><priceScan>2234.01</priceScan><volScan>0.04</volScan></scanRate>
<intrRate><val>0.07</val></intrRate>
<ra>
<a>1000.0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a>
<a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a>
</ra>
</fut>
<fut>
<cId>2</cId><pe>20260227</pe>
<scanRate><priceScan>2234.01</priceScan><volScan>0.04</volScan></scanRate>
<intrRate><val>0.07</val></intrRate>
<ra>
<a>800.0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a>
<a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a>
</ra>
</fut>
</futPf>
<futPf>
<pfId>4</pfId><pfCode>WIDGET</pfCode><name>WIDGET</name>
<fut>
<cId>1</cId><pe>20260130</pe>
<scanRate><priceScan>1100.0</priceScan><volScan>0.02</volScan></scanRate>
<ra>
<a>1100.0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a>
<a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>900.0</a><a>2000.0</a>
</ra>
</fut>
</futPf>
<oopPf>
<pfId>5</pfId><pfCode>NIFTY</pfCode><name>NIFTY</name>
<series>
<pe>20260130</pe>
<v>0.40</v>
<t>0.016438</t>
<scanRate><priceScan>2234.01</priceScan><volScan>0.04</volScan></scanRate>
<intrRate><val>0.07</val></intrRate>
<opt>
<k>24000.00</k><o>C</o><p>260.05</p><d>0.8453</d><v>0.4029</v>
<ra>
<a>100.0</a><a>200.0</a><a>50.0</a><a>60.0</a><a>70.0</a><a>80.0</a>
<a>90.0</a><a>100.0</a><a>110.0</a><a>120.0</a><a>130.0</a><a>140.0</a>
<a>150.0</a><a>160.0</a><a>170.0</a><a>180.0</a>
</ra>
</opt>
<opt>
<k>24100.00</k><o>P</o><p>180.30</p><d>-0.5230</d><v>0.3850</v>
<ra>
<a>100.0</a><a>200.0</a><a>50.0</a><a>60.0</a><a>70.0</a><a>80.0</a>
<a>90.0</a><a>100.0</a><a>110.0</a><a>120.0</a><a>130.0</a><a>140.0</a>
<a>150.0</a><a>160.0</a><a>170.0</a><a>180.0</a>
</ra>
</opt>
<opt>
<k>24200.00</k><o>C</o><p>140.10</p><d>0.3510</d><v>0.3700</v>
<ra>
<a>100.0</a><a>200.0</a><a>50.0</a><a>60.0</a><a>70.0</a><a>80.0</a>
<a>90.0</a><a>100.0</a><a>110.0</a><a>120.0</a><a>130.0</a><a>140.0</a>
<a>150.0</a><a>160.0</a><a>170.0</a><a>180.0</a>
</ra>
</opt>
</series>
</oopPf>
</exchange>
</clearingOrg>
</pointInTime>
</spanFile>
"""

S2_FIXTURE_BYTES = S2_FIXTURE_XML.encode("latin-1")


# --------------------------------------------------------------------------- #
# Block H — New risk_metrics keys
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def s2_snapshot():
    return parse_span_xml(S2_FIXTURE_BYTES)


def test_h1_price_scan_range(s2_snapshot):
    assert s2_snapshot.risk_arrays["NIFTY"].risk_metrics["price_scan_range"] == 2234.01


def test_h2_vol_scan_range(s2_snapshot):
    assert s2_snapshot.risk_arrays["NIFTY"].risk_metrics["vol_scan_range"] == 0.04


def test_h3_cvf_nifty(s2_snapshot):
    assert s2_snapshot.risk_arrays["NIFTY"].risk_metrics["cvf"] == 1.0


def test_h3_cvf_widget(s2_snapshot):
    assert s2_snapshot.risk_arrays["WIDGET"].risk_metrics["cvf"] == 1.0


def test_h4_cvf_defaults_to_one():
    xml = S2_FIXTURE_XML.replace("<cvf>1.00</cvf>", "")
    result = parse_span_xml(xml.encode("latin-1"))
    assert result.risk_arrays["NIFTY"].risk_metrics["cvf"] == 1.0


def test_h5_intra_spread_correct(s2_snapshot):
    assert s2_snapshot.risk_arrays["NIFTY"].risk_metrics["intra_spread_charge_rs"] == 425.0


def test_h6_intra_spread_zero_when_absent(s2_snapshot):
    assert s2_snapshot.risk_arrays["WIDGET"].risk_metrics["intra_spread_charge_rs"] == 0.0


def test_h7_intra_spread_uses_minimum():
    xml = S2_FIXTURE_XML.replace(
        "<rate><val>425.0</val></rate>",
        "<rate><val>600.0</val></rate>",
        1,
    )
    result = parse_span_xml(xml.encode("latin-1"))
    assert result.risk_arrays["NIFTY"].risk_metrics["intra_spread_charge_rs"] == 500.0


def test_h8_risk_free_rate_correct(s2_snapshot):
    assert s2_snapshot.risk_arrays["NIFTY"].risk_metrics["risk_free_rate"] == 0.07


def test_h9_risk_free_rate_defaults_to_zero():
    xml = S2_FIXTURE_XML.replace("<intrRate><val>0.07</val></intrRate>", "")
    result = parse_span_xml(xml.encode("latin-1"))
    assert result.risk_arrays["NIFTY"].risk_metrics["risk_free_rate"] == 0.0


def test_h10_seven_metric_keys_always_present(s2_snapshot):
    expected = {"scan_risk", "short_option_minimum", "price_scan_range",
                "vol_scan_range", "cvf", "intra_spread_charge_rs", "risk_free_rate"}
    for ra in s2_snapshot.risk_arrays.values():
        assert set(ra.risk_metrics.keys()) == expected


def test_h11_s1_keys_unchanged(s2_snapshot):
    assert s2_snapshot.risk_arrays["NIFTY"].risk_metrics["scan_risk"] == 1000.0
    assert s2_snapshot.risk_arrays["NIFTY"].risk_metrics["short_option_minimum"] == 0.0
    assert s2_snapshot.risk_arrays["WIDGET"].risk_metrics["scan_risk"] == 1100.0


# --------------------------------------------------------------------------- #
# Block I — Scenario grid in metadata
# --------------------------------------------------------------------------- #

def test_i1_scan_scenarios_key_present(s2_snapshot):
    assert "scan_scenarios" in s2_snapshot.metadata


def test_i2_scan_scenarios_16_entries(s2_snapshot):
    assert len(s2_snapshot.metadata["scan_scenarios"]) == 16


def test_i3_scenario_dict_has_required_keys(s2_snapshot):
    for sc in s2_snapshot.metadata["scan_scenarios"]:
        for k in ("point", "paired_point", "price_mult", "vol_mult", "weight"):
            assert k in sc, f"Missing key {k} in scenario {sc}"


def test_i4_extreme_scenario_weights_03(s2_snapshot):
    assert s2_snapshot.metadata["scan_scenarios"][14]["weight"] == 0.3
    assert s2_snapshot.metadata["scan_scenarios"][15]["weight"] == 0.3


def test_i5_normal_scenario_weight_10(s2_snapshot):
    assert s2_snapshot.metadata["scan_scenarios"][0]["weight"] == 1.0


def test_i6_scan_scenarios_empty_when_point_def_absent():
    xml = S2_FIXTURE_XML.replace("<pointDef>", "<absent>")
    xml = xml.replace("</pointDef>", "</absent>")
    result = parse_span_xml(xml.encode("latin-1"))
    assert result.metadata["scan_scenarios"] == []


# --------------------------------------------------------------------------- #
# Block J — SpanFutureContract
# --------------------------------------------------------------------------- #

def test_j1_futures_field_present(s2_snapshot):
    assert hasattr(s2_snapshot, "futures")


def test_j2_futures_keyed_by_symbol(s2_snapshot):
    assert "NIFTY" in s2_snapshot.futures


def test_j3_correct_futures_count(s2_snapshot):
    assert len(s2_snapshot.futures["NIFTY"]) == 2
    assert len(s2_snapshot.futures["WIDGET"]) == 1


def test_j4_futures_sorted_nearest_first(s2_snapshot):
    futs = s2_snapshot.futures["NIFTY"]
    assert futs[0].expiry < futs[1].expiry
    assert futs[0].expiry == date(2026, 1, 30)


def test_j5_future_contract_fields_populated(s2_snapshot):
    fut = s2_snapshot.futures["NIFTY"][0]
    assert fut.symbol == "NIFTY"
    assert fut.expiry == date(2026, 1, 30)
    assert fut.price_scan_range == 2234.01
    assert fut.vol_scan_range == 0.04
    assert fut.risk_free_rate == 0.07


def test_j6_future_contract_ra_has_16_values(s2_snapshot):
    assert len(s2_snapshot.futures["NIFTY"][0].ra) == 16


def test_j7_future_ra_values_match_fixture(s2_snapshot):
    assert s2_snapshot.futures["NIFTY"][0].ra[0] == 1000.0


def test_j8_future_contract_is_frozen(s2_snapshot):
    with pytest.raises(FrozenInstanceError):
        s2_snapshot.futures["NIFTY"][0].expiry = date(2026, 1, 1)


def test_j9_symbol_no_fut_pf_has_empty_futures():
    xml = S2_FIXTURE_XML.replace(
        "<ccDef>\n<cc>WIDGET",
        "<ccDef>\n<cc>ORPHAN</cc>\n<name>ORPHAN</name>\n<somTiers><tier><rate><val>0</val></rate></tier></somTiers>\n</ccDef>\n<ccDef>\n<cc>WIDGET",
        1,
    )
    result = parse_span_xml(xml.encode("latin-1"))
    assert result.futures.get("ORPHAN", ()) == ()


def test_j10_future_contract_pe_zeros_excluded():
    xml = S2_FIXTURE_XML.replace(
        "<pe>20260130</pe>",
        "<pe>00000000</pe>",
        1,
    )
    result = parse_span_xml(xml.encode("latin-1"))
    assert len(result.futures.get("NIFTY", ())) == 1


# --------------------------------------------------------------------------- #
# Block K — SpanOptionSeries
# --------------------------------------------------------------------------- #

def test_k1_option_series_field_present(s2_snapshot):
    assert hasattr(s2_snapshot, "option_series")


def test_k2_nifty_option_series_count(s2_snapshot):
    assert len(s2_snapshot.option_series["NIFTY"]) == 1


def test_k3_option_series_fields_correct(s2_snapshot):
    s = s2_snapshot.option_series["NIFTY"][0]
    assert s.symbol == "NIFTY"
    assert s.expiry == date(2026, 1, 30)
    assert s.price_scan_range == 2234.01
    assert s.vol == pytest.approx(0.40, abs=0.001)


def test_k4_symbol_no_oop_pf_has_empty_series(s2_snapshot):
    assert s2_snapshot.option_series.get("WIDGET", ()) == ()


def test_k5_option_series_is_frozen(s2_snapshot):
    with pytest.raises(FrozenInstanceError):
        s2_snapshot.option_series["NIFTY"][0].vol = 0.99


# --------------------------------------------------------------------------- #
# Block L — SpanOptionContract
# --------------------------------------------------------------------------- #

def test_l1_option_contracts_field_present(s2_snapshot):
    assert hasattr(s2_snapshot, "option_contracts")


def test_l2_nifty_option_contract_count(s2_snapshot):
    assert len(s2_snapshot.option_contracts["NIFTY"]) == 3


def test_l3_option_contract_fields_populated(s2_snapshot):
    c = s2_snapshot.option_contracts["NIFTY"][0]
    assert c.symbol == "NIFTY"
    assert c.expiry == date(2026, 1, 30)
    assert c.strike == 24000.00
    assert c.option_type == "C"
    assert c.price == 260.05
    assert c.delta == pytest.approx(0.8453, abs=0.0001)
    assert c.implied_vol == pytest.approx(0.4029, abs=0.0001)


def test_l4_option_contract_ra_has_16_values(s2_snapshot):
    assert len(s2_snapshot.option_contracts["NIFTY"][0].ra) == 16


def test_l5_option_contract_ra_values_match_fixture(s2_snapshot):
    c = s2_snapshot.option_contracts["NIFTY"][0]
    assert c.ra[0] == 100.0
    assert c.ra[15] == 180.0


def test_l6_option_contract_invalid_ra_raises():
    xml = S2_FIXTURE_XML.replace(
        "<a>100.0</a><a>200.0</a><a>50.0</a>",
        "<a>100.0</a><a>200.0</a>",
        1,
    )
    with pytest.raises(UnsupportedSpanSchema) as exc:
        parse_span_xml(xml.encode("latin-1"))
    assert "Expected 16 RA scenarios" in str(exc.value)


def test_l7_option_contract_is_frozen(s2_snapshot):
    with pytest.raises(FrozenInstanceError):
        s2_snapshot.option_contracts["NIFTY"][0].strike = 0.0


def test_l8_implied_vol_absent_defaults_to_zero():
    xml = S2_FIXTURE_XML.replace("<v>0.4029</v>", "")
    result = parse_span_xml(xml.encode("latin-1"))
    c = result.option_contracts["NIFTY"][0]
    assert c.implied_vol == 0.0


def test_l9_option_contracts_count_matches_metadata(s2_snapshot):
    total = sum(len(v) for v in s2_snapshot.option_contracts.values())
    assert total == s2_snapshot.metadata["option_count"]


# --------------------------------------------------------------------------- #
# S1 backward compatibility
# --------------------------------------------------------------------------- #

def test_s2_backwards_compatible_construction():
    snap = SpanSnapshot(
        snapshot_date=date(2026, 1, 1),
        schema_version="4.00",
        exchange="NSE",
        segment="FO",
        file_hash="abc",
        is_settlement=False,
        risk_arrays={},
        metadata={},
    )
    assert snap.futures == {}
    assert snap.option_series == {}
    assert snap.option_contracts == {}


def test_s2_equality_with_defaults():
    a = SpanSnapshot(
        snapshot_date=date(2026, 1, 1),
        schema_version="4.00",
        exchange="NSE",
        segment="FO",
        file_hash="abc",
        is_settlement=False,
        risk_arrays={},
        metadata={},
    )
    b = SpanSnapshot(
        snapshot_date=date(2026, 1, 1),
        schema_version="4.00",
        exchange="NSE",
        segment="FO",
        file_hash="abc",
        is_settlement=False,
        risk_arrays={},
        metadata={},
    )
    assert a == b
