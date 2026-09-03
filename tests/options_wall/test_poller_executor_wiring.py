"""The poll cycle invokes the paper executor once per underlying."""
from core.options_wall.poller import WallPoller
from core.data.options_provider import OptionChainRow


class _FakeProvider:
    def get_weekly_expiry(self, sym):
        return "2026-08-18"

    def fetch_option_chain(self, sym, expiry):
        return [OptionChainRow(strike=100.0, option_type="CE", instrument_key="NSE_FO|1",
                               tradingsymbol="T1", expiry=expiry, ltp=5.0,
                               underlying_ltp=100.0)]


def test_poll_cycle_invokes_executor(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("core.options_wall.poller.UpstoxMarketData",
        lambda: type("M", (), {"fetch_quotes_batch": lambda self, k: {"quotes": {}}})())
    p = WallPoller(heartbeat_path=tmp_path / "hb.json", pid_path=tmp_path / "p.pid",
                   snapshot_db_path=tmp_path / "w.duckdb")
    monkeypatch.setattr(p, "_executor_step",
                        lambda name, sym, rows, expiry: calls.append(name))
    p._poll_cycle(_FakeProvider())
    assert set(calls) == {"NIFTY", "BANKNIFTY", "SENSEX"}
