# IVOL — Idiosyncratic Volatility: Phase 0 Research Record

**Document type:** Sleeve research record (Phase 0 — the candidate brainstorm, the prior evidence behind it, and the free-arithmetic pre-screen that gates it before any pre-registration freeze).

**Status:** Phase 0 **DRAFT, UNFROZEN — pre-RFA, pre-freeze.** No data read taken. No sealed window touched. Not authorized to proceed; this record exists to decide whether `IVOL_PHASE0_PRE_REGISTRATION.md` is worth writing.

**Date:** 2026-07-25

**Origin:** LAG failed TRAIN (wrong-sign IC, momentum-correlated). Operator authorized a new construct. This record is the proposed successor.

**Roles (standing):** Implementation party: TBD at freeze. Lead Reviewer: TBD. Decisions: Operator.

---

## 1. Why this candidate, why now — and a reframe of what kills sleeves

Seven constructs have died (PSB-1 C1–C5, PSB-2 C2/C3, SFB-1/F1, Flow, Skew, Trend, LAG); one has survived (Carry). Before proposing another, the honest diagnostic of *how* they died:

- **Trend** died on *significance* (p=0.131) — weak signal.
- **Skew** died on *significance* (p=0.255) — weak signal.
- **LAG** died on *sign* (−0.031) — wrong signal, 58% Trend-subsumed.
- **Flow** died at the RFA gate (max power 0.6053) — before any data.

**None cleared the standalone TRAIN gates** (significant + correct-sign IC + positive net spread). The 0.80 power hurdle is a *separate* concern — per every sleeve's pre-reg §9, **0.80 binds at the composite (engine) level with Carry, not per-sleeve.** Carry itself never cleared 0.80 standalone; it cleared gates 2/3/5 (sign + net + persistence). So the real bar for a new sleeve is: clear significant + correct-sign + positive-net on TRAIN, **and** add decorrelated breadth to the composite.

On *that* bar, one candidate has dramatically stronger prior evidence than anything tried in the engine:

## 2. The candidate — IVOL thesis

**One line:** rank names by **idiosyncratic (beta-neutralized) realized volatility**; long low-IVOL names, short high-IVOL names. The lottery-preference anomaly — retail overpays for high-vol/lottery stocks, so high-IVOL underperforms and low-IVOL outperforms.

**Economic foundation:** Ang–Hodrick–Xing–Zhang (2006, *Journal of Finance*, "The Cross-Section of Volatility and Expected Returns") and (2009); Frazzini–Pedersen (2014, "Betting Against Beta"). The high-IVOL-underperforms result is one of the most replicated in cross-sectional asset pricing. Frazzini-Pedersen document BAB with t-stats > 5.

## 3. The prior evidence — the differentiator

PSB-1 C5 (cash-equity low-vol, monthly banded) is the **only construct this repo has ever run that cleared the standalone TRAIN-equivalent gates**:

| C5 metric (CLAUDE.md PSB-1 table) | Value |
|---|---|
| Mean IC | **+0.068** (t=3.14, **p=0.001**) — significant, correct sign |
| Gross Q1-Q5 spread | +16.2% |
| Net spread | **+4.3%** at **14 bp/yr** drag |
| Composite power (n*=42) | 0.54 — the *only* metric it missed |

C5 produced the **highest IC of any PSB-1 candidate** and cleared significance + sign + net. It died *only* on the composite power projection. It was never tested in the futures engine. IVOL is that test — with the substrate the engine actually trades, at the cadence the engine actually uses.

## 4. Differentiation from the dead sleeves

| Sleeve (status) | What it ranked | IVOL ranks |
|---|---|---|
| Carry (survived) | futures-vs-spot residual basis | **idiosyncratic volatility** — different economic driver |
| Trend (dead, p=0.131) | own-name past return | **residual vol level** — not path-dependent |
| Skew (dead, p=0.255) | option-implied pessimism | **realized (cash/futures) vol** — no options dependency |
| LAG (dead, wrong sign) | sector-leader catch-up gap | **own-name vol** — no leader conditioning |
| PSB-1 C5 (cash, power fail) | cash low-vol | **futures IVOL, beta-neutralized** — same economics, different substrate |

