"""M4a-CE characterization outcome, mapped onto the Vault closure-ledger vocabulary (mapping fixed before any result).

This is a GR-1.4 NON-CONFIRMATORY characterization: TRAIN and VAL are signal-spent windows (GR-1.3), so nothing here
can be called a confirmation and nothing feeds a gate. VAL cells that pass the Holm rule are "VAL-consistent".

  C4  a defect trigger fired (frozen-file mismatch, independent-verification disagreement, accounting failure)
  C5  no VAL-consistent cell: the pre-declared criterion was tested on data and failed  (construct-scoped)
  C6  >= 1 VAL-consistent cell: positive but incomplete - evidence sufficient to justify a FRESH pre-registered
      confirmatory experiment on an unread surface (construct-scoped; NOT a confirmation)
  C7-C9 unreachable here: no HOLDOUT exists in this package.
A VAL-consistent cell has Holm-adjusted (over the 4 primary cells) one-sided p < 0.05, d-bar > 0, and is not
attrition-fragile (BKV-1 rule: worst-case bound keeps the sign and its Holm-adjusted p < 0.05).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.m4a_compress import stats as S

ALPHA = 0.05


def _key(r) -> tuple:
    return (int(r.h), str(r.comparator))


def val_consistent(tab: pd.DataFrame, alpha: float = ALPHA) -> tuple[list, dict]:
    prim = tab.dropna(subset=["d_p_one"])
    adj = S.holm({_key(r): r.d_p_one for r in prim.itertuples()})
    adj_b = S.holm({_key(r): r.bound_d_p_one for r in prim.itertuples() if np.isfinite(r.bound_d_p_one)})
    out, info = [], {}
    for r in prim.itertuples():
        k = _key(r)
        fragile = (not np.isfinite(r.bound_d_mean)) or r.bound_d_mean <= 0 or adj_b.get(k, 1.0) >= alpha
        info[k] = {"holm_p": adj[k], "fragile": bool(fragile), "d_mean": r.d_mean}
        if adj[k] < alpha and r.d_mean > 0 and not fragile:
            out.append(k)
    return out, info


def classify(val_tab: pd.DataFrame, defects: list | None = None, alpha: float = ALPHA) -> dict:
    defects = list(defects or [])
    cells, info = val_consistent(val_tab, alpha)
    if defects:
        label = "C4 (defect trigger fired - no conclusion)"
    elif not cells:
        label = "C5 (construct-scoped; NON-CONFIRMATORY characterization: no VAL-consistent cell; M4a stays open)"
    else:
        label = ("C6-equivalent (construct-scoped; NON-CONFIRMATORY characterization: VAL-consistent signal - justifies a "
                 "fresh pre-registered test on an unread surface, is not a confirmation)")
    return {"label": label, "defects": defects, "val_consistent": cells, "val_info": info}
