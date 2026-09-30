"""VWAP-XREV pre-freeze, OUTCOME-FREE diagnostics (TRAIN only): event incidence per
candidate q. No forward return, entry or exit price is ever computed here."""
from __future__ import annotations

import json
import sys

import numpy as np

from scripts.vwap_rev import common as C
from scripts.vwap_rev import engine as E

TARGET_INCIDENCE = 0.10


def main() -> None:
    out = {}
    for q in (0.99, 0.995, 0.999):
        p = E.Params(q=q)
        ev, ss = E.run_sessions(p, stages=("TRAIN",))
        tr = ss[ss["stage"] == "TRAIN"]
        n_name_sessions = int(tr["n_elig_names"].sum())
        pairs = ev.groupby(["date", "symbol"]).ngroups if len(ev) else 0
        out[str(q)] = {
            "train_sessions": int(len(tr)),
            "eligible_name_sessions": n_name_sessions,
            "events": int(len(ev)), "events_up": int((ev["side"] == 1).sum()),
            "events_down": int((ev["side"] == -1).sum()),
            "name_sessions_with_event": int(pairs),
            "incidence": pairs / n_name_sessions if n_name_sessions else None,
            "events_per_session": len(ev) / max(len(tr), 1),
            "share_at_first_window_bar": float((ev["k"] == E.K_LO).mean()),
            "share_z_prev_already_beyond": float((ev["z_prev"].abs() >= ev["c"]).mean()),
            "D_quantiles": [float(x) for x in np.quantile(ev["D"], [.1, .25, .5, .75, .9])],
        }
        print(q, json.dumps(out[str(q)], indent=1), flush=True)
    dist = {k: abs(v["incidence"] - TARGET_INCIDENCE) for k, v in out.items()}
    best = min(dist, key=lambda k: (dist[k], -float(k)))
    out["rule_target_incidence"] = TARGET_INCIDENCE
    out["rule_selected_q"] = float(best)
    (C.OUT_DIR / "diagnostics_outcome_free.json").write_text(json.dumps(out, indent=1))
    print("selected q:", best)


if __name__ == "__main__":
    sys.exit(main())
