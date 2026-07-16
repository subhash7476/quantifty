"""Debug C2 scorer — diagnose why scores are empty."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
from scripts.psb2 import harness as H

path = Path("tests/psb2/test_c2_debug.duckdb")
panel = H.load_panel(str(path), cutoff=H.DEV_HI)

t = panel.cal[-1]
t_21 = H._day_back(panel, t, H.DELIV_BASE_END_OFFSET)
t_base = H._day_back(panel, t_21, H.DELIV_BASE_DAYS - 1)

print(f"t={t} (idx={panel.cal.index(t)})")
print(f"t_21={t_21} (idx={panel.cal.index(t_21) if t_21 else 'None'})")
print(f"t_base={t_base} (idx={panel.cal.index(t_base) if t_base else 'None'})")

# Recent window
cal_idx = panel.cal.index(t)
recent_dps = []
for j in range(cal_idx, max(cal_idx - 20, -1), -1):
    dd = panel.cal[j]
    dp_val = panel.dp.get(("S0001", dd))
    if dp_val is not None:
        recent_dps.append(dp_val)
print(f"Recent dps: {len(recent_dps)} (min {H.DELIV_MEAN_MIN})")
print(f"  values: {recent_dps[:5]}...{recent_dps[-3:] if len(recent_dps) > 3 else ''}")

# Baseline window
t_21_idx = panel.cal.index(t_21)
t_base_idx = panel.cal.index(t_base)
base_dps = []
for j in range(t_21_idx, max(t_base_idx - 1, -1), -1):
    dd = panel.cal[j]
    dp_val = panel.dp.get(("S0001", dd))
    if dp_val is not None:
        base_dps.append(dp_val)
print(f"Baseline dps: {len(base_dps)} (min {H.DELIV_BASE_MIN})")
print(f"  first 3: {base_dps[:3]}, last 3: {base_dps[-3:]}")
if base_dps:
    print(f"  mean: {np.mean(base_dps):.4f}, std: {np.std(base_dps, ddof=1):.4f}")

# Now run the scorer
scores = H.score_c2_psb2(panel, t)
print(f"\nScores: {scores}")

if not scores:
    print("\nPossible reasons for empty scores:")
    print("1. members_at() returned empty")
    print(f"   members = {H.members_at(panel, t)}")
    print(f"2. Recent delivery count < {H.DELIV_MEAN_MIN}")
    print(f"   recent = {len(recent_dps)}")
    print(f"3. Baseline count < {H.DELIV_BASE_MIN}")
    print(f"   base = {len(base_dps)}")
    if base_dps:
        print(f"4. Baseline std <= 0: std = {np.std(base_dps, ddof=1):.6f}")
