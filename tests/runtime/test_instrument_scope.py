"""
MM.4 — F&O scope detection (has_derivatives).

The startup-readiness gate is enforced only on the live derivative path. Scope is
derived from the broker-segment prefix of each configured instrument key — pure
and master-independent, because master absence is itself a BLOCK condition and so
scope cannot depend on resolving the master (MM.4_DESIGN_REVIEW.md §2).
"""
from core.runtime.instrument_scope import has_derivatives


def test_nse_fo_key_is_derivative():
    assert has_derivatives(["NSE_FO|53001"]) is True


def test_mcx_fo_key_is_derivative():
    assert has_derivatives(["MCX_FO|428329"]) is True


def test_equity_key_is_not_derivative():
    assert has_derivatives(["NSE_EQ|INE002A01018"]) is False


def test_index_key_is_not_derivative():
    assert has_derivatives(["NSE_INDEX|Nifty 50"]) is False


def test_mixed_universe_with_one_derivative_is_true():
    assert has_derivatives(["NSE_INDEX|Nifty 50", "NSE_EQ|INE002A01018",
                            "NSE_FO|53001"]) is True


def test_equity_and_index_only_universe_is_false():
    assert has_derivatives(["NSE_INDEX|Nifty 50", "NSE_EQ|INE002A01018"]) is False


def test_empty_universe_is_false():
    assert has_derivatives([]) is False
