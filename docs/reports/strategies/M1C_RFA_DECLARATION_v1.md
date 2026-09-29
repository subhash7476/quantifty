# M1c RFA Declaration v1 (FROZEN)

**Status:** FROZEN v1, 2026-09-29. Text immutable from this commit; no M1c read is authorized by any
outcome except as the governed protocol provides (§12 verdict below is ABANDON: no read occurs).
**Governing protocol:** `docs/reports/strategies/M1C_RESEARCH_PROTOCOL_v1.3.md` (commit `a69f23a`),
terminology and estimand preserved exactly. **Methodology:** `METHODOLOGY_VERSION 2.0.0`
(`scripts/rfa/gate.py`; `POWER_HURDLE 0.80`, optimistic-corner verdict, FLOW/CB-N50 precedent).
**No market data were read, no backtest run, no TRAIN executed, no parameter searched, no new
hypothesis introduced, and the frozen protocol is unchanged.** Artifacts consulted (code/docs only):
the v1.3 protocol, MAP v1.1, `governance/rfa/declaration.py`, `scripts/rfa/power.py` and `gate.py`.

## 1. Purpose

Answer pre-data: is the frozen experiment statistically capable of detecting an effect defensible as
materially meaningful? If not, the output is ABANDON — this declaration is not tuned for PASS.

## 2. Estimand (protocol-exact)

Session-portfolio mean of `f = s · R_fwd` (absolute signed forward return, §6 v1.3),
cohort-by-formation-date aggregation (§8.1), one-sided t with Newey–West HAC standard errors, lag = H
(§10). Metric for RFA purposes: `per_trade_pnl` with the session as the period —
annualized Sharpe band plus `cadence_per_year = 250`. Per `gate.py` (cadence cancels):
`ncp = S·√T` with S annualized Sharpe, T stage length in years. H therefore does not enter power;
it enters only fees (§8) and selection (§9).

## 3. VAL design

Window 2018-01-01 → 2022-12-30 (≈1,240 sessions ≈ 4.96 y; exact count fixed from `trading_calendar`
pre-read — calendar arithmetic, not market data). One-sided α = 0.025 (z = 1.9600). Single pinned test.
Note: `power.py` hardcodes ALPHA = 0.05, so the VAL row below uses the identical ncp construction with
the z = 1.96 tail (large-n normal approximation to the noncentral-t; n > 1,000, approximation error
negligible). Minimum detectable Sharpe at 80% power: (1.9600 + 0.8416)/√4.96 = **1.26** (1.33 under the
0.9-session haircut of §6).

## 4. HOLDOUT design

250 trading sessions after FREEZE_DATE 2026-09-29 (≈1.0 y), one-shot, one-sided α = 0.05 (z = 1.6449;
covered exactly by `power.py`/`gate.py` at ALPHA = 0.05). Minimum detectable Sharpe at 80% power:
(1.6449 + 0.8416)/√1.0 = **2.49** (2.62 with the haircut). The frozen 250-session design can resolve
only effects of Sharpe ≈ 2.5 or larger at the repo's power standard.

## 5. H = 1 / 5 / 10 treatment

TRAIN pins one H, so all three cases are assessed without selecting: power is identical across H by the
cadence-invariance identity (§2), so the tables below hold for H ∈ {1, 5, 10} alike. H differentiates
only (a) fee drag (§8: turnover ≈ 2/H of book per day) and (b) TRAIN-selection probabilities (§9).

## 6. Effect-size band (independently defended, pre-data)

Declared band (annualized gross Sharpe): pessimistic **0.2**, central **0.5**, optimistic **1.0**
(`sharpe_lo/hi`, strictly positive per contract; no delta/sd coupling per the O1 lesson).
- **Optimistic 1.0 (ceiling):** the strongest adjacent OOS gross fact is CB-N50 HOLDOUT combined daily
  IC +0.0294 (reversal + basis, single test). Under Grinold translation (IR ≈ IC·√BR) with favorable
  breadth (5–15 independent daily bets net of autocorrelation/overlap), gross IR spans ≈1.0–1.5 — and
  that before costs, on a combined (not reversal-only) statistic, assuming full capture. 1.0 is the
  bottom of that translated range: a generous ceiling nothing adjacent exceeds. ISD F4 (IC −0.0289,
  cost-killed) and PSB-1 C1 (weekly IC +0.023, net −16.8%) corroborate the IC ≈ 0.02–0.03 scale only.
- **Central 0.5:** gate-convention midpoint, inside the translated range under adverse breadth.
- **Pessimistic 0.2:** lower edge under adverse breadth/turnover translation; smallest effect this
  program would call real at daily cadence.
- **Excluded as anchors (stated):** MRLC trade-stream t = 8.62 (documented 24-cell selection + conjunction
  mechanism — winner's-curse inadmissible); RELIANCE `reversal_5` (excluded sign-rule form,
  sign-inconsistent); Carry/TS Basis/IVOL (different mechanisms); any M1c TRAIN or M1c backtest (none
  exist; prohibited). Every bridging choice above errs toward overstating power.

## 7. Power / detectable-effect calculations

Method: one-sided normal approximation Φ(ncp − z_α), ncp = S·√T; T_VAL = 4.96, T_HO = 1.0.

| Stage (α) | S=0.2 | S=0.5 | S=1.0 (optimistic) | S=2.0 (robustness, undefended) |
|---|---|---|---|---|
| VAL (0.025) | 0.06 | 0.20 | **0.61** | 0.99 |
| HOLDOUT (0.05) | 0.07 | 0.13 | **0.26** | 0.64 |

