"""MM9.5-S1 — ParserV400 full TDD test suite (Blocks A–F)."""

import hashlib
from datetime import date
from dataclasses import FrozenInstanceError

import pytest

from core.risk.span.span_snapshot import (
    SpanSnapshot,
    SpanRiskArray,
    UnsupportedSpanSchema,
)
from core.risk.span.span_parser import ParserRegistry
from core.risk.span.parser_v400 import parse_span_xml, SEGMENT_FO

# --------------------------------------------------------------------------- #
# Synthetic PC-SPAN 4.00 XML fixture
# --------------------------------------------------------------------------- #

FIXTURE_XML = """<?xml version="1.0"?>
<spanFile>
<fileFormat>4.00</fileFormat>
<created>202601010900</created>
<definitions/>
<pointInTime>
<date>20260101</date>
<isSetl>0</isSetl>
<clearingOrg>
<ec>NSCCL</ec>
<ccDef>
<cc>NIFTY</cc>
<name>NIFTY</name>
<somTiers>
<tier>
<tn>0</tn>
<rate><val>0</val></rate>
</tier>
</somTiers>
</ccDef>
<ccDef>
<cc>WIDGET</cc>
<name>WIDGET</name>
<somTiers>
<tier>
<tn>0</tn>
<rate><val>15.0</val></rate>
</tier>
</somTiers>
</ccDef>
<exchange>
<exch>NSE</exch>
<phyPf>
<pfId>1</pfId>
<pfCode>NIFTY</pfCode>
<name>NIFTY</name>
</phyPf>
<phyPf>
<pfId>2</pfId>
<pfCode>WIDGET</pfCode>
<name>WIDGET</name>
</phyPf>
<futPf>
<pfId>3</pfId>
<pfCode>NIFTY</pfCode>
<name>NIFTY</name>
<fut>
<cId>1</cId>
<pe>20260130</pe>
<ra>
<a>1000.0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a>
<a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a>
</ra>
</fut>
<fut>
<cId>2</cId>
<pe>20260227</pe>
<ra>
<a>800.0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a>
<a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a>
</ra>
</fut>
</futPf>
<futPf>
<pfId>4</pfId>
<pfCode>WIDGET</pfCode>
<name>WIDGET</name>
<fut>
<cId>1</cId>
<pe>20260130</pe>
<ra>
<a>1100.0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a>
<a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>900.0</a><a>2000.0</a>
</ra>
</fut>
</futPf>
<oopPf>
<pfId>5</pfId>
<pfCode>NIFTY</pfCode>
<name>NIFTY</name>
<series>
<opt/>
<opt/>
<opt/>
<opt/>
<opt/>
<opt/>
<opt/>
<opt/>
<opt/>
<opt/>
</series>
</oopPf>
</exchange>
</clearingOrg>
</pointInTime>
</spanFile>
"""

FIXTURE_BYTES = FIXTURE_XML.encode("latin-1")


def _all_gain_fixture() -> bytes:
    xml = """<?xml version="1.0"?>
<spanFile>
<fileFormat>4.00</fileFormat>
<created>202601010900</created>
<definitions/>
<pointInTime>
<date>20260101</date>
<isSetl>0</isSetl>
<clearingOrg>
<ec>NSCCL</ec>
<ccDef>
<cc>TEST</cc>
<name>TEST</name>
<somTiers><tier><rate><val>0</val></rate></tier></somTiers>
</ccDef>
<exchange>
<exch>NSE</exch>
<phyPf><pfId>1</pfId><pfCode>TEST</pfCode></phyPf>
<futPf>
<pfId>2</pfId><pfCode>TEST</pfCode>
<fut>
<cId>1</cId>
<pe>20260130</pe>
<ra>
<a>-100.0</a><a>-200.0</a><a>-50.0</a><a>-60.0</a><a>-70.0</a><a>-80.0</a>
<a>-90.0</a><a>-100.0</a><a>-110.0</a><a>-120.0</a><a>-130.0</a><a>-140.0</a>
<a>-150.0</a><a>-160.0</a><a>-170.0</a><a>-180.0</a>
</ra>
</fut>
</futPf>
<oopPf><pfId>3</pfId><pfCode>TEST</pfCode><series/></oopPf>
</exchange>
</clearingOrg>
</pointInTime>
</spanFile>"""
    return xml.encode("latin-1")


def _orphan_fixture() -> bytes:
    """Fixture with ORPHAN ccDef that has no matching futPf."""
    xml = FIXTURE_XML.replace(
        "</ccDef>\n<ccDef>\n<cc>WIDGET",
        "</ccDef>\n<ccDef>\n<cc>ORPHAN</cc>\n<name>ORPHAN</name>\n<somTiers><tier><rate><val>5.0</val></rate></tier></somTiers>\n</ccDef>\n<ccDef>\n<cc>WIDGET",
        1,
    )
    return xml.encode("latin-1")


