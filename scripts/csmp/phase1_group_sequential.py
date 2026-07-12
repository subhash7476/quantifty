"""CSMP Phase-1 D-iii: multiplicity of the §10 extension schedule (DEV-ONLY stats).

Confirms the naive "re-read annually until it clears" schedule inflates family-wise
Type-I well past nominal, and builds valid α-spending (group-sequential) boundaries
over the pre-specified look schedule so the extension path is Approval-bearing at a
controlled overall one-sided α = 0.05.

Look schedule (calendar facts): cumulative post-2022 formation-months
  #42 (2026-06, Phase-6 primary), then #56 (2027-08) and annually to #128 (2033-08).
Information fraction t_k = n_k / 128. Test statistic per look k:
  Z_k = mean(IC_1..n_k) / (SD/sqrt(n_k)),  correlated across looks (Brownian).
Uses only dev-window facts: IC SD = 0.2078, dev effect = 0.0458. No sealed read.
Deterministic (seed 20260711).
"""
import math
import numpy as np
from scipy.stats import norm

SD = 0.2078          # dev IC SD (phase1_prereg_analysis.py)
MU_DEV = 0.0458      # dev mean IC
LOOKS = np.array([42, 56, 68, 80, 92, 104, 116, 128])
NMAX = LOOKS[-1]
T = LOOKS / NMAX
ALPHA = 0.05
M = 400_000
SEED = 20260711


def z_paths(mu, rng):
    x = rng.normal(mu, SD, size=(M, NMAX))
    csum = np.cumsum(x, axis=1)
    Z = np.empty((M, len(LOOKS)))
    for j, nk in enumerate(LOOKS):
        Z[:, j] = (csum[:, nk - 1] / nk) / (SD / math.sqrt(nk))
    return Z


def z_paths_piecewise(mu_pre, mu_post, rng):
    """Drift mu_pre for months 1..42 (the sealed window), mu_post for 43..128.
    Models an edge that is alive across the sealed window and then decays."""
    x = np.empty((M, NMAX))
    x[:, :42] = rng.normal(mu_pre, SD, size=(M, 42))
    x[:, 42:] = rng.normal(mu_post, SD, size=(M, NMAX - 42))
    csum = np.cumsum(x, axis=1)
    Z = np.empty((M, len(LOOKS)))
    for j, nk in enumerate(LOOKS):
        Z[:, j] = (csum[:, nk - 1] / nk) / (SD / math.sqrt(nk))
    return Z


def crossing_rate(Z, b):
    return float((Z >= b[None, :]).any(axis=1).mean())


def cumulative_power(Z, b):
    crossed = (Z >= b[None, :])
    first = np.where(crossed.any(1), crossed.argmax(1), len(LOOKS))
    return [(first <= k).mean() for k in range(len(LOOKS))]


def calibrate(shape_fn, Z0):
    lo, hi = 1.0, 6.0
    for _ in range(40):
        c = (lo + hi) / 2
        if crossing_rate(Z0, shape_fn(c)) > ALPHA:
            lo = c
        else:
            hi = c
    return (lo + hi) / 2


def main():
    rng = np.random.default_rng(SEED)
    Z0 = z_paths(0.0, rng)
    Z1 = z_paths(MU_DEV, rng)

    # single-shot reference at #42
    b1_single = norm.ppf(1 - ALPHA)
    p_single = float((Z1[:, 0] >= b1_single).mean())
    print(f"Look schedule (cumulative months): {list(map(int, LOOKS))}  -> t={np.round(T,3).tolist()}")
    print(f"Single-shot #42: b=1.645  one-sided a=0.050  power={p_single:.3f}\n")

    # naive: every look at one-sided 1.645, stop-on-success
    b_naive = np.full(len(LOOKS), norm.ppf(1 - ALPHA))
    print(f"NAIVE schedule (Rev-3 §10): per-look a=0.05, stop-on-success, {len(LOOKS)} looks")
    print(f"  family-wise Type-I (H0) = {crossing_rate(Z0, b_naive):.3f}   "
          f"(mb_L12 one-sided Type-I we disqualified = 0.129)")
    print(f"  cumulative power to #128 (H1) = {crossing_rate(Z1, b_naive):.3f}  <- invalid, inflated\n")

    families = {
        "O'Brien-Fleming (b_k = c/sqrt(t_k))": lambda c: c / np.sqrt(T),
        "Pocock (b_k = c)":                    lambda c: np.full(len(LOOKS), c),
    }
    pocock_b = None
    for name, shape in families.items():
        c = calibrate(shape, Z0)
        b = shape(c)
        if name.startswith("Pocock"):
            pocock_b = b
        fwer = crossing_rate(Z0, b)
        cumpow = cumulative_power(Z1, b)
        a_look = 1 - norm.cdf(b)
        print(f"{name}  [c={c:.3f}]  overall one-sided a={fwer:.3f}")
        print("  look:      " + "  ".join(f"#{n:<4d}" for n in LOOKS))
        print("  boundary:  " + "  ".join(f"{x:5.2f}" for x in b))
        print("  nominal a: " + "  ".join(f"{x:5.3f}" for x in a_look))
        print("  cum power: " + "  ".join(f"{x:5.3f}" for x in cumpow))
        print(f"  --> Phase-6 (#42) power = {cumpow[0]:.3f} ; road to #128 power = {cumpow[-1]:.3f}\n")

    # D-iii decisive scenario: what is Pocock's terminal power if the edge decays
    # AFTER the sealed window? (edge alive months 1-42, then a fraction of dev drift)
    print("Decay sensitivity (single-shot #42 uses only months 1-42; Pocock #128 uses all looks):")
    print(f"  {'post-#42 edge':16} | single-shot #42 | Pocock #128")
    for frac, tag in [(1.0, "persists (100%)"), (0.5, "half (50%)"), (0.0, "dead (0%)")]:
        Zp = z_paths_piecewise(MU_DEV, MU_DEV * frac, rng)
        ss = float((Zp[:, 0] >= b1_single).mean())
        pk = crossing_rate(Zp, pocock_b)
        print(f"  {tag:16} | {ss:15.3f} | {pk:11.3f}")
    print("  (single-shot #42 is invariant to post-2026 decay; Pocock's terminal power collapses toward alpha.)")


if __name__ == "__main__":
    main()
