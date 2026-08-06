# SE-3 — Confirmatory Read (Phase 2, one-shot)

**Window:** 2016-02-11 -> 2022-12-31 | **Variant A only, skip-a-day** | **Run:** script-generated, no hand-edited numbers

---

> ## ⚠️ POST-HOC SUBSTRATE FINDING, 2026-08-06 (annotated; script-generated numbers below are NOT edited)
>
> The FUTSTK settle series feeding A10 RV is **un-adjusted for splits/bonuses**; 17 Nifty-50
> corporate actions inside the window produce fabricated one-day crashes that survive the §3.5
> roll-gap guard. **378 RV-contaminated and 72 dh-contaminated name-days (~0.44%).** Bounded
> ceiling on mean_IC contribution ≈ **0.040** (`SE3_CA_CONTAMINATION_REVIEW.md` §3). **G1/G2 and the
> NO-BUILD verdict are unaffected**; the point estimate −0.1124 carries a bounded CA bias and must
> not be used as a δ anchor for any future construct. See `SE3_CA_CONTAMINATION_REVIEW.md`.
>
> This annotation is a disclosure attached to a frozen one-shot; Phase 2 was **not** re-run and the
> snapshot is untouched.

---

## 1. Fence proof

- stock options: observed `trade_date` range [2016-02-11, 2022-12-30]
- stock futures: observed `trade_date` range [2016-02-11, 2022-12-30]
- Hard assertion per source — **PASSED**

## 2. Window ledger (post-run)

| Leg | Window | State after |
|---|---|---|
| **OPTSTK stock options** | **2016-02-11 -> 2022-12-31** | **SPENT — confirmatory read** |
| NIFTY index options | 2016-02-11 -> 2022-12-31 | **Unread** — variant A does not touch the index leg |
| OPTSTK stock options | 2023-01-02 -> 2025-12-31 | Spent (breadth probe) |
| Both legs | 2026-01-01 -> 2026-07 | **Preserved** |

## 3. THE CONFIRMATORY RESULT

| Statistic | Value |
|---|---|
| n_dates | 1680 |
| mean_IC | -0.1124 |
| sd_IC | 0.1940 |
| Newey-West t (lag 5) | -21.5157 |
| NW p (two-sided) | 0.0000e+00 |
| AC1 | 0.0778 |
| G1: IC significant at alpha=0.05 two-sided | **PASS** |
| G2: sign negative as declared | **PASS** |

## 4. D2 — realized sd_IC vs declared band

| Bound | Value |
|---|---|
| Declared band | [0.1877, 0.26] |
| Realized sd_IC | 0.1940 |
| Inside band | **YES** |

## 5. D3 — effective breadth (raw panel)

| Statistic | Realized | Probe reference |
|---|---|---|
| rho_bar | 0.195 | 0.150 |
| N_eff | 4.7 | 5.9 (upper estimate) |
| PC1 share | 24.30% | — |

## 6. D1 — quintile L/S P&L across the cost ladder (DIAGNOSTIC, NOT GATING)

Direction: **long BOTTOM richness quintile, short TOP** (pinned a priori).
Every ladder rung is an **ASSUMPTION** — the substrate has no bid/ask, so option
costs are not measurable historically (pre-reg section 5). P&L is vega-scaled
per unit; a negative or indistinguishable net is the PRE-DECLARED expected
outcome ('real but unharvestable'), which does NOT falsify the IC claim.

| Rung (bps of premium) | n_days | gross total | net total | net mean/day |
|---|---|---|---|---|
| 0 | 1680 | 6.8166 | -5081.0994 | -3.0245 |
| 25 | 1680 | 6.8166 | -5086.2026 | -3.0275 |
| 50 | 1680 | 6.8166 | -5091.3057 | -3.0305 |
| 100 | 1680 | 6.8166 | -5101.5121 | -3.0366 |

Net = gross minus the FULL pre-reg §5.1 cost stack, in vega-scaled units:
(1) the rung's round-trip spread cost (2 × rung_bps of premium); (2) statutory
option charges, era-dated — STT sell-side on premium (0.017% pre-2016-06-01, 0.05%
after), exchange txn (0.0495%, assumption), SEBI (0.0001%), stamp buy-side (0.1%
pre-2020-07-01, 0.003% after — assumption), GST 18% (assumption), brokerage Rs
20.0/order; (3) the futures-leg hedge cost via the canonical
`core/execution/futures/futures_fees.py` (era-dated STT/exchange/SEBI/stamp/GST
+ brokerage), on the hedge notional |delta| x F, open and close.