def _empty_futpf_fixture() -> bytes:
    """Fixture where WIDGET futPf has no <fut> children."""
    xml = FIXTURE_XML.replace(
        "<futPf>\n<pfId>4</pfId>\n<pfCode>WIDGET</pfCode>\n<name>WIDGET</name>\n<fut>\n<cId>1</cId>\n<pe>20260130</pe>\n<ra>\n<a>1100.0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a>\n<a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>900.0</a><a>2000.0</a>\n</ra>\n</fut>\n</futPf>",
        "<futPf>\n<pfId>4</pfId>\n<pfCode>WIDGET</pfCode>\n<name>WIDGET</name>\n</futPf>",
    )
    return xml.encode("latin-1")


# --------------------------------------------------------------------------- #
# Block A — Registry and dispatch
# --------------------------------------------------------------------------- #

def test_a1_parse_span_xml_registered_under_400():
    reg = ParserRegistry()
    reg.register("4.00", parse_span_xml)
    assert reg._parsers.get("4.00") is parse_span_xml


def test_a2_v1_key_absent():
    reg = ParserRegistry()
    assert reg._parsers.get("v1") is None


def test_a3_registry_parse_returns_snapshot():
    reg = ParserRegistry()
    reg.register("4.00", parse_span_xml)
    result = reg.parse("4.00", FIXTURE_BYTES)
    assert isinstance(result, SpanSnapshot)


def test_a4_unknown_version_raises():
    reg = ParserRegistry()
    reg.register("4.00", parse_span_xml)
    with pytest.raises(UnsupportedSpanSchema) as exc:
        reg.parse("9.99", b"ignored")
    assert "9.99" in str(exc.value)


def test_a5_parse_span_csv_deleted():
    with pytest.raises(ImportError):
        from core.risk.span.span_parser import parse_span_csv  # noqa


# --------------------------------------------------------------------------- #
# Block B — Metadata extraction
# --------------------------------------------------------------------------- #

@pytest.fixture
def snapshot():
    return parse_span_xml(FIXTURE_BYTES)


def test_b1_snapshot_date(snapshot):
    assert snapshot.snapshot_date == date(2026, 1, 1)


def test_b2_schema_version(snapshot):
    assert snapshot.schema_version == "4.00"


def test_b3_exchange(snapshot):
    assert snapshot.exchange == "NSE"


def test_b4_segment(snapshot):
    assert snapshot.segment == SEGMENT_FO


def test_b5_file_hash(snapshot):
    expected = hashlib.sha256(FIXTURE_BYTES).hexdigest()
    assert snapshot.file_hash == expected


def test_b6_is_settlement_false_intraday(snapshot):
    assert snapshot.is_settlement is False


def test_b7_is_settlement_true_settlement():
    sett_xml = FIXTURE_XML.replace("<isSetl>0</isSetl>", "<isSetl>1</isSetl>")
    result = parse_span_xml(sett_xml.encode("latin-1"))
    assert result.is_settlement is True


def test_b8_metadata_clearing_org(snapshot):
    assert snapshot.metadata["clearing_org"] == "NSCCL"


def test_b9_metadata_created(snapshot):
    assert snapshot.metadata["created"] == "202601010900"


def test_b10_metadata_underlying_count(snapshot):
    assert snapshot.metadata["underlying_count"] == 2


def test_b11_snapshot_is_frozen(snapshot):
    with pytest.raises(FrozenInstanceError):
        snapshot.risk_arrays = {}


# --------------------------------------------------------------------------- #
# Block C — Futures extraction
# --------------------------------------------------------------------------- #

def test_c1_both_underlyings_in_risk_arrays(snapshot):
    assert "NIFTY" in snapshot.risk_arrays
    assert "WIDGET" in snapshot.risk_arrays


def test_c2_scan_risk_from_nearest_expiry(snapshot):
    # NIFTY nearest expiry is 20260130 → scan_risk = 1000.0
    # Farther expiry is 20260227 → scan_risk = 800.0
    assert snapshot.risk_arrays["NIFTY"].risk_metrics["scan_risk"] == 1000.0


def test_c3_single_contract_underlying(snapshot):
    # WIDGET has one contract → scan_risk = 1100.0
    assert snapshot.risk_arrays["WIDGET"].risk_metrics["scan_risk"] == 1100.0


