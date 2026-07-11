from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from core.msi.msrp.validation_scoring import (
    ScoredWindow,
    vix_regime,
    build_day_evidence,
    score_window,
)


def test_vix_regime_thresholds():
    assert vix_regime(14.9) == 0
    assert vix_regime(15.0) == 1
    assert vix_regime(24.9) == 1
    assert vix_regime(25.0) == 2


def test_build_day_evidence_has_four_named_features():
    ev = build_day_evidence(0.01, 0.011, 0.012, 13.0, datetime(2024, 3, 1))
    assert {e.evidence_type for e in ev} == {"rv_daily", "rv_weekly", "rv_monthly", "vix_close"}
    assert all(e.artifact_version == "v1.0.0" for e in ev)


def _synthetic_inputs(n_days=60):
    rng = np.random.default_rng(7)
    days = pd.bdate_range("2024-01-01", periods=n_days)
    closes_by_day = {}
    for d in days:
        base = 20000 + 100 * np.sin(d.dayofyear)
        closes_by_day[pd.Timestamp(d).normalize()] = base + rng.normal(0, 5, size=90).cumsum()
    vix = pd.Series(15 + 5 * np.cos(np.arange(n_days)), index=days, name="vix")
    return closes_by_day, vix


def test_score_window_shapes_and_boundary_drop():
    from core.msi.dra.filesystem_artifact_loader import FilesystemArtifactLoader
    root = Path(__file__).resolve().parents[3]
    artifact = FilesystemArtifactLoader().load(
        str(root / "core" / "msi" / "artifacts" / "forward_vol_v2")
    )
    closes_by_day, vix = _synthetic_inputs(60)
    sw = score_window(artifact, closes_by_day, vix, "2024-02-15", "2024-03-22")
    assert isinstance(sw, ScoredWindow)
    n = len(sw.dates)
    assert n > 0
    assert sw.s_cand.shape == sw.s_fix.shape == sw.s_vix.shape == sw.y.shape == (n,)
    assert sw.s_unc.shape == sw.rv_next.shape == (n,)
    assert np.all(sw.s_unc >= 0) and np.all(sw.rv_next > 0)
    assert set(np.unique(sw.y)).issubset({0, 1})
    assert sw.n_dropped_boundary >= 0
