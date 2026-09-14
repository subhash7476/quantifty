"""Pre-RFA power sketch for the Gann faithful (GF) candidates. Pure arithmetic: no market data, no outcomes.

NOT an RFA declaration. It sets power.ALPHA for its own process only and must never be imported by
governance/rfa. Reported in docs/reports/ptms/PTMS_GANN_PREREG_DESIGN_DECISIONS_2026-09-14.md §E.

Parameterisation: rank_ic, noncentral t, one-sided; ncp = delta * sqrt(n) / sd, n = formation dates.
- delta: central 0.03 (anchored on CB-N50 HOLDOUT IC +0.029, a different hypothesis — borrowed, not
  Gann-specific evidence); optimistic 2x = 0.06; pessimistic 0.01.
- sd: optimistic = the independence floor 1/sqrt(k-1) for k eligible names per date; central x1.5,
  pessimistic x2 for cross-sectional dependence. Date clustering moves sd UP, so the floor is generous.
- alpha: 0.05 / M_PRIMARY, M_PRIMARY = 7 primary cells (decision D).
- windows: forward-only horizons after a freeze; the 2011-03-25 -> 2026-09-11 development span is shown
  for information only and is never confirmatory (exposure register GR-1).
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "rfa"))
import power  # noqa: E402

M_PRIMARY = 7
ALPHA = 0.05 / M_PRIMARY
DELTA = {"opt": 0.06, "cen": 0.03, "pes": 0.01}
SD_MULT = {"opt": 1.0, "cen": 1.5, "pes": 2.0}

# id, formations per year, eligible names per date (k), role
CONSTRUCTS = [
    ("GF-1 Master Square time points", 52, 100, "primary"),
    ("GF-4T/R8 Rule 8 day windows", 52, 100, "primary"),
    ("GF-5 anniversary month", 12, 100, "primary"),
    ("GF-6 reaction duration (Rule 4 / 3-day swings)", 52, 40, "primary"),
    ("GF-7 diminishing sections (Rule 8 / 3-day swings)", 52, 50, "primary"),
    ("GF-8 percentage levels (Rule 3 / Ch IV)", 52, 100, "primary"),
    ("GF-10 time overbalance (Rule 8)", 52, 45, "primary"),
    ("GF-9 modal swing duration (stock extension)", 52, 100, "secondary"),
    ("GF-6m reaction duration, month-end cadence", 12, 40, "rejected cadence"),
    ("GF-7m culmination, 4-week cadence", 13, 50, "rejected cadence"),
]
HORIZONS = {"fwd 1y": 1, "fwd 2y": 2, "fwd 3y": 3, "fwd 5y": 5, "dev 15.5y (info only)": 15.5}


def main():
    power.ALPHA = ALPHA
    print(f"alpha one-sided = 0.05/{M_PRIMARY} = {ALPHA:.5f}")
    print()
    print("| Construct | role | k | sd floor | " + " | ".join(f"{h} opt / cen" for h in HORIZONS) + " |")
    print("|---|---|---|---|" + "---|" * len(HORIZONS))
    for cid, per_year, k, role in CONSTRUCTS:
        floor = 1 / math.sqrt(k - 1)
        cells = []
        for years in HORIZONS.values():
            n = int(per_year * years)
            p_opt = power.power_at(DELTA["opt"], floor * SD_MULT["opt"], n, two_sided=False)
            p_cen = power.power_at(DELTA["cen"], floor * SD_MULT["cen"], n, two_sided=False)
            cells.append(f"{p_opt:.2f} / {p_cen:.2f}")
        print(f"| {cid} | {role} | {k} | {floor:.3f} | " + " | ".join(cells) + " |")
    print()
    print("| Construct | role | n for 0.80 opt | years fwd | n for 0.80 cen | years fwd | n for 0.80 pes | years fwd |")
    print("|---|---|---|---|---|---|---|---|")
    for cid, per_year, k, role in CONSTRUCTS:
        floor = 1 / math.sqrt(k - 1)
        row = []
        for corner in ("opt", "cen", "pes"):
            n = power.n_required(DELTA[corner], floor * SD_MULT[corner], 0.80, two_sided=False)
            row.append(f"{n} | {n / per_year:.1f}" if n else "None | —")
        print(f"| {cid} | {role} | " + " | ".join(row) + " |")


if __name__ == "__main__":
    main()
