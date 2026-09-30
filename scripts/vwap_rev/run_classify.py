"""VWAP-XREV: apply the frozen classification tree to the VAL/HOLDOUT primary tables (run after HOLDOUT)."""
from __future__ import annotations

import json
import sys

import pandas as pd

from scripts.vwap_rev import analyze as A
from scripts.vwap_rev import classify as K
from scripts.vwap_rev import common as C
from scripts.vwap_rev import freeze as F
from scripts.vwap_rev import universe as U
from scripts.vwap_rev.run_primary import RESULT_DIR, cells_path

SIDE_INT = {"up_disp_short": 1, "down_disp_long": -1}
MEMBERSHIP_CERTIFIED_ONLY_CAP = 0.005


def main() -> None:
    defects = []
    try:
        F.assert_frozen()
    except RuntimeError as e:
        defects.append(f"freeze hash mismatch: {e}")
    cert_only = U.certified_only_share(U.load())
    if cert_only > MEMBERSHIP_CERTIFIED_ONLY_CAP:
        defects.append(f"membership agreement failure: certified-only share {cert_only:.4f}")
    val = pd.read_csv(cells_path("primary", "VAL"))
    hold = pd.read_csv(cells_path("primary", "HOLDOUT"))
    d2 = pd.read_csv(cells_path("delay2", "HOLDOUT"))
    v = K.val_confirmed(val)
    clean, _ = K.holdout_confirmed(v, hold, d2)
    net_lb = {}
    if clean:
        ev = pd.read_parquet(C.OUT_DIR / "events_primary_HOLDOUT.parquet")
        a = K.ALPHA / len(clean)
        for side, H in clean:
            net_lb[(side, H)] = A.net_lower_bound(ev, SIDE_INT[side], H, A.BASE_KAPPA, a)
    res = K.classify(val, hold, d2, net_lb, defects)
    res["net_lower_bounds_bp"] = {f"{s}/h{h}": float(x) for (s, h), x in net_lb.items()}
    res["certified_only_share"] = cert_only
    out = RESULT_DIR / "classification.json"
    out.write_text(json.dumps(res, indent=2, default=str))
    print(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    sys.exit(main())
