"""Synthetic-only check (numpy RNG, no market data): per-date Spearman IC between binary score and binary outcome."""
import math
import numpy as np
from scipy.stats import norm, spearmanr

rng = np.random.default_rng(7)
D = 20000

def sim(k, p, q, rho):
    zp, zq = norm.ppf(1 - p), norm.ppf(1 - q)
    ics = []
    undefined = 0
    for _ in range(D):
        x = rng.standard_normal(k)
        y = rho * x + math.sqrt(1 - rho * rho) * rng.standard_normal(k)
        s, o = (x > zp).astype(float), (y > zq).astype(float)
        if s.std() == 0 or o.std() == 0:
            undefined += 1
            continue
        ics.append(np.corrcoef(s, o)[0, 1])  # Spearman on binaries == Pearson on binaries (phi)
    ics = np.array(ics)
    return ics.mean(), ics.std(), undefined / D

def atten(p, q):
    zp, zq = norm.ppf(1 - p), norm.ppf(1 - q)
    return norm.pdf(zp) * norm.pdf(zq) / math.sqrt(p * (1 - p) * q * (1 - q))

def phi_max(p, q):
    a, b = min(p, q), max(p, q)
    return math.sqrt(a * (1 - b) / (b * (1 - a)))

print("| k | p | q | null sd sim | 1/sqrt(k-1) | 1/sqrt(4p(1-p)(k-1)) | undefined dates | mean phi @ latent 0.03 | analytic 0.03*atten | phi_max |")
print("|---|---|---|---|---|---|---|---|---|---|")
for k, p, q in [(100, 0.5, 0.3), (100, 0.29, 0.3), (100, 0.17, 0.3), (45, 0.4, 0.3), (40, 0.05, 0.3), (40, 0.02, 0.3), (100, 0.5, 0.1)]:
    _, sd0, und0 = sim(k, p, q, 0.0)
    m3, _, _ = sim(k, p, q, 0.03)
    print(f"| {k} | {p} | {q} | {sd0:.4f} | {1/math.sqrt(k-1):.4f} | {1/math.sqrt(4*p*(1-p)*(k-1)):.4f} | {und0:.3f} | {m3:.4f} | {0.03*atten(p, q):.4f} | {phi_max(p, q):.2f} |")