def test_c4_weight_03_applied():
    """RA[14] (weight 0.3), RA[15] (weight 0.3), RA[0] (weight 1.0) → max = 1100.0"""
    result = parse_span_xml(FIXTURE_BYTES)
    assert result.risk_arrays["WIDGET"].risk_metrics["scan_risk"] == 1100.0


def test_c5_som_zero_for_index(snapshot):
    assert snapshot.risk_arrays["NIFTY"].risk_metrics["short_option_minimum"] == 0.0


def test_c6_som_positive_for_stock(snapshot):
    assert snapshot.risk_arrays["WIDGET"].risk_metrics["short_option_minimum"] == 15.0


def test_c7_both_metrics_always_present(snapshot):
    for sym, ra in snapshot.risk_arrays.items():
        assert "scan_risk" in ra.risk_metrics
        assert "short_option_minimum" in ra.risk_metrics


def test_c8_risk_array_symbol_matches_cc(snapshot):
    assert snapshot.risk_arrays["NIFTY"].symbol == "NIFTY"
    assert snapshot.risk_arrays["WIDGET"].symbol == "WIDGET"


def test_c9_all_gain_ra_returns_zero():
    result = parse_span_xml(_all_gain_fixture())
    assert result.risk_arrays["TEST"].risk_metrics["scan_risk"] == 0.0


def test_c10_futures_contract_count(snapshot):
    assert snapshot.metadata["futures_contract_count"] == 3


# --------------------------------------------------------------------------- #
# Block D — Options extraction
# --------------------------------------------------------------------------- #

def test_d1_option_count(snapshot):
    assert snapshot.metadata["option_count"] == 10


def test_d2_options_not_in_risk_arrays(snapshot):
    assert len(snapshot.risk_arrays) == 2


def test_d3_absent_oop_pf_does_not_raise():
    """WIDGET has no oopPf — parsing completes without error."""
    result = parse_span_xml(FIXTURE_BYTES)
    assert "WIDGET" in result.risk_arrays


# --------------------------------------------------------------------------- #
# Block E — Error handling
# --------------------------------------------------------------------------- #

def test_e1_non_latin1_bytes():
    with pytest.raises(UnsupportedSpanSchema) as exc:
        parse_span_xml(b"\xff\xfe\x00\x01")
    # All byte sequences are valid latin-1; XML parser rejects the content
    assert "Malformed SPAN XML" in str(exc.value)


def test_e2_malformed_xml():
    with pytest.raises(UnsupportedSpanSchema) as exc:
        parse_span_xml(b"this is not xml")
    assert "Malformed SPAN XML" in str(exc.value)


def test_e3_missing_file_format():
    bad = b"""<?xml version="1.0"?><spanFile><created>202601010900</created></spanFile>"""
    with pytest.raises(UnsupportedSpanSchema) as exc:
        parse_span_xml(bad)
    assert "Missing <fileFormat>" in str(exc.value)


def test_e4_wrong_file_format():
    bad = b"""<?xml version="1.0"?><spanFile><fileFormat>5.00</fileFormat></spanFile>"""
    with pytest.raises(UnsupportedSpanSchema) as exc:
        parse_span_xml(bad)
    assert "5.00" in str(exc.value)


def test_e5_missing_point_in_time_date():
    bad = FIXTURE_XML.replace("<date>20260101</date>", "").encode("latin-1")
    with pytest.raises(UnsupportedSpanSchema) as exc:
        parse_span_xml(bad)
    assert "Missing or invalid" in str(exc.value)


def test_e6_ra_fewer_than_16():
    # Build fixture where NIFTY first futures contract has only 1 RA value
    xml = FIXTURE_XML.replace(
        "<a>1000.0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a><a>0</a>",
        "<a>1000.0</a><a>0</a><a>0</a>",
        1,
    )
    with pytest.raises(UnsupportedSpanSchema) as exc:
        parse_span_xml(xml.encode("latin-1"))
    assert "Expected 16 RA scenarios" in str(exc.value)


def test_e7_non_numeric_ra():
    # Replace first NIFTY futures RA value with non-numeric
    xml = FIXTURE_XML.replace(
        "<a>1000.0</a>",
        "<a>N/A</a>",
        1,
    )
    with pytest.raises(UnsupportedSpanSchema) as exc:
        parse_span_xml(xml.encode("latin-1"))
    assert "Invalid RA value" in str(exc.value)


def test_e8_cc_def_no_matching_fut_pf():
    """ORPHAN ccDef has no futPf → scan_risk=0.0, no raise."""
    result = parse_span_xml(_orphan_fixture())
    assert result.risk_arrays["ORPHAN"].risk_metrics["scan_risk"] == 0.0
    assert result.risk_arrays["ORPHAN"].risk_metrics["short_option_minimum"] == 5.0