**D1 supports NO sizing claim.** gross_total is a sum of vega-scaled unit P&L over
1,680 days — not a return, not a Sharpe, not comparable to capital. Pre-reg §4
pins exactly this: `rank_ic` PROCEED does not imply `per_trade_pnl` PROCEED, and
realized `N_eff` 4.7 (below the probe's 5.9) means a ~50-name book
carries roughly five independent bets.

Statutory schedule (era-dated, per-leg, fraction of premium):

| Component | Rate / rule | Source |
|---|---|---|
| Option STT on sale | 0.017% (pre-2016-06-01), 0.05% after — of premium | NSE Budget-2016-17 (Mint/ET) |
| Exchange txn charge | 0.0495% of premium (flat) | **ASSUMPTION** (repo fee model) |
| SEBI fee | 0.0001% of premium | repo fee model |
| Stamp duty (buy) | 0.1% pre-2020-07-01, 0.003% after | **ASSUMPTION** (state-level pre-2020) |
| GST | 18% on (brokerage+exchange+SEBI) | **ASSUMPTION** (service tax pre-2017) |
| Brokerage | Rs 20.0 flat per order | repo fee model |
| Futures leg | `core/execution/futures/futures_fees.py` — era-dated STT (0.01% pre-2023), exchange 0.0021%, SEBI, stamp, GST, brokerage | canonical repo model |

## 7. Outcome matrix (pre-reg section 4)

**Significant, correct sign.** IC demonstrated, but the D1 net is **negative
even at 0 bp of assumed spread** once statutory + futures-leg costs are folded
in. Matrix row 2:

> **NO-BUILD. The IC finding stands and is recorded. This is the expected
> outcome given `N_eff` 5.9 and §5.**


P&L is a reported diagnostic and CANNOT falsify the IC claim (pre-reg section 4).

## 8. Predictions (state-before-run)

| # | Prediction | Actual | Held? |
|---|---|---|---|
| Q6 | Realized sd_IC inside declared band [0.1877, 0.26] | 0.1940 | **HELD** |
| Q7 | Realized raw rho_bar ABOVE probe's 0.150 | 0.195 | **HELD** |

**There is no prediction on the IC itself** (pre-reg section 4 outcome matrix is the pre-declared reading).

## 9. Implementation notes

- Skip-a-day construction reproduces `breadth_probe.py`'s corrective run (richness at t, return over t+1 -> t+2, per-name row shift).
- Reuses `black76_delta`, `black76_vega`, `implied_vol`, `_parity_forward` from `scripts/osc/sd_probe.py` (A14).
- Variant B absent; no index-options database reference anywhere in this module.
- S3: frozen snapshot records 1679 usable dates vs threshold 756 (PASS).
  **Reconciliation (lead review MEDIUM-1, resolved):** Phase 1's original waterfall subtracted a flat
  `all_dates[20]` (21-trading-day skip), giving 1679; Phase 2's actual A10 >=18-observation floor admits
  2016-03-10 (first date with >=20 names having RV), giving 1680. The corrected Phase 1 `first_usable`
  now certifies the same 1680 dates (2016-03-10 .. 2022-12-28) that Phase 2 consumed — the counts
  reconcile. Phase 2's count was correct; Phase 1's waterfall line was the wrong one.
- **DISCLOSURE (HIGH-2, lead review): the one-shot read was re-executed once after a result was seen.**
  The first run recorded G1 FAIL at p = 2.0 — an impossible p-value, `2·(1−cdf(t))` without `abs()` on t = −21.5.
  The p-formula was corrected and the run re-executed under operator authorization (which prompt §7 permits).
  NW t (−21.5157) and n_dates (1680) were **identical on both runs** — the correction recomputed a deterministic
  function of an unchanged statistic, so the one-shot property is intact in substance; the re-execution is a
  disclosed deviation, not a defective read. The D1 ladder fix changed only `net`; gross (6.8166 at every rung)
  and the IC are unchanged by it.
- One-shot enforced: refuses if snapshot exists or S3 not PASS. Nothing under `data/` written.

### NOTE — what the magnitude most plausibly is (lead review §7)

Realized |IC| 0.1124 is 3.6x the top of the declared delta band and lands within 0.0006 of the probe's
skip-a-day −0.1130 — the number CLAUDE.md prohibits as the delta anchor. The reading most consistent with
the whole artifact is that `richness` substantially restates **name-level IV mean reversion**: high IV today,
lower IV tomorrow, which is a known statistical property, not necessarily a capturable premium. It predicts
exactly what was observed — an enormous, stable IC alongside a D1 P&L that does not survive plausible costs.
Cross-window stability is NOT independent confirmation: the helper cross-check test guarantees the two
modules agree, so a shared construction artifact would reproduce across both windows by design and still pass.
Any successor must state this explicitly rather than cite the two windows as two confirmations.
