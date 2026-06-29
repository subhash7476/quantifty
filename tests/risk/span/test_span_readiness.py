"""Block K — span_readiness evaluate/assess (MM9.4-S2)."""

from datetime import date
from typing import Optional

from core.instruments.master_readiness import ReadinessState
from core.risk.span.span_freshness import expected_span_date
from core.risk.span.span_readiness import (
    SpanReadinessVerdict,
    evaluate,
    assess,
    build_span_readiness,
)
from core.risk.span.span_repository import SpanRepository


def test_evaluate_ready_when_dates_match():
    verdict = evaluate(
        snapshot_date=date(2026, 6, 29),
        expected_date=date(2026, 6, 29),
    )
    assert verdict.state is ReadinessState.FRESH
    assert verdict.reason == "READY"


def test_evaluate_refuse_when_snapshot_absent():
    verdict = evaluate(
        snapshot_date=None,
        expected_date=date(2026, 6, 29),
    )
    assert verdict.state is ReadinessState.BLOCK
    assert "absent" in verdict.reason.lower()


def test_evaluate_refuse_when_stale():
    verdict = evaluate(
        snapshot_date=date(2026, 6, 27),
        expected_date=date(2026, 6, 29),
    )
    assert verdict.state is ReadinessState.BLOCK
    assert "stale" in verdict.reason.lower()


def test_assess_ready_when_load_succeeds():
    class _MockRepo:
        def load(self, d):
            class _Snap:
                snapshot_date = d
            return _Snap()

    verdict = assess(_MockRepo(), date(2026, 6, 29))
    assert verdict.state is ReadinessState.FRESH


def test_assess_refuse_when_load_raises():
    class _FailingRepo:
        def load(self, d):
            raise FileNotFoundError("no file")

    verdict = assess(_FailingRepo(), date(2026, 6, 29))
    assert verdict.state is ReadinessState.BLOCK


def test_assess_refuse_when_load_corrupt():
    class _CorruptRepo:
        def load(self, d):
            raise ValueError("checksum mismatch")

    verdict = assess(_CorruptRepo(), date(2026, 6, 29))
    assert verdict.state is ReadinessState.BLOCK


def test_build_span_readiness_returns_callable():
    repo = SpanRepository.__new__(SpanRepository)
    checker = build_span_readiness(repo)
    assert callable(checker)


def test_build_span_readiness_returns_readiness_verdict(tmp_path):
    from core.risk.span.span_snapshot import SpanSnapshot, SpanRiskArray
    import pickle
    snap_dir = tmp_path / "span"
    snap_dir.mkdir(exist_ok=True)
    snap = SpanSnapshot(date(2026, 6, 29), "v1", "NSE", "FO", "h", False, {}, {})
    with open(snap_dir / "nse_fo_span_2026-06-29.parquet", "wb") as f:
        pickle.dump(snap, f)
    repo = SpanRepository(snap_dir)
    checker = build_span_readiness(repo)
    verdict = checker()
    assert isinstance(verdict, SpanReadinessVerdict)
