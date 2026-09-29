# M1c RFA Declaration v3 — Mathematical and Provenance Review

**Date:** 2026-09-29 · **Reviewed:** `M1C_RFA_DECLARATION_v3.md` (commit `f4b7e44`), with v1 and v2 for the band and mapping history. No data, no new research, no redesign. Every number below was recomputed by hand from the declaration's own inputs.

## Verdict

**ABANDON genuinely follows, and robustly.** The reasons the declaration gives for it are partly wrong, though. Two statements are incorrect and should be corrected by erratum or v4. Neither changes the verdict.

## 1. Arithmetic, tables and thresholds — verified

- MDE at 80% power: VAL (1.960 + 0.8416)/√4.96 = 1.258; HOLDOUT (1.6449 + 0.8416)/√1.0 = 2.487.
- Every table cell was recomputed as Φ(S√(T/H) − z_α) and matches to rounding, for all H and all S. Examples: VAL/H=1/S=1 gives 0.605; HOLDOUT/H=1/S=1 gives 0.259; HOLDOUT/H=10/S=2 gives 0.156.
- Sessions for 80%: 7.85 y × 250 = 1,962 (VAL); 6.18 y × 250 = 1,546 (HOLDOUT). ✓
- Rescue thresholds: the long-run variance ratio is r = 1 + 2Σρ.
  - HOLDOUT needs r ≤ (1/2.4865)² = 0.162, i.e. Σρ ≤ −0.42. ✓
  - VAL needs r ≤ (2.2271/2.8016)² = 0.632, i.e. Σρ ≤ −0.18. ✓
  - HOLDOUT binds, as stated.
- The W-based derivation is algebraically correct: the shared-day counts, Var(x) = ΣV, S₀ ≤ vH², and S₀/σ_x² ≤ H. The failure-direction statements are also correct.

## 2. Findings

**R3-1 (MATERIAL, non-decisive) — the √H penalty is a unit mismatch between the band and the mapping.**
- v2/v3 define S as the annualized standardized mean of the session series x, using the √250 convention. That is Sharpe of an H-day overlapping trade series.
- The band, however, was derived (v1 §6) from a Grinold daily-book IR, i.e. the annualized Sharpe of the strategy's daily P&L.
- Under W with the strategy's Sharpe, the HAC test on x has ncp = μ_x√n/√S₀ = H·m·√n / (H√v) ≥ S_strat·√T for every H. The overlap cancels: x̄ ≈ H·b̄ and LRV(x) ≈ H²·LRV(b), where b is the stacked book's daily return.
- The √H penalty appears only if the band is read as S_x = √H·S_strat. The band was never defined that way.
- Consequences:
  - The H=5 and H=10 rows of the §3 and §4 tables understate power.
  - The claim that v1 "overstated power by up to √H" is unsupported; v1's mapping was right for a strategy-Sharpe band.
  - "ABANDON strengthened" is unsupported.
  - The correct tables collapse every H to the H=1 row (VAL 0.61 at S=1; HOLDOUT 0.26).
  - The rescue thresholds then hold identically for all H.
- The verdict is unaffected: the best cell was always H=1, which is unchanged.
- *Fix:* state that the band is a strategy-level Sharpe and ncp ≥ S√T for all H (equivalently, S_x = √H·S_strat).

**R3-2 (MATERIAL, non-decisive) — the band ceiling is mislabelled, and one adjacent fact is not in the exclusion list.**
- v1 §6 translates CB-N50's IC of +0.0294 with IR = IC·√(250·b). For b = 5 to 15 independent daily bets that gives about 1.04 to 1.80, not "1.0–1.5", and it then calls **1.0**, the *bottom*, a "generous ceiling". That is inconsistent: an optimistic corner should sit at the top of the range it derives.
- At S = 1.5 VAL power is Φ(1.38) = 0.92 and VAL passes. So the v1 §10 claim that "VAL alone fails the standard" holds only at the S = 1.0 ceiling. The verdict actually rests on HOLDOUT size: HOLDOUT at S = 1.5 gives 0.44, at S = 1.8 gives 0.56, and only S ≥ 2.49 passes.
- PSB-1 C2 (mean IC +0.035, t 6.63; later retired) is a stronger adjacent dev fact than the C1 the declaration cites, yet it is neither anchored nor listed as excluded. It cannot flip the verdict, since the band would have to reach 2.49.
- *Fix:* restate the ABANDON as HOLDOUT-binding: it holds for any ceiling below 2.49. Record C2 in the exclusion or disclosure list. The pessimistic and central band values are conventions, not derived, and are irrelevant to an optimistic-corner verdict.

**R3-3 (MINOR):**
- The HAC finite-sample size distortion at n = 250, lag ≤ 10 is ignored. It is liberal, so nominal α understates true size; it is negligible for this verdict.
- The joint sequential power is ≤ min(VAL, HOLDOUT), so the min-based rule is generous, not strict.
- The band is applied uniformly across H, which is now correct under R3-1.

## 3. Does ABANDON follow? — Yes

- PASS requires HOLDOUT power ≥ 0.80. With 250 sessions at α = 0.05 that requires S ≥ 2.49 at every H, on either mapping.
- The band (ceiling 1.0, or up to 1.8 on its own translation) and even the undefended S = 2.0 fall short.
- The only paths to a flip are a sustained daily autocorrelation sum ≤ −0.42 (implausible on diversified multi-day sums) or S ≥ 2.49 (unsupported).
- The two errors above lower some non-binding cells and mislabel the ceiling, but neither creates or removes the conclusion.

## 4. Recommendation

Keep ABANDON. Issue an erratum or v4 correcting R3-1 and R3-2. No re-run and no change to the protocol are needed.
