# PSB-2 — Panel Screening Battery, Increment 2: Phase 0 Research Record

**Document type:** Program research record (Phase 0 — the brainstorm that shapes the program, and the operator decisions that gate it)

**Status:** Phase 0 OPEN — D8, D9, D10 **RATIFIED** 2026-07-14. Protocol freeze draft in progress.

**Date:** 2026-07-14

**Predecessor:** PSB-1, CLOSED 2026-07-14 on the verdict "no winner recommended" (`docs/reports/PSB1_PHASE0_RESEARCH_RECORD.md`, §8). PSB-2 is the fourth Knowledge program.

**Roles (standing):** Implementation party: DeepSeek V4. Lead Reviewer: Claude (prompts and reviews only). Decisions: Operator.

---

## 1. Why this program, why now

PSB-1 did not fail on the signal. Three of the five candidates produced statistically significant positive IC: C1 (t=3.76, p<0.0001), C2 (t=6.63, p<4e-11), C3 (t=2.93, p=0.002). Two produced gross Q1-Q5 spreads above +14% (C2, C3). One produced a positive net spread (C5, +4.3% annualized).

It failed on the **cost structure**. Delivery-equity STT at 0.1% per leg with weekly rebalance turnover of ~0.80 imposes a ~13pp/yr fee hurdle. C1–C4 all confirmed this: gross spreads of +1% to +17% were consumed by 12–17pp/yr fee drag. The STT is the binding constraint, not the signal.

PSB-2's design answer: **every candidate must clear the fee model by construction.** The protocol selects candidates whose turnover ≤ 0.06 (monthly cadence or slower, or banded exits at tighter thresholds), whose holding period asymmetry reduces the taxed side, or whose signal is strong enough that the residual after fees is unambiguously positive. C5 proved the model works — it's the template.

Three institutional lessons carried forward from PSB-1:

1. **Fee model first, signal second.** A candidate that cannot clear delivery-era fees at its natural cadence is not a candidate.
2. **Substrate certification is a pre-commitment artifact.** The four-arm contract suite (`scripts/psb1/contract_arms.py`) validates the adjusted series before any candidate runs. PSB-2 inherits the certified substrate without modification.
3. **The frozen protocol discipline works.** PSB-1's pre-registered screening found exactly what it was designed to find, reported honestly, and stopped on its own rules. PSB-2 keeps that discipline.

## 2. What PSB-2 inherits (fully certified, zero additional consumption)

| Asset | Detail | Source |
|---|---|---|
| Certified equity EOD store | 7,030,920 adjusted rows, 0 view-induced fabrications | Four-arm contract suite (PSB-1 Prompts 2–5) |
| Delivery fields | `deliv_pct` present 2020-01-01 onward (SECFULL era) | CSMP gate (a) audit |
| Point-in-time universe | NIFTY-200 membership reconstructable at date *t* | CSMP gate (c); `build_universe.py` |
| Time-aware entity resolution | `symbol_entity_intervals` — recycled tickers, ISIN fragments both resolved | PSB-1 Prompts 3, 5 |
| Delivery-equity fee model | Era-accurate, 6 rate schedules (STT, NSE, SEBI, stamp, GST, DP), gate-(b) audited | `core/execution/equity/delivery_fees.py` |
| Screening harness | `screening_harness.py` — loader, grids, C1–C5 scoring, metrics, power, AC₁/NW | PSB-1 Phase 1 |
| Panel loader lineage | `load_window()` descendant with entity-grain dedup, dev-fenced, `deliv_pct` through `rn=1` | Commit `0ae1dc4` |
| Validation machinery | Content-addressed validation records, sealed-fence assertions, deterministic seeded runs, script-generated mechanical verdict tables | CSMP/PSB-1 patterns |
| Contract arms | Four-arm suite: intra-symbol CA-shape, cross-symbol handoff, prev_close identity, factor evidence | `scripts/psb1/contract_arms.py` |

## 3. Operator decisions (RATIFIED 2026-07-14)

All three decisions put to the operator during Phase 0 brainstorming were ratified as recommended.

