from unittest.mock import MagicMock
from core.database.ingestors.websocket_ingestor import WebSocketIngestor

def test_handle_message_only_enqueues_raw_bytes():
    writer = MagicMock()
    ing = WebSocketIngestor(["X"], access_token="t", writer=writer)
    ing._handle_message(b"\x08\x01raw-bytes")
    writer.enqueue_frame.assert_called_once_with(b"\x08\x01raw-bytes")

def test_ping_params_stored():
    writer = MagicMock()
    ing = WebSocketIngestor(["X"], access_token="t", writer=writer,
                            ping_interval=10.0, ping_timeout=30.0)
    assert ing.ping_interval == 10.0 and ing.ping_timeout == 30.0

def test_tickbuffer_removed():
    import core.database.ingestors.websocket_ingestor as mod
    assert not hasattr(mod, "TickBuffer")
