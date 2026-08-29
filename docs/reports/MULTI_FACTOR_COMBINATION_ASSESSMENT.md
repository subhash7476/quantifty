# Multi-Factor Combination Assessment — every RFA-declared construct

**Date:** 2026-08-28 (revised 2026-08-29 — TS Basis substrate repaired, sixth sleeve added,
composite gate implemented)
**Question:** across all constructs ever declared through the RFA gate, can any of them
be combined into a multi-factor model?
**Method:** structural screen over all 14 declarations, then a measured pairwise
combination matrix on the subset that survives the screen
(`SLEEVE_COMBINATION_MATRIX.md`, script-generated).
**Standing:** decision-support. Arithmetic on already-measured quantities and already-read
windows. **No sealed window was touched** — every query is fenced at
`formation_date <= 2022-12-31`, and the realized maximum (2022-12-30) is printed in the
matrix report.

---

## 0. Answer

**15 pairs measured across the six combinable sleeves. 13 are worse than their own best leg.
Two beat it, and both of those are unusable. Zero candidates.**

- **`LAG + SKEW`** (lift 1.291) needs a sign for LAG that **opposes its registration** and a
  sign for SKEW that was **never registered** — two directions read from burned data.
- **`TS_BASIS + IVOL`** (lift 1.024) passes the mechanical sign check only because IVOL's IC
  was negative as registered *on TRAIN+HOLDOUT*. **IVOL's sealed read reversed that sign**
  (+0.018, net −13.78%), so the check approves a direction the out-of-sample data has already
  refuted. A 2.4% edge on 71 formations is inside the noise regardless, and both legs' sealed
  reads are spent.
- **`CARRY + TS_BASIS` — the pair most worth testing — measures lift 0.986.** Marginally
  worse than Carry alone. The reason is that they are substantially **the same factor**:
  ρ(signal) **+0.6172**, ρ(IC) **+0.5344**. This materially revises the CLAUDE.md estimate
  (L/S return ρ = 0.46, blend Sharpe ~2.09 vs ~1.72).
- **Carry is degraded by every partner it has**: +TS_BASIS 0.986, +IVOL 0.928, +TREND 0.765,
  +SKEW 0.488, +LAG 0.332.

This is not a claim that multi-factor models don't work. It is a claim about *these* factors:
the repo's non-Carry sleeves are wrong-signed, unsigned, or strongly correlated with Carry,
and none of them adds enough information to justify a combination.

---

## 1. The precedent already in the repo — and the gate defect it hid

`IVOL_COMPOSITE_CHECK_REPORT.md` is a completed, script-generated, real-data run of exactly
the experiment being asked about. Its numbers:

| | IR | Power @ n*=42 |
|---|--:|--:|
| Carry standalone | 0.6159 | 0.9887 |
| IVOL standalone | 0.3057 | 0.6192 |
| **Composite (Carry − IVOL)** | **0.6005** | **0.9854** |

**The composite is worse than Carry alone on both metrics.** It was recorded as
**"Gate-4 Verdict: PASS"** and that PASS authorized opening the sealed window — because the
gate asked only *"composite ≥ 0.80"*, never *"composite > best standalone"*. The sealed read
came back sign-flipped (IVOL IC +0.018, net −13.78%).

