# TS Basis — Evidence Status Assessment

**Date:** 2026-09-24 · **Branch:** `research/funnels-filter`
**Standing:** research-design and evidence-status assessment. Git history, frozen reports and code
were read. **No data was read and no backtest run.**
**Tags:** **[E]** established, **[I]** inconclusive, **[H]** hypothesis.

---

## 0. Answer in one paragraph

**TS Basis did not pass its pre-registered gate, and it never had a valid gate to pass.**
- Its HOLDOUT was computed, inspected and used to declare the strategy "VIABLE" *before* the
  pre-registration was frozen. So HOLDOUT was never out-of-sample (§1).
- Its SEALED read was authorised by that already-seen HOLDOUT, through a wrong estimator. It was
  taken after Carry's SEALED PASS on the same window from the same basis data.
- Every number (TRAIN, HOLDOUT, SEALED) is a **spot**-return measurement. The book trades futures.
  In futures, the closely related Carry signal loses its entire spread to basis convergence.

What this does **not** mean: that the underlying spot phenomenon is false. SEALED spot IC +0.077
(t 5.89) is strong evidence that the basis level predicts *spot* returns. The Carry measurement
says that for the basis family, spot predictability and tradable futures returns are different
things.

**Bottom line:**
- **The strategy is unvalidated,** because of procedural failure.
- **As a futures book it is probably untradable [H],** because of the instrument.
- **The spot phenomenon is probably real [I],** and nothing here shows it false.

---

## 1. What exactly is wrong

Five defects, ranked by weight. The first two are new in this assessment.

| # | Defect | Evidence | Tag |
|---|---|---|---|
| **D1** | **HOLDOUT was seen before the pre-registration was even written.** At discovery, commit `22bb3dd` (2026-07-23 23:20), `ts_basis_reversal.py` computed TRAIN **and HOLDOUT** IC (+0.0412, t 1.93) and net spread (+14.80%), and declared the strategy **"VIABLE — positive net spread on both TRAIN and HOLDOUT."** The pre-registration text first appears 10 minutes later in `fa692c8` (23:30). That draft already says "Only HOLDOUT … provides out-of-sample confirmation" and marks HOLDOUT "**To be tested**". It was frozen at `5c1f5d2` (07-24 08:06). The "HOLDOUT read" `d177a04` two minutes later reproduced a net spread already on record. `TS_BASIS_REAUTHORIZATION_ASSESSMENT.md` §A.1 ("reconstructed from git") starts its timeline at the freeze and misses `22bb3dd`. That is why its "one multiplicity increment" pricing no longer holds. | git history | **[E]** |
| **D2** | **Everything is measured in spot.** `run_sealed.py:113-116` and `run_net_spread.py` score `fwd_ret_1m`, the adjusted *equity* close-to-close return, and charge no roll costs. In the same windows, Carry's spot spread (+14.4% / +8.4%) becomes gross futures −3.1% / −4.8%, because convergence equals the held basis gap (`CARRY_FUTURES_TRANSLATION_REVIEW.md`). TS Basis's signal correlates +0.62 with Carry's and its long leg holds names with high basis. | code; Carry measurement | **[E]** it is spot; **[H]** that the same wipe-out applies |
| D3 | **Wrong estimator in the authorising gate.** HOLDOUT was reported with Pearson (p 0.0245 < 0.025) instead of the registered Spearman (p 0.0313 > 0.025). This is the known de-authorisation (`b9524cf`). The discovery script also used Pearson (`np.corrcoef`, `22bb3dd` line 309). Its HOLDOUT +0.0412 matching the later Spearman recomputation is therefore a coincidence, or a sign of a different store. | `TS_BASIS_SEALED_REPORT.md` banner; `22bb3dd` source | **[E]** for the estimator; **[I]** for the match |
| D4 | **The sealed window was not blind to the basis family.** Carry's SEALED PASS (+20.52%, same window, same basis data) was on record before TS Basis was registered (pre-reg §7 cites it). With ρ(IC) +0.53 between the two, TS Basis's sealed success was partly predictable from Carry's. That is a selection concern on top of D1 and D3. | pre-reg §7; `MULTI_FACTOR_COMBINATION_ASSESSMENT.md` | **[E]** that it was known; **[I]** how much it matters |
| D5 | **Multiplicity was under-counted.** Pre-reg declared m ≥ 2. The same evening saw Carry v1, Carry v2, a weekly-vs-monthly Carry comparison (`8f4673b`, 22:58), and TS Basis discovery under a file named `…_reversal.py` whose final direction is persistence. The docstring says a 252-day lookback; the code uses 504. Discovery TRAIN IC was +0.0894; the frozen pipeline reports +0.0704 on the same 47 formations. The gap is unexplained: estimator, construction or store. Whether a direction or lookback was *chosen* cannot be proved or ruled out. | `22bb3dd` source; reports | **[I]** |

Separately, the sealed read is **not falsified.** Its internals are clean: Spearman, a
construction SHA-locked before the read, one shot only (`TS_BASIS_REAUTHORIZATION_ASSESSMENT.md`
§A.2). D1, D2 and D4 are what that assessment did not have.

