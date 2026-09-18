"""JEV-NMS-1 A3 — L3 operator ruling (tie rule, L3 baseline, L5 halt threshold).

The A3 addendum is checked against its pinned SHA-256 and its references
(F1 configuration, A2 addendum, protocol, Amendment 2, L3 run record, L3
report) before use. Arithmetic is exact: fractions, never float differences.
"""
from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
A3_ADDENDUM = REPO / "governance" / "jev_nms_1" / "config_amendment_3.json"
EXPECTED_A3_SHA256 = "d4dfe8614326aca885efdd978f28c3c366c29127d3edf20c230ef071c6455e63"
REFERENCES = ("f1_configuration", "a2_addendum", "protocol_document", "amendment_2",
              "l3_run_record", "l3_report")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_a3() -> dict:
    if _sha256(A3_ADDENDUM) != EXPECTED_A3_SHA256:
        raise RuntimeError("config_amendment_3.json does not match its pinned SHA-256")
    a3 = json.loads(A3_ADDENDUM.read_text(encoding="utf-8"))
    for key in REFERENCES:
        ref = a3[key]
        if _sha256(REPO / ref["file"]) != ref["sha256"]:
            raise RuntimeError(f"{ref['file']} does not match its A3 reference")
    return a3


def frozen_argmax(probs: dict, class_order: list[str]) -> str:
    """First class in the frozen order whose probability equals the maximum."""
    top = max(probs[c] for c in class_order)
    return next(c for c in class_order if probs[c] == top)


def l5_threshold(agreements: int, pairs: int, pp_below: int) -> Fraction:
    return Fraction(agreements, pairs) - Fraction(pp_below, 100)


def l5_halts(agreements: int, pairs: int, threshold: Fraction) -> bool:
    return Fraction(agreements, pairs) < threshold