| # | Decision | Ruling | Rationale recorded |
|---|---|---|---|
| D8 | Sealed-window policy for new families | **LIFTED — momentum fence is down.** The 2023–2026 window is unspent (PSB-1 made no sealed read). The one prior momentum read (CSMP, December 2022 cutoff) is disclosed as prior exposure per PSB-1 D2; a successor program may apply an explicit α penalty if strictness is wanted. **Does not affect the CSMP sealed window**: PSB-1 never read it; CSMP's own sealed read (Phase 6, 42 monthly observations) stands exactly as banked. Momentum-family constructs in PSB-2's slate are new designs (staggered holding, long-only) — not a re-run of the CSMP construct. | No new consumption of the sealed window occurred. The fence was credibility, not data — and six months have passed since CSMP's read, adding 6 sealed months to any future gate. |
| D9 | Candidate slate | **RATIFIED — 5 candidates, fee-survivable by construction.** Exact formulas pinned at protocol freeze; directions pre-registered. See §5 for the proposed slate. | PSB-1's 5-candidate battery proved the screening model works. PSB-2 narrows the design space to fee-survivable constructs only — fewer infinite-parameter degrees of freedom, less risk of post-hoc tuning. |
| D10 | Cadence floor | **RATIFIED — monthly or slower.** No weekly construct is eligible for the slate. The fee model imposes this constraint mechanically; recording it as an explicit decision prevents a future candidate from being nominated at a weekly cadence "just to check." | PSB-1's C1–C4 all recorded positive IC but negative net spread at weekly cadence. The gap between signal and cost opens at ~0.06 turnover; weekly rebalancing (0.77–0.83 turnover) is always on the wrong side of it. |

## 4. The design space — fee-survivable constructs

PSB-2 candidates are designed against three cost-structure axes:

### Axis 1 — Cadence and holding period

The fee drag scales directly with annual turnover. Monthly rebalancing (C5) drops turnover from ~0.80 to ~0.04. Slower cadences — quarterly, semi-annual — reduce it further. The holding period determines how many STT legs are paid per year per name.

### Axis 2 — Banded/triggered exits

C5's 0.40 exit band means a name enters the top quintile only at the 20th percentile and exits only when it falls past the 40th. The band absorbs noise around the cutoff; without it, a name oscillating between the 19th and 21st percentiles would churn every month. Tighter bands (0.30, 0.25) reduce turnover further at the cost of holding names that have weakened but not collapsed.

### Axis 3 — Asymmetric entry/exit

A signal that enters on strong conviction (top decile) and exits only on a reversal signal (not a rank drop) pays STT only on genuine entry/exit — not on rank noise. This is the hardest to pre-register (the exit rule must be fixed at protocol freeze) but offers the largest fee reduction.

## 5. Proposed candidate slate (5, formulas pinned at protocol freeze)

