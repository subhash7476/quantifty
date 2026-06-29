"""
PC-SPAN 4.00 XML Parser (MM9.5-S2).

Owns the complete transformation from raw PC-SPAN 4.00 XML bytes to a
fully-populated SpanSnapshot. No pre-processing required; no post-processing
expected.

Public API:
    parse_span_xml(raw: bytes) -> SpanSnapshot

Internal helpers are module-private (underscore-prefixed).
"""

import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

from core.risk.span.span_snapshot import (
    SpanRiskArray,
    SpanSnapshot,
    SpanFutureContract,
    SpanOptionSeries,
    SpanOptionContract,
    UnsupportedSpanSchema,
)

SEGMENT_FO = "FO"
SCENARIO_WEIGHTS: List[float] = [1.0] * 14 + [0.3, 0.3]
SPAN_CVF_EXPECTED = 1.0


def parse_span_xml(raw: bytes) -> SpanSnapshot:
    text = _decode_raw(raw)
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as e:
        raise UnsupportedSpanSchema(f"Malformed SPAN XML: {e}")

    file_hash = hashlib.sha256(raw).hexdigest()
    schema_version = _extract_text(root, "fileFormat", "Missing <fileFormat> in SPAN file")
    if schema_version != "4.00":
        raise UnsupportedSpanSchema(
            f"Parser v4.00 received fileFormat '{schema_version}'"
        )

    created_ts = root.findtext("created", "")
    snapshot_date_s = _extract_text(
        root, "pointInTime/date",
        f"Missing or invalid <pointInTime/date>: '{root.findtext('pointInTime/date')}'"
    )
    is_setl_s = root.findtext("pointInTime/isSetl", "0")
    clearing_org = root.findtext("pointInTime/clearingOrg/ec", "")
    exchange_code = root.findtext("pointInTime/clearingOrg/exchange/exch", "NSE")

    try:
        snapshot_date = datetime.strptime(snapshot_date_s, "%Y%m%d").date()
    except (ValueError, TypeError):
        raise UnsupportedSpanSchema(
            f"Missing or invalid <pointInTime/date>: '{snapshot_date_s}'"
        )

    fut_pfs: Dict[str, Element] = {
        fp.findtext("pfCode", ""): fp
        for fp in root.findall("pointInTime/clearingOrg/exchange/futPf")
        if fp.findtext("pfCode", "") != ""
    }

    phy_pfs: Dict[str, Element] = {
        pp.findtext("pfCode", ""): pp
        for pp in root.findall("pointInTime/clearingOrg/exchange/phyPf")
        if pp.findtext("pfCode", "") != ""
    }

    oop_pf_index: Dict[str, Element] = {
        op.findtext("pfCode", ""): op
        for op in root.findall("pointInTime/clearingOrg/exchange/oopPf")
        if op.findtext("pfCode", "") != ""
    }

    ccdefs = root.findall("pointInTime/clearingOrg/ccDef")
    oop_pfs = root.findall("pointInTime/clearingOrg/exchange/oopPf")
    scan_scenarios = _extract_scan_scenarios(root)

    risk_arrays: Dict[str, SpanRiskArray] = {}
    scenario_values: Dict[str, Tuple[float, ...]] = {}
    futures_by_symbol: Dict[str, Tuple[SpanFutureContract, ...]] = {}
    option_series_by_symbol: Dict[str, Tuple[SpanOptionSeries, ...]] = {}
    option_contracts_by_symbol: Dict[str, Tuple[SpanOptionContract, ...]] = {}
    futures_count = 0
    option_count = sum(
        len(oop.findall("series/opt"))
        for oop in oop_pfs
    )

    for cc in ccdefs:
        symbol = cc.findtext("cc", "")
        if not symbol:
            continue

        short_option_minimum = _safe_float(cc.findtext("somTiers/tier/rate/val", "0"))

        spread_vals = [
            _safe_float(d.findtext("rate/val"))
            for d in cc.findall("dSpread")
        ]
        intra_spread_charge_rs = min(spread_vals) if spread_vals else 0.0

        fut_pf = fut_pfs.get(symbol)
        scan_risk = 0.0
        fut_ra: Tuple[float, ...] = ()
        price_scan_range = 0.0
        vol_scan_range = 0.0
        risk_free_rate = 0.0

        if fut_pf is not None:
            futs = fut_pf.findall("fut")
            eligible = [f for f in futs if f.findtext("pe", "00000000") != "00000000"]
            futures_count += len(futs)
            if eligible:
                nearest = min(eligible, key=lambda f: f.findtext("pe", ""))
                fut_ra = _extract_ra_tuple(nearest)
                scan_risk = _derive_scan_risk(fut_ra)
                price_scan_range = _safe_float(nearest.findtext("scanRate/priceScan"))
                vol_scan_range = _safe_float(nearest.findtext("scanRate/volScan"))
                risk_free_rate = _safe_float(nearest.findtext("intrRate/val"))

        phy_pf = phy_pfs.get(symbol)
        cvf = _safe_float(phy_pf.findtext("cvf") if phy_pf is not None else None, default=SPAN_CVF_EXPECTED)

        risk_arrays[symbol] = SpanRiskArray(
            symbol=symbol,
            risk_metrics={
                "scan_risk": scan_risk,
                "short_option_minimum": short_option_minimum,
                "price_scan_range": price_scan_range,
                "vol_scan_range": vol_scan_range,
                "cvf": cvf,
                "intra_spread_charge_rs": intra_spread_charge_rs,
                "risk_free_rate": risk_free_rate,
            },
        )

        if fut_ra:
            scenario_values[symbol] = fut_ra

        symbol_futures = _extract_future_contracts(symbol, fut_pf)
        if symbol_futures:
            futures_by_symbol[symbol] = symbol_futures

        symbol_series, symbol_contracts = _extract_option_data(symbol, oop_pf_index.get(symbol))
        if symbol_series:
            option_series_by_symbol[symbol] = symbol_series
        if symbol_contracts:
            option_contracts_by_symbol[symbol] = symbol_contracts

    metadata: Dict[str, Any] = {
        "created": created_ts,
        "clearing_org": clearing_org,
        "underlying_count": len(risk_arrays),
        "futures_contract_count": futures_count,
        "option_count": option_count,
        "scan_scenarios": scan_scenarios,
    }

    if scenario_values:
        metadata["scenario_values"] = scenario_values

    return SpanSnapshot(
        snapshot_date=snapshot_date,
        schema_version=schema_version,
        exchange=exchange_code,
        segment=SEGMENT_FO,
        file_hash=file_hash,
        is_settlement=(is_setl_s == "1"),
        risk_arrays=risk_arrays,
        metadata=metadata,
        futures=futures_by_symbol,
        option_series=option_series_by_symbol,
        option_contracts=option_contracts_by_symbol,
    )