**Root cause:** the frozen §13 rule 3 ("after ≥2 TRAIN reads, the realized composite faces
0.80") is satisfiable by a composite that *destroys* value, because 0.80 is an absolute
floor, not a comparison. A single strong leg carries the composite over the bar.

**Fix implemented** — see §5.

---

## 2. Structural screen — all 14 declarations

A multi-factor model requires the legs to **score the same objects at the same times**.
Constructs that predict different things cannot be blended; the question closes before any
statistics are computed.

| # | Construct | Metric | Cadence | Cross-section | RFA | Gate outcome | Combinable? |
|---|---|---|---|---|---|---|---|
| 1 | **CARRY** | rank_ic | monthly | SSF ~180 names | PROCEED 0.8893 | TRAIN(v1 sign)→HOLDOUT PASS→**SEALED PASS** | ✅ **yes** |
| 2 | **TS_BASIS** | rank_ic | monthly | SSF | PROCEED 1.0000 | TRAIN PASS→HOLDOUT defect→SEALED **de-authorized** | ✅ yes |
| 3 | **TREND** | rank_ic | monthly | SSF | PROCEED 0.9110 | TRAIN FAIL (t=1.13) | ✅ yes |
| 4 | **SKEW** | rank_ic | monthly | SSF liquid-options subset | (no gate report; pre-reg ~0.83) | TRAIN FAIL (t=−1.15) | ✅ yes |
| 5 | **IVOL** | rank_ic | monthly | SSF | PROCEED 0.9853 | TRAIN PASS→HOLDOUT PASS→gate-4 PASS→**SEALED FAIL** | ✅ yes |
| 6 | **LAG** | rank_ic | monthly | SSF | PROCEED 0.8893 | TRAIN FAIL (wrong sign, 58% subsumed) | ✅ yes |
| 7 | FLOW | rank_ic | monthly | SSF | **ABANDON 0.6053** | no read taken | ❌ no signal exists |
| 8 | TS_BASIS_DAILY | rank_ic | **daily** | SSF | frozen | research-only; TRAIN+HOLDOUT burned as selection | ❌ cadence |
| 9 | CB_N50 | rank_ic | **daily** | **Nifty 50 constituents** | PROCEED 1.0000 | TRAIN PASS→HOLDOUT PASS→CLOSED | ❌ universe + cadence |
| 10 | ISD-OPEN-DRIVE | rank_ic | **daily intraday** | PIT F&O, EOD-flat | PROCEED 0.9938 | battery TRAIN **FAIL** | ❌ cadence/horizon |
| 11 | ISD-OVERNIGHT-GAP | rank_ic | **daily intraday** | PIT F&O, EOD-flat | PROCEED 0.9938 | battery TRAIN **FAIL** (net −3196 bp) | ❌ cadence/horizon |
| 12 | A-INDEX-INTRADAY | **per_trade_pnl** | daily | **single index** | PROCEED 0.8720 | TRAIN PASS→**HOLDOUT FAIL** (−0.22 bp) | ❌ no cross-section |
| 13 | RS-MOM | **per_trade_pnl** | weekly | **two indices** | **ABANDON 0.337** | no read taken | ❌ no cross-section |
| 14 | O1-VRP | **per_trade_pnl** | weekly | **single index** | **WITHDRAWN** (crossed corner) | no read taken | ❌ no cross-section |

### Why the exclusions are structural, not statistical

- **#12–14 have no cross-section.** `per_trade_pnl` on one or two index time series produces
  a single P&L stream, not a rank over names. There is nothing to blend into a
  cross-sectional z-score. Combining two P&L streams *is* possible as portfolio allocation,
  but that is a different exercise with much harsher demonstrability arithmetic
  (`ncp = S·√T`, √T_sealed ≈ 1.89 → Sharpe ≥ ~1.3) — and #13/#14 never produced a signal to
  allocate to, while #12 failed HOLDOUT.
- **#9 CB-N50** ranks Nifty 50 constituents daily — different universe *and* cadence. Its
  honest effect size is the HOLDOUT +0.029, not the TRAIN +0.059.
- **#10–11 ISD** are daily intraday, EOD-flat — a different prediction horizon, and both
  failed the battery TRAIN (F4 net **−3,196 bp**).
- **#7 FLOW** was killed by the gate before any data was read. There is no signal series.

That leaves **six** constructs sharing one cross-section and one cadence, on 71 aligned
month-end formations, 2017-02-28 → 2022-12-30.

---

## 3. The measured result

Full table: `SLEEVE_COMBINATION_MATRIX.md` §2.

### Standalone

| Sleeve | Mean IC | SD(IC) | IR | t | Registered sign |
|---|--:|--:|--:|--:|---|
| CARRY | +0.0479 | 0.0799 | **0.5995** | +5.05 | ✅ positive |
| TS_BASIS | +0.0534 | 0.1031 | **0.5181** | +4.37 | ✅ positive |
| IVOL | −0.0420 | 0.1513 | 0.2777 | −2.34 | negative — **flipped on SEALED** |
| SKEW | −0.0245 | 0.1165 | 0.2099 | −1.77 | **none** (two-sided) |
| LAG | −0.0207 | 0.1357 | 0.1525 | −1.28 | positive — **realized negative** |
| TREND | +0.0180 | 0.1436 | 0.1251 | +1.05 | ✅ positive |

**Two sleeves carry signal** (Carry t +5.05, TS Basis t +4.37). The other four have |t| ≤ 2.34,
two of them wrong-signed.

### Pairwise, ranked by lift

> **Reading the IR columns.** `Best leg` is measured **on that pair's own intersection**, not
> the full panel, so a sleeve's IR varies by row (Carry: 0.5995 full-panel, 0.6719 on the LAG
> intersection, 0.3326 on the narrower SKEW one). `Mean names` shows intersection width.
> Lift is always composite ÷ best leg **on the same rows**.

