"""VWAP-XREV classification: the protocol's precedence-ordered, mutually exclusive tree.

Inputs are the PRIMARY-variant VAL and HOLDOUT cell tables only. TRAIN and every robustness
result never enter. Pure function: same tables -> same label.

Tree (first match wins):
  C4  a pre-listed defect trigger fired (hash mismatch, membership-agreement failure,
      NaN-outcome share above the cap in a primary cell)
  C5  no cell is VAL-confirmed
  C8  >=1 VAL-confirmed cell is HOLDOUT-confirmed, survives the microstructure qualifier,
      and passes the economic gate
  C7  same, economic gate fails
  C6  >=1 VAL-confirmed cell, none HOLDOUT-confirmed, HOLDOUT point estimate > 0 in >=1 of them
  C5  otherwise (VAL-confirmed, HOLDOUT null or reversed)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.vwap_rev import stats as S

ALPHA = 0.05
NAN_CAP = 0.02
MICRO_HORIZONS = (5, 10)


def _primary(tab: pd.DataFrame) -> pd.DataFrame:
    return tab[tab["side"] != "pooled"]


def val_confirmed(val_tab: pd.DataFrame, alpha: float = ALPHA) -> list[tuple]:
    """Cells whose Holm-adjusted (over all 10 primary VAL cells) one-sided p < alpha with mean > 0."""
    prim = _primary(val_tab)
    adj = S.holm({(r.side, r.H): r.p_one_nw for r in prim.itertuples()})
    return [(r.side, r.H) for r in prim.itertuples()
            if adj[(r.side, r.H)] < alpha and r.session_mean_bp > 0]


def holdout_confirmed(v_cells: list[tuple], hold_tab: pd.DataFrame, delay2_tab: pd.DataFrame | None,
                      alpha: float = ALPHA) -> tuple[list[tuple], list[tuple]]:
    """HOLDOUT Holm over the VAL-confirmed cells only; then the delay-2 microstructure qualifier.
    Returns (confirmed_and_clean, microstructure_contaminated)."""
    if not v_cells:
        return [], []
    prim = _primary(hold_tab).set_index(["side", "H"])
    adj = S.holm({c: prim.loc[c, "p_one_nw"] for c in v_cells})
    hold_ok = [c for c in v_cells if adj[c] < alpha and prim.loc[c, "session_mean_bp"] > 0]
    clean, dirty = [], []
    d2 = _primary(delay2_tab).set_index(["side", "H"]) if delay2_tab is not None else None
    for c in hold_ok:
        if c[1] in MICRO_HORIZONS:
            m2 = d2.loc[c, "session_mean_bp"] if d2 is not None and c in d2.index else np.nan
            if not (np.isfinite(m2) and m2 > 0):
                dirty.append(c)
                continue
        clean.append(c)
    return clean, dirty


def classify(val_tab: pd.DataFrame, hold_tab: pd.DataFrame, delay2_tab: pd.DataFrame | None,
             net_lb: dict, defects: list[str] | None = None, alpha: float = ALPHA) -> dict:
    """net_lb: {(side, H): one-sided bootstrap lower bound of the HOLDOUT net mean at the base kappa,
    computed at level alpha/m by the caller for m = number of clean HOLDOUT-confirmed cells}."""
    defects = list(defects or [])
    for name, tab in (("VAL", val_tab), ("HOLDOUT", hold_tab)):
        prim = _primary(tab)
        bad = prim[prim["nan_share"] > NAN_CAP]
        if len(bad):
            defects.append(f"NaN-outcome share > {NAN_CAP:.0%} in {name} cells "
                           + ",".join(f"{r.side}/h{r.H}" for r in bad.itertuples()))
    v = val_confirmed(val_tab, alpha)
    clean, dirty = holdout_confirmed(v, hold_tab, delay2_tab, alpha)
    econ = [c for c in clean if net_lb.get(c, -np.inf) > 0]
    hp = _primary(hold_tab).set_index(["side", "H"])
    pos_holdout = [c for c in v if hp.loc[c, "session_mean_bp"] > 0]
    if defects:
        label = "C4"
    elif not v:
        label = "C5"
    elif clean and econ:
        label = "C8"
    elif clean:
        label = "C7"
    elif pos_holdout:
        label = "C6"
    else:
        label = "C5"
    return {"label": label, "defects": defects, "val_confirmed": v,
            "holdout_confirmed_clean": clean, "microstructure_contaminated": dirty,
            "economic_pass_cells": econ, "holdout_positive_among_val_confirmed": pos_holdout}