| # | Construct | Cadence | Rationale |
|---|---|---|---|
| 1 | **Low-volatility, tighter band** — C5 variant. Trailing 252-day σ rank; enter top quintile, exit only when the name falls out of the **top 30%** (0.30 band, tighter than C5's 0.40). | Monthly | Direct refinement of PSB-1's closest candidate. Tighter band should further reduce turnover without sacrificing the core low-vol effect. C5's +4.3% net return at 0.40 band provides the baseline; 0.30 should improve net spread at minimal IC cost. |
| 2 | **Delivery-percentage anomaly, monthly** — C3's signal on C5's cadence. Cross-sectional rank of `deliv_pct` z-score, banded exit. | Monthly | PSB-1's C3 showed +0.025 mean IC at weekly cadence with +17.5% gross Q1-Q5 spread. The signal is real; the weekly cadence is what killed it. At monthly cadence with banded exit, it should clear fees. The delivery register is the repository's untapped comparative advantage (§4 of the PSB-1 record). |
| 3 | **Delivery-conditioned reversal, monthly** — C4's interaction on monthly cadence. Reversal signal gated by delivery: revert low-delivery moves, persist high-delivery moves. | Monthly | The interaction bet at a cadence where fees don't dominate. PSB-1's C4 was null (mean IC −0.003) but at weekly cadence — the delivery signal may need longer to express. Monthly gives it that room. |
| 4 | **Momentum, long-only, multi-month holding** — cross-sectional trailing 12-month return (skip most recent month), long the top quintile, hold for 6 months (staggered portfolios, 1/6th rebalanced monthly). | Monthly rebalance, 6-month hold | **Momentum fence LIFTED (D8).** The CSMP closure binds momentum to fresh pre-registration; this construct is structurally different from CSMP's (monthly rebalance, long-only, staggered). Turnover ~0.17 (1/6th of the portfolio each month) → fee drag ~2.5pp/yr. The literature's strongest factor; PSB-2 gives it a fee-survivability test. One prior momentum read (CSMP, 42 monthly observations) is disclosed per PSB-1 D2; the successor pre-registration may apply an α penalty. |
| 5 | **Quality-at-reasonable-price (QARP)** — composite: rank of (ROE / trailing σ) among the NIFTY-200, banded exit. Low-turnover tilt, not a trading signal. | Monthly | Turnover should be ~0.10 or lower (the composition of high-quality names is sticky). The metric is well-documented in Indian markets; the test is whether it produces enough dispersion in the 200-name universe to generate a positive net spread after fees. |

**Excluded:** any weekly-rebalance construct; any high-turnover intraday derivative construct (different fee regime, different universe, out of PSB scope); any factor-zoo combination (the multiplicity penalty exceeds plausible effect sizes per PSB-1 §6-C).

## 6. Screening design — the PSB-1 protocol carried forward

PSB-2 reuses the PSB-1 protocol structure (`PSB1_PROTOCOL.md` Rev 2) with one amendment: the §5 candidate definitions are the five constructs above, and the §3 cadence rule is **monthly only** (D10). All other provisions — the §4 common scoring rules, §6 metrics, §7 power projection (≥0.80 hurdle), §8 Bonferroni-deflated selection (m=5), §9 immutability, §10 determinism — carry forward unchanged.

The fee model is the same `delivery_equity_fees()` with κ=5bp/side. The net spread construction (top quintile − formation-complete baseline, both legs charged, C5-banded-equivalent for all candidates) carries forward.

**New for PSB-2:** the pre-run substrate certification (`certify_substrate.py`) runs before any candidate score touches real data. The four-arm contract suite must return 0 undocumented violations. This is a structural gate — no Phase 2 without a certified substrate.

## 7. Program structure and boundaries

**Phases:**
- **Phase 0 — Protocol freeze.** Operator ratifies D8–D10. DeepSeek V4 drafts the PSB-2 screening protocol (adapting the frozen PSB-1 protocol with the five new candidates). Lead Review. **FROZEN.**
- **Phase 1 — Harness adaptation.** Adapt `screening_harness.py` for the five new candidates (scoring functions, banded-exit variants where not already handled). Dev-proven on synthetic data. No real-data scores.
- **Phase 2 — The battery run.** Five candidates in declared order; one script-generated report per candidate; no peeking-driven tweaks.
- **Phase 3 — Selection report + operator decision.** Same selection machinery (projected sealed power ranking, Bonferroni evidence floor). At most one winner.

**Boundaries:**
- **No sealed read.** 2023-01→2026-06 stays untouched (D8 determines whether momentum-family constructs may be nominated for a future sealed read — not for PSB-2's dev window, which is still 2012→2022).
- **No new data ingestion.** Substrate inherited from PSB-1.
- **No consumer, no strategy code.** Nothing lands in `core/strategies/`.
- **Fee-survivable by construction.** No candidate may be nominated whose natural cadence is weekly or shorter.

**Artifacts:** all reports land as `docs/reports/PSB2_*.md`, in the established mold.

## 8. Next actions

1. ~~Operator rulings on D8, D9, D10~~ — **RATIFIED 2026-07-14.**
2. DeepSeek V4 drafts the **PSB-2 screening protocol** (`docs/reports/PSB2_PROTOCOL.md`) with the five candidate formulas pinned, adapted from the frozen PSB-1 protocol template. The protocol retains the §4 common scoring rules, §6 metrics, §7 power projection (≥0.80 hurdle), §8 Bonferroni deflation (m=5), §9 immutability, and §10 determinism — only the §3 cadence rule and §5 candidate definitions change.
3. Lead Review of the protocol; operator ratifies; protocol **FROZEN**.
4. Prompt 1 (harness adaptation) issued to DeepSeek V4.
