"""Composite gate — the lift-first rule for combining sleeves.

IVOL section 9 gate 4 (IVOL_COMPOSITE_CHECK_REPORT.md) asked only
"composite power >= 0.80" and returned PASS on a composite whose IR (0.6005) was
BELOW Carry standalone (0.6159). That PASS authorized opening the sealed window,
which then failed. The 0.80 hurdle is an absolute floor and cannot detect a
combination that destroys value.

This gate evaluates three conditions IN ORDER, and stops at the first failure:

  1. LIFT      -- composite IR must EXCEED the best standalone leg's IR, both
                  measured on the same intersection. A combination that does not
                  beat its own best leg is a dilution, not a combination.
  2. SIGN      -- every leg's realized IC sign must match a sign that was
                  REGISTERED before the data was read. A leg with no registered
                  sign, or whose realized sign opposes its registration, forces a
                  sign chosen from data and has no valid confirmatory test.
  3. POWER     -- composite power at n* must clear the hurdle.

Order matters: power is the last check, not the first, because a diluting
composite can clear 0.80 on the strength of one leg alone.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.rfa.power import power_at  # noqa: E402

HURDLE = 0.80


@dataclass(frozen=True)
class Leg:
    name: str
    ic: np.ndarray          # per-formation IC series on the common intersection
    registered_sign: int    # +1 / -1; 0 means none was registered
    sign_falsified: bool = False
    """Set when a LATER out-of-sample read reversed this leg's registered sign.

    The sign check below compares the registered sign against the series it is
    handed. Hand it TRAIN+HOLDOUT and IVOL passes -- its IC was negative as
    registered on those windows. IVOL's SEALED read then flipped it (+0.018, net
    -13.78%), and that read is invisible to a gate looking only at the earlier
    series. This flag makes the falsification visible so the gate cannot approve
    a direction the data has already refuted."""


@dataclass(frozen=True)
class Verdict:
    passed: bool
    stage: str              # "LIFT" | "SIGN" | "POWER" | "ALL"
    reason: str
    lift: float
    ir_composite: float
    ir_best_leg: float
    best_leg: str
    power: float
    sign_failures: tuple = field(default=())


def _ir(ic):
    sd = float(np.std(ic, ddof=1))
    return abs(float(np.mean(ic))) / sd if sd > 0 else float("nan")


def evaluate(composite_ic, legs, n_star, hurdle=HURDLE, two_sided=False):
    """composite_ic: IC series of the composite. legs: list[Leg]. All series must
    be measured on the SAME formations, or the lift comparison is meaningless."""
    if len(legs) < 2:
        raise ValueError("a composite needs at least two legs")
    n = len(composite_ic)
    for leg in legs:
        if len(leg.ic) != n:
            raise ValueError(
                f"leg {leg.name} has {len(leg.ic)} formations, composite has {n} — "
                "lift requires a common intersection")

    ir_c = _ir(composite_ic)
    ir_legs = {leg.name: _ir(leg.ic) for leg in legs}
    best_leg = max(ir_legs, key=ir_legs.get)
    ir_best = ir_legs[best_leg]
    lift = ir_c / ir_best if ir_best > 0 else float("nan")

    mean_c = float(np.mean(composite_ic))
    sd_c = float(np.std(composite_ic, ddof=1))
    power = power_at(abs(mean_c), sd_c, n_star, two_sided=two_sided)

    def _v(passed, stage, reason, sign_failures=()):
        return Verdict(passed, stage, reason, lift, ir_c, ir_best, best_leg,
                       power, tuple(sign_failures))

    if not (lift > 1.0):
        return _v(False, "LIFT",
                  f"composite IR {ir_c:.4f} does not exceed best leg {best_leg} "
                  f"{ir_best:.4f} (lift {lift:.3f}) — dilution, not combination")

    sign_failures = []
    for leg in legs:
        realized = int(np.sign(np.mean(leg.ic)))
        if leg.registered_sign == 0:
            sign_failures.append(f"{leg.name}: no registered sign")
        elif leg.registered_sign != realized:
            sign_failures.append(
                f"{leg.name}: realized sign {realized:+d} opposes registered "
                f"{leg.registered_sign:+d}")
        elif leg.sign_falsified:
            sign_failures.append(
                f"{leg.name}: registered sign {leg.registered_sign:+d} matches this "
                "series but was REVERSED by a later out-of-sample read")
    if sign_failures:
        return _v(False, "SIGN",
                  "composite requires a sign read from data: " + "; ".join(sign_failures),
                  sign_failures)

    if power < hurdle:
        return _v(False, "POWER",
                  f"composite power {power:.4f} < hurdle {hurdle:.2f} at n*={n_star}")

    return _v(True, "ALL",
              f"lift {lift:.3f} > 1, signs registered, power {power:.4f} >= {hurdle:.2f}")