| Pair | Mean names | ρ(signal) | ρ(IC) | IR composite | Best leg | **Lift** | Sign discipline |
|---|--:|--:|--:|--:|--:|--:|---|
| LAG + SKEW | 80 | −0.0780 | −0.0637 | 0.3021 | 0.2340 | **1.291** | ❌ both legs |
| **TS_BASIS + IVOL** | 145 | −0.0033 | +0.0460 | 0.5304 | 0.5181 | **1.024** | ✅ |
| CARRY + TS_BASIS | 145 | **+0.6172** | **+0.5344** | 0.6566 | 0.6657 | 0.986 | ✅ |
| CARRY + IVOL | 166 | −0.0358 | +0.0896 | 0.5562 | 0.5995 | 0.928 | ✅ |
| TREND + IVOL | 154 | −0.1676 | −0.6122 | 0.2354 | 0.2846 | 0.827 | ✅ |
| CARRY + TREND | 153 | −0.0391 | −0.2432 | 0.4978 | 0.6510 | 0.765 | ✅ |
| TS_BASIS + TREND | 145 | −0.0135 | +0.0364 | 0.3963 | 0.5222 | 0.759 | ✅ |
| IVOL + LAG | 145 | +0.3093 | +0.5210 | 0.1980 | 0.2964 | 0.668 | ❌ LAG |
| CARRY + SKEW | 88 | −0.6329 | −0.5085 | 0.1621 | 0.3326 | 0.488 | ❌ SKEW |
| TS_BASIS + LAG | 137 | +0.0059 | −0.1114 | 0.2164 | 0.5084 | 0.426 | ❌ LAG |
| TS_BASIS + SKEW | 83 | −0.3970 | −0.4865 | 0.1529 | 0.3765 | 0.406 | ❌ SKEW |
| CARRY + LAG | 144 | +0.0185 | +0.1947 | 0.2231 | 0.6719 | 0.332 | ❌ LAG |
| IVOL + SKEW | 88 | +0.0102 | +0.0305 | 0.0883 | 0.2707 | 0.326 | ❌ SKEW |
| TREND + LAG | 145 | −0.8822 | −0.9530 | 0.0318 | 0.1525 | 0.208 | ❌ LAG |
| TREND + SKEW | 85 | +0.0925 | +0.1879 | 0.0154 | 0.2312 | 0.067 | ❌ SKEW |

### Findings

**F1 — Carry and TS Basis are substantially the same factor.** ρ(signal) **+0.6172**,
ρ(IC) **+0.5344**. Both are basis constructs (Carry is *residual* basis, TS Basis is basis
*level*), and the measurement says the residualization removes less than half the shared
variation. Their composite lands at lift **0.986** — a fractional loss, not a gain. Even the
optimistic reading is bounded: at ρ = 0.53 the additive formula `√(N/(1+(N−1)ρ))` caps the
lift at ~1.14 *before* any IC-correlation drag, and the drag consumes it. (That formula assumes
roughly equal leg strength, which holds here — Carry 0.5995 vs TS Basis 0.5181 — but does not
hold for pairs whose legs differ several-fold, such as Carry+TREND.)

This revises the estimate recorded in CLAUDE.md (L/S return ρ = 0.46; blend Sharpe ~2.09 vs
Carry-alone ~1.72). That estimate was decision-support on return series; this is a direct
IC-level measurement on the registered monthly construction, and it is less favourable.

**F2 — the only two lifts above 1.0 are both unusable.**
- `LAG + SKEW` (1.291) needs a sign for LAG that **opposes its one-sided registration** and a
  sign for SKEW that was **never registered**. Two signs read from burned data.
- `TS_BASIS + IVOL` (1.024) passes the mechanical sign check because on TRAIN+HOLDOUT IVOL's
  IC was negative as registered. **But IVOL's sealed read flipped that sign** (+0.018, net
  −13.78%). The check approves a direction the out-of-sample data has already falsified. A
  2.4% lift on 71 formations is also well inside noise.

**F3 — LAG is very close to negative Trend.** ρ(signal) **−0.8822**, ρ(IC) **−0.9530**. The
pre-registered subsumption guard fired at 58% (resid IC / raw IC); this supersedes it with
the direct quantity. These are one factor, sign-flipped, and their composite cancels to
IR 0.0318 (lift 0.208).

