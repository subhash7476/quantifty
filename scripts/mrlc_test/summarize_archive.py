import numpy as np
import pandas as pd

sets = {
    "dev 2023-26 (196 names, 1m store)": r"data/mrlc_test/trades_2_0_guard.csv",
    "OOS 2015-22 (100 names, archive)": r"data/mrlc_test/trades_arc_os_2_0_guard.csv",
    "OVL 2023-25 (100 names, archive)": r"data/mrlc_test/trades_arc_ov_2_0_guard.csv",
}
th = (10.0, 15.0, 20.0)
for tf in ("1h", "4h", "1d"):
    print(f"\n===== {tf} (2x stop, news guard, net) =====")
    print(f"{'window':34s} {'thr':>4s} {'n':>5s} {'win%':>6s} {'exp':>6s} {'t':>6s} {'totalR':>8s}")
    for label, path in sets.items():
        df = pd.read_csv(path)
        df = df[df["tf"] == tf]
        for t in th:
            sub = df[df["divergence_pct"] <= -t]
            n = len(sub)
            if n == 0:
                print(f"{label:34s} {t:>4.0f} {0:>5d} {'-':>6s} {'-':>6s} {'-':>6s} {'-':>8s}")
                continue
            mean = sub["r_net"].mean()
            tt = mean / (sub["r_net"].std(ddof=1) / np.sqrt(n))
            print(f"{label:34s} {t:>4.0f} {n:>5d} {(sub['r_net']>0).mean()*100:>5.1f}% "
                  f"{mean:>6.2f} {tt:>6.2f} {sub['r_net'].sum():>8.1f}")
