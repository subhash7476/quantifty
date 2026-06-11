"""
MM7E §6 — composition acceptance for the production composition root.

scripts.fno_runner.build_runner constructs the five E1 objects with the correct
settings and conditions the master-readiness checker on the universe
(Finding E1-c): present for an F&O universe, omitted for equity. Design B
(ADR-MM7E-1): the root ACCEPTS the SignalSource by injection and does not build
one — asserted here by passing a source through and reading it back off the
driver.

Built with the MM7C/MM7D.1 isolation construction (monkeypatch
handler_mod.ExecutionStore -> tmp; Finding E1-a). No real data / live provider /
RealTimeClock is touched.
"""

from core.execution.handler import ExecutionHandler, ExecutionMode
from core.brokers.paper_broker import PaperBroker
from core.runtime.config import Mode
from core.instruments.master_readiness import ReadinessState

from _runner_harness import DERIV, EQUITY, NoopSource, build, make_master

import scripts.fno_runner as fno_runner


def test_runner_builds_handler_with_load_db_state_true(tmp_path, monkeypatch):
    # The handler is the recovery/ledger authority; the root must build it with
    # recovery on (handler.py:186-187, ADR-001). Capture the construction kwarg.
    captured = {}
    real_ctor = fno_runner.ExecutionHandler

    def _spy(*args, **kwargs):
        captured.update(kwargs)
        return real_ctor(*args, **kwargs)

    monkeypatch.setattr(fno_runner, "ExecutionHandler", _spy)
    d = build(tmp_path, monkeypatch, source=NoopSource(), symbols=(EQUITY,))

    assert captured["load_db_state"] is True
    assert isinstance(d._execution, ExecutionHandler)


def test_runner_constructs_paperbroker_for_paper_rung(tmp_path, monkeypatch):
    # The paper rung's broker IS PaperBroker (synthetic fills, no capital).
    d = build(tmp_path, monkeypatch, source=NoopSource(), symbols=(EQUITY,))
    assert isinstance(d._execution.broker, PaperBroker)
    assert d._execution.config.mode is ExecutionMode.PAPER


def test_runner_targets_mode_live_executionmode_paper_first(tmp_path, monkeypatch):
    # E2: the first supported runtime is Mode.LIVE + ExecutionMode.PAPER.
    d = build(tmp_path, monkeypatch, source=NoopSource(), symbols=(EQUITY,))
    assert d.config.mode is Mode.LIVE
    assert d._execution.config.mode is ExecutionMode.PAPER


def test_runner_omits_checker_for_equity_universe(tmp_path, monkeypatch):
    # Finding E1-c carve-out: equity-only LIVE legitimately has no checker; and
    # Design B — the injected source is what the driver carries (the root did not
    # construct it).
    source = NoopSource()
    d = build(tmp_path, monkeypatch, source=source, symbols=(EQUITY,))
    assert d._master_readiness is None
    assert d._source is source


def test_runner_injects_master_readiness_when_derivatives(tmp_path, monkeypatch):
    # Finding E1-c / W4: an F&O universe gets the REAL resolver-backed checker,
    # built over the fixture master and returning FRESH when invoked (proving it
    # is the real factory, not a hand-written verdict lambda).
    master = make_master(tmp_path)
    d = build(tmp_path, monkeypatch, source=NoopSource(), symbols=(DERIV,),
              underlyings=["NIFTY"], master_db_path=master)
    assert d._master_readiness is not None
    assert d._master_readiness().state is ReadinessState.FRESH
