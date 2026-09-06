# TS Basis / TS Basis Daily — Re-Authorization Assessment

**Generated:** 2026-07-31
**Author:** assessment pass (no code changed, no data read, no window spent)
**Question put by the operator:** *TS Basis Daily is not pre-registered, and TS Basis violated a
gate and was de-authorized — can we undo the wrong and register them again?*

---

## 0. Verdict

| Construct | Can the past be undone? | What is actually available |
|---|---|---|
| **TS Basis** (monthly) | **No.** The sealed window is spent and the authorizing gate genuinely did not hold. | The *defect can be priced*. The sealed number is estimator-correct and internally clean; the cost of the broken gate is one multiplicity increment, which the result survives by ~5 orders of magnitude. Standing stays **PAPER candidate** — but "not falsified" is demonstrable, not merely asserted. |
| **TS Basis Daily** | **No retroactive registration.** TRAIN and HOLDOUT are both burned as *selection surfaces*, so no pre-registration written today can claim them. | **RESOLVED 2026-08-01 — research-only (§B.4).** One unspent one-shot window exists (SEALED 2023-01-01 → 2026-07-24, 876 formations). The operator declared the construct research-only, so that window is **preserved unspent** and `run_sealed.py` is guarded against running. |

The short answer to "undo the wrong": no. The useful answer: **the monthly's wrong is smaller
than the label suggests, and the daily's situation is not a wrong at all — it is an unspent
asset that is one careless run away from being destroyed.**

---

## Part A — TS Basis (monthly)

### A.1 What actually happened (reconstructed from git, not from summaries)

| Date | Commit | Event |
|---|---|---|
| 2026-07-23 | — | Pre-registration frozen. SHA `07265b507179667588d06cb35c1e98c72bd065a3bbf95cf9a6c7d8b996a1ad84`. Sign `+1`, construction pinned, α = 0.025 one-sided (Bonferroni, m ≥ 2). |
| 2026-07-24 | `d177a04` | **HOLDOUT read** → reported **PASS**, IC +0.043, p = 0.0245 < 0.025, net +14.80%. *Computed with Pearson (`np.corrcoef`), not the pre-registered Spearman rank-IC.* |
| 2026-07-24 | — | `TS_BASIS_SEALED_READ_PROTOCOL.md` frozen (SHA `8bdec782…`), **the same day, holding a holdout report that said PASS.** |
| 2026-07-24 02:40Z | `42d17fc` | **SEALED read taken.** One shot. IC +0.076687, SD 0.084419, n = 42, t = 5.8872, p = 3.130120e-07, net +22.57%. |
| 2026-07-25 | `b9524cf` | Estimator defect found. Pearson → Spearman fixed at 4 sites. HOLDOUT recomputed: IC +0.0412, t = 1.96, **p = 0.0313 > α = 0.025 → FAIL**. SEALED report banner-marked **retroactively de-authorized**. |

### A.2 What is clean — and this matters

Three things survive scrutiny and are worth stating precisely, because the "de-authorized"
label obscures them:

1. **The sealed read used the correct estimator.** `scripts/signal_engine/ts_basis/run_sealed.py`
   used `spearmanr` from creation. It appears in no `-S pearson` or `-S corrcoef` search of its
   history, and the remediation commit `b9524cf` says so in its own message: *"run_sealed.py:135
   already used spearmanr (correct, unchanged)."* The Pearson bug never touched SEALED.
2. **The construction was frozen before the read.** Signal, sign, universe, portfolio, fees and
   no-trade band were all pinned in the 07-23 pre-registration under a SHA that has not moved.
   Nothing was tuned after the sealed result was seen.
3. **The one-shot rule was honored.** The sealed read was run exactly once. `run_sealed.py` has
   a single commit. The report was never regenerated — `b9524cf` appended a disclosure banner
   and changed no number.

So this is **not a contaminated result**. Internal validity is intact. What failed is
*selection*: the read should not have been authorized when it was.

### A.3 Why the de-authorization cannot be reversed

Two arguments for reversal exist. Both fail, and it is worth recording why, because both will
recur.

