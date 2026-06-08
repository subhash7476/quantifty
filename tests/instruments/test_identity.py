"""
Phase 4C.2 — Canonical identity (CANONICAL_INSTRUMENT_ARCHITECTURE.md §D4).

The canonical_id is a deterministic, broker-independent structured key (Option B,
§D4.2). Determinism depends on underlying-name normalization (§D4.3): the repo
spells the same underlying three ways, and they must collapse to one token.
"""
from datetime import date

from core.instruments.canonical import AssetClass
from core.instruments.identity import canonical_id, normalize_underlying
from core.instruments.option import OptionType


def test_normalize_underlying_index_long_form():
    assert normalize_underlying("NSE_INDEX|Nifty 50") == "NIFTY"
    assert normalize_underlying("NSE_INDEX|Nifty Bank") == "BANKNIFTY"


def test_normalize_underlying_short_form_passthrough():
    assert normalize_underlying("NIFTY") == "NIFTY"
    assert normalize_underlying("BANKNIFTY") == "BANKNIFTY"


def test_normalize_underlying_collapses_three_spellings_to_one():
    assert (
        normalize_underlying("NSE_INDEX|Nifty 50")
        == normalize_underlying("Nifty 50")
        == normalize_underlying("nifty")
        == "NIFTY"
    )


def test_canonical_id_option():
    cid = canonical_id(
        AssetClass.OPTION, exchange="NSE", underlying="NSE_INDEX|Nifty 50",
        expiry=date(2026, 2, 25), strike=22500.0, option_type=OptionType.CALL,
    )
    assert cid == "NSE:OPT:NIFTY:2026-02-25:22500:CE"


def test_canonical_id_future():
    cid = canonical_id(
        AssetClass.FUTURE, exchange="NSE", underlying="NIFTY",
        expiry=date(2026, 2, 26),
    )
    assert cid == "NSE:FUT:NIFTY:2026-02-26"


def test_canonical_id_equity_anchors_on_isin():
    cid = canonical_id(AssetClass.EQUITY, exchange="NSE", isin="INE002A01018")
    assert cid == "NSE:EQ:INE002A01018"


def test_canonical_id_index():
    cid = canonical_id(AssetClass.INDEX, exchange="NSE", underlying="NSE_INDEX|Nifty 50")
    assert cid == "NSE:IDX:NIFTY"


def test_canonical_id_preserves_fractional_strike():
    cid = canonical_id(
        AssetClass.OPTION, exchange="NSE", underlying="NIFTY",
        expiry=date(2026, 2, 25), strike=22500.5, option_type=OptionType.PUT,
    )
    assert cid == "NSE:OPT:NIFTY:2026-02-25:22500.5:PE"


def test_canonical_id_is_deterministic_across_input_spellings():
    a = canonical_id(
        AssetClass.OPTION, exchange="NSE", underlying="NSE_INDEX|Nifty 50",
        expiry=date(2026, 2, 25), strike=22500.0, option_type=OptionType.CALL,
    )
    b = canonical_id(
        AssetClass.OPTION, exchange="NSE", underlying="NIFTY",
        expiry=date(2026, 2, 25), strike=22500.0, option_type="CE",
    )
    assert a == b
