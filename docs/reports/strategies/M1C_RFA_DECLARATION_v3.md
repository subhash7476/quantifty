# M1c RFA Declaration v3 (FROZEN)

**Status:** FROZEN v3, 2026-09-29. Supersedes v2 (`66bcc42`, immutable). This version answers the
outstanding mathematical objection: v2's floor was derived under unstated premises while calling itself
"assumption-free". The assumption is now stated precisely, the floor made explicitly conditional, and
the verdict re-examined in both failure directions. No band value, window, α, hurdle, table entry, or
protocol text changes. **Verdict: ABANDON (retained).** Governing protocol v1.3 unchanged.
Methodology 2.0.0, hurdle 0.80. No market data read, no backtest, no TRAIN, no new hypothesis.

## 1. Correction to v2 (adjudication: option B)

v2 §2 wrote "With daily innovations white" and "Var(x_τ) = H·v" and then called the resulting floor
"the unique assumption-free choice". That is inconsistent: whiteness (no serial correlation in signed
daily innovations) and scale constancy are premises, and state-dependence (overlapping R5 windows,
persistent tails, slow-moving reference distributions) is real. The floor is therefore **conditional,
not guaranteed**. What survives without any premise is only the overlap geometry (H-day windows
reformed every session); everything else below is conditioned on Assumption W, stated exactly in §2.

## 2. Assumption W and the conditional floor

**Assumption W (serially uncorrelated centered signed daily innovations, bounded scales).** Let
d_{τ,j} be cohort τ's mean signed return on session τ+j, centered at its (possibly state-dependent)
mean. Assumed: Cov(d_{τ,j}, d_{τ',j'}) = 0 whenever τ+j ≠ τ'+j′ (no serial correlation at any nonzero
calendar lag), with uniformly bounded daily variance scales. No Gaussianity, no independence, no
cross-sectional restriction is assumed. This is strictly weaker than the repo gate's own iid basis in
`power.py`, and it is the standard weak-form premise behind every daily t-test.

**Derivation (conditional on W).** x_τ = Σ_{j=2}^{H+1} d_{τ,j}; cohorts τ, τ+k share H−k calendar days
(0 ≤ k ≤ H; disjoint beyond). Under W, cross-day covariances vanish, so with per-day scales,
Cov(x_τ, x_{τ+k}) runs only over shared days: |Cov| ≤ Σ_{shared} √(a_d·b_d) (Cauchy–Schwarz), and
Var(x_τ) = Σ_{j=2}^{H+1} v_{τ,j}. Summing lags gives S_0 ≤ v̄·H² against σ_x² = H·v̄-type scale (common
scale shown for clarity; with drifting scales the same steps go through with sup-scale at the cost of
looseness, edge effects O(H/n) negligible at n ≈ 250/1,240 — direction safe). Hence S_0/σ_x² ≤ H and
**ncp ≥ S_ann·√(T/H), conditional on W**, equality for identical cohorts. H=1 reproduces v1 exactly
(no overlap: whiteness alone); H=n degenerates correctly. Finite-sample HAC noise around S_0 remains
disclosed as ignored, either direction; dependence beyond lag H (slow-state regimes) would breach NW(H)
consistency — that is the protocol's own premise (N3-cleared, "reported not patched"), not this RFA's.

**Status of the R5-persistence observation.** R5(t), R5(t+1) share 5 of 6 closes (protocol arithmetic),
so persistent classifications with shared names/signs are a *reasoned expectation*, i.e. the floor is
plausibly near the truth — recorded as expectation, not premise. The verdict below needs only W.

