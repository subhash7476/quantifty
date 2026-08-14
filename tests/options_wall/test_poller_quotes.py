"""The wall poller fetches quotes each cycle and persists them with the chain."""
from core.options_wall.poller import WallPoller
from core.data import options_wall_store as store
from core.data.options_provider import OptionChainRow


class _FakeProvider:
    def get_weekly_expiry(self, sym):
        return "2026-08-18"

    def fetch_option_chain(self, sym, expiry):
        return [OptionChainRow(strike=100.0, option_type="CE", instrument_key="NSE_FO|1",
                               tradingsymbol="T1", expiry=expiry, ltp=5.0,
                               underlying_ltp=100.0)]


def test_poll_cycle_persists_quotes(tmp_path, monkeypatch):
    db = tmp_path / "wall.duckdb"
    monkeypatch.setattr(
        "core.options_wall.poller.UpstoxMarketData",
        lambda: type("M", (), {"fetch_quotes_batch":
            lambda self, keys: {"quotes": {"NSE_FO|1": {"best_bid": 4.9, "best_ask": 5.1}}}})(),
    )
    # keep the executor step out of this unit test
    monkeypatch.setattr(WallPoller, "_executor_step",
                        lambda self, name, sym, rows, expiry: None, raising=False)
    p = WallPoller(heartbeat_path=tmp_path / "hb.json", pid_path=tmp_path / "p.pid",
                   snapshot_db_path=db)
    p._poll_cycle(_FakeProvider())
    back = store.latest_snapshot("NSE_INDEX|Nifty 50", "2026-08-18", db_path=db)
    assert back[0].best_bid == 4.9 and back[0].best_ask == 5.1