The cleanest distinction: IVOL is a **levels/risk** signal (slow-moving, like Carry's basis), not a **behavioral/path** signal (momentum, reversal, diffusion — all noisy). Levels signals have lower turnover and more stable IC dispersion — the structural reason C5's fee drag was only 14 bp/yr.

## 5. The India structural argument — direct, not vague

Low-vol is driven by **lottery preference** (Kumar 2009; Bali–Cakici–Whitelaw 2011): retail investors overpay for stocks with lottery-like (high-vol, high-skew) payoffs. India has **among the highest retail participation in global equity markets** → the driver is amplified → the anomaly should be **larger**, not smaller. This is the same "India enlarges a named anomaly" structural bet as LAG, but applied to (a) a more robust anomaly globally and (b) one whose driver (retail lottery preference) is **directly and measurably stronger in India** — not a vague "frictions" hand-wave.

## 6. Free RFA pre-screen (no data touched — verified against `scripts/rfa/power.py`)

Convention: `metric="rank_ic"`, noncentral-t, one-sided α=0.05, `n* = 42` (sealed 2023-01 → 2026-07).

**Predicted sign: NEGATIVE** (high vol → low return). Delta is declared as a positive magnitude representing |IC| (same convention as Flow's declaration). Bands anchored on C5 (+0.068) and the BAB literature (~0.04–0.06):

`ncp = (delta / SD)·√n*`, √42 = 6.481:

| Corner | delta (\|IC\|) | SD | ncp | Power | Verdict |
|---|---|---|---|---|---|
| Optimistic | 0.060 | 0.10 | 3.889 | **0.9853** | **PROCEED** |
| Central | 0.050 | 0.14 | 2.315 | **0.7361** | below 0.80 but **near** |
| Pessimistic | 0.040 | 0.18 | 1.441 | 0.4096 | below |

**Formations required for power 0.80** (via `power.n_required`):
- Optimistic corner (0.060 / 0.10): **19 formations** — huge margin (window holds 42).
- Central corner (0.050 / 0.14): **50 formations** — just 8 short of the 42 available.

**Interpretation:** IVOL is the **first candidate whose central case approaches standalone 0.80** (0.7361 vs everyone else's ~0.55–0.57). That is the direct consequence of C5's strong prior IC — IVOL's delta ceiling (0.060) is the highest of any sleeve declared. It clears the RFA gate at the optimistic corner with the largest margin of any candidate (0.9853), and unlike LAG/Trend/Skew, its central case is close enough that a TRAIN realization slightly above 0.05 IC would clear 0.80 *standalone*, not just at composite.

## 7. Why the build is nearly free (reuses certified substrate)

IVOL consumes no new ingestion:

| Input | Source | Status |
|---|---|---|
| Per-name roll-adjusted continuous returns | `data/signal_engine/trend/continuous.duckdb` (363 underlyings) | Built (commit `0ea419e`) — reused unchanged from Trend/LAG |
| Realized vol | trailing 60-session daily log returns from continuous series | Trivial (reuses Trend's VOL_WINDOW=60 pattern) |
| Beta + sector neutralization | same OLS machinery as Carry/Trend/LAG | Reusable |
| Era futures fee model | existing §8 fee machinery | Reusable |
| RFA gate + power math | `governance/rfa/` + `scripts/rfa/power.py` | Reusable |

Marginal build ≈ one construction script (`build_ivol.py` — realized vol → z → neutralized) + one TRAIN runner. The continuous-series work is already done (third reuse).

## 8. Honest caveats (disclosed before freeze, not after)

1. **Prior exposure: PSB-1 C5 is the closest prior read.** C5 was *cash-equity* low-vol; IVOL is *futures* + explicitly beta-neutralized (residual vol). Different substrate, universe, fee structure, and neutralization — but disclosed as prior-adjacent. With Trend (dead) and LAG (dead) also in the vol/momentum neighborhood, **m ≥ 3** for the family-wise penalty. The Bonferroni evidence floor tightens accordingly.
2. **C5's high IC dispersion is the real risk.** C5 cleared IC and net but reached only 0.54 composite power — meaning its IC dispersion was high relative to its (strong) IC. If futures IVOL has similarly high dispersion, it clears the standalone TRAIN gates (significance + sign + net) but contributes only modest composite breadth. **The bet:** the futures substrate (liquid, filtered universe, beta-neutralized at the return level) has lower IC dispersion than cash — defensible but unproven. The gate-2 SD band check ([0.10, 0.18]) is the honest arbiter: if realized SD > 0.18, the C2 wide-SD stop fires and the sleeve halts.
3. **The sign is NEGATIVE.** High vol predicts *low* returns. This is the opposite direction to Carry/Trend/LAG (all positive-signed). The construction and gate logic must reflect this (long low-z_ivol, short high-z_ivol; significance tested in the negative direction). Not a problem, but a place to be careful in implementation.
4. **This is the last high-prior-Sharpe anomaly.** After IVOL, the documented cross-sectional anomaly space with IC > 0.05 is effectively exhausted (momentum/reversal/skew/diffusion/low-vol all tested). If IVOL fails, the honest answer is **Carry-alone** or a non-cross-sectional problem class. IVOL is the best remaining shot, not a guarantee.

## 9. What this record is NOT

- **Not a frozen pre-registration.** No SHA-256, no bands pinned. That is `IVOL_PHASE0_PRE_REGISTRATION.md`, the next step if the operator authorizes.
- **Not an RFA declaration.** The §6 numbers are verified against `power.py` for decision support; the binding gate runs through `governance/rfa/declarations/ivol.py`.
- **Not a data read.** Zero formations consumed. TRAIN/HOLDOUT/SEALED all untouched.
- **Not a guarantee.** IVOL's central-case strength rests on C5's prior IC transferring to futures — which is exactly what TRAIN tests.

## 10. Decision requested from operator

| Option | Meaning |
|---|---|
| **PROCEED to pre-reg** | Authorize `IVOL_PHASE0_PRE_REGISTRATION.md` (DRAFT) + `governance/rfa/declarations/ivol.py`, then run the free RFA gate. Still no data read until frozen + PROCEED. |
| **REVISE** | Reject IVOL (e.g., too prior-exposed via C5, negative-sign complexity) and stop. |
| **STOP** | Accept the engine at Carry-alone; do not pursue a new construct. The documented finding supports this as defensible. |
