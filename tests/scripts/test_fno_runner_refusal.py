"""
MM7E §4/§6 — the refusal contract at the composition root.

These are the SEMANTIC refusals the driver does not own (the driver already
refuses missing clock/provider/LIVE-handler inside run()). The composition root
adds: a live run needs a source (the T1 acceptance predicate); a live F&O
universe needs master readiness (its underlyings — W4); ExecutionMode.LIVE needs
a broker-positions reconciliation source (deferred to #6). A vacuous paper
reconcile WARNS (no real book to diverge from) rather than refusing.

Refuse > warn > fallback (Constitution §7): a trading runtime never falls back.
"""

import logging

import pytest

from core.execution.handler import ExecutionMode

from _runner_harness import DERIV, EQUITY, NoopSource, build


def test_refuses_when_source_missing():
    # The most dangerous failure mode is a live runtime with no signal origin
    # (looks healthy, does nothing). The root refuses before constructing the
    # driver — no isolation needed, it raises before touching any collaborator.
    with pytest.raises(ValueError, match="SignalSource"):
        from scripts.fno_runner import build_runner
        build_runner(source=None, symbols=[EQUITY])


def test_refuses_fno_live_without_master_readiness():
    # A live F&O run with no checker is the W4 trap: a vacuous pass that also
    # disables G1 restore-canonicalization. The root refuses an F&O universe with
    # no underlyings (underlyings are not derivable from broker keys).
    with pytest.raises(ValueError, match="master readiness|underlyings"):
        from scripts.fno_runner import build_runner
        build_runner(source=NoopSource(), symbols=[DERIV], underlyings=None)


def test_refuses_live_executionmode_without_live_broker():
    # ExecutionMode.LIVE without a real BrokerAdapter is an unsafe wiring —
    # PaperBroker synthetic fills would silently produce a LIVE-flagged run with
    # no real orders. The root refuses before touching any other collaborator.
    with pytest.raises(ValueError, match="BrokerAdapter|broker"):
        from scripts.fno_runner import build_runner
        build_runner(source=NoopSource(), symbols=[EQUITY],
                     execution_mode=ExecutionMode.LIVE, broker=None)


def test_warns_when_reconciliation_vacuous_on_paper(tmp_path, monkeypatch, caplog):
    # At ExecutionMode.PAPER a vacuous reconcile is acceptable, but the operator
    # must KNOW the gate has no teeth yet — emit a WARNING, do not refuse.
    with caplog.at_level(logging.WARNING, logger="scripts.fno_runner"):
        d = build(tmp_path, monkeypatch, source=NoopSource(), symbols=(EQUITY,),
                  broker_positions=None)
    assert d is not None  # did NOT refuse
    assert any("vacuous" in r.message.lower() or "reconcil" in r.message.lower()
               for r in caplog.records)
