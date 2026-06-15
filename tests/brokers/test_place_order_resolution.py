"""
4C.7 — place_order broker payload resolution.

Verifies that UpstoxAdapter.place_order routes derivative orders through
CanonicalInstrument → UpstoxMapping.to_broker() → BrokerRef.instrument_key
instead of the pre-4C.7 display-symbol fallback, and that the product code
comes from BrokerRef.product_code rather than the hardcoded "I".

Acceptance criteria (PHASE_4C_IMPLEMENTATION_PLAN.md §2 / 4C.7):
  P1  F&O order with CI → instrument_token == instrument_key (not display symbol)
  P2  F&O order with CI → product == ref.product_code (not hardcoded "I")
  P3  Equity order (CI absent) → instrument_token == order.symbol, product == "I"
  P4  Derivative order, CI absent → BrokerContractError (fail-fast, no payload sent)
  P5  Futures order, CI absent → BrokerContractError (fail-fast)
  P6  LookupError from to_broker → propagates as BrokerContractError

Planned #4 end-to-end payload tests (real mapping, no mock):
  P7  OPTION CI (product=None) + real mapping → payload product="D" (NRML default)
  P8  FUTURE CI (product=None) + real mapping → payload product="D" (NRML default)
"""
from datetime import date
from unittest.mock import MagicMock
import pytest

from scripts.fetch_instrument_master import parse_instruments, write_snapshot
from core.brokers.mapping.upstox import UpstoxMapping
from core.instruments.resolver import InstrumentResolver

from core.brokers.upstox_adapter import UpstoxAdapter, BrokerContractError
from core.brokers.mapping.base import BrokerRef
from core.instruments.canonical import CanonicalInstrument, AssetClass
from core.instruments.instrument_base import InstrumentType
from core.instruments.option import OptionType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_CE = CanonicalInstrument(
    asset_class=AssetClass.OPTION,
    exchange="NSE_FO",
    underlying="NIFTY",
    expiry=date(2026, 6, 16),
    strike=22500.0,
    option_type=OptionType.CALL,
    lot_size=65,
    tick_size=0.05,
    segment="NSE_FO",
    product="NRML",
    display_symbol="NIFTY16JUN2622500CE",
)

_REF = BrokerRef(
    instrument_key="NSE_FO|54710",
    tradingsymbol="NIFTY16JUN2622500CE",
    product_code="D",  # NRML → "D" per _PRODUCT map in upstox.py
)


def _adapter(monkeypatch, mapping_mock):
    """UpstoxAdapter with UpstoxMapping replaced by mapping_mock."""
    monkeypatch.setattr(
        "core.brokers.upstox_adapter.UpstoxMapping",
        lambda: mapping_mock,
    )
    return UpstoxAdapter("key", "secret", "token", MagicMock())


def _order(ci=None, instrument_type=InstrumentType.OPTION,
           symbol="NIFTY16JUN2622500CE", side="BUY"):
    """Minimal order-like object for adapter unit tests."""
    o = MagicMock()
    o.canonical_instrument = ci
    o.instrument_type = instrument_type
    o.symbol = symbol
    o.quantity = 65
    o.order_type.value = "MARKET"
    o.price = 0
    o.signal_id_reference = "sig-4c7-test"
    o.side = side
    return o


def _capture(adapter, monkeypatch):
    """Patch _make_request to capture the payload without HTTP."""
    captured = {}

    def fake_request(method, endpoint, data=None, params=None):
        if data:
            captured.update(data)
        return {"status": "success", "data": {"order_id": "ORD-TEST"}}

    monkeypatch.setattr(adapter, "_make_request", fake_request)
    return captured


# ---------------------------------------------------------------------------
# P1 — F&O option order with CI routes via instrument_key, not display symbol
# ---------------------------------------------------------------------------
def test_p1_fo_order_uses_instrument_key_not_display_symbol(monkeypatch):
    mapping = MagicMock()
    mapping.to_broker.return_value = _REF
    adapter = _adapter(monkeypatch, mapping)
    payload = _capture(adapter, monkeypatch)

    adapter.place_order(_order(ci=_CE))

    assert payload["instrument_token"] == "NSE_FO|54710"
    assert payload["instrument_token"] != "NIFTY16JUN2622500CE"
    mapping.to_broker.assert_called_once_with(_CE)


# ---------------------------------------------------------------------------
# P2 — product comes from BrokerRef.product_code, not hardcoded "I"
# ---------------------------------------------------------------------------
def test_p2_product_from_broker_ref_not_hardcoded(monkeypatch):
    mapping = MagicMock()
    mapping.to_broker.return_value = _REF  # product_code="D"
    adapter = _adapter(monkeypatch, mapping)
    payload = _capture(adapter, monkeypatch)

    adapter.place_order(_order(ci=_CE))

    assert payload["product"] == "D"
    assert payload["product"] != "I"


