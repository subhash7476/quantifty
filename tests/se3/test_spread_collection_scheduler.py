"""Tests for the SE-3 spread-collection scheduler wrapper — market-hours gate."""
import importlib

import pytest

import scripts.se3.schedule_spread_collection as w


@pytest.mark.parametrize("market_open,expected", [
    (False, 0),  # outside market hours / holiday / weekend -> no-op
])
def test_noop_when_market_closed(monkeypatch, market_open, expected):
    class FakeMH:
        @staticmethod
        def is_market_open():
            return market_open

    monkeypatch.setattr(
        "core.database.utils.market_hours.MarketHours.is_market_open",
        staticmethod(FakeMH.is_market_open),
    )
    monkeypatch.setattr(w.subprocess, "run", lambda *a, **k: pytest.fail(
        "collector must not run when market is closed"))
    assert w.main() == expected


def test_runs_collector_and_propagates_exit_when_market_open(monkeypatch):
    class FakeMH:
        @staticmethod
        def is_market_open():
            return True

    class FakeResult:
        returncode = 0
        stdout = "once: 15 observed, 3 skipped, 0 errors"
        stderr = ""

    calls = {}

    def fake_run(*args, **kwargs):
        calls["cmd"] = args[0]
        calls["cwd"] = kwargs.get("cwd")
        calls["timeout"] = kwargs.get("timeout")
        return FakeResult()

    monkeypatch.setattr(
        "core.database.utils.market_hours.MarketHours.is_market_open",
        staticmethod(FakeMH.is_market_open),
    )
    monkeypatch.setattr(w.subprocess, "run", fake_run)
    assert w.main() == 0
    assert calls["cmd"][-2].endswith("collect_option_spreads.py")
    assert calls["cmd"][-1] == "--once"
    assert calls["cwd"] is not None
    assert calls["timeout"] == 120


def test_propagates_nonzero_when_market_open(monkeypatch):
    class FakeMH:
        @staticmethod
        def is_market_open():
            return True

    class FakeResult:
        returncode = 2
        stdout = "once: 0 observed, 0 skipped, 0 errors"
        stderr = ""

    monkeypatch.setattr(
        "core.database.utils.market_hours.MarketHours.is_market_open",
        staticmethod(FakeMH.is_market_open),
    )
    monkeypatch.setattr(w.subprocess, "run",
                        lambda *a, **k: FakeResult())
    assert w.main() == 2
