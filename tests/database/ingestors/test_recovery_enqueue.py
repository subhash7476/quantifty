from datetime import datetime
from unittest.mock import MagicMock
from core.database.manager import DatabaseManager
from core.database.ingestors.recovery_manager import RecoveryManager
from core.database.ingestors.live_buffer_writer import RecoverBars

def test_recovery_submits_recoverbars_not_direct_write(tmp_path, monkeypatch):
    DatabaseManager.reset_instance()
    db = DatabaseManager(tmp_path, read_only=False)
    db.bootstrap_live_buffer()
    writer = MagicMock()
    client = MagicMock()
    bar_ts = datetime(2020, 1, 1, 10, 5)
    client.fetch_intraday_candles_v3.return_value = [
        {"timestamp": bar_ts, "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 10}
    ]
    rm = RecoveryManager(client, db_manager=db, writer=writer)
    monkeypatch.setattr(rm, "_should_recover", lambda symbol: (datetime(2020,1,1,10,0), datetime(2020,1,1,10,6)))
    rm._recover_symbol("X")
    assert writer.submit.called
    cmd = writer.submit.call_args[0][0]
    assert isinstance(cmd, RecoverBars)
    assert cmd.rows and cmd.rows[0][0] == "X"
