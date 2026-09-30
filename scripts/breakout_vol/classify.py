"""BKV-1 classification: the protocol's precedence-ordered, mutually exclusive tree (pure function).

Vault closure-ledger vocabulary (mapping fixed in the protocol before any result):
  C4  defect trigger fired (frozen file changed, independent-verification disagreement, benchmark identity
      failure, attrition/NaN cap) -> no conclusion
  C5  the pre-registered criterion was tested on data and failed: no VAL-confirmed cell, OR a VAL-confirmed
      cell set that the one-shot HOLDOUT did not confirm (construct-scoped)
  C6  >= 1 VAL-confirmed cell and the HOLDOUT is not read (unspent / not authorised): positive but incomplete
  C7  HOLDOUT-confirmed (clean, non-fragile) but the economic gate fails
  C8  HOLDOUT-confirmed and the economic gate passes
  C9  independent replication window - unreachable on this substrate
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.breakout_vol import stats as S

ALPHA = 0.05


def primary(tab: pd.DataFrame) -> pd.DataFrame:
    return tab.dropna(subset=["d_p_one"])


def cell_key(r) -> tuple:
    return (int(r.N), int(r.H), str(r.side))


def val_confirmed(val_tab: pd.DataFrame, alpha: float = ALPHA) -> tuple[list, dict]:
    """Holm over ALL primary VAL cells; confirmed iff adjusted p < alpha, mean(B-C) > 0 and not attrition-fragile."""
    prim = primary(val_tab)
    adj = S.holm({cell_key(r): r.d_p_one for r in prim.itertuples()})
    adj_bound = S.holm({cell_key(r): r.bound_d_p_one for r in prim.itertuples() if np.isfinite(r.bound_d_p_one)})
    out, info = [], {}
    for r in prim.itertuples():
        k = cell_key(r)
        fragile = (not np.isfinite(r.bound_d_mean)) or r.bound_d_mean <= 0 or adj_bound.get(k, 1.0) >= alpha
        info[k] = {"holm_p": adj[k], "fragile": bool(fragile), "d_mean": r.d_mean}
        if adj[k] < alpha and r.d_mean > 0 and not fragile:
            out.append(k)
    return out, info


def holdout_confirmed(v_cells: list, hold_tab: pd.DataFrame, alpha: float = ALPHA) -> tuple[list, dict]:
    if not v_cells:
        return [], {}
    prim = primary(hold_tab)
    rows = {cell_key(r): r for r in prim.itertuples()}
    adj = S.holm({c: rows[c].d_p_one for c in v_cells if c in rows})
    adj_bound = S.holm({c: rows[c].bound_d_p_one for c in v_cells if c in rows and np.isfinite(rows[c].bound_d_p_one)})
    out, info = [], {}
    for c in v_cells:
        r = rows.get(c)
        if r is None:
            continue
        fragile = (not np.isfinite(r.bound_d_mean)) or r.bound_d_mean <= 0 or adj_bound.get(c, 1.0) >= alpha
        info[c] = {"holm_p": adj[c], "fragile": bool(fragile), "d_mean": r.d_mean}
        if adj[c] < alpha and r.d_mean > 0 and not fragile:
            out.append(c)
    return out, info


def classify(val_tab: pd.DataFrame, hold_tab: pd.DataFrame | None, econ_pass: dict | None = None,
             defects: list | None = None, alpha: float = ALPHA) -> dict:
    defects = list(defects or [])
    v, vinfo = val_confirmed(val_tab, alpha)
    h, hinfo = ([], {}) if hold_tab is None else holdout_confirmed(v, hold_tab, alpha)
    econ = [c for c in h if (econ_pass or {}).get(c, False)]
    if defects:
        label = "C4"
    elif not v:
        label = "C5"
    elif hold_tab is None:
        label = "C6"
    elif not h:
        label = "C5"
    elif econ:
        label = "C8"
    else:
        label = "C7"
    return {"label": label, "defects": defects, "val_confirmed": v, "val_info": vinfo,
            "holdout_read": hold_tab is not None, "holdout_confirmed": h, "holdout_info": hinfo,
            "economic_pass_cells": econ}