**Failure directions (both stated).** Positive autocorrelation (drift persistence, regime clustering,
slow-state dependence) → true S_0 above the bound → true power below the tables → ABANDON strengthened.
Negative autocorrelation (e.g. bid/ask bounce) → power above the tables — the only direction that could
threaten the verdict; quantified in §6 as rescue thresholds. Bounce is idiosyncratic (diversifies across
~10² names/session by the rule's own tail rates × panel size — structural, no data) and diluted by the
1-session gap inside H-day sums; systematic negative daily autocorrelation contradicts the same
weak-form premise the gate uses.

## 3. VAL design (α = 0.025, T ≈ 4.96 y)

Unchanged from v2 (floor formula identical; only its epistemic status changed). Power = Φ(ncp − 1.96):

| H | T_eff (y) | MDE S (80%) | S=0.2 | S=0.5 | S=1.0 opt | S=2.0 robustness |
|---|---|---|---|---|---|---|
| 1 | 4.96 | 1.26 | 0.06 | 0.20 | 0.61 | 0.99 |
| 5 | 0.99 | 2.81 | 0.04 | 0.07 | 0.17 | 0.51 |
| 10 | 0.50 | 3.98 | 0.03 | 0.05 | 0.10 | 0.29 |

## 4. HOLDOUT design (250 sessions, α = 0.05, T = 1.0 y)

| H | T_eff (y) | MDE S (80%) | S=0.2 | S=0.5 | S=1.0 opt | S=2.0 robustness |
|---|---|---|---|---|---|---|
| 1 | 1.00 | 2.49 | 0.07 | 0.13 | 0.26 | 0.64 |
| 5 | 0.20 | 5.56 | 0.06 | 0.08 | 0.12 | 0.23 |
| 10 | 0.10 | 7.86 | 0.06 | 0.07 | 0.09 | 0.16 |

## 5. Band standing

[0.2, 0.5, 1.0] retained verbatim with v1 provenance and exclusions (adjacent-magnitude question,
independent of the ncp mapping). Fee-drag floors (125/H %/yr) and selection treatment retained
unchanged.

## 6. PASS / ABANDON with rescue analysis

Rule unchanged: PASS iff optimistic-corner power ≥ 0.80 at BOTH stages for the pinned H. Best cells:
VAL/H=1 at 0.61, HOLDOUT/H=1 at 0.26 — **ABANDON** (no data read; protocol returns to draft). Rescue
thresholds (what W-violation would be needed to flip): HOLDOUT/H=1 requires S_0/σ² ≤ (1.0/2.4865)² ≈
0.16, i.e. sustained Σρ ≤ −0.42; VAL/H=1 requires Σρ ≤ −0.18 — but PASS needs both, so the HOLDOUT
threshold binds. No plausible microstructure effect reaches −0.42 sustained on multi-day diversified
portfolio sums (§2); positive-autocorrelation violations only deepen ABANDON. The verdict is therefore
robust in both failure directions, not an artifact of W.

## 7. Pre-read inputs, governance, no-data statement

As v1 §11–§12 and v1 §14 (band/method/α/hurdle frozen here; exact VAL count from `trading_calendar`;
companion `.py` transcription unchanged in values; v1/v2 immutable). No M1c market data, backtest,
TRAIN output, or prior M1c result was read, used, or inherited in v2 or in this correction; the mapping
is time-series algebra on the frozen construction, the band from adjacent public record.

## Targeted consistency check (this correction only)

- Frozen estimand: session-mean of f = s·R_fwd, untouched. ✓
- Sharpe definition: standardized session mean, unchanged as parameter. ✓
- HAC/noncentrality mapping: now conditional on stated W; floor formula unchanged; "assumption-free"
  language removed everywhere it appeared. ✓
- H=1/5/10: per-cell tables; H=1 reproduces v1 exactly (nesting check). ✓
- VAL/HOLDOUT power: table entries bit-identical to v2 (status change only). ✓
- PASS/ABANDON rule: same mechanical rule, re-evaluated per pinned H plus rescue thresholds. ✓

## Change Log

- v3 (2026-09-29, FROZEN): W-assumption stated precisely (§2); floor made conditional (was mislabeled
  assumption-free); structural-persistence note downgraded to reasoned expectation; failure directions
  with rescue thresholds (§§2, 6); 0.9-haircut withdrawal retained; all tables/band/rule unchanged;
  verdict ABANDON retained on corrected epistemics. v1/v2 immutable.
