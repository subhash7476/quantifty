"""Power arithmetic for the proposed non-confirmatory Stage-1 screen and a possible later confirmatory read.

Pure arithmetic: no market data, no outcomes. Reuses the k / p / q / band assumptions of gf_power_sketch.py.
NOT an RFA declaration. Reported in PTMS_GANN_STAGE1_PREREG_COMPLETION_2026-09-14.md §9-§10.

- Screen: m = 4 constructs (GF-1, GF-4T/R8, GF-7, GF-10), alpha = 0.05/4 one-sided.
- Windows are calendar spans only; whether any of them is admissible is an operator ruling.
"""
import math

import gf_power_sketch as g

M_SCREEN = 4
WINDOWS = {
    "screen, dev-only 2011-03-25..2022-12-30": 11.77,
    "screen, full 2011-03-25..2026-09-11": 15.47,
    "confirmatory IF ruled fresh, 2023-01-02..2026-09-11": 3.69,
    "confirmatory, forward 5y": 5.0,
}
SCREEN_IDS = ("GF-1", "GF-4T/R8", "GF-7", "GF-10")


def main():
    g.power.ALPHA = 0.05 / M_SCREEN
    print(f"alpha one-sided = 0.05/{M_SCREEN} = {g.power.ALPHA:.5f}; q = {g.Q_OUTCOME}")
    print()
    print("| Construct | window | years | n defined dates | power opt | power cen |")
    print("|---|---|---|---|---|---|")
    for cid, per_year, k, p, _basis, _role in g.CONSTRUCTS:
        short = cid.split()[0]
        if short not in SCREEN_IDS:
            continue
        a, fd, floor = g.attenuation(p, g.Q_OUTCOME), g.p_defined(p, g.Q_OUTCOME, k), 1 / math.sqrt(k - 1)
        for wname, years in WINDOWS.items():
            n = int(per_year * years * fd)
            p_opt = g.power.power_at(g.DELTA["opt"] * a, floor * g.SD_MULT["opt"], n, two_sided=False)
            p_cen = g.power.power_at(g.DELTA["cen"] * a, floor * g.SD_MULT["cen"], n, two_sided=False)
            print(f"| {short} | {wname} | {years} | {n} | {p_opt:.2f} | {p_cen:.2f} |")


if __name__ == "__main__":
    main()
