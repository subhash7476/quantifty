"""Tests for the Options-Wall snapshot store.

The store is append-only and multi-symbol; these tests pin the round-trip
(append -> latest -> timestamps) and that a second append accumulates rather than
overwrites.
"""
from core.data import options_wall_store as ws
from core.data.options_provider import OptionChainRow


def _row(strike, otype, ltp, key):
    return OptionChainRow(
        strike=strike, option_type=otype, instrument_key=key, tradingsymbol=key,
        expiry="2026-08-18", ltp=ltp,
    )


def test_append_and_latest_roundtrip(tmp_path):
    db = tmp_path / "wall.duckdb"
    rows = [_row(100.0, "CE", 5.0, "K1"), _row(100.0, "PE", 4.0, "K2")]
    ws.append_snapshot(rows, "NSE_INDEX|Nifty 50", "2026-08-18", db_path=db)

    chain = ws.latest_snapshot("NSE_INDEX|Nifty 50", "2026-08-18", db_path=db)
    assert len(chain) == 2
    assert {r.strike for r in chain} == {100.0}

    tss = ws.snapshot_timestamps("NSE_INDEX|Nifty 50", db_path=db)
    assert len(tss) == 1


def test_append_accumulates_and_latest_is_newest(tmp_path):
    db = tmp_path / "wall.duckdb"
    ws.append_snapshot([_row(100.0, "CE", 5.0, "K1")], "NSE_INDEX|Nifty 50",
                       "2026-08-18", db_path=db)
    ws.append_snapshot([_row(101.0, "CE", 6.0, "K3")], "NSE_INDEX|Nifty 50",
                       "2026-08-18", db_path=db)

    tss = ws.snapshot_timestamps("NSE_INDEX|Nifty 50", db_path=db)
    assert len(tss) == 2  # accumulated, not overwritten

    chain = ws.latest_snapshot("NSE_INDEX|Nifty 50", "2026-08-18", db_path=db)
    assert len(chain) == 1
    assert chain[0].strike == 101.0


def test_append_and_read_bid_ask(tmp_path):
    db = tmp_path / "wall.duckdb"
    rows = [_row(100.0, "CE", 5.0, "NSE_FO|1")]
    quotes = {"NSE_FO|1": {"best_bid": 4.9, "best_ask": 5.1}}
    ws.append_snapshot(rows, "NSE_INDEX|Nifty 50", "2026-08-18",
                       db_path=db, quotes=quotes)
    back = ws.latest_snapshot("NSE_INDEX|Nifty 50", "2026-08-18", db_path=db)
    assert back[0].best_bid == 4.9
    assert back[0].best_ask == 5.1


def test_append_without_quotes_leaves_bid_ask_null(tmp_path):
    db = tmp_path / "wall.duckdb"
    rows = [_row(100.0, "CE", 5.0, "NSE_FO|1")]
    ws.append_snapshot(rows, "NSE_INDEX|Nifty 50", "2026-08-18", db_path=db)
    back = ws.latest_snapshot("NSE_INDEX|Nifty 50", "2026-08-18", db_path=db)
    assert back[0].best_bid is None
    assert back[0].best_ask is None


def test_latest_snapshot_migrates_pre_bid_ask_store(tmp_path):
    """A store created before best_bid/best_ask existed must read (and migrate),
    not die with a Binder Error on the new SELECT columns."""
    import duckdb

    db = tmp_path / "wall.duckdb"
    con = duckdb.connect(str(db))
    con.execute("CREATE SEQUENCE snapshot_id_seq START 1")
    con.execute("""
        CREATE TABLE option_chain_snapshot (
            snapshot_id INTEGER DEFAULT nextval('snapshot_id_seq'),
            snapshot_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            underlying_symbol VARCHAR NOT NULL,
            expiry_date VARCHAR NOT NULL,
            strike_price DOUBLE NOT NULL,
            option_type VARCHAR NOT NULL,
            instrument_key VARCHAR NOT NULL,
            tradingsymbol VARCHAR NOT NULL,
            ltp DOUBLE,
            open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE,
            oi BIGINT DEFAULT 0, oi_change BIGINT DEFAULT 0,
            oi_change_pct DOUBLE DEFAULT 0.0, volume BIGINT DEFAULT 0,
            iv DOUBLE, delta DOUBLE, gamma DOUBLE, theta DOUBLE,
            vega DOUBLE, rho DOUBLE,
            lot_size INTEGER DEFAULT 75,
            underlying_ltp DOUBLE,
            PRIMARY KEY (snapshot_id)
        )
    """)
    con.execute("""
        INSERT INTO option_chain_snapshot (underlying_symbol, expiry_date,
            strike_price, option_type, instrument_key, tradingsymbol,
            ltp, underlying_ltp)
        VALUES ('NSE_INDEX|Nifty 50', '2026-08-18', 100.0, 'CE',
                'NSE_FO|1', 'T1', 5.0, 100.0)
    """)
    con.commit()
    con.close()

    back = ws.latest_snapshot("NSE_INDEX|Nifty 50", "2026-08-18", db_path=db)
    assert back[0].strike == 100.0
    assert back[0].best_bid is None

    rows = [_row(100.0, "CE", 5.0, "NSE_FO|1")]
    ws.append_snapshot(rows, "NSE_INDEX|Nifty 50", "2026-08-18", db_path=db,
                       quotes={"NSE_FO|1": {"best_bid": 4.9, "best_ask": 5.1}})
    back = ws.latest_snapshot("NSE_INDEX|Nifty 50", "2026-08-18", db_path=db)
    assert back[0].best_bid == 4.9
    assert back[0].best_ask == 5.1