**Argument 1 — "0.0313 is close enough to 0.025."**
Unavailable. It is being made after seeing a favorable sealed result (+22.57%). Whether the
operator would have accepted a 25% threshold overrun *before* seeing that number is unknowable,
and that unknowability is the entire reason thresholds are pinned in advance. Relaxing α
post-hoc is the exact failure mode the repo's own C2 guard note warns against.

**Argument 2 — "the sealed protocol's §1 preconditions never required IC significance, and all
three passed."**
This is textually true. `TS_BASIS_SEALED_READ_PROTOCOL.md` §1 lists exactly three preconditions
— net-of-fee gate > 0 on TRAIN *and* HOLDOUT (passed, +14.80%), combination frozen (passed),
construction frozen (passed) — and HOLDOUT IC significance is not among them. It fails anyway,
for two reasons:

- **Timing.** §1 was drafted on 2026-07-24 while holding a holdout report that said
  `PASS, p=0.0245`. Nobody lists a precondition they already believe is satisfied. The omission
  therefore carries no information about what would have been authorized had the corrected
  number been in hand. It cannot be converted into affirmative authorization after the fact.
- **Structure.** The pre-registration's own header conditions the sealed window on *"the
  acceptance rule … met on TRAIN and HOLDOUT."* §6 is the only candidate in the frozen document.
  Reading §6 as pure falsification-with-no-acceptance-content makes that header refer to nothing
  — and would have authorized a sealed spend on a **negative-signed** IC as long as net > 0.
  No one pre-registers that.

Reversal on existing data is not available. The window is spent, and it was spent early.

### A.4 What *is* available: pricing the defect

The de-authorization's stated basis is a **multiplicity/selection** concern. Multiplicity has a
standard price, and it can be paid without moving any threshold:

| Multiplicity assumption | Deflated sealed p | Clears α = 0.05? |
|---|---|---|
| m = 2 (as declared in pre-reg §7) | 6.26e-07 | Yes |
| m = 10 (generous — every basis-family look) | 3.13e-06 | Yes |
| m = 100 (absurdly generous) | 3.13e-05 | Yes |
| **Break-even m** | — | **≈ 159,700 tests** |

You would need roughly **160,000 independent tests** for a sealed p of 3.130120e-07 to be a
selection artifact. The number of basis-family looks taken in this repo is in the single digits.

**What this establishes:** TS Basis is **not falsified**, and the broken gate's statistical cost
is negligible.
**What this does not establish:** authorization. "The read shouldn't have happened" is not
repaired by "the p-value is robust." Those are different claims, and only the first one is what
was violated.

**Net effect on standing: unchanged.** TS Basis remains the strongest PAPER candidate in the
repo, resolvable only by forward paper months. That is where CLAUDE.md already has it. The value
of this section is that the position is now *demonstrated* rather than asserted — and that a
future reader will not mistake "de-authorized" for "the signal failed."

### A.5 If forward paper is wanted, what it costs

Forward-paper formations required to reach power 0.80 on the monthly construct, one-sided
(computed from `scripts/rfa/power.py`):

| Effect-size scenario | δ | SD | n @ α=0.05 | n @ α=0.025 | Years @ α=0.025 |
|---|--:|--:|--:|--:|--:|
| Declared optimistic (crossed corner) | 0.090 | 0.08 | 7 | 9 | 0.8 |
| Declared central | 0.060 | 0.11 | 23 | 29 | 2.4 |
| Declared pessimistic | 0.030 | 0.14 | 137 | 173 | 14.4 |
| **HOLDOUT realized (the planning number)** | **0.0412** | **0.1031** | **41** | **52** | **4.3** |
| SEALED realized (*not* the planning number — see below) | 0.0767 | 0.0844 | 10 | 12 | 1.0 |

**Why HOLDOUT and not SEALED is the planning number, given §A.4.** §A.4 argues the sealed read is
internally clean, and that is true — but "clean" is not the same as "usable for planning here."
SEALED is the window whose *favorable* result prompted this reconsideration in the first place.
Sizing a forward run off δ=0.0767 selects the effect size on the strength of the very result
being re-examined, which would make the forward test look conclusive by construction. HOLDOUT is
the estimate that was not chosen for being large. The honest range to hold in mind is therefore
**12 to 52 months**, with the planning assumption at the pessimistic end of that range.

