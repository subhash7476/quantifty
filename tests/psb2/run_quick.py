import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.psb2.test_formula_fidelity import *
import time
t0 = time.time()
for fn in [test_fortnightly_grid, test_exit_band, test_staggered_tranches,
           test_bonferroni_m, test_c2_fortnightly_mean_min_8,
           test_c2_252_day_baseline_ending_t21,
           test_c3_21_day_return_horizon, test_c4_lookback,
           test_power_hurdle, test_slippage_kappa]:
    name = fn.__name__
    try:
        fn()
        print(f"  PASS {name}")
    except Exception as e:
        print(f"  FAIL {name}: {e}")
print(f"Done in {time.time()-t0:.1f}s")
