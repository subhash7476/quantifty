# Late-Cycle Stock-Straddle Selling — Evidence and Provenance Audit

**Date:** 2026-09-24 · **Branch:** `research/funnels-filter` · **Type:** audit only.

**Scope honoured.**
- No backtest, no optimisation, no new signal, no GEX conditioning, no funnel.
- **No market data was read.** The sources were:
  - the study report and its scripts;
  - git objects, including the unreachable original commits;
  - the original session transcript (`~/.claude/projects/F--nifty/bfb195bb-….jsonl`), read for tool-call timestamps only;
  - file listings.
- The forward-power figures are arithmetic.

**Subject.** `docs/reports/strategies/OPTIONS_SELLER_EDGE_STUDY_2026-09-11.md` (on `main` via `5bbf49a`;
originally `6b20f0f` + `52b71ab` on the deleted branch `research/options-seller-edge`), and
`scripts/research/options_seller_edge/`.

**Tags.** **[E]** means read from code, git or transcript. **[I]** means inference.

---

## Classification: **INSUFFICIENT EVIDENCE**

- **What the evidence supports:**
  - The discovery result is strong.
  - The prediction-before-confirmation claim is verified by the transcript: the §4 predictions
    were written 14 seconds before the first 2023+ read.
  - The 2023–26 replication is real by the study's own rules.
- **What it does not support:**
  - **The regime that matters now is unproven.** After the Nov-2024 reform, the pre-registered
    row reads +6.7% of premium, t 1.37, n 21. The seller-hostile exit gives t 0.86.
  - **The construct carries an outcome-conditioned exclusion that has never been measured** (§7.1).
  - **Forward time can only confirm slowly.** At the reproducible post-reform net Sharpe of about
    0.65–1.0, confirmation takes about 6–15 years of monthly cycles.
- **Why not CLOSE:** every window and every cut is positive, and nothing measured shows absence.
- **Why not WORTH NEW CLEAN EXPERIMENT:** question 8 is answered no, and a construction defect
  must be sized first.
- **This respects the study's own frozen rule.** Its rule fired as "candidate for a proper
  pre-registration" (P1, P2 and P4 passed), not as "retire". INSUFFICIENT EVIDENCE is this
  audit's answer to question 8, not an override of that outcome.

---

## 1. What was discovered in 2016–2022

**The construct.** Sell the ATM straddle on every F&O stock (strike nearest the same-expiry
future, both legs traded at entry) at the close k sessions before the monthly expiry. Buy it back
at the T−1 close. Returns are in % of entry premium, equal-weighted across names within each
expiry, with t computed across expiries [E] (`build_stock_straddles.py`, `cycle_study.py`).

**Discovery results** (80 expiries, ~166 names each):

| Result | Value |
|---|---|
| Best row, 10 sessions before expiry | gross +13.8%/cycle (t 6.05); net at 2% spread +11.5% (t 4.98); 76% of expiries positive |
| Six entry offsets examined | 10-before is the in-sample best; Bonferroni m = 6 does not threaten it |
| Stable claim | "the last two weeks", with per-session decay rising monotonically into expiry |
| Short-straddle seller | positive in every row |
| NIFTY monthly straddle | n.s. |
| Dispersion power | 0.14 |
| vrp60 rank IC | +0.040 (t 3.40): a tilt, not the effect |

**Selection degrees of freedom in discovery:**
- six entry offsets;
- robustness cuts (exit-traded, PCP, liquidity halves, VRP buckets);
- **one ad hoc re-parameterisation of the build.** The first build had offsets {start, m10, m5}
  and was widened to six (`07:30:39` edit), after a first-pass read of discovery only at `07:28:53` [E].

## 2. What was frozen before the confirmation period

**No formal pre-registration exists.** There is no RFA declaration, no SHA-pinned freeze file and
no protocol. The study calls itself "exploratory … not a pre-registration" (header) [E].

**What was fixed before the 2023+ read**, all verified from the transcript [E]:

| Time (UTC, 2026-09-11) | Event |
|---|---|
| 07:27:42 → 07:30:53 | Straddle parquet built. It contains every expiry through 2026-08, so the 2023+ outcomes were on disk from this point |
| 07:28:53, 07:32:37 | Reads with window 2016-01-01 → 2022-12-31 only |
| **07:35:21** | Report written containing the §4 predictions P1–P6 and their pass conditions |
| **07:35:35** | First read with a 2023+ window (`cycle_study.py` for 2023-01→2026-08, pre- and post-reform) |
| 07:35:35 onward | **§4 is unchanged.** The §4 text in the 07:35:21 write was **diffed** against §4 on `main` (`5bbf49a`): byte-identical, 1,524 characters. That covers the P-rows, the pass conditions and the "retires it" decision sentence. §5 in that write was the placeholder "_Pending — run after §4 was saved._" |
| 07:32:37 → 07:35:35 | **No script was edited** between the last discovery run and the first confirmation run; the only write in that interval was the report. The 07:47 port into `scripts/` rewrote paths only, as read from the port script's source |

**Pre-prediction exposure to 2023+ data**, also from the transcript [E]:
- one RELIANCE option-chain snapshot on 2025-03-05, used to check bhavcopy close/settle semantics;
- era-level untraded-row statistics.

Neither is a straddle return. The exposure is minor and disclosed here.

**What the predictions froze:** the offset (10-before), the T−1 exit, the 2% spread cost, the
split date 2024-11-20 and the P1–P6 pass conditions.