---

## 2. Why the positive HOLDOUT and SEALED do not count as usable evidence

- **TRAIN (+0.070 / +0.089):** discovery surface, zero confirmatory weight. Pre-reg §0 says so.
- **HOLDOUT (+0.0412, p 0.0313):**
  - Seen before the freeze (D1), so it is a second discovery surface, not a test.
  - Even taken at face value it fails the registered α 0.025.
  - It was also used to select the construct ("VIABLE", "outperforms Carry by +784 bp").
- **SEALED (+0.0767, t 5.89, net +22.57%):**
  - Reached through a gate that (a) rested on seen data (D1), (b) used the wrong estimator (D3),
    and (c) was entered knowing the window favoured basis signals (D4).
  - Its p-value survives any plausible multiplicity count (re-authorisation assessment §A.4).
    What it cannot survive is the fact that nothing about the *path* to the read was blind.
  - **And it is a spot measurement (D2).** A perfectly authorised SEALED read would still only
    confirm spot predictability, not a return the registered futures book can earn.

So the positive numbers are **real measurements of the wrong things through a compromised
process.** That is not the same as false.

---

## 3. Signal, gate, selection, or something else?

| Layer | Verdict |
|---|---|
| **Pre-registration and gate** | **Failed.** HOLDOUT pre-seen (D1), wrong estimator (D3), multiplicity under-counted (D5). "Did not pass its pre-registered gate" is accurate, and understates it: the gate was never capable of being passed legitimately |
| **Sealed-window selection** | **Compromised** (D1 + D3 + D4). The window is now spent for this construct |
| **Instrument** | **The load-bearing problem going forward (D2).** Probably fatal to the futures strategy **[H]**; directly measurable on TRAIN+HOLDOUT without touching sealed data |
| **The spot signal itself** | **Not shown false.** Spot IC is positive in every window, strong on SEALED. Probably a real spot regularity **[I]**, economically the same family as Carry: spot moving toward rich futures prices, or a closing-price measurement effect (see §8, P4) |

Precisely:
- **"The strategy did not pass its pre-registered gate"** is **true.**
- **"The underlying phenomenon is probably false"** is **not supported** for the spot
  phenomenon.
- **For the tradable claim** (TS Basis earns money in futures), the phenomenon is **probably
  absent [H].** That is a statement about the instrument, not the gate, and it is testable.

---

## 4. Possible roles next to Carry

| Role | Assessment |
|---|---|
| **Independent alpha** | **No.** ρ(signal) +0.62 and ρ(IC) +0.53 with Carry; same data; both registered long-high-basis (anti-carry by KMPV Eq. 5). Probably shares Carry's convergence loss in futures [H] |
| **Incremental / residual signal** | **Open hypothesis [H]; the only role worth defining.** The component of own-history basis deviation that is orthogonal to the cross-sectional basis level has never been computed. It is a new quantity with no registered sign (§7) |
| **Confirmation filter** | **No.** Filtering Carry on a signal it correlates with at +0.62 mostly re-selects Carry's own extremes and narrows the book. Structurally rejected in `FUNNEL_CARRY_CONDITIONING_AUDIT_2026-09-24.md` §4 |
| **Diversification component** | **No evidence, measured evidence against.** The equal-weight blend with Carry has lift **0.986** (below Carry alone) on the repaired monthly store. The Sharpe 2.09 figure has unverified provenance. If both lose convergence in futures, blending two losing books diversifies nothing |
| **Conditioning variable** | **No.** Month-level conditioning is undemonstrable (65–740 months for 80% power, funnel audit §7), and it would condition basis on basis |

---

## 5. Why a positive measured return does not justify a mixture today

1. **Wrong currency.** Every positive TS Basis return is spot. The only futures measurement in the
   family (Carry) turned +14% spot into −3% futures. A mixture of futures books cannot be sized
   off spot returns.
2. **No measured benefit even in spot.** Blend lift 0.986.
3. **Weights would be fitted on burned data.** Every window (TRAIN, HOLDOUT, SEALED) is spent for
   both legs. Any mixing weight is chosen in-sample: the TS Basis Daily failure mode
   (m ≫ 1, no α justified).
4. **It cannot run forward.** The builder requires `fwd_ret_1m IS NOT NULL`, so it cannot score a
   live formation (§8, P2). A mixture would silently be Carry alone.
5. **Governance.** De-authorised; the repo's lift-first `composite_gate.py` would reject the pair
   at the LIFT stage.

---

## 6. Minimum new evidence to rehabilitate TS Basis

In order. Each step can end it.

1. **Futures translation of the frozen TS Basis book, TRAIN+HOLDOUT, fenced ≤ 2022-12-31.**
   - Descriptive, the same method as `futures_translation.py`. It is a measurement, not a variant,
     and reads no sealed data.
   - **Kill rule, written now:** if the futures IC is ≤ 0, or convergence consumes the spot spread
     (gross futures ≤ 0), TS Basis is closed as a futures strategy. No forward run can
     rehabilitate a construct that earns nothing in the instrument it trades.
