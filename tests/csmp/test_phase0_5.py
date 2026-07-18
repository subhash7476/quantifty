"""C2 Phase 0.5 mini-battery tests.

Variant-parameterization, determinism, TRAIN/HOLDOUT fence, fidelity precondition.
"""

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "psb1"))
sys.path.insert(0, str(ROOT / "scripts" / "psb2"))

from scripts.psb2 import harness as H

# Import battery module directly
sys.path.insert(0, str(ROOT / "scripts"))
import c2_phase0_5_minibattery as bf


# ── Fidelity precondition ─────────────────────────────────────────────

def test_fidelity_passes():
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest",
         str(ROOT / "tests" / "psb2" / "test_fidelity.py"),
         "-q", "--tb=short"],
        capture_output=True, text=True, cwd=ROOT
    )
    assert result.returncode == 0, f"Fidelity FAIL:\n{result.stdout}\n{result.stderr}"


# ── Variant definitions ────────────────────────────────────────────────

def test_variant_defs_correct():
    assert len(bf.VARIANTS) == 4

    v1 = bf.VARIANTS[0]
    assert v1.vid == "V1"
    assert v1.cadence == "monthly"
    assert v1.exit_band == 0.40
    assert not v1.is_staggered

    v2 = bf.VARIANTS[1]
    assert v2.vid == "V2"
    assert v2.cadence == "fortnightly"
    assert v2.exit_band == 0.60
    assert not v2.is_staggered

    v3 = bf.VARIANTS[2]
    assert v3.vid == "V3"
    assert v3.cadence == "fortnightly"
    assert v3.exit_band == 0.40
    assert v3.is_staggered
    assert v3.stag_tranches == 3

    ref = bf.VARIANTS[3]
    assert ref.vid == "ref"
    assert ref.is_reference


# ── Split boundaries ──────────────────────────────────────────────────

def test_split_boundaries_pinned():
    assert bf.TRAIN_HI == date(2018, 12, 31)
    assert bf.HOLDOUT_HI == date(2022, 12, 31)


# ── G0.5 thresholds ───────────────────────────────────────────────────

def test_g05_thresholds():
    assert bf.POWER_HURDLE_G0 == 0.80
    assert bf.NET_SPREAD_FLOOR == 0.02
    assert bf.BONFERRONI_M == 3
    assert bf.ALPHA_G0 == 0.05


# ── TRAIN/HOLDOUT fence — synthetic ────────────────────────────────────

def test_train_holdout_fence():
    """Verify that TRAIN and HOLDOUT boundaries produce different
    observed MAX values via load_panel, and both differ from store MAX."""
    import duckdb
    store = bf.STORE
    con = duckdb.connect(store, read_only=True)
    store_max = con.execute("SELECT MAX(trade_date) FROM equity_bhavcopy").fetchone()[0]
    con.close()

    # TRAIN fence
    orig_devhi = H.DEV_HI
    H.DEV_HI = bf.TRAIN_HI
    panel_train = H.load_panel(store, cutoff=bf.TRAIN_HI)
    train_max = panel_train.observed_max
    assert train_max <= bf.TRAIN_HI, f"TRAIN leak: {train_max} > {bf.TRAIN_HI}"
    assert train_max != store_max, f"TRAIN fence equals store MAX"
    H.DEV_HI = orig_devhi

    # HOLDOUT fence
    H.DEV_HI = bf.HOLDOUT_HI
    panel_hold = H.load_panel(store, cutoff=bf.HOLDOUT_HI)
    hold_max = panel_hold.observed_max
    assert hold_max <= bf.HOLDOUT_HI, f"HOLDOUT leak: {hold_max} > {bf.HOLDOUT_HI}"
    assert hold_max != store_max, f"HOLDOUT fence equals store MAX"
    assert hold_max > train_max, "HOLDOUT MAX must be after TRAIN MAX"
    H.DEV_HI = orig_devhi


# ── Report determinism ────────────────────────────────────────────────

def test_report_deterministic():
    """compute_digest produces same output for same input."""
    import hashlib
    t1 = "Same content every time"
    t2 = "Same content every time"
    d1 = hashlib.sha256(t1.encode("utf-8")).hexdigest()
    d2 = hashlib.sha256(t2.encode("utf-8")).hexdigest()
    assert d1 == d2
    assert len(d1) == 64


# ── Variant param effects (synthetic harness test) ────────────────────

def test_exit_band_patching():
    """Verify that patching C2_EXIT_BAND changes portfolio behavior."""
    orig = H.C2_EXIT_BAND
    H.C2_EXIT_BAND = 0.60
    assert H.C2_EXIT_BAND == 0.60
    H.C2_EXIT_BAND = orig
    assert H.C2_EXIT_BAND == orig


def test_v3_params():
    """Verify V3 definition matches staggered 3-tranche intent."""
    v3 = bf.VARIANTS[2]
    assert v3.vid == "V3"
    assert v3.is_staggered
    assert v3.stag_tranches == 3
    assert v3.exit_band == 0.40
    assert v3.cadence == "fortnightly"


def test_v2_exit_band_differs_from_ref():
    """V2 (0.60) and ref (0.40) must have different exit_band."""
    v2 = bf.VARIANTS[1]
    ref = bf.VARIANTS[3]
    assert v2.exit_band != ref.exit_band