**What they did not freeze:**
- P4 (positive in both sub-windows) had **no t hurdle**, only a sign.
- The ex-ante liquidity screen, the conservative exit, and the §9.1 construct wording ("entry legs
  ≥ 100 contracts") were **all chosen after the confirmation window was read**. The
  `liquidity_diagnostics.py` docstring says "added after §5 was read" [E].

**Git caveat.**
- The predictions and the results entered git together in one commit (`6b20f0f`, 08:58 UTC). So
  the ordering is provable only from the transcript, not from git.
- Both original commits are now **unreachable** (branch deleted; `git log --all` does not list
  them) and can be removed by garbage collection. `main` holds a byte-copy (`5bbf49a`).
- Pinning them with a tag is an operator decision.

**The transcript can disappear.**
- The transcript is the only proof of the ordering. Its SHA-256 is `326eb5eb0a068f48667bb3d14fc28914e63ad6849a3689ba03591726316bd3ae`.
- No `cleanupPeriodDays` is set in the user or project settings, so Claude Code's default retention applies; I believe that default is 30 days. At that default the 2026-09-11 session could be pruned around mid-October.
- The relevant records are extracted to `STOCK_STRADDLE_SELLING_PROVENANCE_EXTRACT_2026-09-24.md`: tool-call timestamps, commands, and the verbatim first-written §4/§5. No market data is reproduced.
- Preserving the raw file is a second operator decision.

## 3. What 2023–2026 evidence is out of sample, and what is consumed

| Evidence | Status |
|---|---|
| 2023-01 → 2026-08 (43 expiries), pre-registered rows P1–P6 | **Genuinely out of sample for the 10-before, all-names, 2%-spread construct.** Now **spent**: the study's own governance note says the window is spent for the late-cycle short-premium family |
| Same window, liquidity cuts, conservative exit, the ≥100-contract construct | **Post-hoc on the confirmation window.** Descriptive only; not out-of-sample evidence for the §9.1 construct |
| Post-reform sub-window 2024-11-20 → 2026-08 (21 expiries) | Out of sample for P4 (sign only); spent |
| "Last 12 cycles" incl. Aug-2026 (first post-CAS monthly, +29.0%) | Spent; one observation |
| Stock-option store beyond 2026-09-10 | Not read by the study |

**Consequence:** no historical stock-option window remains unread for this family.

## 4. Post-Nov-2024 performance (2024-11-20 → 2026-08-24, n = 21 expiries)

**Pre-registered row first:** 10-before, all names, net at 2% spread. Per-expiry basket means, in %
of entry premium. From study §5.3 and §5.4 [E]:

| Row | Mean | t | Status |
|---|--:|--:|---|
| **Pre-registered: all names, observed exit** | **+6.7%** | **1.37** | P4 passed on sign only (no t hurdle) |
| All names, conservative exit | +4.2% | 0.86 | post-hoc valuation |
| Entry legs ≥ 100 contracts, observed / conservative | +7.4% / +5.0% | 1.49 / 1.01 | post-hoc screen (this is the "best t 1.49") |
| Top ~40 most-traded names, observed / conservative | +4.3% / +2.0% | 0.77 / 0.36 | post-hoc |
| Pre-reform comparator, all names | +9.6% | 3.15 | |

**Sharpe, and what each figure is:**
- **Basket Sharpe 1.19** (§5.3): from `cycle_study.py`'s `pnl_f`, which is **gross**, with no
  spread and no fees [E].
- **Net Sharpe 0.84, mean +0.30%/cycle of notional, sd 1.25%, worst −3.18%** (§5.5): computed
  by an **ad hoc snippet** in the transcript (`07:44:06`), not by any committed script. That
  snippet also used a slightly different row filter from `load()`.
  - The 18% margin is a round assumption; `NseMarginEngine` was not run.
  - **Not reproducible from the repo.**
- **Reproducible net approximation** (t·√(12/n)) [I]: about 1.0 on the observed exit, about 0.65
  on the conservative exit.

**Costs as coded** (`cycle_study.py` `load()`/`net()`) [E]:
- Half of a 2% relative spread on entry premium, plus half on exit premium.
- STT on the sell-leg premium: 0.05% → 0.0625% (2023-04) → 0.1% (2024-10).
- Exchange charges (0.053% → 0.035%) × 1.18 GST on both legs.
- Stamp 0.003% on the exit (buy) leg.
- Brokerage approximated as a flat 0.3% of premium.

**Not reported:** post-reform gross at the 10-before row, and post-reform break-even spread.
**Whole confirmation window:** break-even spread 10.7%.

## 5. The proposed 2026-09-29 paper cycle

**Not run. Not spent.** [E]
- **Planned dates:** entry 2026-09-15 close, exit 2026-09-28 close. These match `nse_holidays.py`:
  09-14 is a holiday.
- **No stock-option quote exists for 2026-09-15.**
  - `spread_snapshot.py` writes `data/scratch/options_seller_edge/stock_opt_spreads.parquet`, and
    that file is absent. The folder holds only `stock_straddles.parquet`, dated 09-11.
  - Even the 2026-09-11 snapshot survives only as numbers in the report. It was written to the
    original session's scratchpad, which no longer exists.
- **The wall chain snapshots (2026-09-15 … 09-24) cannot stand in.** Their writer's universe is
  index-only: `NSE_INDEX|Nifty 50`, `Nifty Bank` and `BSE_INDEX|SENSEX` (`options_wall_counterfactual/battery.py:36`).
  They were not opened.
- **Nothing in git records it.** No commit after 2026-09-11 mentions a paper cycle.
- **The exit (2026-09-28) is still in the future.**

**The cycle is not clean either.** Its entry has passed, and about 7 of its 9 hold sessions are
now public. A freeze written today could not claim it as forward evidence.

## 6. Clean forward window remaining

- **Historical:** none. Stock options 2016 → 2026-08 are all read, discovery and confirmation.
- **Forward:** only cycles whose T−10 entry falls **after** a committed freeze. From
  `nse_holidays.py` [E]:

  | Expiry | T−10 entry | T−1 exit | Status |
  |---|---|---|---|
  | 2026-09-29 | 09-15 | 09-28 | lost, as above |
  | **2026-10-27** | **2026-10-12** | 2026-10-26 | **first clean cycle, if a freeze is committed before 2026-10-12** |
  | 2026-11-23 (Mon; 11-24 is a holiday) | 2026-11-06 | 2026-11-20 | |
  | 2026-12-29 | 12-14 | 12-28 | |

  - Expiry dates are read from the stock-option contract master (`nse_fo_instruments.duckdb`, snapshot 2026-09-24): 210 underlyings on 09-29 and 10-27, 209 on 11-23. December is not yet listed, so its date comes from the calendar rule.
- **Cadence:** 12 cycles a year at best.

## 7. Economic realism

### 7.1 Outcome-conditioned exclusion (construction defect, unmeasured)

- **What the code does:**
  - `build_stock_straddles.py` computes `ca_in_hold`: the count of front-future days with
    |ln return| ≥ 0.25 (+28% / −22%) **between entry and exit**.
  - `cycle_study.load()` then drops every cycle with `ca_in_hold ≠ 0` [E].
- **Why it matters:** the study describes this as a corporate-action filter, but it is evaluated
  on the **hold-period outcome**. A live book cannot un-trade a cycle after a crash.
- **What it removes:** splits and bonuses probably already fall out through a missing exit strike,
  because strikes are adjusted [I]. So the filter's extra effect falls on genuine single-day
  moves of −22% or worse, and +28% or more. Those are the seller's worst losses.
- **Where it applies:** both discovery and confirmation, and it runs through every table in the study.
- **Size: not measured, and not estimated here.**
- **Consequence:** any freeze must replace it with an ex-ante corporate-action calendar.

### 7.2 Other assumptions

| Assumption | Assessment |
|---|---|
| Entry and exit at the bhavcopy `close` (last trade), less half a 2% spread | Reasonable only if close ≈ mid. **Bid/ask evidence is a single mid-cycle day (DTE 12, 2026-09-11), not persisted.** T−10 and T−1 spreads are unmeasured, and relative spreads on shrunken T−1 premiums are likely wider [I]. Mitigant: break-even is 10.7%, about 5× the assumed 2%, so costs are not the binding risk |
| Untraded exit legs valued at `settle` (theoretical), 10–15% of exits | Addressed by the conservative Black-76 exit floor (t 2.01 confirmation, 0.86 post-reform) |
| Entry staleness | Entry requires both legs traded; the PCP-error cut changes nothing (+8.4%, t 2.97). Adequately handled |
| Exit before expiry (T−1, physical settlement avoided) | Correct design |
| STT schedule | Misses the 0.15% sell-side rate from 2026-04 (`core/execution/options/fees.py`). Affects about 5 cycles; immaterial |
| Brokerage as 0.3% of premium | Approximation of ₹20/order; disclosed |
| Margin | 18% is an assumption. The expiry-week **physical-delivery margin step-up falls inside the hold** [E: study §5.5]. It affects return on capital, not % of premium |
| Liquidity and capacity | Returns are one-lot, equal-weight. No capacity or impact study. The edge is **weakest in the ~40 most-traded names** (confirmation t 1.81, post-reform t 0.77) |
| F&O ban periods | `build_stock_straddles.py` has no ban filter. New short positions are prohibited on names above 95% of their market-wide position limit, but the entry filter only requires both legs to have traded that day. Unmeasured; direction unknown |
| Tail | Confirmation skew −1.40. The Apr-2025 cycle was −2.95% of notional, about 7 average cycles |

## 8. Is there enough forward sample for a new preregistered experiment?

**Not for confirmation on any useful horizon.** Monthly cycles needed for power 0.80 at one-sided
α = 0.05 (normal approximation, consistent with the study's `scripts/rfa/power.py` figure of 76 at S 1.0) [I]:

| Declared net Sharpe | Anchor | Cycles | Years |
|--:|---|--:|--:|
| 0.65 | post-reform, conservative exit (reproducible) | ~176 | ~14.6 |
| 0.84 | post-reform §5.5 (unreproducible) | ~105 | ~8.8 |
| 1.0 | post-reform, observed exit (reproducible) | ~74 | ~6.2 |
| 1.42 | whole confirmation window (pre-reform dominated) | ~37 | ~3.1 |

**Falsification is faster**: a few large losing cycles would be informative. But a forward
experiment framed as confirmation cannot deliver on a horizon shorter than 6 years unless the
Sharpe is pre-reform-like, which the post-reform data does not support.

## 9. Minimum next research action

**One step, audit-class, and no unread window is spent:** measure the §7.1 exclusion.
- Count the cycles and trades dropped by `ca_in_hold`, and their seller P&L.
- Separate genuine price moves from corporate actions against the CSMP corporate-action register.
- Do it on the already-spent 2016 → 2026-08 rows, with the construct and all other code unchanged.
- This decides whether the historical result survives its only known look-ahead.
- **Why this is legitimate on a spent window:** restoring the dropped crash cycles can only add
  seller losses. The measurement can confirm or kill the result but cannot rescue it, which
  distinguishes it from re-mining variants on spent data.

**What follows depends on the result:**
- **If the result survives,** the next step is an RFA declaration with an independently defended
  Sharpe band. Expect ABANDON or long-horizon PROCEED, per §8.
  - A freeze would have to be committed **before 2026-10-12** to claim the Oct-27 cycle.
  - Missing that date costs one cycle (one month).
- **If the result does not survive,** the classification moves to CLOSE.

**Cost:** zero new cycles and zero unread data. The one-month deadline only matters if the
operator wants the Oct-27 cycle.

## 10. Effect on earlier documents (same branch, uncommitted)

- `BASIS_FAMILY_POST_MORTEM_2026-09-24.md` listed straddle selling as READY for a clean
  experiment. That is superseded by this audit (INSUFFICIENT EVIDENCE).
  - Its proposed E0 kill screen reads the same 2016–22 straddle rows, so it inherits §7.1's
    outcome filter.
  - A pointer has been added.
- `INSTRUMENT_CORRECTNESS_AUDIT_2026-09-24.md` lists straddle selling as instrument-correct. That
  still holds: the instrument is right, and the defect is in the construction.