Power of a fixed-length forward paper run at α = 0.025:

| Scenario | 12 months | 24 months | 36 months |
|---|--:|--:|--:|
| Declared optimistic | 0.943 | 1.000 | 1.000 |
| Declared central | 0.407 | 0.726 | 0.889 |
| HOLDOUT realized | 0.244 | 0.466 | 0.645 |
| Declared pessimistic | 0.100 | 0.170 | 0.239 |

**Read this honestly:** on the cleanest out-of-sample effect-size estimate available
(HOLDOUT: δ=0.0412, SD=0.1031), a forward paper run needs **~52 months — over four years** — to
be conclusive at the multiplicity-adjusted floor. A 24-month run has power 0.47: more likely than
not to be inconclusive even if the signal is exactly as good as HOLDOUT measured it. This is the
demonstrability wall from the SFB-1/F1 section, arriving again on schedule.

---

## Part B — TS Basis Daily

### B.1 Retroactive registration is not available

`governance/rfa/declarations/ts_basis_daily.py` exists but was never frozen (line 2: *"SHA-256
will be computed after freeze"*), and **its prior-exposure statement is factually false as of
today.** It asserts:

> *"The daily TS Basis has NOT been read on TRAIN or HOLDOUT."*
> *"HOLDOUT (2021-2022) is unread for the daily variant."*

The repo's own commits falsify both:

| Commit | Date | What it did to TRAIN/HOLDOUT |
|---|---|---|
| `80f5e86` | 07-28 | Failure analysis over TRAIN — 117,809 signals bucketed by ADV, VIX, sector, \|z\|, gap. Produced explicit tuning advice ("raise the \|z\| threshold", "higher ADV floor"). |
| `48f83bb` | 07-28 | Recovery-state filter **selected on TRAIN, checked on HOLDOUT, and promoted** — HOLDOUT used as the acceptance surface (report §5: "HOLDOUT spread improvement PASS +5.75pp"). |
| `4521b86` | 07-28 | TP@0.5% exit policy chosen on "**TRAIN/HOLDOUT**" (+4–5pp net on both). |
| `80f5e86` | 07-28 | ML reject filter trained across TRAIN / VAL / HOLDOUT (discarded — but the window was read). |
| `9c97c98` → `e113f6b` | — | Sector cap max-2/leg added, then reverted after evaluation. |

HOLDOUT was not a holdout for this construct. It was a **selection surface**, used repeatedly to
accept and reject variants. A declaration cannot be frozen today claiming otherwise, and the
current file must be corrected before it is relied on for anything.

**This is a blocking finding, and it is independent of what the operator decides next.**

### B.2 The thing that *is* available — and it is the real answer to the question

**SEALED 2023-01-01 → 2026-07-20 has never been read for TS Basis Daily.** Verified four ways:

- No `TS_BASIS_DAILY_SEALED_REPORT.md` and no `TS_BASIS_DAILY_SEALED_SNAPSHOT.json` exist.
- Neither was ever committed on any branch (`git log --all --diff-filter=A` returns nothing).
- No daily report mentions "sealed" anywhere.
- **All 19 daily scripts were swept** — the 16 in `scripts/signal_engine/ts_basis_daily/` plus the
  3 top-level `scripts/ts_basis_daily_*.py` — for any date literal in 2023 or later. **`run_sealed.py`
  is the only file in the entire daily surface that references a post-2022 date.** Every other
  script (including `run_net_spread.py`, `validate_recovery_filter.py`, `apply_recovery_filter.py`,
  `research_exit_optimization.py`, `analyze_trade_intelligence.py`, `build_trade_intelligence.py`,
  `run_m2_analytics.py`, `run_failure_analysis.py`, `snapshot_options.py`) hard-stops at
  `2022-12-31` or carries no window bound at all.

`scripts/signal_engine/ts_basis_daily/run_sealed.py` exists and is loaded (window
`2023-01-01 → 2026-07-20`) but has never been executed to a committed artifact.

**Disclosed contamination, bounded:** the daily construct was created `d81859b` on **2026-07-27**,
and the operator has since watched the live `/ts-basis-daily/` panel and forward runner. That is
roughly **4 trading days** (2026-07-27 → 2026-07-31) of observed live signal at the very tail of
the declared range. Excising it — ending the sealed window at **2026-07-24** — removes the
exposure at a cost of 5 formations. Everything from 2023-01-01 through 2026-07-24 has zero
evaluated-outcome exposure.

**Exact counts** (measured 2026-08-01 from `ts_signals.duckdb`, `COUNT(DISTINCT formation_date)`
where `z_ts IS NOT NULL`): TRAIN 1,202 · HOLDOUT 495 · **SEALED 2023-01-01 → 2026-07-24: 876** ·
after 2026-07-24: 5 (excluded as observed).

**So there is one clean, one-shot, 876-formation window sitting on disk.** This is what "register
it again" can actually mean. It requires no forward waiting.

### B.3 What it would cost to spend it — the part that should give pause

Two problems, and the second is serious.

**Problem 1 — what gets frozen must be the whole selected stack.**
Every component below was chosen on seen data, so all of them must be frozen together and
disclosed as selected: base signal (z_ts, `LOOKBACK_ROWS = 252` trailing **rows**), the `basis_reverting` filter, the
TP@0.5% exit policy, the ranking rule that survived `e113f6b`, ADV floor, \|z\| threshold. You
cannot freeze "the signal" and treat the overlays as neutral implementation — they were fitted.
This raises m materially above the declaration's stated `m >= 1`, and pricing that is the
operator's call, not a detail.

**Problem 2 — the RFA gate would PROCEED only on the crossed corner.**
Recomputed from `scripts/rfa/power.py` against the declaration's own bands
(δ ∈ [0.005, 0.020], SD ∈ [0.12, 0.20]), one-sided, target power 0.80:

| Corner | δ | SD | n required | Years @ 250/yr |
|---|--:|--:|--:|--:|
| Optimistic (δ_hi × SD_lo — **crossed**) | 0.020 | 0.12 | **224** | 0.90 |
| Central | 0.0125 | 0.16 | **1,015** | 4.06 |
| Pessimistic | 0.005 | 0.20 | **9,894** | 39.6 |

Power at the **876** formations actually available (measured, §B.2):

| Corner | n=250 | n=500 | **n=876 (actual)** |
|---|--:|--:|--:|
| Optimistic | 0.837 | 0.981 | **0.9995** |
| Central | 0.340 | 0.540 | **0.7472** |
| Pessimistic | 0.106 | 0.139 | **0.1826** |

**A 44× spread in required n across the declared band, with PROCEED resting entirely on the
crossed corner (δ_hi paired with SD_lo).** This is precisely the artifact that withdrew O1
(`RFA_GATE_O1_REVIEW.md` §1). At the *central* assumption the existing 876-formation window
delivers power **0.7472 — below the 0.80 hurdle.**

The window cannot be extended *backwards* — NSE F&O history cannot predate 2016 — but it can be
extended **forwards**, and that changes the options materially. Central needs 1,015 formations;
**876** already exist on disk; the shortfall is **139 formations ≈ 6.8 months** at the measured
accrual rate of **20.4 formations/month** (stable: 245 / 246 / 248 in 2023 / 2024 / 2025).

**But 6.8 months is the arithmetic minimum, and pinning there is a mistake.** 1,015 is
`n_required` at *exactly* 0.80. Because the horizon must be fixed in the pre-registration and
cannot be extended after the fact, any shortfall in realized formations — universe attrition,
a thinner F&O list, `z_ts` nulls from the 12-observation minimum — lands the read under the
hurdle with no recovery available. **Pin 9 months, not 7.** See Option 1b in §B.4.

Note also that daily cadence buys nothing here: by the repo's own cadence-invariance result
(`ncp = S·√T`), running daily instead of monthly multiplies formations by ~20 while dividing
per-formation IC by ~√20. The daily variant's large `n` is not free power — and the declaration's
own band (δ 0.005–0.020 vs the monthly 0.030–0.090) already concedes this.

### B.4 The decision — RESOLVED 2026-08-01: Option 3, research-only

> **✅ OPERATOR DECISION, 2026-08-01: TS Basis Daily is RESEARCH-ONLY.**
>
> The construct has **no promotion path**. It is not frozen, not gated, and no sealed read is
> authorized. The **876-formation SEALED window (2023-01-01 → 2026-07-24) is preserved unspent.**
>
> **What this permits:** the construct continues as an exploratory tool. The `/ts-basis-daily/`
> panel, `ts_basis_daily_forward_runner.py`, the signal build and the EOD chain all keep running.
> Nothing is switched off.
>
> **What this forecloses:** freezing the declaration, running `run_sealed.py`, any gated
> evaluation, and any promotion to capital. Further accumulation of selection debt on TRAIN and
> HOLDOUT is pointless rather than harmful — there is no window left for it to contaminate,
> because none will be spent.
>
> **Enforcement, not just declaration:** `run_sealed.py` now refuses to run and writes nothing.
> This follows the repo's own lesson from the 2026-07-31 stale-feed incident — a constraint that
> is documented but never asserted is documentation, not a control. Deleting the guard is not by
> itself authorization to spend the window.
>
> **Why this is a defensible outcome, not a failure.** Spending the window now bought 0.7472
> central power on a stack that was still moving four days earlier. Option 1b bought 0.80 at the
> cost of freezing a construct whose whole overlay set — filter, exit, ranking — was fitted on
> seen data and whose multiplicity was never priced. Research-only declines to pay either price
> and keeps the only irreplaceable asset intact. The window survives for a construct that earns
> it; this one had not.

The options as assessed before the decision are preserved below for the record:

- **Option 1 — spend the daily sealed window.** Correct the declaration, freeze the full selected
  stack with a real SHA, write a sealed-read protocol with pinned α and acceptance rule, then run
  `run_sealed.py` exactly once on 2023-01-01 → 2026-07-24. Upside: a genuine out-of-sample read
  available *now*, no waiting. Downside: at the central effect-size assumption it is
  **underpowered (0.7472)**, and it is the last such window that will ever exist for this family.
- **Option 1b — freeze now, read once in 9 months. *(Recommended if the daily construct is to be
  pursued at all.)*** Correct the declaration, freeze the full selected stack today, and
  pre-register the evaluation window as **2023-01-01 → freeze + 9 months**, read **exactly once**
  when it closes. At 20.4 formations/month that yields ~876 + ~184 = **~1,060 formations**,
  clearing the 1,015 the central assumption needs with ~45 formations of margin. It costs 9
  months of waiting instead of the 4+ years a pure-forward monthly run needs (§A.5), spends the
  one-shot window only once, and spends it at adequate power rather than at 0.7472. It also
  imposes a useful discipline: the stack must stop moving today, because everything after the
  freeze is evaluation data.
  *(Why 9 and not the 6.8-month arithmetic minimum: 1,015 is `n_required` at exactly 0.80, and
  the horizon cannot be extended after the fact. Pinning at the minimum means any attrition in
  realized formations lands the read below the hurdle with no recovery. The margin is cheap;
  the failure is not.)*
- **Option 2 — do not spend it.** Keep the daily construct in research, run it forward in paper
  alongside monthly TS Basis, and preserve the sealed window until there is a stack worth
  spending it on. Costs nothing, forecloses nothing.
- **Option 3 — declare the daily construct research-only.** Accept it as an unregistered
  exploratory tool feeding the live panel, with no promotion path, and stop accumulating
  selection debt on it.

**Recommendation: Option 1b, or Option 2 if the stack is still moving.** `e113f6b` (a reverted
ranking change) is four days old, which suggests the construct is still under active modification
— and a one-shot window must not be spent on a moving target. Option 1b resolves that tension
directly: it *requires* the stack to freeze today, and buys adequate power for the cost of an
8-month wait. Option 1 (spend now at 0.740) is the weakest of the three, because it consumes the
last window at below-hurdle power to save 8 months.

---

## C. Findings requiring action regardless of the decision above

1. **`governance/rfa/declarations/ts_basis_daily.py` is inaccurate on two counts.** ✅ **CORRECTED
   2026-08-01.** It was never frozen, so correcting it cost nothing — but leaving it would have
   been worse than having no declaration, because a future reader would take it at face value.
   The delta/sd bands were left **unchanged** on purpose: re-banding after seeing the power
   arithmetic would be the same post-hoc move the RFA contract exists to prevent. A caveat was
   added to `sd_provenance` recording that the band is not yet defended against the selection
   history, and `n_available` was corrected 850 → 876 from a direct count.
   - **(a) False prior-exposure statement** (§B.1). It claims TRAIN and HOLDOUT are unread for the
     daily variant; five commits say otherwise.
   - **(b) Wrong lookback.** `delta_provenance` describes "504-day calendar lookback and
     12-observation minimum" — inherited verbatim from the monthly declaration. The daily build
     (`build_ts_basis_daily.py:28`) uses `LOOKBACK_ROWS = 252` as a **row-count** window
     (`ROWS BETWEEN 252 PRECEDING AND 1 PRECEDING`), not a 504-calendar-day one. The declaration
     does not describe the construct it declares.
2. **`TS_BASIS_SEALED_READ_PROTOCOL.md` §1 miscites its own mandate** — it claims to be "the final
   gate mandated by `TS_BASIS_PHASE0_PRE_REGISTRATION.md` §8", but §8 is *"What would make this
   illegitimate"*. The pre-reg has no section mandating a sealed read. This drafting looseness is
   what made Argument 2 in §A.3 superficially available.
3. **The fee-model certification arms are currently failing, and the daily net-spread numbers
   depend on them.** `tests/sfb/test_certification_arms.py::TestArmFE::test_all_boundaries_pass`
   fails on the 2008-06-01 STT boundary (returns 10.0, expects 12.5). This is **pre-existing on
   `main`** and unrelated to any TS Basis work — but the entire case for this construct rests on
   *net*-of-fee spreads, which run through that fee model. The failing boundary is in 2008, well
   outside the 2016+ futures substrate, so it most likely does not touch the daily numbers —
   **but "most likely" is doing real work in that sentence.** Before any sealed read, confirm
   which era boundaries the daily net-spread path actually exercises. Not urgent now; blocking
   before a one-shot read. (A second pre-existing failure,
   `tests/portfolio/test_carry_metrics.py::test_metrics_sink_called_during_execute` — `IndexError`
   at `carry_rebalancer.py:534` — is unrelated to fees but should not be left rotting either.)
4. **The pre-registration has no explicitly labelled acceptance rule.** Its header refers to "the
   acceptance rule" but no section is so named; §6 is titled "Falsifiable predictions" and mixes
   predictions with a falsification clause. Every future pre-registration in this repo should
   carry a section headed **"Acceptance rule (what authorizes the next window)"**, stated
   separately from the falsification clause. This single drafting gap is the proximate cause of
   the entire TS Basis dispute.

---

## D. What this assessment did not do

- **No code was changed, no declaration edited, no window read.** No data was touched.
- **No pre-registration was written.** The forward-`n` arithmetic in §A.5 and §B.3 should be seen
  before committing to a protocol, because it may change which option the operator wants.
- **The daily sealed read was not run**, and must not be until §C.1 is fixed and a protocol with a
  pinned acceptance rule is frozen.

---

**Bottom line.** The monthly wrong cannot be undone, but it is smaller than its label: the sealed
read is estimator-correct, construction-frozen and one-shot-clean, and the broken gate's price is
a multiplicity increment the result survives ~160,000× over. TS Basis is not falsified; it is
unauthorized, and only forward paper resolves that — 12 to 52 months depending on which effect
size you plan against, with the honest planning number at the long end.

The daily construct cannot be retroactively registered, but it holds something more valuable than
a retroactive stamp: **one unspent one-shot window on 876 formations already on disk**, currently
guarded by a declaration that misstates both what has been read and what the construct does. That
window is worth only 0.7472 power at the central assumption on its own — but combined with 9
months of forward data it clears 0.80 with margin. **Fix the declaration, freeze the stack, and
pre-register a single read of 2023-01-01 → freeze + 9 months.** That is the closest thing to "registering it
again" that is actually available, and unlike everything else on the table, it is not a
compromise.