2. **Only if (1) survives: repair provenance.** A forward-capable builder with no `fwd_ret` filter,
   scripts pointed at the monthly store, and the store archived.
3. **A new pre-registration.** Its own RFA, measured on futures returns. Effect-size band anchored
   on the (1) futures result, never on SEALED. An explicit acceptance rule. All D1–D5 disclosed as
   prior exposure.
4. **Forward-only confirmation after a new freeze date.**
   - At the spot HOLDOUT effect size (0.041 / 0.103), about **52 months** at α 0.025
     (re-authorisation assessment §A.5).
   - At a futures effect size it is likely **longer or unreachable.**

There is no shortcut through any existing window.

---

## 7. Is "TS Basis adds information after residualising on Carry" a new hypothesis?

**Yes, a genuinely new one, requiring its own pre-registration and RFA.**
- **Different quantity.** It is the part of z_ts orthogonal to z_carry_neut. Plausibly closer to
  basis *change* (basis momentum) than to basis level **[H]**. Neither parent measured it.
- **The repo has already ruled on this shape.** `BASIS_MOMENTUM_DECISION_REVIEW.md` §3 declined
  basis-momentum because no unread window exists to validate it. A residualised TS signal inherits
  that ruling unless the operator explicitly revisits it.
- **No registered sign.** TS Basis's +1 applies to the raw z_ts. The residual's sign would have
  to be declared ex-ante, and must be economically defended for **futures** returns.
- **Fully prior-exposed.** TRAIN, HOLDOUT and SEALED are all read for both parents. Any
  historical residual IC is an in-sample **kill screen only** (for example, kill if the upper
  95% bound < 0.02), never evidence.
- **Confirmation is forward-only,** and the RFA must clear with an ex-ante band. At a residual IC
  plausibly below either parent's, it will likely **ABANDON.** Know this before writing it.

---

## 8. Data and provenance problems in the current implementation

| # | Problem | Effect on the positive result | Tag |
|---|---|---|---|
| P1 | Spot `fwd_ret_1m` target; no roll cost | Positive numbers are spot-only; futures result unmeasured (D2) | [E] |
| P2 | `build_ts_signals.py:66-69` requires `fwd_ret_1m IS NOT NULL` for every row, including the scored one | Cross-section at *t* conditioned on a price existing at *t*+1 (survivorship-type look-ahead, small); no live formation can be scored | [E] |
| P3 | `run_holdout.py` and `run_sealed.py` read `ts_signals.duckdb`, which since `03fc76a` (07-26) holds the **weekly** store (on disk: mtime Aug 10). The store the sealed read used (07-24) is not archived: nothing in `data/signal_engine/ts_basis/` or `data/_baselines/` dates from then. And the Carry source store was later rebuilt, including a period with `fwd_ret_1m` all NULL (`MULTI_FACTOR…` defect 1) | Neither HOLDOUT nor SEALED can be regenerated bit-for-bit from repo state today | [E] |
| P4 | **Dividend seasonality in raw basis vs price-return target.** TS Basis uses raw, unadjusted basis. A name heading into an ex-date has a futures price net of the dividend, so its basis dips below its own history. Low z_ts puts it in the short leg. Its *price* return (ordinary dividends are not added back in `equity_bhavcopy_adjusted`) then drops by the dividend. That is mechanical spot "alpha": worth nothing to a futures holder or a total-return holder. Carry's dividend component was −2 to −15 bp/month; the own-history construction plausibly isolates dividend months more sharply | Inflates the spot spread by an unmeasured amount | [H] |
| P5 | Asynchronous closes: futures close (last trade) vs spot official close (30-min VWAP) | Spot-close error enters the signal and the target with opposite signs, which can make a spot IC mechanical. The settle check covered only the futures side | [H] |
| P6 | No beta or sector neutralisation; beta checked (+0.022), sector exposure never tested | Unknown sector tilt in the spread | [I] |
| P7 | Discovery-vs-frozen TRAIN IC gap (+0.0894 vs +0.0704, same 47 formations). **Both computed with Pearson, so the estimator is not the explanation.** The construction or source store differed between 23:20 and 23:30 on 07-23. Also a 252-vs-504 lookback docstring mismatch | Cannot confirm the frozen construction is the one that was first evaluated | [I] |
| P8 | Not affected by Carry's dividend sign defect (TS Basis does not dividend-adjust) | — | [E] |

P1, P4 and P5 can each be checked on TRAIN+HOLDOUT data without touching sealed data.
P1 matters most.

---

## 9. Recommendation

- Record TS Basis as **"unvalidated (procedural), untranslated (instrument); spot phenomenon not
  falsified."** Retire the "strongest PAPER candidate" wording.
  `TS_BASIS_REAUTHORIZATION_ASSESSMENT.md` §A.4's "defect priced at one multiplicity increment"
  does not survive D1: HOLDOUT was never an out-of-sample test.
- **Next step, if any:** §6 step 1, the futures translation with the kill rule. It is the
  cheapest, most decisive and cleanest test available. Until it runs, no role for TS Basis
  (alpha, residual, filter, diversifier, conditioner) should be designed.