# ---------------------------------------------------------------------------
# P3 — equity order (CI absent, EQUITY type) uses display symbol + "I"
# ---------------------------------------------------------------------------
def test_p3_equity_order_uses_display_symbol_and_intraday(monkeypatch):
    mapping = MagicMock()
    adapter = _adapter(monkeypatch, mapping)
    payload = _capture(adapter, monkeypatch)

    adapter.place_order(_order(
        ci=None,
        instrument_type=InstrumentType.EQUITY,
        symbol="RELIANCE",
    ))

    assert payload["instrument_token"] == "RELIANCE"
    assert payload["product"] == "I"
    mapping.to_broker.assert_not_called()


# ---------------------------------------------------------------------------
# P4 — option derivative, CI absent → BrokerContractError; no payload sent
# ---------------------------------------------------------------------------
def test_p4_option_without_ci_raises_broker_contract_error(monkeypatch):
    mapping = MagicMock()
    adapter = _adapter(monkeypatch, mapping)
    request_calls = []
    monkeypatch.setattr(adapter, "_make_request",
                        lambda *a, **kw: request_calls.append(kw) or {})

    with pytest.raises(BrokerContractError, match="canonical_instrument"):
        adapter.place_order(_order(ci=None, instrument_type=InstrumentType.OPTION))

    assert request_calls == [], "broker API must not be called when fail-fast fires"


# ---------------------------------------------------------------------------
# P5 — futures derivative, CI absent → BrokerContractError
# ---------------------------------------------------------------------------
def test_p5_future_without_ci_raises_broker_contract_error(monkeypatch):
    mapping = MagicMock()
    adapter = _adapter(monkeypatch, mapping)
    monkeypatch.setattr(adapter, "_make_request", lambda *a, **kw: {})

    with pytest.raises(BrokerContractError, match="canonical_instrument"):
        adapter.place_order(_order(
            ci=None,
            instrument_type=InstrumentType.FUTURE,
            symbol="NIFTY26JUNFUT",
        ))


# ---------------------------------------------------------------------------
# P6 — LookupError from to_broker propagates as BrokerContractError
# ---------------------------------------------------------------------------
def test_p6_lookup_error_from_mapping_propagates_as_broker_contract_error(monkeypatch):
    mapping = MagicMock()
    mapping.to_broker.side_effect = LookupError("no mapping for canonical_id")
    adapter = _adapter(monkeypatch, mapping)
    monkeypatch.setattr(adapter, "_make_request", lambda *a, **kw: {})

    with pytest.raises(BrokerContractError, match="mapping"):
        adapter.place_order(_order(ci=_CE))


# ---------------------------------------------------------------------------
# Planned #4 — end-to-end payload tests with real mapping (product=None path)
# ---------------------------------------------------------------------------

@pytest.fixture
def _db(tmp_path):
    path = tmp_path / "instruments.duckdb"
    rows = [
        {"segment": "NSE_FO", "instrument_key": "NSE_FO|53001",
         "tradingsymbol": "NIFTY26FEBFUT", "name": "NIFTY",
         "expiry": "2026-02-26", "instrument_type": "FUT",
         "lot_size": 75, "tick_size": 5},
        {"segment": "NSE_FO", "instrument_key": "NSE_FO|54710",
         "tradingsymbol": "NIFTY26FEB2522500CE", "name": "NIFTY",
         "expiry": "2026-02-25", "strike_price": 22500.0,
         "instrument_type": "CE", "lot_size": 75, "tick_size": 5},
    ]
    write_snapshot(parse_instruments(rows, "2026-02-01"), db_path=path)
    return path


def test_p7_option_ci_no_product_default_nrml(_db, monkeypatch):
    r = InstrumentResolver(db_path=_db)
    ci = r.resolve_option("NIFTY", date(2026, 2, 25), 22500.0, "CE")
    assert ci.product is None  # production reality: resolver never sets product

    adapter = UpstoxAdapter("key", "secret", "token", MagicMock())
    adapter._mapping = UpstoxMapping(db_path=_db)
    captured = _capture(adapter, monkeypatch)

    adapter.place_order(_order(ci=ci, instrument_type=InstrumentType.OPTION))

    assert captured["product"] == "D", "OPTION with product=None must emit NRML ('D')"
    assert captured["instrument_token"] == "NSE_FO|54710"


def test_p8_future_ci_no_product_default_nrml(_db, monkeypatch):
    r = InstrumentResolver(db_path=_db)
    ci = r.resolve_future("NIFTY", as_of=date(2026, 2, 1))
    assert ci.product is None

    adapter = UpstoxAdapter("key", "secret", "token", MagicMock())
    adapter._mapping = UpstoxMapping(db_path=_db)
    captured = _capture(adapter, monkeypatch)

    adapter.place_order(_order(ci=ci, instrument_type=InstrumentType.FUTURE,
                               symbol="NIFTY26FEBFUT"))

    assert captured["product"] == "D", "FUTURE with product=None must emit NRML ('D')"
    assert captured["instrument_token"] == "NSE_FO|53001"