def _safe_float(s: Optional[str], default: float = 0.0) -> float:
    if s is None or s == "":
        return default
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


def _decode_raw(raw: bytes) -> str:
    try:
        return raw.decode("latin-1")
    except (UnicodeDecodeError, LookupError) as e:
        raise UnsupportedSpanSchema(f"Cannot decode SPAN file as latin-1: {e}")


def _extract_text(root: Element, path: str, error_msg: str) -> str:
    val = root.findtext(path)
    if val is None or val == "":
        raise UnsupportedSpanSchema(error_msg)
    return val


def _extract_ra_tuple(elem: Element) -> Tuple[float, ...]:
    a_elements = elem.findall("ra/a")
    if len(a_elements) != 16:
        raise UnsupportedSpanSchema(
            f"Expected 16 RA scenarios, got {len(a_elements)}"
        )
    vals: List[float] = []
    for a in a_elements:
        try:
            vals.append(float(a.text))
        except (ValueError, TypeError) as e:
            raise UnsupportedSpanSchema(
                f"Invalid RA value '{a.text or ''}' in <ra/a>: {e}"
            )
    return tuple(vals)


def _derive_scan_risk(ra: Tuple[float, ...]) -> float:
    weighted_losses = [v * w for v, w in zip(ra, SCENARIO_WEIGHTS)]
    return max(0.0, max(weighted_losses))


