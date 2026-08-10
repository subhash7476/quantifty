from unittest.mock import MagicMock, patch
import scripts.market_ingestor as mi

def test_try_connect_starts_ws_before_recovery(tmp_path):
    order = []
    daemon = mi.MarketIngestorDaemon.__new__(mi.MarketIngestorDaemon)
    daemon.symbols = ["X"]
    daemon.db_manager = MagicMock()
    daemon.writer = MagicMock()
    daemon._update_websocket_status = lambda *a, **k: None

    fake_ws = MagicMock()
    fake_ws.start.side_effect = lambda: order.append("ws_start")

    with patch.object(mi, "WebSocketIngestor", return_value=fake_ws), \
         patch.object(mi, "UpstoxClient", MagicMock()), \
         patch.object(mi, "RecoveryManager") as RM, \
         patch.object(mi, "threading") as th:
        # capture recovery thread creation as the "recovery" marker
        th.Thread.side_effect = lambda *a, **k: order.append("recovery_thread") or MagicMock()
        daemon._try_connect("token")

    assert order.index("ws_start") < order.index("recovery_thread")