**F4 — ρ(IC) governs composite IR, not ρ(signal).** `CARRY + IVOL` measures ρ(signal)
−0.0358 — textbook "decorrelated, should combine well" — yet ρ(IC) is **+0.0896** and the
composite loses. The gate-4 report saw the same thing (realized/quadrature ratio 0.873 at
signal ρ −0.036, IC ρ +0.2287). **Signal decorrelation does not imply IC decorrelation, and
only the latter buys breadth.**

**F5 — the breadth thesis is not falsified; it has no inputs here.**
`IR ≈ √(Σ IRᵢ²)` requires weakly-correlated sleeves *that individually carry signal*. Of six,
two carry signal — and those two are correlated at ρ(IC) +0.53. The remaining four are noise,
and averaging noise into signal is what the lift column measures.

---

## 4. Substrate defects — found, then repaired

Both were discovered while building the matrix. Both are now fixed.

### Defect 1 — Carry's forward returns were entirely NULL — **FIXED**

`data/signal_engine/carry/signals.duckdb` had `fwd_ret_1m` NULL in **all 23,419 rows**. Both
`run_train.py:262` and `run_net_spread.py:196` filter `fwd_ret_1m IS NOT NULL` against that
store (`SIG_DB`, `run_train.py:30` / `run_net_spread.py:23`), so they had no rows to score.

**Why it did not self-heal:** `build_carry.py:308-314` scopes the fill to
`formation_date IN (fmt_dates) AND fwd_ret_1m IS NULL` — only dates built in that same run.
An incremental refresh fills the new month and leaves history NULL. The `UPDATE` at line 352
is unguarded: if the `eq_subset` join yields nothing, zero rows are filled and the build
still reports success — the repo's own "printed but never asserted" failure class.

**Repair:** `scripts/signal_engine/carry/backfill_fwd_returns.py` — committed, idempotent,
`--dry-run` capable, using the identical join. Unlike `build_carry.py` it **asserts** that
rows filled equals rows the join said were fillable and exits non-zero otherwise.

- Copy-first baseline taken before the write: `data/_baselines/carry_signals_20260829_091650.duckdb`
- Filled **22,973** of 23,419; 446 remain NULL (last formations with no
  `fwd_formation_date`, plus delisted names) — the expected shape.
- **Validated:** against `ivol/signals.duckdb` on 19,622 common rows, **0 mismatches,
  max absolute difference 0.0**.

### Defect 2 — TS Basis's store was the weekly variant — **FIXED**

`build_ts_signals.py` hardcoded `carry/weekly_signals.duckdb` as its source and wrote to the
default `ts_signals.duckdb`, so the on-disk "TS Basis" store was a **weekly** grid (349 fenced
formations on Fridays, only 35 month-ends) — not the registered monthly sleeve.

**Repair:** `--source {weekly,monthly}` flag. `monthly` reads `carry/signals.duckdb` and
writes `ts_signals_monthly.duckdb`. Non-destructive: the default stays `weekly` so
`refresh_all_strategies.py` is unchanged, and the weekly store was **not written** — mtime
unchanged (Aug 10), counts unchanged (67,794 rows, 535 formations). The z parameters (504 calendar days, MIN_OBS 12,
winsorize ±3) are identical on both grids; only formation spacing differs.

- Built: **17,309 signals across 112 formations**, of which **71 fall in the fenced window** —
  exactly the grid the other five sleeves use.
- This unblocked the `CARRY + TS_BASIS` measurement, which was the one pair worth testing.

### Defect 3 — `fwd_ret_1m` disagrees between stores — **open**

IVOL and LAG match exactly on all 17,406 common rows; TREND differs on **183** (~1.1%).
Carry now matches IVOL exactly. TREND is unreconciled. Low severity — TREND is a TRAIN-failed
sleeve — but it should be resolved before TREND is ever re-read.

---

## 5. The gate change — implemented

`scripts/signal_engine/combination/composite_gate.py` evaluates three conditions **in order**,
stopping at the first failure:

1. **LIFT** — composite IR must exceed the best standalone leg's IR, both on the same
   intersection. A combination that does not beat its own best leg is a dilution.
2. **SIGN** — every leg's realized IC sign must match a sign registered *before* the read. No
   registered sign, or a realized sign opposing registration, means the composite needs a
   direction chosen from data and has no valid confirmatory test.
   **Plus `Leg.sign_falsified`.** A naive sign check compares the registration against
   *whatever series it is handed*. Hand it TRAIN+HOLDOUT and IVOL passes — its IC was negative
   as registered on those windows — while the SEALED read that reversed it stays invisible.
   That is the exact hole that produced F2's spurious `TS_BASIS + IVOL` survivor. Declaring
   `sign_falsified=True` fails the leg at the SIGN stage, so the gate cannot approve a
   direction later data refuted.
