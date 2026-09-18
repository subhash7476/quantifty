"""JEV-NMS-1 §13 L1 fence guard: which state may a Jev-calling stage touch.

Active sets per §10 / §23: S0 -> D-fit; L2 -> D-fit or D-eval; L3 -> D-fit or
D-eval; development -> D-eval. A state is callable only if its session is
§4-eligible (step-1 artifact) inside the stage's active set. Refused always:
H-exposed (no Jev calls), every buffer date (> F1), any date outside every
defined set, and any date whose store file is absent or beyond the store's
last file (store guard). P has no active set until F2 is set, so it refuses
everything.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

ACTIVE_SETS = {"S0": ("d_fit",), "L2": ("d_fit", "d_eval"), "L3": ("d_fit", "d_eval"),
               "development": ("d_eval",), "P": ()}
F1 = date(2026, 9, 18)


class FenceViolation(RuntimeError):
    """A stage attempted to touch a state outside its active set."""


class Fence:
    def __init__(self, eligibility: dict, store: Path):
        self._eligible = {name: {r["date"] for r in recs if r["eligible"]}
                          for name, recs in eligibility["sessions"].items()}
        files = sorted(p.stem for p in store.glob("*.duckdb"))
        self._store, self._store_last = store, files[-1] if files else None

    def check(self, stage: str, state_key: str) -> None:
        d = state_key[:10]
        if stage not in ACTIVE_SETS:
            raise FenceViolation(f"unknown stage {stage!r}")
        if date.fromisoformat(d) > F1:
            raise FenceViolation(f"{d} is a buffer/post-F1 date")
        if d in self._eligible.get("h_exposed", set()) or d >= "2026-01-01":
            raise FenceViolation(f"{d} is H-exposed: no Jev calls")
        if self._store_last is None or d > self._store_last or not (self._store / f"{d}.duckdb").exists():
            raise FenceViolation(f"{d} is beyond the store or its file is absent")
        if not any(d in self._eligible[s] for s in ACTIVE_SETS[stage]):
            raise FenceViolation(f"{d} is not an eligible session of {stage}'s active set "
                                 f"{ACTIVE_SETS[stage]}")
