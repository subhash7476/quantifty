# IVOL — Gate 4 Composite Power Check

**Script-generated** — `scripts/signal_engine/ivol/composite_check.py`. Code commit `0987324`.

**Frozen protocol:** `IVOL_PHASE0_PRE_REGISTRATION.md` §9 gate 4 / §13 (declaration SHA `d7ebcbcc…`).

**What this is:** arithmetic on already-measured TRAIN quantities — no new data read, no sealed window touched. Combines the frozen Carry and IVOL signals into the equal-risk-weight composite and projects power to the sealed window (n*=42).

**Common TRAIN formations:** 47 (2017-02-28 -> 2020-12-31), intersection of names both sleeves score, mean 165 names/formation.

## Standalone vs Composite (on the common intersection)

| Sleeve | Mean IC | SD(IC) | IR (|mean|/SD) | t | Standalone power (n*=42) |
|---|---|---|---|---|---|
| Carry (z_carry_neut) | +0.047378 | 0.076921 | 0.6159 | 4.2226 | 0.9887 |
| IVOL (z_ivol_neut) | -0.049769 | 0.162801 | 0.3057 | -2.0958 | 0.6192 |
| **Composite (z_carry - z_ivol)** | **+0.069774** | **0.116201** | **0.6005** | **4.1166** | **0.9854** |

## Realized Cross-Sleeve Correlation

| Quantity | Value | Meaning |
|---|---|---|
| Signal correlation (pooled, z_carry vs z_ivol) | -0.0359 | decorrelated |
| Per-formation IC correlation | +0.2287 | do the sleeves' monthly ICs move together? |

The breadth thesis (`IR ≈ √(Σ IR_i²)` when uncorrelated) rewards low correlation. A signal correlation near zero means the composite IR approaches the quadrature sum of the standalone IRs.

## Breadth Decomposition

| Quantity | Value |
|---|---|
| √(IR_carry² + IR_ivol²) [quadrature, if uncorrelated] | 0.6876 |
| Realized composite IR (|mean|/SD) | 0.6005 |
| Ratio (realized / quadrature) | 0.8732 |

Signal correlation -0.0359 is low, so the realized composite IR should approach the quadrature sum — confirmed by the ratio above.

## Power Projection (n* = 42, sealed window)

| Sleeve | Power |
|---|---|
| Carry standalone | 0.9887 |
| IVOL standalone | 0.6192 |
| **Composite (Carry + IVOL)** | **0.9854** |
| Hurdle | 0.80 |

## Gate-4 Verdict

**PASS** — composite power 0.9854 >= 0.80 hurdle. The 2-sleeve engine (Carry + IVOL) clears the 0.80 hurdle at the composite level.

**Next:** §9 gate 5 — the one-shot SEALED read (2023-01 → present), the final unrepeatable resource. Composite clearance authorizes opening it.
