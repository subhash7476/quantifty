"""Diagnose C2 signal detection."""
import sys
sys.path.insert(0, '.')
from pathlib import Path
import numpy as np
from datetime import date, timedelta
from scripts.psb2 import harness as H
from scripts.psb2.run_devproof import _bulk_build

out = Path("data/psb2_synthetic/diag.duckdb")
_bulk_build(out, "c2")

panel = H.load_panel(str(out), cutoff=H.DEV_HI)
cal = []
d = date(2010, 1, 4)
while len(cal) < 3000:
    if d.weekday() < 5:
        cal.append(d)
    d += timedelta(days=1)

fg = H.fortnightly_grid(cal)
dev_fg = [d for d in fg if H.C2_DEV_LO <= d <= H.DEV_HI]
print(f"Dev fortnightly dates: {len(dev_fg)}")

# Check first 5 formation dates
for t in dev_fg[:5]:
    scores = H.score_c2_psb2(panel, t, fg=fg)
    if scores:
        sig_scores = [s for e, s in scores.items() if e < "S0007"]
        other_scores = [s for e, s in scores.items() if e >= "S0007"]
        print(f"  {t}: sig mean={np.mean(sig_scores):.3f} other mean={np.mean(other_scores):.3f}")
    else:
        print(f"  {t}: no scores")