def test_e9_fut_pf_no_fut_children():
    """WIDGET futPf has no <fut> children → scan_risk=0.0."""
    result = parse_span_xml(_empty_futpf_fixture())
    assert result.risk_arrays["WIDGET"].risk_metrics["scan_risk"] == 0.0


# --------------------------------------------------------------------------- #
# Block F — Regression
# --------------------------------------------------------------------------- #

def test_f1_six_original_fields_unchanged(snapshot):
    assert hasattr(snapshot, "snapshot_date")
    assert hasattr(snapshot, "schema_version")
    assert hasattr(snapshot, "exchange")
    assert hasattr(snapshot, "segment")
    assert hasattr(snapshot, "file_hash")
    assert hasattr(snapshot, "risk_arrays")
    assert hasattr(snapshot, "metadata")


def test_f2_is_settlement_frozen(snapshot):
    with pytest.raises(FrozenInstanceError):
        snapshot.is_settlement = True


def test_f3_span_risk_array_unchanged():
    ra = SpanRiskArray(symbol="NIFTY", risk_metrics={"sr": 0.15})
    assert ra.symbol == "NIFTY"
    assert ra.risk_metrics == {"sr": 0.15}


def test_f4_registry_passes_bytes():
    reg = ParserRegistry()
    captured = []
    def _capture(raw: bytes) -> SpanSnapshot:
        captured.append(raw)
        return SpanSnapshot(
            snapshot_date=date(2026, 1, 1),
            schema_version="4.00",
            exchange="NSE",
            segment="FO",
            file_hash=hashlib.sha256(raw).hexdigest(),
            is_settlement=False,
            risk_arrays={},
            metadata={},
        )
    reg.register("4.00", _capture)
    reg.parse("4.00", b"test bytes")
    assert captured[0] == b"test bytes"


def test_f5_unknown_version_via_registry():
    reg = ParserRegistry()
    reg.register("4.00", parse_span_xml)
    with pytest.raises(UnsupportedSpanSchema) as exc:
        reg.parse("3.00", b"...")
    assert "3.00" in str(exc.value)


def test_f6_no_imports_from_forbidden_modules():
    import ast
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[3] / "core" / "risk" / "span" / "parser_v400.py"
    tree = ast.parse(src.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("core.execution"), f"Forbidden import: {alias.name}"
                assert not alias.name.startswith("core.runtime"), f"Forbidden import: {alias.name}"
                assert "SpanRepository" not in alias.name
                assert "SpanMarginCalculator" not in alias.name
        if isinstance(node, ast.ImportFrom):
            assert node.module is None or "core.execution" not in node.module, f"Forbidden import: {node.module}"
            assert node.module is None or "core.runtime" not in node.module, f"Forbidden import: {node.module}"
            assert node.module is None or "SpanMarginCalculator" not in node.module, f"Forbidden import: {node.module}"
            assert node.module is None or "LoopDriver" not in (node.module or ""), f"Forbidden import: {node.module}"
            assert node.module is None or "ExecutionHandler" not in (node.module or ""), f"Forbidden import: {node.module}"


def test_f7_parse_deterministic():
    result_a = parse_span_xml(FIXTURE_BYTES)
    result_b = parse_span_xml(FIXTURE_BYTES)
    assert result_a == result_b


def test_f8_full_suite_unchanged():
    """Marker test — actual regression checked by running the full suite."""
    pass


# --------------------------------------------------------------------------- #
# Block G — Scenario values preserved in metadata
# --------------------------------------------------------------------------- #

def test_g1_scenario_values_in_metadata(snapshot):
    assert "scenario_values" in snapshot.metadata
    sc = snapshot.metadata["scenario_values"]
    assert "NIFTY" in sc
    assert "WIDGET" in sc
    assert len(sc["NIFTY"]) == 16
    assert len(sc["WIDGET"]) == 16


def test_g2_scenario_values_match_expected(snapshot):
    sc = snapshot.metadata["scenario_values"]
    # NIFTY nearest expiry RA[0] = 1000.0
    assert sc["NIFTY"][0] == 1000.0
    # WIDGET RA[14] = 900.0, RA[15] = 2000.0
    assert sc["WIDGET"][14] == 900.0
    assert sc["WIDGET"][15] == 2000.0


def test_g3_zero_scan_risk_underlying_has_no_scenario_values():
    """ORPHAN has no futures → not in scenario_values."""
    result = parse_span_xml(_orphan_fixture())
    sc = result.metadata.get("scenario_values", {})
    assert "ORPHAN" not in sc
