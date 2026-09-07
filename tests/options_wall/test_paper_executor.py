"""Paper executor: opens one ATM fly on a farm signal, then manages/closes it."""
from datetime import datetime

from core.analytics.options_analytics import (
    GEXResult, OIAnalysisResult, OptionsStructuralData, PCRResult,
)
from core.data.options_provider import OptionChainRow
from core.options_wall.paper_executor import PaperConfig, PaperExecutor

_PREMIA = {
    97: (4.0, 0.5), 98: (3.2, 0.8), 99: (2.5, 1.2), 100: (1.8, 1.8),
    101: (1.2, 2.5), 102: (0.8, 3.2), 103: (0.5, 4.0),
}


def _row(strike, ot, ltp, iv=15.0):
    r = OptionChainRow(strike=float(strike), option_type=ot,
                       instrument_key=f"{ot}{strike}", tradingsymbol=f"{ot}{strike}",
                       expiry="2026-08-18", ltp=ltp, iv=iv, underlying_ltp=100.0)
    r.best_bid = ltp - 0.01
    r.best_ask = ltp + 0.01
    return r


def _chain():
    rows = []
    for k, (ce, pe) in _PREMIA.items():
        rows.append(_row(k, "CE", ce))
        rows.append(_row(k, "PE", pe))
    return rows


def _structural(regime="Positive GEX (Stable)", pin=100.0, spot=100.0):
    gex = GEXResult(net_gamma_total=10.0, net_gamma_ce=1.0, net_gamma_pe=1.0,
                    gamma_by_strike={pin: 10.0, 101.0: 1.0}, zero_gamma_level=None,
                    regime=regime)
    return OptionsStructuralData(
        underlying="NSE_INDEX|Nifty 50", underlying_ltp=spot, expiry="2026-08-18",
        timestamp=datetime.now(), pcr=PCRResult(pcr=1.0, total_ce_oi=1, total_pe_oi=1),
        gex=gex, oi_analysis=OIAnalysisResult())


def test_opens_when_farm_signal_and_no_open_position(tmp_path):
    ex = PaperExecutor(PaperConfig(wing_pct=0.03), db_path=tmp_path / "r.duckdb")
    action = ex.step("NSE_INDEX|Nifty 50", _chain(), _structural(), realized_vol=1.0,
                     now=datetime(2026, 8, 14, 10, 0))
    assert action == "open"


def test_does_not_open_outside_entry_window(tmp_path):
    ex = PaperExecutor(PaperConfig(wing_pct=0.03), db_path=tmp_path / "r.duckdb")
    action = ex.step("NSE_INDEX|Nifty 50", _chain(), _structural(), realized_vol=1.0,
                     now=datetime(2026, 8, 14, 15, 20))  # after 15:00
    assert action is None


def test_regime_flip_closes_open_position(tmp_path):
    db = tmp_path / "r.duckdb"
    ex = PaperExecutor(PaperConfig(wing_pct=0.03), db_path=db)
    ex.step("NSE_INDEX|Nifty 50", _chain(), _structural(), 1.0, datetime(2026, 8, 14, 10, 0))
    action = ex.step("NSE_INDEX|Nifty 50", _chain(),
                     _structural(regime="Negative GEX (Volatile)"), 1.0,
                     datetime(2026, 8, 14, 11, 0))
    assert action == "regime_flip"


def test_time_stop_squares_off(tmp_path):
    db = tmp_path / "r.duckdb"
    ex = PaperExecutor(PaperConfig(wing_pct=0.03), db_path=db)
    ex.step("NSE_INDEX|Nifty 50", _chain(), _structural(), 1.0, datetime(2026, 8, 17, 10, 0))
    # expiry 2026-08-18 (Tue) -> DTE 1 on Mon; 15:15 is the squareoff
    action = ex.step("NSE_INDEX|Nifty 50", _chain(), _structural(), 1.0,
                     datetime(2026, 8, 17, 15, 15))
    assert action == "time_stop"


def test_manual_close_closes_regardless_of_rules(tmp_path):
    from core.options_wall import persistence
    db = tmp_path / "r.duckdb"
    ex = PaperExecutor(PaperConfig(wing_pct=0.03), db_path=db)
    ex.step("NSE_INDEX|Nifty 50", _chain(), _structural(), 1.0, datetime(2026, 8, 14, 10, 0))
    tid = persistence.open_trades("NSE_INDEX|Nifty 50", db_path=db)[0]["trade_id"]
    # Stable regime, mid-session, no TP/SL — nothing the rules would close on.
    result = ex.manual_close("NSE_INDEX|Nifty 50", tid, _chain(),
                             datetime(2026, 8, 14, 11, 0))
    assert result == "manual"
    assert persistence.open_trades("NSE_INDEX|Nifty 50", db_path=db) == []
    assert persistence.all_trades("NSE_INDEX|Nifty 50", db_path=db)[0]["exit_reason"] == "manual"


