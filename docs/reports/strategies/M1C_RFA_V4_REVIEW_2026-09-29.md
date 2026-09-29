# M1c RFA Declaration v4 — Review

**Date:** 2026-09-29 · **Reviewed:** `M1C_RFA_DECLARATION_v4.md` (commit `d86f0b3`) against my v3 review (R3-1..R3-3). No data, no new research, no redesign. Numbers recomputed by hand.

## Verdict

R3-1 and R3-2 are correctly resolved in arithmetic, and **ABANDON follows**, HOLDOUT-binding. Three residual statement-level issues remain; none is decisive.

## 1. Verified

- **Mapping (§2).** Regrouping Σx_τ by calendar day gives x̄ ≈ H·b̄ and LRV(x) ≈ H²·LRV(b). Under W at book level, ncp = (m/√v_b)·√n = S_strat·√T for every H. This is correct, and it is an equality under W, not merely a floor. The v3 session-unit form is properly reconciled via S_x = √H·S_strat.
- **Tables.** VAL at S=1.8 is Φ(1.8·2.2271 − 1.96) = Φ(2.049) = 0.980. HOLDOUT at S=1.8 is Φ(1.8 − 1.6449) = Φ(0.155) = 0.562. Sessions required at the 1.8 corner: (2.8016/1.8)² × 250 = 606 (VAL), (2.4865/1.8)² × 250 = 477 (HOLDOUT; v4 says 478). C2-implied S=2.14 gives HOLDOUT Φ(0.495) = 0.69. All match.
- **Grinold range.** 0.0294·√(250b) gives 1.04 (b=5) and 1.80 (b=15). The v1 error is correctly acknowledged, and the optimistic corner now sits at the top of its own derived range.
- **Rule.** VAL 0.98 passes, HOLDOUT 0.56 fails, so ABANDON. Any ceiling below 2.49 fails HOLDOUT. The rescue thresholds are H-independent and correct (Σρ ≤ −0.42 and ≤ −0.18).

## 2. Findings

**V4-1 (MATERIAL, non-decisive) — the PSB-1 C2 exclusion conflates two different "C2" constructs.**
- v4 §5 calls it "fortnightly residual-reversal IC +0.035, retired on extended-history power".
- PSB-1 C2 is **weekly residual reversal** (n=529, IC +0.035, t 6.63; its outcome was net −8.6% on fees).
- The fortnightly, extended-history-power retirement is **PSB-2 C2**, the delivery-% anomaly (IC +0.0349).
- So the "repeats the documented C2 error" argument does not apply to the construct actually being excluded.
- The exclusion itself may still stand: residual is not absolute, and weekly is not daily.
- The "C2-implied S ≈ 2.14" derivation is not shown. From the cited figures the annualized weekly IC-IR is about 2.08, and an IC-IR is not a strategy Sharpe.
- The can't-flip conclusion holds regardless.
- *Fix:* correct the description, then either derive the 2.14 or delete it.

**V4-2 (MATERIAL, non-decisive) — the optimistic corner rests on an undeclared breadth cap.**
- The 1.8 top uses b ≤ 15 independent daily bets, a figure imported from CB-N50's 50-name universe. The declaration applies it to a ~2,300-name panel without defending the cap.
- The verdict's break-even is b* = (2.4865/0.0294)² / 250 ≈ 28.7 bets per day. Above that, the same IC translation gives HOLDOUT power ≥ 0.80.
- That is not obviously out of reach for a broad panel.
- The IC also transfers from a 50-name large-cap daily-horizon composite to a sparse 5-day-tail signal.
- "Robust for any ceiling below 2.49" is true, but the ceiling's derivation carries this hidden premise.
- *Fix:* state b* and the premise b < ~29 in §5, without changing the band; label ABANDON as conditional on that breadth premise.

**V4-3 (MINOR) — a stale figure.** §2 says HAC over-rejection "cannot bridge 0.26 → 0.80". The optimistic corner is now 0.56 → 0.80. Bridging would need a true size of about 0.17 (z = 1.8 − 0.8416 = 0.958), and fixed-b literature suggests distortion of that size is not expected at n=250. State the arithmetic.

## 3. Recommendation

ABANDON stands and is HOLDOUT-binding. v4 removes the unit error and the mislabelled ceiling. An erratum or v5 should fix V4-1 to V4-3, with no re-run and no protocol change.