Sessions required for 80% power at the optimistic corner: VAL-α 1,962 sessions (have ≈1,240);
HOLDOUT-α 1,546 sessions (have 250). Zero-formation haircut: tails of a ~2,300-name panel make
P(empty session) ≈ 0 by rule arithmetic (5%/95% tails × thousands of names); a 0.9 effective-session
sensitivity is carried (MDEs 1.33 / 2.62) and changes nothing. HAC lag-H reduces effective n further —
same direction, covered by the haircut.

## 8. Economic vs statistical distinction (pre-data relevance analysis)

The RFA cannot establish economic viability pre-data (turnover is realized, not assumed). What can be
bounded pre-data is the fee-drag floor from rule arithmetic plus the fee schedule (no market data):
steady-state book ≈ H daily cohorts → daily round-trip turnover ≈ 2/H of book; all-in delivery
round-trip ≈ 0.25% floor (STT 0.20% + stamp/exchange/SEBI/GST/brokerage/DP per the repo fee record).
Annual drag ≈ (2/H)·0.25%·250 = 125/H %: **H=1 → ~125%, H=5 → ~25%, H=10 → ~12.5%.** At book vol 8–15%/yr
(assumption, stated range — feeds relevance only, never the statistical verdict, which is vol-free),
the relevance Sharpe is ≈ drag/vol: H=10 → 0.8–1.6; H=5 → 1.7–3.1; H=1 → 8–16. So only H=10 is even
arguably feasible, yet HOLDOUT resolves only Sharpe ≥ 2.5 — above the H=10 relevance bar. H∈{1,5} are
fee-doomed pre-data for any plausible gross, though TRAIN may still pin them on gross significance
(structural strike, disclosed; §11.3 would catch it only after a year). Statistical significance is not
economic viability; here neither is reachable.

## 9. Selection

TRAIN searches 3 families × 3 horizons and pins one by largest right-sign |t| (|t| ≥ 1.0). No
VAL/HOLDOUT correction is introduced — the frozen protocol requires none, and downstream tests are
single and pinned. The selection is not pretended away: the TRAIN maximum is winner's-curse-biased, so
a pin may be luck; VAL/HOLDOUT power above is unconditional on selection merit. Context (not a gate):
P(TRAIN pins | band) at n≈1,240 is material (≈0.3–0.9 across the band), so pipeline entry is plausible
and the binding constraints are downstream. Prior exposure per protocol §9 stands.

## 10. PASS / ABANDON (mechanical)

**PASS iff optimistic-corner power ≥ 0.80 at BOTH VAL and HOLDOUT** (repo gate standard; §12 requires
covering both sizes). Computed: VAL 0.61, HOLDOUT 0.26 — **verdict: ABANDON** (VAL alone fails the
standard, so the verdict does not hinge on HOLDOUT). Robustness: even an undefended S = 2.0 fails
HOLDOUT (0.64); only S ≥ 2.49 passes — a band top no adjacent evidence supports, and this declaration
does not supply one. Per frozen §12: no data read at any stage occurs; the protocol returns to draft.

## 11. Pre-read inputs (no discretion remaining)

Frozen: this file (by commit hash), protocol v1.3 (`a69f23a`), band [0.2, 0.5, 1.0], cadence 250,
one-sided tests, α 0.025/0.05, hurdle 0.80, METHODOLOGY_VERSION 2.0.0. Pre-read derivations with zero
discretion: exact VAL session count from `trading_calendar`; companion `.py` declaration module(s)
transcribing these values (`sharpe_lo/hi`, `cadence_per_year`, `prior_exposure` = protocol §9 clause,
`n_available` ≈ 1240 / 250); gate run for the HOLDOUT-α record. Nothing here requires or permits an
M1c result.

## 12. Governance and freeze requirements

This declaration freezes by commit; SHA-256 digest recorded at freeze per repo convention. It predates
all M1c reads. Any amendment (band, α, sizes, hurdle) creates a new version — this text is never edited
in place. Execution remains blocked per protocol §12/§15 regardless of any other artifact.

## 13. Self-audit against frozen §12 and §15

- §12 "returns ABANDON → no read": returned ABANDON; no read authorized. ✓
- §12 "cover the session-portfolio test at VAL and HOLDOUT sizes": both computed (§7 table, §10 rule). ✓
- §15.2 (declaration content): metric stated (§2), band independently defended with provenance and
  exclusions (§6), both sizes covered (§7). ✓
- Terminology/estimand protocol-exact (§2 matches §6/§8.1/§10 v1.3; absolute, no netting). ✓
- No M1c data read in creation (statement §14 below; only protocol/MAP/governance code consulted). ✓
- "Genuinely pre-data and mechanically specified": all numbers herein are calendar arithmetic, fee-schedule
  arithmetic, or normal-approximation power math; the verdict reads off the §7 table. ✓
- Unresolved: exact VAL calendar-session count (operator fixes from `trading_calendar` pre-read; a lookup,
  not a decision). Nothing else outstanding.

## 14. Explicit statement

No M1c market data, backtest, TRAIN output, or prior M1c experiment result was read, used, or inherited
in creating this declaration. The effect-size band derives solely from adjacent-construct public record
(CB-N50, ISD, PSB-1) with bridging assumptions stated in §6. Nothing herein was chosen to make the
experiment feasible — the verdict is ABANDON.

## Change Log

- v1 (2026-09-29, FROZEN): initial and only version. Created under frozen protocol v1.3 §15.2/§12.
  Verdict ABANDON (optimistic-corner power 0.61 VAL / 0.26 HOLDOUT vs 0.80 hurdle). Any future amendment
  is a new version; this text is immutable.