def test_manual_close_unknown_trade_returns_none(tmp_path):
    ex = PaperExecutor(PaperConfig(wing_pct=0.03), db_path=tmp_path / "r.duckdb")
    assert ex.manual_close("NSE_INDEX|Nifty 50", 999, _chain(),
                           datetime(2026, 8, 14, 11, 0)) is None


def test_only_one_open_position_per_index(tmp_path):
    from core.options_wall import persistence as pers
    db = tmp_path / "r.duckdb"
    ex = PaperExecutor(PaperConfig(wing_pct=0.03), db_path=db)
    ex.step("NSE_INDEX|Nifty 50", _chain(), _structural(), 1.0, datetime(2026, 8, 14, 10, 0))
    # second qualifying signal while one is open -> manage (no exit here) -> None, no new row
    action = ex.step("NSE_INDEX|Nifty 50", _chain(), _structural(), 1.0,
                     datetime(2026, 8, 14, 10, 30))
    assert action is None
    assert len(pers.open_trades("NSE_INDEX|Nifty 50", db_path=db)) == 1


def test_qty_derived_from_chain_lot_size(tmp_path):
    from core.options_wall import persistence as pers
    db = tmp_path / "r.duckdb"
    ex = PaperExecutor(PaperConfig(wing_pct=0.03), db_path=db)  # lots defaults to 1
    chain = _chain()
    for r in chain:
        r.lot_size = 30  # BankNifty-like lot; must flow through to qty, not hardcoded 75
    ex.step("NSE_INDEX|Nifty Bank", chain, _structural(), 1.0, datetime(2026, 8, 14, 10, 0))
    opens = pers.open_trades("NSE_INDEX|Nifty Bank", db_path=db)
    assert len(opens) == 1
    assert opens[0]["qty"] == 30


def _chain_scaled(factor):
    """Same chain with every premium scaled — moves the mark without moving strikes."""
    rows = []
    for k, (ce, pe) in _PREMIA.items():
        rows.append(_row(k, "CE", round(ce * factor, 4)))
        rows.append(_row(k, "PE", round(pe * factor, 4)))
    return rows


def test_tp_fires_at_quarter_of_credit(tmp_path):
    db = tmp_path / "r.duckdb"
    ex = PaperExecutor(PaperConfig(wing_pct=0.03), db_path=db)
    ex.step("NSE_INDEX|Nifty 50", _chain(), _structural(), 1.0, datetime(2026, 8, 14, 10, 0))
    # 0.70x premia -> mark 136.5 vs credit 195 -> +30% of credit: above 0.25, below 0.50
    action = ex.step("NSE_INDEX|Nifty 50", _chain_scaled(0.70), _structural(), 1.0,
                     datetime(2026, 8, 14, 11, 0))
    assert action == "tp"


def test_tp_does_not_fire_below_threshold(tmp_path):
    db = tmp_path / "r.duckdb"
    ex = PaperExecutor(PaperConfig(wing_pct=0.03), db_path=db)
    ex.step("NSE_INDEX|Nifty 50", _chain(), _structural(), 1.0, datetime(2026, 8, 14, 10, 0))
    # 0.90x premia -> +10% of credit
    action = ex.step("NSE_INDEX|Nifty 50", _chain_scaled(0.90), _structural(), 1.0,
                     datetime(2026, 8, 14, 11, 0))
    assert action is None


def test_sl_fires_on_fraction_of_max_loss(tmp_path):
    """The stop must be reachable: a fly cannot lose a multiple of its own credit."""
    db = tmp_path / "r.duckdb"
    ex = PaperExecutor(PaperConfig(wing_pct=0.03), db_path=db)
    ex.step("NSE_INDEX|Nifty 50", _chain(), _structural(), 1.0, datetime(2026, 8, 14, 10, 0))
    # credit 195, max_loss 30. 1.15x premia -> mark 224.25 -> -29.25, past 0.5 x max_loss.
    # The old -2.0 x credit rule needed -390, which this position can never reach.
    action = ex.step("NSE_INDEX|Nifty 50", _chain_scaled(1.15), _structural(), 1.0,
                     datetime(2026, 8, 14, 11, 0))
    assert action == "sl"


def test_sl_does_not_fire_inside_the_band(tmp_path):
    db = tmp_path / "r.duckdb"
    ex = PaperExecutor(PaperConfig(wing_pct=0.03), db_path=db)
    ex.step("NSE_INDEX|Nifty 50", _chain(), _structural(), 1.0, datetime(2026, 8, 14, 10, 0))
    # 1.05x premia -> -9.75, inside 0.5 x max_loss (-15)
    action = ex.step("NSE_INDEX|Nifty 50", _chain_scaled(1.05), _structural(), 1.0,
                     datetime(2026, 8, 14, 11, 0))
    assert action is None
