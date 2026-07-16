"""Check if per-step signal survives in forward returns and C2 scores."""
import sys
sys.path.insert(0, '.')
from pathlib import Path
import numpy as np
from scripts.psb2.run_devproof import _build_signal, _bday_span, N_CAL_DAYS, H

out = Path("data/psb2_synthetic/check.duckdb")
_build_signal(out, "c2", seed_offset=1)
panel = H.load_panel(str(out), cutoff=H.DEV_HI)
cal = _bday_span(panel.cal[0], N_CAL_DAYS)
fg = H.fortnightly_grid(cal)
dev_fg = [d for d in fg if H.C2_DEV_LO <= d <= H.DEV_HI]
print(f"Dev FG count: {len(dev_fg)}")

# Check C2 scores at first formation date
scores = H.score_c2_psb2(panel, dev_fg[0], fg=fg)
if scores:
    sig_z = [s for e, s in scores.items() if e < "S0011"]
    other_z = [s for e, s in scores.items() if e >= "S0011"]
    print(f"C2 z-scores at {dev_fg[0]}: sig_mean={np.mean(sig_z):.3f} other_mean={np.mean(other_z):.3f}")

# Check forward returns
for t in dev_fg[:5]:
    g_idx = fg.index(t)
    tp = fg[g_idx + 1]
    sig_fwd, other_fwd = [], []
    for ent in H.members_at(panel, t):
        f = H._ret(panel, ent, t, tp)
        if f is not None:
            (sig_fwd if ent < "S0011" else other_fwd).append(f)
    print(f"  {t}: sig_fwd={np.mean(sig_fwd):.4f} other_fwd={np.mean(other_fwd):.4f}")
