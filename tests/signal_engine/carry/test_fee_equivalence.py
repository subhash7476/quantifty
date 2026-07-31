"""WS-A.2 — Proven equivalence between canonical fee module and Carry SEALED
harness inline model.

Purpose (CARRY_IMPLEMENTATION_BRIDGE.md section 5.1): establish whether the
SEALED +20.52% transfers to the canonical module WITHOUT re-reading the SEALED
window (one-shot rule, SEALED protocol section 2).

run_net_spread.py now calls the canonical module directly, so comparisons
against it are structurally circular (both call the same code, different return
shapes). The load-bearing equivalence proof is the run_sealed vs module
comparison — run_sealed is the frozen one-shot artifact that stays inline.

FINDINGS (post WS-A refactor):
  - STT is BYTE-IDENTICAL over every research window.
  - SEALED diverges ONLY on post-2024-10 exchange_txn (module applies the
    era-accurate 0.00189% MII reduction; run_sealed uses flat 0.0021%) ->
    canonical SEALED net marginally ABOVE +20.52%.
  - run_sealed.stt_rate returns 0.0001 for pre-2008 dates (its else branch);
    the module returns 0.0. Immaterial — no window covers pre-2008.
"""

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from core.execution.futures.futures_fees import futures_fees, stt_futures_rate
from scripts.signal_engine.carry.run_sealed import (
    _leg_fees as sealed_leg_fees,
    stt_rate as sealed_stt_rate,
)

TV = 1_000_000.0  # Rs 10 lakh notional per leg


# ============================================================
# STT byte-identity over every research window (the §5.1 fix target)
# ============================================================

def test_stt_identical_sealed_vs_run_sealed():
    # run_sealed.stt_rate is 3-tier; the module is 4-tier (it carries the
    # 0.017% 2008-06-01 -> 2013-05-31 tier that run_sealed lacks). They must
    # still match on every date any research window can reach, i.e. from
    # 2013-06-01 onward — see the divergence test below.
    for d in [date(2023, 3, 31), date(2023, 4, 1), date(2024, 9, 30),
              date(2024, 10, 1), date(2025, 6, 1), date(2026, 7, 20)]:
        assert stt_futures_rate(d) == sealed_stt_rate(d), (
            f"SEALED STT rate mismatch at {d}: module={stt_futures_rate(d)} "
            f"sealed={sealed_stt_rate(d)}"
        )
        f = futures_fees(side="SELL", trade_value=TV, trade_date=d)
        s = sealed_leg_fees(side="SELL", trade_value=TV, trade_date=d)
        assert f.stt == s["stt"], f"SEALED STT leg mismatch at {d}"


def test_run_sealed_stt_pre_2008_quirk_documented():
    """run_sealed.stt_rate returns 0.0001 for pre-2008 (its else branch); the
    module returns 0.0. Immaterial - no research window covers pre-2008 - but
    pinned here so it is a known, documented divergence, not a silent one."""
    assert sealed_stt_rate(date(2008, 5, 31)) == 0.0001
    assert stt_futures_rate(date(2008, 5, 31)) == 0.0


def test_run_sealed_stt_2008_to_2013_divergence_documented():
    """2008-06-01 -> 2013-05-31: the module applies the real 0.017% rate;
    run_sealed's inline 3-tier table flattens it to 0.0001.

    Same class as the pre-2008 quirk above and equally immaterial - the
    futures substrate begins 2016-02-11, so no research window can reach these
    dates. run_sealed.py is a FROZEN one-shot artifact and is deliberately NOT
    edited to match. Pinned here so the divergence is loud rather than silent.
    """
    for d in (date(2008, 6, 1), date(2010, 1, 1), date(2013, 5, 31)):
        assert sealed_stt_rate(d) == 0.0001
        assert stt_futures_rate(d) == 0.00017

    # The divergence closes at the Budget 2013 cut and never reopens.
    for d in (date(2013, 6, 1), date(2016, 2, 11), date(2023, 3, 31)):
        assert sealed_stt_rate(d) == stt_futures_rate(d) == 0.0001


# ============================================================
# SEALED vs run_sealed (the model that produced +20.52%)
# ============================================================

def test_sealed_pre_mii_fully_identical():
    """SEALED 2023-01 -> 2024-09-30: every component matches exactly."""
    for d in [date(2023, 6, 15), date(2024, 9, 30)]:
        for side in ("BUY", "SELL"):
            f = futures_fees(side=side, trade_value=TV, trade_date=d)
            s = sealed_leg_fees(side=side, trade_value=TV, trade_date=d)
            assert abs(f.total - s["total"]) < 1e-9, f"pre-MII total at {d} {side}"


def test_sealed_post_mii_exchange_txn_diverges_conservatively():
    """SEALED 2024-10-01 -> 2026-07-20: the canonical module applies the
    era-accurate 0.00189% MII reduction; run_sealed uses flat 0.0021%. Every
    other component (incl. STT) matches; canonical total is LOWER -> canonical
    SEALED net lands ABOVE +20.52%."""
    for d in [date(2024, 10, 1), date(2025, 6, 1), date(2026, 7, 20)]:
        for side in ("BUY", "SELL"):
            f = futures_fees(side=side, trade_value=TV, trade_date=d)
            s = sealed_leg_fees(side=side, trade_value=TV, trade_date=d)
            # matching components
            assert abs(f.brokerage - s["brokerage"]) < 1e-9
            assert abs(f.sebi_fee - s["sebi_fee"]) < 1e-9
            assert abs(f.stamp_duty - s["stamp_duty"]) < 1e-9
            assert abs(f.stt - s["stt"]) < 1e-9
            # exchange_txn: canonical LOWER
            assert abs(f.exchange_txn - TV * 0.0000189) < 1e-9
            assert abs(s["exchange_txn"] - TV * 0.000021) < 1e-9
            assert f.total < s["total"], (
                f"canonical SEALED total must be lower post-MII at {d} {side}: "
                f"module={f.total} sealed={s['total']}"
            )