def _extract_scan_scenarios(root: Element) -> List[Dict]:
    scenarios: List[Dict] = []
    for sp in root.findall("pointInTime/clearingOrg/pointDef/scanPointDef"):
        try:
            num = _safe_float(sp.findtext("priceScanDef/numerator", ""))
            den = _safe_float(sp.findtext("priceScanDef/denominator", ""), default=1.0)
            vnum = _safe_float(sp.findtext("volScanDef/numerator", ""))
            vden = _safe_float(sp.findtext("volScanDef/denominator", ""), default=1.0)
            scenarios.append({
                "point": int(float(sp.findtext("point", "0"))),
                "paired_point": int(float(sp.findtext("pairedPoint", "0"))),
                "price_mult": num / den if den != 0.0 else 0.0,
                "vol_mult": vnum / vden if vden != 0.0 else 0.0,
                "weight": _safe_float(sp.findtext("weight", ""), default=1.0),
            })
        except (ValueError, TypeError):
            continue
    return scenarios


def _extract_future_contracts(
    symbol: str,
    fut_pf: Optional[Element],
) -> Tuple[SpanFutureContract, ...]:
    if fut_pf is None:
        return ()
    result: List[SpanFutureContract] = []
    for fut in fut_pf.findall("fut"):
        pe_s = fut.findtext("pe", "")
        if not pe_s or pe_s == "00000000":
            continue
        try:
            expiry = datetime.strptime(pe_s, "%Y%m%d").date()
        except ValueError:
            continue
        ra = _extract_ra_tuple(fut)
        result.append(SpanFutureContract(
            symbol=symbol,
            expiry=expiry,
            price=_safe_float(fut.findtext("p")),
            delta=_safe_float(fut.findtext("d"), default=1.0),
            time_to_expiry=_safe_float(fut.findtext("t")),
            risk_free_rate=_safe_float(fut.findtext("intrRate/val")),
            price_scan_range=_safe_float(fut.findtext("scanRate/priceScan")),
            vol_scan_range=_safe_float(fut.findtext("scanRate/volScan")),
            ra=ra,
        ))
    result.sort(key=lambda c: c.expiry)
    return tuple(result)


def _extract_option_data(
    symbol: str,
    oop_pf: Optional[Element],
) -> Tuple[Tuple[SpanOptionSeries, ...], Tuple[SpanOptionContract, ...]]:
    if oop_pf is None:
        return (), ()
    series_list: List[SpanOptionSeries] = []
    contracts_list: List[SpanOptionContract] = []
    for series in oop_pf.findall("series"):
        pe_s = series.findtext("pe", "")
        if not pe_s or pe_s == "00000000":
            continue
        try:
            expiry = datetime.strptime(pe_s, "%Y%m%d").date()
        except ValueError:
            continue
        series_list.append(SpanOptionSeries(
            symbol=symbol,
            expiry=expiry,
            vol=_safe_float(series.findtext("v")),
            price_scan_range=_safe_float(series.findtext("scanRate/priceScan")),
            vol_scan_range=_safe_float(series.findtext("scanRate/volScan")),
            time_to_expiry=_safe_float(series.findtext("t")),
            risk_free_rate=_safe_float(series.findtext("intrRate/val")),
        ))
        for opt in series.findall("opt"):
            ra = _extract_ra_tuple(opt)
            contracts_list.append(SpanOptionContract(
                symbol=symbol,
                expiry=expiry,
                strike=_safe_float(opt.findtext("k")),
                option_type=opt.findtext("o", ""),
                price=_safe_float(opt.findtext("p")),
                delta=_safe_float(opt.findtext("d")),
                implied_vol=_safe_float(opt.findtext("v")),
                ra=ra,
            ))
    return tuple(series_list), tuple(contracts_list)