3. **POWER** — composite power at n* must clear 0.80.

**Order is the whole point.** Power is last, not first, because a diluting composite can clear
0.80 on the strength of one leg alone — which is exactly what happened.

**Validated against the real gate-4 case.** Replaying Carry+IVOL on the same 47 TRAIN
formations, the gate reproduces every published intermediate number and reverses the verdict:

| Quantity | Gate-4 report | This gate |
|---|--:|--:|
| Formations | 47 | 47 |
| IR Carry | 0.6159 | 0.6159 |
| IR IVOL | 0.3057 | 0.3057 |
| IR composite | 0.6005 | 0.6005 |
| Power | 0.9854 | 0.9854 |
| **Verdict** | **PASS** | **FAIL (stage LIFT, lift 0.975)** |

**Tests:** `tests/signal_engine/test_composite_gate.py` — **10 passing**. One test asserts the
diluting composite's power is ≥ 0.80 *and* that the gate rejects it anyway, pinning the
regression. Another pins the `sign_falsified` hole: it first asserts the pair passes when the
falsification is not declared, then that declaring it fails at SIGN.

**Not yet done:** this gate is not wired into any pre-registration. `CARRY_PHASE0_PRE_REGISTRATION.md`
§13 rule 3 still reads as an absolute-0.80 rule. Amending a frozen pre-registration is an
operator decision, not a code change.

---

## 6. Governance verdict

**No multi-factor combination is authorized, and none is recommended.**

The arithmetic and the governance constraint agree, which is the cleanest kind of answer —
the question fails on its own numbers before it reaches the window problem.

- 13 of 15 pairs destroy value. The 2 that don't are unusable (F2).
- **The SSF/basis family has no unread confirmatory window.** SEALED 2023→present is spent:
  Carry PASS, TS Basis de-authorized, IVOL FAIL.
- **Futures history cannot predate 2016**, so n* cannot exceed ~42 monthly formations. The
  calendar lever is exhausted (SFB-1/F1).
- A combination introduces **free parameters** — weights, or a sign for LAG/SKEW. Fitting them
  on TRAIN+HOLDOUT is the TS Basis Daily failure mode exactly ("TRAIN and HOLDOUT both burned
  as SELECTION surfaces, m ≫ 1, no α is justified").
- `CARRY_PHASE0_PRE_REGISTRATION.md` §13 rule 4 already forbids the required move:
  **"Weights are never tuned to manufacture 0.80."**

### What is actually available

1. **Carry standing alone is unchanged by this work.** This assessment did not evaluate
   whether Carry should ship — that was settled before it. What it establishes is narrower and
   still useful: **no available partner improves Carry.** Every combination tested makes it
   worse, so there is no case for adding a sleeve to it.
2. **TS Basis stays a PAPER-forward candidate.** Its de-authorization is a gate defect, not a
   signal defect (standalone IR 0.5181, t +4.37), and only forward paper months can resolve
   it. Its monthly construction is now reproducible again (defect 2). **But note F1:** it is
   ~53% correlated with Carry at the IC level, so running both is closer to running Carry at
   larger size than to running two sleeves.
3. **A genuine second factor must come from outside this set** — a different cross-section or
   a different economic claim, with its own pre-registration, its own RFA on an independently
   defended band, and its own unread window. It does not come from recombining constructs that
   have already failed.

---

## Artifacts

| File | Purpose |
|---|---|
| `scripts/signal_engine/combination/sleeve_pair_matrix.py` | Measurement harness (fenced, canonical returns, lift + sign discipline) |
| `scripts/signal_engine/combination/composite_gate.py` | **The lift-first composite gate** |
| `tests/signal_engine/test_composite_gate.py` | Gate tests — 10 passing |
| `scripts/signal_engine/carry/backfill_fwd_returns.py` | Defect-1 repair (guarded, idempotent) |
| `docs/reports/SLEEVE_COMBINATION_MATRIX.md` | Script-generated matrix — standalone stats, 15 pairs |
| `docs/reports/IVOL_COMPOSITE_CHECK_REPORT.md` | The prior composite run whose defect this names |
| `data/_baselines/carry_signals_20260829_091650.duckdb` | Copy-first baseline taken before the defect-1 write |
