"""Pre-RFA power sketch for the Gann faithful (GF) candidates. Pure arithmetic: no market data, no outcomes.

NOT an RFA declaration. It sets power.ALPHA for its own process only and must never be imported by
governance/rfa. Reported in docs/reports/ptms/PTMS_GANN_PREREG_DESIGN_DECISIONS_2026-09-14.md §E.

Statistic: per-date cross-sectional Spearman IC between a BINARY construct score (flag fraction p) and
the BINARY Rule 10 outcome (base rate q) over k eligible names. On two binaries Spearman is phi.
- sd: the permutation-null sd of a correlation is 1/sqrt(k-1) for any margins (verified on synthetic
  data, phi_null_check.py). Central x1.5 and pessimistic x2 for cross-sectional dependence.
- delta: bands are LATENT associations — central 0.03 anchored on CB-N50 HOLDOUT IC +0.029 (a
  continuous feature vs a continuous return, different hypothesis, borrowed); optimistic 0.06;
  pessimistic 0.01. Dichotomising both sides attenuates them:
  phi ~= rho * pdf(z_p) * pdf(z_q) / sqrt(p(1-p) q(1-q))  (bivariate-normal threshold model).
- n: a date is defined only if both score and outcome vary across the k names;
  P(defined) = (1-(1-p)^k-p^k) * (1-(1-q)^k-q^k). Years = n_required / (per_year * P(defined)).
- p and q are DESIGN ASSUMPTIONS (construct geometry, symmetry or a stated guess), never measured.
- alpha: 0.05 / M_PRIMARY, M_PRIMARY = 7 primary cells (decision D).
"""
import math
import sys
from pathlib import Path

from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "rfa"))
import power  # noqa: E402

M_PRIMARY = 7
ALPHA = 0.05 / M_PRIMARY
DELTA = {"opt": 0.06, "cen": 0.03, "pes": 0.01}
SD_MULT = {"opt": 1.0, "cen": 1.5, "pes": 2.0}
Q_OUTCOME = 0.30  # assumed 5-session base rate of a Rule 10 signal; not measured

# id, formations per year, k eligible names, p flag fraction, basis of p, role
CONSTRUCTS = [
    ("GF-1 Master Square time points", 52, 100, 0.29, "geometry: 6 dates per 144 days, week overlap", "primary"),
    ("GF-4T/R8 Rule 8 day windows", 52, 100, 0.50, "geometry: 67 of 185 window days, week overlap", "primary"),
    ("GF-5 anniversary month", 12, 100, 0.17, "geometry: 2 of 12 months", "primary"),
    ("GF-6 reaction beyond 65 days", 52, 40, 0.05, "assumed", "primary"),
    ("GF-7 diminishing section", 52, 50, 0.20, "assumed", "primary"),
    ("GF-8 45-50% below a bull-state K3 top", 52, 40, 0.02, "assumed", "primary"),
    ("GF-10 time overbalance", 52, 45, 0.40, "symmetry: about half of declines outlast the previous", "primary"),
    ("GF-9 modal swing duration (stock extension)", 52, 100, 0.20, "assumed", "secondary"),
]
HORIZONS = {"fwd 1y": 1, "fwd 3y": 3, "fwd 5y": 5, "fwd 10y": 10, "dev 15.5y (info only)": 15.5}


def attenuation(p, q):
    zp, zq = norm.ppf(1 - p), norm.ppf(1 - q)
    return norm.pdf(zp) * norm.pdf(zq) / math.sqrt(p * (1 - p) * q * (1 - q))


def p_defined(p, q, k):
    return (1 - (1 - p) ** k - p ** k) * (1 - (1 - q) ** k - q ** k)


def main():
    power.ALPHA = ALPHA
    print(f"alpha one-sided = 0.05/{M_PRIMARY} = {ALPHA:.5f}; q = {Q_OUTCOME}")
    print()
    print("| Construct | role | k | p | basis of p | attenuation | P(date defined) | phi at cen |")
    print("|---|---|---|---|---|---|---|---|")
    for cid, per_year, k, p, basis, role in CONSTRUCTS:
        a = attenuation(p, Q_OUTCOME)
        print(f"| {cid} | {role} | {k} | {p} | {basis} | {a:.2f} | {p_defined(p, Q_OUTCOME, k):.2f} | {DELTA['cen'] * a:.4f} |")
    print()
    print("| Construct | " + " | ".join(f"{h} opt / cen" for h in HORIZONS) + " |")
    print("|---|" + "---|" * len(HORIZONS))
    for cid, per_year, k, p, _basis, _role in CONSTRUCTS:
        a, fd, floor = attenuation(p, Q_OUTCOME), p_defined(p, Q_OUTCOME, k), 1 / math.sqrt(k - 1)
        cells = []
        for years in HORIZONS.values():
            n = int(per_year * years * fd)
            p_opt = power.power_at(DELTA["opt"] * a, floor * SD_MULT["opt"], n, two_sided=False)
            p_cen = power.power_at(DELTA["cen"] * a, floor * SD_MULT["cen"], n, two_sided=False)
            cells.append(f"{p_opt:.2f} / {p_cen:.2f}")
        print(f"| {cid} | " + " | ".join(cells) + " |")
    print()
    print("| Construct | n for 0.80 opt | years fwd | n for 0.80 cen | years fwd | n for 0.80 pes | years fwd |")
    print("|---|---|---|---|---|---|---|")
    for cid, per_year, k, p, _basis, _role in CONSTRUCTS:
        a, fd, floor = attenuation(p, Q_OUTCOME), p_defined(p, Q_OUTCOME, k), 1 / math.sqrt(k - 1)
        row = []
        for corner in ("opt", "cen", "pes"):
            n = power.n_required(DELTA[corner] * a, floor * SD_MULT[corner], 0.80, two_sided=False)
            row.append(f"{n} | {n / (per_year * fd):.1f}" if n else "None | —")
        print(f"| {cid} | " + " | ".join(row) + " |")


if __name__ == "__main__":
    main()
