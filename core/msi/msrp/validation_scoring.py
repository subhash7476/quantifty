"""Per-day discriminant scoring for the A2 Validation Harness (dossier §3).

Computes s_cand (frozen artifact's expected_next_day_realized_vol via a DIRECT
evaluate() call — not the DRA KnowledgeObject wrapper), s_fix (hardcoded VIX gate),
s_vix (raw VIX), and the label Y = 1[RV_{t+1} > trailing-20d median]. Pure over the
supplied closes_by_day / vix_series so it is unit-testable on synthetic data.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Tuple

import numpy as np
import pandas as pd

from core.msi.contracts.evidence import Evidence
from core.msi.msrp.forward_vol import compute_daily_rv, compute_har_features

MEDIAN_WINDOW = 20  # trailing-20-trading-day median (dossier §3.1)


@dataclass(frozen=True)
class ScoredWindow:
    dates: Tuple[str, ...]
    s_cand: np.ndarray       # predicted E[RV_{t+1}] (estimate value)
    s_fix: np.ndarray
    s_vix: np.ndarray
    y: np.ndarray
    s_unc: np.ndarray        # predicted uncertainty (estimate.uncertainty) — for calibration
    rv_next: np.ndarray      # actual RV_{t+1} — for calibration coverage
    n_dropped_boundary: int
    requested_window: Tuple[str, str]


def vix_regime(vix: float) -> int:
    if vix < 15.0:
        return 0
    if vix < 25.0:
        return 1
    return 2


def build_day_evidence(
    rv_daily: float, rv_weekly: float, rv_monthly: float, vix: float, as_of: datetime
) -> Tuple[Evidence, ...]:
    fields = [
        ("rv_daily", rv_daily),
        ("rv_weekly", rv_weekly),
        ("rv_monthly", rv_monthly),
        ("vix_close", vix),
    ]
    return tuple(
        Evidence(
            evidence_id=f"{name}|{as_of.isoformat()}",
            source_observation_ids=(),
            construction_timestamp=as_of,
            evidence_type=name,
            evidence_value=float(value),
            artifact_version="v1.0.0",
            provenance_metadata={},
            quality_metadata={},
            version="1.0",
        )
        for name, value in fields
    )


def score_window(
    artifact,
    closes_by_day: Dict[pd.Timestamp, np.ndarray],
    vix_series: pd.Series,
    window_start: str,
    window_end: str,
) -> ScoredWindow:
    rv = compute_daily_rv(closes_by_day)
    feats = compute_har_features(rv)
    vix = vix_series.copy()
    vix.index = pd.DatetimeIndex([pd.Timestamp(d).normalize() for d in vix.index])

    ws = pd.Timestamp(window_start)
    we = pd.Timestamp(window_end)

    med = rv.rolling(window=MEDIAN_WINDOW, min_periods=MEDIAN_WINDOW).median()
    rv_next = rv.shift(-1)

    dates, s_cand, s_fix, s_vix, y, s_unc, rvn = [], [], [], [], [], [], []
    n_dropped = 0
    for t in feats.index:
        if t < ws or t > we:
            continue
        if t not in vix.index or pd.isna(med.get(t, np.nan)):
            continue
        rvt_next = rv_next.get(t, np.nan)
        if pd.isna(rvt_next):
            n_dropped += 1
            continue
        row = feats.loc[t]
        vix_t = float(vix.loc[t])
        ev = build_day_evidence(
            float(row["rv_daily"]), float(row["rv_weekly"]), float(row["rv_monthly"]),
            vix_t, t.to_pydatetime(),
        )
        ms = artifact.evaluate(ev)
        dates.append(t.date().isoformat())
        s_cand.append(float(ms.estimates[0].value))
        s_unc.append(float(ms.estimates[0].uncertainty))
        s_fix.append(float(vix_regime(vix_t)))
        s_vix.append(vix_t)
        rvn.append(float(rvt_next))
        y.append(1 if float(rvt_next) > float(med.loc[t]) else 0)

    return ScoredWindow(
        dates=tuple(dates),
        s_cand=np.array(s_cand, dtype=float),
        s_fix=np.array(s_fix, dtype=float),
        s_vix=np.array(s_vix, dtype=float),
        y=np.array(y, dtype=int),
        s_unc=np.array(s_unc, dtype=float),
        rv_next=np.array(rvn, dtype=float),
        n_dropped_boundary=n_dropped,
        requested_window=(window_start, window_end),
    )
