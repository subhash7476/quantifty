"""The trades table: open a paper trade, read it back open, then close it."""
from datetime import date, datetime

from core.options_wall import persistence as p
from core.options_wall.fly import build_iron_fly
from tests.options_wall.test_fly import _chain


def test_open_then_close_trade(tmp_path):
    db = tmp_path / "res.duckdb"
    fly = build_iron_fly(_chain(), spot=100.0, wing_pct=0.03, qty=75,
                         trade_date=date(2026, 8, 14))
    tid = p.open_paper_trade("NSE_INDEX|Nifty 50", "2026-08-18", fly,
                             datetime(2026, 8, 14, 10, 0), db_path=db)
    assert tid > 0

    opens = p.open_trades("NSE_INDEX|Nifty 50", db_path=db)
    assert len(opens) == 1
    assert opens[0]["exit_ts"] is None
    assert opens[0]["short_strike"] == 100.0
    assert opens[0]["net_credit"] == fly.net_credit

    p.close_paper_trade(tid, datetime(2026, 8, 14, 14, 0), exit_mark=1000.0,
                        exit_fees=230.0, gross_pnl=500.0, net_pnl=270.0,
                        exit_reason="tp", db_path=db)
    assert p.open_trades("NSE_INDEX|Nifty 50", db_path=db) == []


def test_read_path_never_creates_trades_table(tmp_path):
    """Flask reads trades every ~7s; the read path must stay read-only so the
    poller remains the results DB's sole writer. A results DB whose `trades`
    table doesn't exist yet returns [] and is left without the table created."""
    import duckdb

    db = tmp_path / "res.duckdb"
    # A results DB that has other tables but no `trades` (poller hasn't written
    # a trade yet, or Flask opened the dashboard before the poller's first cycle).
    conn = duckdb.connect(str(db))
    conn.execute("CREATE TABLE scan_results (ts TIMESTAMP)")
    conn.close()

    assert p.open_trades("NSE_INDEX|Nifty 50", db_path=db) == []
    assert p.all_trades("NSE_INDEX|Nifty 50", db_path=db) == []

    conn = duckdb.connect(str(db), read_only=True)
    tables = {r[0] for r in conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main'").fetchall()}
    conn.close()
    assert "trades" not in tables          # the read path created nothing


def test_all_trades_returns_open_and_closed_newest_first(tmp_path):
    db = tmp_path / "res.duckdb"
    fly = build_iron_fly(_chain(), spot=100.0, wing_pct=0.03, qty=75,
                         trade_date=date(2026, 8, 14))
    t1 = p.open_paper_trade("NSE_INDEX|Nifty 50", "2026-08-18", fly,
                            datetime(2026, 8, 14, 10, 0), db_path=db)
    t2 = p.open_paper_trade("NSE_INDEX|Nifty 50", "2026-08-25", fly,
                            datetime(2026, 8, 15, 10, 0), db_path=db)
    p.close_paper_trade(t1, datetime(2026, 8, 14, 14, 0), exit_mark=1000.0,
                        exit_fees=230.0, gross_pnl=500.0, net_pnl=270.0,
                        exit_reason="tp", db_path=db)

    rows = p.all_trades("NSE_INDEX|Nifty 50", db_path=db)
    assert [r["trade_id"] for r in rows] == [t2, t1]        # newest entry first
    assert rows[0]["exit_ts"] is None                        # t2 still open
    assert rows[1]["exit_reason"] == "tp"                    # t1 closed


def test_open_trade_marks_computes_unrealized_pnl():
    from core.options_wall.engine import _open_trade_marks
    trade = {
        "qty": 2,
        "net_credit": 200.0,  # (60 + 40) short - (0 wing) = 100/unit × 2
        "entry_legs": (
            '[{"side":"SELL","type":"CE","strike":100,"mid":60.0},'
            '{"side":"SELL","type":"PE","strike":100,"mid":40.0},'
            '{"side":"BUY","type":"CE","strike":110,"mid":0.0},'
            '{"side":"BUY","type":"PE","strike":90,"mid":0.0}]'),
    }
    quotes = {(100, "CE"): {"mid": 55.0}, (100, "PE"): {"mid": 30.0},
              (110, "CE"): {"mid": 5.0}, (90, "PE"): {"mid": 4.0}}
    # cost to close = (55 + 30) short - (5 + 4) wings = 76/unit × 2 = 152
    mark, unrealized, legs = _open_trade_marks(trade, quotes)
    assert mark == 152.0
    assert unrealized == 48.0                                # 200 credit - 152 mark
    assert legs[0]["cur_mid"] == 55.0


def test_open_trade_marks_none_when_a_leg_is_unquoted():
    from core.options_wall.engine import _open_trade_marks
    trade = {"qty": 1, "net_credit": 100.0,
             "entry_legs": '[{"side":"SELL","type":"CE","strike":100,"mid":60.0}]'}
    mark, unrealized, legs = _open_trade_marks(trade, {})     # no quotes
    assert mark is None and unrealized is None
    assert legs[0]["cur_mid"] is None


def test_open_paper_trade_survives_a_sequence_reset_to_1(tmp_path):
    """A rebuilt store keeps its rows but restarts wall_trade_id_seq at 1.

    The 2026-09-04 compaction did exactly this: trades 1-7 were copied forward
    while the sequence was recreated at START 1, so every subsequent insert
    collided on the primary key and the poller swallowed it as a warning.
    """
    import duckdb
    db = tmp_path / "r.duckdb"
    conn = duckdb.connect(str(db))
    p.init_schema(conn)
    # simulate the rebuild: rows present, sequence untouched at 1
    conn.execute(
        "INSERT INTO trades (trade_id, underlying, expiry, entry_ts, short_strike, "
        "call_wing, put_wing, qty, net_credit, entry_fees, max_loss) "
        "VALUES (1,'NSE_INDEX|Nifty 50','2026-09-08','2026-09-07 10:00:00',"
        "23800,24150,23450,75,9000,100,17250)")
    conn.commit()
    conn.close()

    fly = build_iron_fly(_chain(), spot=100.0, wing_pct=0.03, qty=75,
                         trade_date=date(2026, 9, 7))
    tid = p.open_paper_trade("NSE_INDEX|Nifty 50", "2026-09-08", fly,
                                datetime(2026, 9, 7, 14, 30), db_path=db)
    assert tid > 1
    assert len(p.all_trades("NSE_INDEX|Nifty 50", db_path=db)) == 2
