# Stage A — Index Intraday Structural Discovery Lab

**Status:** DESIGN — for operator review. No code written, no data read beyond
the substrate census in §14. Nothing here is a result.
**Date:** 2026-08-29
**Governing precedents:** `A_PHASE0_PRE_REGISTRATION.md` (the Stage-B template
this defers to) · `ISD_PROGRAM_REASSESSMENT.md` (the cost-floor closure rule) ·
`A_INDEX_INTRADAY_PRIOR_EXPOSURE_AUDIT.md` (the exposure boundary) ·
`TS_BASIS_REAUTHORIZATION_ASSESSMENT.md` §B (what an ungoverned search costs)

---

# PART I — METHODOLOGY

## 1. What Stage B gets right

Stage B is not the thing to fix. Its properties, in order of value:

1. **Pre-commitment.** Hypothesis, parameters, universe, execution rules,
   costs, tests, gates and termination are frozen before the relevant result
   is consumed, and the freeze is SHA-sealed. A's pre-registration
   (`ccb32090704a3396`) and RFA declaration (`221c6ca9…`) were written before
   the first TRAIN read and were never edited afterwards.
2. **One-shot windows with a termination mapping.** "HOLDOUT fail → construct
   retired, SEALED untouched" was written before the result and executed
   against a construct the operator wanted to work. That is the whole game.
3. **Matched empirical nulls rather than textbook t-tests.** Sign-permutation
   and block-shift nulls preserve the return-magnitude and autocorrelation
   structure that a parametric test assumes away.
4. **Costs as a gate, not a footnote.** The net-spread gate (`mean net > 0` at
   era-accurate fees and *measured* slippage) has killed more constructs in
   this repo than any statistical test.
5. **The RFA power pre-check.** Free, reads no data, and has produced two
   genuine kills (FLOW 0.6053, RS-MOM 0.337).
6. **Prior-exposure disclosure as a first-class artifact.**

**None of this changes.** Stage A sits in front of it and hands it a better
input. Everything downstream of the promotion memo in §12 is Stage B exactly
as it exists today, with one amendment (§8).

## 2. What Stage B structurally cannot do — and the real reason

The usual framing is efficiency: pre-registering every idea is impractical for
a broad search. True, but weak. The strong argument is about validity.

**Stage B's multiplicity accounting is only valid conditional on the
hypothesis having been generated independently of the data. Today that
condition is asserted, never documented.**

A declared `m = 2` (two cells, w30/w45) and deflated its per-cell α to 0.025
accordingly. But the search that actually produced "opening-drive
continuation on the index" was:

> a deleted pair-research script's *byproduct* observation (intraday ratio
> slopes +1.10/+1.17) → a reassessment memo's option (a) → one construct.

How many phenomena were considered and silently dropped along the way? How
many horizon and window choices were entertained before 30/45 minutes? The
artifacts cannot say, because nothing recorded the search. `m = 2` is
therefore a claim about the world that no artifact in this repo supports.

This is not an accusation of misconduct — the A work is the most disciplined
in the repo. It is a structural gap: **the hypothesis-generation step is the
only step in the pipeline with no governance, no ledger, and no SHA.** Every
downstream α is computed conditional on that ungoverned step.

Stage A's product is therefore not ideas. **Stage A's product is a countable
denominator.** It makes the size of the search an auditable number so that
Stage B's α means what it says.

The repo has already paid for this lesson once, in the opposite direction.
TS Basis Daily was killed not because its numbers were bad (TRAIN net +60.23%,
HOLDOUT +41.44%) but because the search behind them was untracked: filters
chosen on TRAIN, promoted on a HOLDOUT accept/reject check, TP levels set on
both, an ML filter trained across all three. The verdict was "m ≫ 1 and no α
is justified." Stage A is the mechanism that would have made that number
knowable in advance instead of reconstructible in hindsight.

## 3. Why not the two alternatives

**(A) Pre-register everything.** Every question gets its own pre-registration,
RFA, certification and gate sequence. A cost roughly one engineer-week of
governance per hypothesis. At that rate a 6-family scan is a year of work to
answer questions that are, individually, an afternoon of arithmetic. Worse, it
*inverts* the economics: the cheapest thing (measuring a conditional mean) is
wrapped in the most expensive machinery, so the search stays narrow — which is
exactly how a repo ends up testing one hypothesis and calling the quadrant
closed.

**(B) Explore freely, then present the survivor as a clean backtest.** The
standard failure; needs no argument. Note only that it is not primarily a
*dishonesty* failure — it is a *record-keeping* failure. The researcher who
explored 240 cells and pre-registers the best one may believe every word of
the pre-registration. The document is still false, because `m = 1` is false.

**Stage A is the middle layer that makes (A) affordable by making (B)
auditable.** The governing principle:

> **Exploration can discover hypotheses. Exploration cannot certify them.**

## 4. The contamination boundary — fences relabelled, not redrawn

This is the load-bearing design decision, and it is a decision about *data*,
not about labelling discipline. Exploration consumes evidence. A rule that
says "call it exploratory" without partitioning the data changes nothing.

**The partition (operator decision D-A1 in §18):**

| Window | Span | Sessions | Stage A | Stage B |
|---|---|---:|---|---|
| **DISCOVERY** | 2012-01-02 → 2018-12-31 | 1,699 tradeable | **Read freely and repeatedly.** No α computed here ever carries forward. | Reproduction check only (§7) |
| **HOLDOUT** | 2019-01-01 → 2022-12-31 | 988 | **Never touched. Enforced in code.** | First α-bearing gate |
| **SEALED** | 2023-01-01 → spend date | 873 today | **Never touched. Enforced in code.** | One-shot confirmatory gate |

**No data is lost. Only the accounting changes.** DISCOVERY is what Stage B
calls TRAIN. Under Stage A it is reclassified from "an α-bearing gate" to "the
search surface" — spent by design, deliberately and once, in exchange for a
recorded denominator.

Enforcement is mechanical, not cultural: the Stage-A session loader **refuses**
any date ≥ 2019-01-01 and raises. This mirrors
`scripts/signal_engine/ts_basis_daily/run_sealed.py`, which refuses to run. A
researcher cannot accidentally read HOLDOUT; they must edit and commit a guard
removal, which is visible in review.

**Both precedents are already decided in this repo, and they agree:**

- **Carry** burned TRAIN for sign discovery (v1 found IC +0.041 at the wrong
  sign; v2 re-registered the positive sign) and went on to pass HOLDOUT and
  SEALED. Burning the discovery surface is survivable *when the confirmatory
  windows stay clean.*
- **TS Basis Daily** burned TRAIN **and** HOLDOUT as selection surfaces and was
  made unpromotable. Burning a confirmatory window is not survivable.

Stage A is Carry's pattern, generalized and made explicit.

## 5. What Stage A costs — stated up front, not discovered later

Stage A is not free, and a design that claims otherwise should be distrusted.

1. **DISCOVERY stops being evidence.** A promoted construct's Stage-B TRAIN
   result carries approximately zero confirmatory weight (§7). The repo loses
   1,699 sessions of α-bearing surface.
2. **The α budget concentrates on HOLDOUT (n=988) and SEALED (n=873).** This
   has a direct, computable power consequence, and it is the most important
   number in this document (§8).
3. **Every family explored becomes permanent disclosed prior exposure**, even
   the ones that find nothing. A future construct in an explored family
   inherits that record.
4. **Stage A adds a real chance of finding nothing.** A broad scan that returns
   no promotable phenomenon is a *successful* Stage-A run, and it will feel
   like a wasted month. The design must make that outcome cheap enough to
   accept — hence ~5 files, not a framework.

Accepting (1) and (2) is the price of fixing §2. The design's claim is that
this trade is favourable, not that it is costless.

## 6. Gate 0 — three free screens before any data is read

All three read zero market data and run before a family enters a declared map.
This ordering is itself a finding from the A retrospective (§10): A discovered
its cost problem at HOLDOUT, having already spent the full governance sequence.

**0a. Cost-floor arithmetic.** The intended execution vehicle has a measured
round-trip cost. Any family whose plausible gross effect cannot clear it by the
promotion margin (§12, P2) is dead before exploration.

| Vehicle | Measured round-trip | Source |
|---|---:|---|
| Cash equity intraday, EOD-flat | **≥ 8.6 bp/session** (closure rule) | `ISD_PROGRAM_REASSESSMENT.md` §3 |
| Nifty futures, EOD-flat, ₹2Cr notional | **3.76–4.65 bp/trip** by era (current era 4.53 midpoint) | **Measured** by `scripts/stage_a/gate0.py` from the frozen fee module |

> **Corrected 2026-08-29.** This row previously quoted "~3.3–5.3 bp" taken from
> A's narrative. Gate 0 computed it from `futures_fees.py` directly: era means
> are 2.667 (DISCOVERY) / 2.042 (HOLDOUT) / 2.693 (current) bp of fees, plus the
> measured slippage lane and the D5 basis mean. The lane is also **flat in
> notional** (2.91 bp at ₹0.2Cr → 2.67 bp at ₹50Cr), so there is no size lever.
> Full detail and two flagged defects: `STAGE_A_GATE0_REPORT.md`.

**0b. Prior-exposure audit.** What has already read this substrate, for what
target? `A_INDEX_INTRADAY_PRIOR_EXPOSURE_AUDIT.md` is the template and is
mostly reusable — its central finding (index 1m 2012–2025 read *structurally*
by the DayType pipeline; *evaluatively* clean everywhere except the 2023+ pair
research) applies unchanged to Stage A.

**0c. Provisional RFA.** Given the phenomenon's plausible effect band and the
formation count at the **first α-bearing gate**, is 0.80 power reachable at the
**central** corner? If not, the family cannot produce a promotable candidate
however interesting the exploration is — abandon before exploring.

## 7. What Stage B's TRAIN becomes: a reproduction check

If a phenomenon was found on DISCOVERY, re-running it there after freezing
proves nothing — it passes by construction. Pretending otherwise would import
exactly the contamination Stage A exists to prevent.

So for a Stage-A-promoted construct, the Stage-B TRAIN gate is redefined:

> **Reproduction check.** Does the frozen, costed, fully executable rule
> reproduce the exploratory effect within a tolerance declared *in the
> promotion memo, before the Stage-B code is written*?
>
> - **Failing is informative** and terminates the construct. It means the
>   phenomenon did not survive being made executable — the gap between "a
>   conditional mean exists" and "an entry at t+1 open, an exit rule, real fees
>   and measured slippage capture it" is where most exploratory findings die.
>   This is the single most valuable thing the reproduction check does.
> - **Passing is not evidence** and consumes no α. It is a build-correctness
>   check, reported as such.

Concretely: the promotion memo states "exploratory gross effect +X bp at
horizon h; the frozen construct must produce gross ≥ 0.7·X on DISCOVERY." A
shortfall means the executable translation lost the effect, and the reasons
(entry lag, exit rule, session-validity exclusions, sign convention) are
diagnosable *before* HOLDOUT is spent.

**Consequence: the entire α budget lives in HOLDOUT and SEALED.** Which forces
the next section.

## 8. The RFA defect Stage A forces into the open

**Verified in code, not assumed.** `scripts/rfa/gate.py::_evaluate_per_trade_pnl`
computes

```python
max_power = power_at(_per_formation(corner_sharpe), 1.0, decl.n_available, two_sided)
```

— the verdict is taken at `sharpe_hi` (the **optimistic** corner) against a
**single researcher-chosen** `n_available`. A declared `n_available = 873`
(SEALED-today) and received **PROCEED at 0.8720**.

Reproduced from `scripts/rfa/power.py` (script output; matches
`A_PHASE0_PRE_REGISTRATION.md` §3 exactly):

```
gate            n       pessimistic   central   optimistic
TRAIN         1699        0.5904      0.8911      0.9873
HOLDOUT        988        0.4143      0.7083      0.9055
SEALED-today   873        0.3812      0.6616      0.8720   <- the declared verdict
SEALED-floor  1270        0.4899      0.8002      0.9564

n_required:  optimistic 699 · central 1270 · pessimistic 2992
```

**The defect:** the RFA verdict is reported at a corner and an `n` that need
not correspond to the gate that can actually retire the construct. For A the
retiring gate was HOLDOUT, whose **central power is 0.7083** — a ~29%
false-retirement rate against the construct's own declared central effect.
That number appears in A's §3 table but is not what the gate judged.

**Honest caveat, so this memo does not outrun its numbers:** A's HOLDOUT
produced a *negative point estimate* (−0.22 bp net; gross +3.13 against ~3.41
bp cost). Its retirement does not rest on power at all and was correct. The
defect is **prospective** — it will bite the next construct that fails a
low-power first gate by a thin margin — not a claim that A was mis-killed.

**Required amendment (a deliverable, not a footnote).** For any
Stage-A-promoted construct:

- `n_available` MUST be the formation count at the **first α-bearing gate**
  (HOLDOUT under this design), not at the last gate.
- The promotion decision (§12, P7) is taken at the **central** corner. PROCEED
  at the optimistic corner remains the gate's published floor semantics —
  unchanged, so no frozen declaration is invalidated — but Stage-A promotion
  adds a **stricter** requirement on top.
- If central power at the first α-bearing gate is < 0.80, the construct is not
  promotable: either the window must grow, or the phenomenon must be stronger.

Under this rule A would not have been promotable as specified (HOLDOUT central
0.7083). That is the amendment doing its job: it says "this gate cannot settle
this question," which is a different and more useful statement than "this
construct failed."

## 9. How Stage A avoids becoming a data-mining machine

Six mechanisms. The first is the one that matters; the rest are support.

### M1 — SHA the search map, not the hypothesis (the core mechanism)

You cannot pre-register the hypothesis. You **can** pre-register the search.

Before the first run, a `STAGE_A_MAP_<slug>.md` + `.json` pair is written and
committed, declaring the complete cell space: families × event definitions ×
horizons × conditioning states, plus the per-cell minimum-n floor, the null
construction, the α, and the promotion thresholds. It is SHA-256 sealed exactly
as `A_PHASE0_PRE_REGISTRATION.md` is.

The auditable quantity becomes **declared / executed / reported**:

- declared 240, executed 240, reported 1 → honest, and the multiplicity
  correction has a real denominator.
- declared 6, executed 240 → the fraud mode.

A JSONL ledger alone *cannot* detect the fraud mode, because rows are appended
after the fact and an unwritten row is invisible. The map must exist and be
SHA'd **before** execution, and every ledger row carries the map SHA. The
report generator refuses to emit if `executed ⊄ declared`.

Adding a cell after seeing results is permitted exactly once per family and
only by writing a **new map with a new SHA**, which resets the denominator to
declared ∪ new and is visible in git history. There is no silent path.

### M2 — Max-statistic family-wise null, not BH

On a single index series every cell is measured on the same ~1,700 sessions, so
cells are heavily dependent. BH over 240 dependent cells is simultaneously too
conservative (ignores the dependence) and too lenient (says nothing about cells
the researcher considered).

The correct device is a **max-statistic empirical null** (Westfall–Young /
White's Reality Check) over the declared map: per iteration, circular-shift the
event/signal series against forward returns in month blocks, recompute the
statistic for **every declared cell**, and retain the maximum. A cell clears
only if its observed statistic beats the (1−α) quantile of that max
distribution.

This is the honest answer to "I scanned 240 cells," and it prices dependence
correctly. `scripts/isd/battery_stats.py` already implements the month-block
circular-shift machinery — reuse it, do not rewrite it.

### M3 — Effect-size floor tied to the cost wall, evaluated before statistics

This repo's binding constraint has been economic three times running. A
phenomenon that is statistically real but below the cost floor is not
promotable at any p-value. **P2 in §12: gross effect ≥ 2× the measured
round-trip cost for the intended vehicle.** For Nifty futures EOD-flat that is
**≥ ~6.6 bp** against the ~3.3 bp lane.

This filter is free, requires no null, and kills most of the mining space
before any statistics are computed. It is also the filter that would have
flagged A (§10).

### M4 — Mechanism registers its predicted signature *before* the run

"Monotonic horizon decay" is findable in noise if you go looking for it after
the scan. So the mechanism statement in the declared map must commit, in
advance, to:

- the **predicted decay shape** across the declared horizons, and
- at least one **conditional prediction** testable on a window Stage A never
  touches — e.g. "if this is dealer hedging flow, it is stronger on expiry
  days"; "if this is auction information release, it is stronger after large
  overnight gaps."

The conditional prediction is carried into the Stage-B pre-registration as a
**second pre-committed HOLDOUT test**. It is the cheapest genuine protection
against a story fitted to a curve, because a fitted story has no reason to make
a correct conditional prediction out-of-sample.

### M5 — No selection at a grid corner

The F1 lesson, verbatim: TRAIN grid search picked `n=5` (window minimum) with
`k_sl=2.5`/`k_tp=5.0` (both maxima). A boundary argmax does not mean "the
optimum lies outside the grid"; it usually means the objective is **flat** in
that dimension and the argmax is noise. Any cell selected at a declared-grid
boundary is **non-promotable** and is reported as a flat-objective diagnostic.

### M6 — Coarse grids and broad families, by construction

Horizons are declared on a coarse geometric ladder (5/15/30/60/120 min, EOD),
not a swept range. Thresholds are declared as distributional quantiles (e.g.
top/bottom tercile of the conditioning variable) rather than tuned levels. The
lab makes it awkward to express a finely-swept parameter and easy to express a
family — the correct incentive gradient for discovery.

## 10. Reinterpreting the A work in this framework

**A was a legitimate and well-executed Stage-B experiment.** The freeze held,
the gates fired as written, the negative result was accepted without re-tuning,
and the sealed window was preserved. Nothing about A's *execution* needs
defending.

**A was not a Stage-A research programme, and was never presented as one.** The
correct reading of its closure is:

> One hypothesis — opening-period return → same-session continuation, at two
> window lengths, on one instrument, at one entry and one exit — was tested and
> failed out-of-sample.

Not: "index intraday does not work." The prior-exposure audit makes the
distinction sharp and is worth quoting for the successor: the index 1m store
had been read *structurally* (DayType regime features) and the *pair* had been
tested for mean reversion, but **no broad index single-name trading-rule
evaluation across the space of intraday phenomena has ever been run in this
repo.** A tested one point in that space.

**What Stage A would have changed — stated precisely, not generously.** The
cost-viability screen (M3) applied to A's own numbers:

| Quantity | TRAIN (2012–2018) | HOLDOUT (2019–2022) |
|---|---:|---:|
| Gross sign-applied mean (w45) | +4.41 bp | +3.13 bp |
| Round-trip cost (fees + slippage) | ~3.26 bp | ~3.41 bp |
| **gross / cost** | **1.35** | **0.92** |
| Mean net | +1.27 bp | −0.22 bp |

A `gross ≥ 2× cost` floor requires ≥ ~6.5 bp; A measured 4.41. **Stage A would
have flagged A as sub-threshold on cost viability**, and the finding would have
been recorded as an exploratory observation ("opening-drive continuation is
present at ~4.4 bp gross, below the promotion floor for this vehicle") rather
than promoted.

Two honest qualifications:

1. This is **not free** — it costs one DISCOVERY read to measure the 4.41. The
   saving is the *governance* sequence (certification, pre-registration, RFA
   ratification, two frozen gate runs, closure record), not the data.
2. "Flagged" is not "killed." An operator could rationally have promoted a
   1.35× construct anyway, with the thin margin disclosed. The value of the
   screen is that the margin would have been **stated before the investment**,
   as a decision, rather than discovered at HOLDOUT as a result.

**And the counterfactual runs the other way too:** A's TRAIN gross of +4.41 bp
is real information about the index intraday space that a Stage-A scan would
have produced in an afternoon, alongside 200-odd other cells — which is
precisely the comparison this whole design rests on.

---

# PART II — ARCHITECTURE

## 11. Module map — five files, not fifteen interfaces

The brief's 15 requirements are **methodology sections, not modules.** A
15-interface framework is the failure mode of this deliverable; CLAUDE.md's
"no over-engineering" applies with full force to a research lab whose most
likely outcome is "nothing promotable."

```
scripts/stage_a/
  session.py     # data interface + session/event model + fence enforcement
  features.py    # causal feature & event registry (the contract)
  study.py       # forward-return matrix, event study, strategy experiment, costs
  stats.py       # thin wrapper over scripts/isd/battery_stats.py + max-stat null
  run_map.py     # executes a declared map -> ledger + report
```

Reused, not rebuilt: `scripts/isd/battery_stats.py` (NW/AC1/circular-shift
nulls), `scripts/isd/read_1m.py` (schema-drift normalization pattern),
`core/execution/futures/futures_fees.py` (era-accurate fees, 13 tests green),
`scripts/rfa/power.py` (provisional RFA), `core/market/session_schedule.py`
(session windows — never a bare constant).

### 11.1 Data interface — `session.py`

```python
DISCOVERY_LO, DISCOVERY_HI = date(2012, 1, 2), date(2018, 12, 31)

def load_session(d: date, symbols=(NIFTY, BANKNIFTY)) -> Session | None:
    """Raises FenceViolation if d > DISCOVERY_HI. Returns None if the session
    fails the certified validity rules."""
```

- **Fence enforcement is the first statement in the function.** Reading HOLDOUT
  or SEALED from Stage A requires a committed code edit.
- **Certified exclusions are applied once, here, never per-experiment** —
  reusing A's certification register **whole, for provenance** (so the two
  stages exclude identically and any divergence is a bug): first bar
  date-stamped with the session; permanent holes (2018-05, 22 sessions — the
  only one inside DISCOVERY; 2023-02, 20 sessions); 12 out-of-shape
  Diwali/special sessions; 66 partials.
- **Era label** (`vendor` / `native` / `cas`) attached per session. DISCOVERY is
  entirely `vendor`, which is a simplification *and* a disclosed risk: any
  phenomenon discovered on DISCOVERY is discovered in a single microstructure
  era, and the vendor era has no 09:15 auction bar (opening print = first bar
  open, median 3.2 bp / p99 25 bp from the official open). Every promotion memo
  must state this.

`Session` exposes aligned numpy arrays (`open/high/low/close`, `minute_of_day`,
bar index) per symbol, plus prior-session context (`prev_close`, overnight gap)
and `n_bars`. No pandas in the hot path; one session is ~375 rows and a scan is
1,699 sessions × 240 cells.

### 11.2 Causal feature interface — `features.py`

```python
Feature   = Callable[[Session], np.ndarray]   # len == n_bars; f[t] uses bars 0..t only
Condition = Callable[[Session], np.ndarray]   # bool mask, same contract
```

The causality contract is enforced by an automatic test, not by review (§15,
T1): compute `f` on the full session, then on the session truncated at bar `t`,
and assert `f_full[t] == f_trunc[t]` for a random sample of `t`. Any feature
that peeks fails immediately. **This is the single most valuable test in the
lab** — it makes look-ahead a build error rather than a review finding.

### 11.3 Session/event model

An **event** is `(session_date, bar_index t, covariates)` emitted where a
Condition is true. Deliberately general: it does not assume one trade per day,
a fixed entry time, a direction, or a fixed window. Those were properties of A,
not properties of "intraday."

### 11.4 Event-study interface — `study.py`

One forward-return matrix per session, computed once and shared by all cells —
this is what makes a 240-cell scan cheap:

```
R[t, h] = (close[t + h] - open[t + 1]) / open[t + 1]   # bp, gross, sign-free
```

Entry is always `open[t+1]`, never `close[t]`. Horizons are the declared coarse
ladder plus "to EOD" (the 15:14 bar close — the last continuous print in all
three eras, per A's D6).

`event_study(events, horizons)` returns per horizon: n, mean, median, SD,
hit-rate, NW t, and the decay profile across horizons. **Sign-free unless the
map declares a direction** — the lab reports a conditional distribution, and
"which way does it go" is a mechanism claim that must be declared, not read off
the output.

**Overlap is handled explicitly, not ignored.** Events at t and t+1 with h=60
share 98% of their return path. The lab reports effective sample size alongside
n, uses `NW lag ≥ h`, and relies on the block-shift null (which preserves the
overlap structure) for inference. A cell whose n is large only because of
overlap is flagged.

### 11.5 Strategy-experiment interface

The same events, plus an exit rule and the cost model, producing net per-trade
returns. Costs come from the frozen modules — `futures_fees.py` at the
canonical ₹2Cr notional, plus the *measured* slippage lanes (0.66–0.78 bp/side
by era and window, `A_COST_SUBSTRATE_MEASUREMENTS.md`) and the D5 basis mean
(~0.4 bp), with basis dispersion (19.2 bp p90) disclosed rather than costed.

**Strategy experiments are gated behind the event study.** The map must show
the phenomenon exists before an executable variant of it may be run. This is
the brief's §6 separation, enforced by the runner: a strategy cell whose parent
event-study cell did not clear M3's effect floor is refused.

### 11.6 Statistics — `stats.py`

Wraps `battery_stats.py` for NW t, AC1 and the circular-shift null; adds the
max-statistic family-wise null over the declared map (§9 M2). Everything is
seeded (SEED=42) and deterministic: same map + same code SHA → byte-identical
output.

### 11.7 Ledger and report — `run_map.py`

`data/stage_a/<slug>/ledger.jsonl`, append-only, one row per executed cell,
each carrying: `map_sha`, `code_git_sha`, `cell_id`, `family`, `params`,
`executed_at`, `n_events`, `n_effective`, gross effect by horizon, cost lane,
net, NW t, AC1, per-cell empirical p, max-stat p, and `verdict ∈ {exploratory,
flagged_corner, below_cost_floor, promotable_candidate}`. This satisfies the
brief's §7 ledger requirements; researcher/model identity comes from the git
commit author, not a self-reported field.

The report generator enforces the contamination language:

- every table stamped **"EXPLORATORY — NOT EVIDENCE"**;
- refuses to emit a p-value without the accompanying declared/executed counts
  and the max-stat p;
- refuses to emit if `executed ⊄ declared`;
- the words *validated*, *alpha*, *edge*, and *out-of-sample* are rejected by a
  lint check on Stage-A artifacts.

## 12. Candidate promotion — the gate out of Stage A

A phenomenon is promotable only if **all** hold. Any failure → it stays an
exploratory observation, recorded, and the family's exposure is disclosed.

| # | Criterion |
|---|---|
| **P1** | **Mechanism.** A written economic story, plus its registered predicted signature (decay shape + ≥1 conditional prediction) — declared in the map *before* the run (M4). |
| **P2** | **Effect floor.** Gross effect ≥ **2× measured round-trip cost** for the intended vehicle (M3), **computed per era from the fee schedule at the map's declared vehicle — not a fixed constant.** For Nifty futures EOD-flat the measured lane runs 3.76–4.65 bp/trip (§6), so the floor runs **~7.5 bp (HOLDOUT era) to ~9.07 bp (current era)**. **DISCOVERY is entirely vendor era, so the floor Stage A actually applies is the low end — and a phenomenon clearing 6.6 bp on vendor-era costs may not clear the native/CAS-era cost it faces at HOLDOUT and SEALED.** The promotion memo must therefore report the effect against **both** the DISCOVERY-era floor and the current-era floor, and a candidate that clears only the former is disclosed as era-fragile. This is exactly how A died: a ~1.3 bp gross decay plus a ~0.2 bp fee rise flipped the net. |
| **P3** | **Family-wise significance.** Clears the max-statistic null over the **whole declared map** at α = 0.05 (M2). |
| **P4** | **Robustness.** Same sign in ≥2 non-overlapping DISCOVERY sub-periods, and across the horizon neighbourhood — a decay profile, not a single-horizon spike. |
| **P5** | **Not a corner.** Not selected at a declared-grid boundary (M5). |
| **P6** | **Sample floor.** n ≥ the map's declared per-cell minimum, with effective-n reported after overlap adjustment. |
| **P7** | **Provisional RFA at the central corner, at the first α-bearing gate** (§8). Power ≥ 0.80 at HOLDOUT n with the central declared effect. **The band must be defended from mechanism and external anchors, NOT fitted to the DISCOVERY measurement** — see the circularity rule below. |

**P7 circularity rule (load-bearing).** The effect measured on DISCOVERY may
**not** be used as the central point of the RFA band. If it were, the band
would be fitted to the discovery read and §8's amendment would be undermined at
the exact point of use — which is the C2 defect the repo has already recorded:
*"the gate's verdict is only as good as the declared SD, which is why SD must be
independently defended rather than inherited from a short in-sample read."*

So: the promotion memo declares the band from mechanism, literature and
out-of-family anchors, and **discloses the DISCOVERY measurement as prior
exposure alongside it**, explicitly not as the point estimate. Where the
independently-defended band is weaker than the measured effect — the normal
case, and the correct default given selection inflation — the weaker band
governs P7. If no honestly independent band clears 0.80 at n=988, the
phenomenon is **not promotable**, regardless of how large the DISCOVERY effect
was. CB-N50's hand-off records the same discipline from the other direction:
the honest effect size was the shrunk HOLDOUT +0.029, not the selection-inflated
TRAIN +0.059.

Passing all seven produces a **Promotion Memo** (`STAGE_A_PROMOTION_<slug>.md`)
containing: the phenomenon; the mechanism and its registered conditional
prediction; the exploratory magnitudes and the **reproduction tolerance** for
Stage-B TRAIN (§7); the full declared/executed/reported counts and map SHA; the
provisional RFA arithmetic; and the complete prior-exposure record.

**The promotion memo is an input to a Stage-B pre-registration, never a
substitute for one.** Its numbers are exploratory and are quoted in Stage B
only as prior-exposure disclosure and as the reproduction target.

## 13. Handoff into Stage B

```
STAGE A                                    STAGE B
Gate 0 (cost / exposure / provisional RFA)
  -> declared map (SHA'd, committed)
  -> execute ALL declared cells on DISCOVERY
  -> ledger + exploratory report
  -> promotion memo (P1-P7)  ------------>  PRE-REGISTRATION (frozen, SHA'd)
                                             - prior exposure = the Stage-A
                                               record + map SHA + counts
                                             - m argued from the map, not
                                               from the surviving cell count
                                           -> RFA DECLARATION
                                             - n_available = HOLDOUT n
                                             - judged at the central corner
                                           -> SUBSTRATE CERTIFICATION
                                           -> TRAIN = reproduction check (no alpha)
                                           -> HOLDOUT = first alpha-bearing gate
                                              (+ the M4 conditional prediction
                                               as a second pre-committed test)
                                           -> SEALED (one-shot, unchanged)
                                           -> PAPER -> LIVE
```

The interaction is one-way and one-shot. **Stage B never returns to Stage A.** A
Stage-B failure does not license re-exploring the same family for a variant that
would have passed — that is the C2-reopen temptation the repo already declined
once, in a different costume. A new Stage-A map, with a new SHA and a new
denominator, is the only path, and its report must disclose the failed Stage-B
construct as prior exposure.

## 14. Substrate constraints — verified, and two of them bite

Measured against the live store during this design (`NSE_INDEX|Nifty 50`,
`NSE_INDEX|Nifty Bank`, per-date 1m DuckDB files):

| Finding | Consequence |
|---|---|
| **Index volume is 0 in every era** — verified on 2015-06-10, 2019-06-10, 2024-06-10, 2026-08-20; both indices, 375 bars each, `max(volume) = 0` throughout | **Two of the brief's example questions are not answerable on this substrate.** "Does price relative to VWAP have predictive information?" and "Does volume/intensity contain information?" have **no index-level data**. VWAP is undefined; TWAP is the only available analogue (which is what the DayType pipeline uses). A volume/participation family requires either constituent-level 1m aggregation (the CB-N50 pattern — expensive, and a different construct) or 1m index-futures data, **which does not exist in this repo at any date**. Recorded now rather than discovered mid-scan. |
| **BankNifty 1m is complete across DISCOVERY** — 1,705 of 1,705 files 2012–2018 carry both indices | The Nifty↔BankNifty lead-lag and divergence family **is** explorable, on a window the pair research never touched (it read 2023-01 → 2026-05 only). DISCOVERY is evaluatively clean for the pair. |
| DISCOVERY = 1,705 Nifty-bearing files; **1,699 tradeable** after A's session-validity rules | The per-cell n floor must be set against this, not against the file count. **Caveat on the 1,699:** A's §3 table labels it "cell 1" (w30) while `A_HOLDOUT_CLOSURE.md` cites it for w45, and the trial ledger records no per-cell n — so the two cells' counts are not separately evidenced. The count depends on the entry-bar validity rule, so **each map re-measures n per cell** rather than inheriting this figure. |
| DISCOVERY is entirely the **vendor** era (no 09:15 auction bar; opening print = first bar open) | Single-microstructure-era discovery. A mandatory disclosure in every promotion memo, and a real generalization risk to HOLDOUT (native era) and SEALED (native + CAS). |

## 15. Tests

| # | Test | Why it matters |
|---|---|---|
| **T1** | **Look-ahead detector** — truncation invariance for every registered feature (§11.2) | Makes look-ahead a build error. The highest-value test in the lab. |
| **T2** | **Fence refusal** — `load_session` raises on any date ≥ 2019-01-01 | The contamination boundary is code, not culture. |
| **T3** | **Max-stat null calibration** — on synthetic pure-noise data with 240 declared cells, the max-stat procedure rejects at ~5% while naive per-cell α=0.05 rejects far more | The test that *proves* the anti-mining machinery works rather than asserting it. |
| **T4** | **Forward-return matrix identity** vs a naive per-event loop | The vectorized fast path must equal the obvious slow one. |
| **T5** | **Ledger reconciliation** — `executed ⊄ declared` ⇒ report FAILs | The M1 fraud-mode detector. |
| **T6** | **Cost parity** — the lab's cost lane reproduces `futures_fees.py` and the A measured slippage bands exactly | No parallel cost model may drift from the frozen one. |
| **T7** | **Determinism** — same map + seed ⇒ byte-identical ledger and report | CLAUDE.md's stronger-than-coverage guarantee. |

## 16. Example exploratory families (illustrative slate, not a commitment)

Each needs a mechanism sketch and a Gate-0 pass before entering a map. Sized so
a first map is ~150–250 cells, not thousands.

| Family | Question | Mechanism sketch | Gate-0 note |
|---|---|---|---|
| **F-OPEN** | Does the opening move continue or reverse, and at which horizons? | Overnight information concentrates into the opening print; incomplete impounding ⇒ continuation, overshoot ⇒ reversal | **Prior-exposed by A** at the 30/45-min window, EOD horizon: +4.41 bp gross TRAIN. A scan generalizes horizon and window; A's cells are disclosed, not re-discovered |
| **F-GAP** | Does behaviour differ after large overnight moves? Gap × intraday interaction | Overnight risk-premium release vs. overreaction | ISD F4 (equity gap **fade** — strongest effect the repo has measured, cost-killed) is the disclosed cousin at a different level |
| **F-VOL** | Does volatility expansion/contraction predict subsequent movement or direction? | Vol clustering is the best-established intraday regularity; the tradable question is whether it maps to *direction* or only to *magnitude* | Magnitude-only findings are unpromotable for a directional vehicle — declare this before running |
| **F-RANGE** | Range extremes, breakouts, and **failed** breakouts | Liquidity provision around stop clusters | The failed-breakout cell is the interesting one and needs a careful causal definition (failure is only known after the fact) |
| **F-TOD** | Time-of-day conditional returns and session shape | Auction-to-auction liquidity cycle; lunch-hour thinness | Cheap; a natural conditioning axis for every other family rather than a family on its own |
| **F-REL** | Nifty↔BankNifty lead-lag; does divergence predict convergence or continuation? | Bank-sector information leads index-level repricing | **Explorable on clean DISCOVERY** (§14). The pair *mean-reversion* hypothesis is falsified on 2023+; the intraday **trending** slopes (+1.10/+1.17) are the direction-favourable prior |

Deliberately **excluded** at Gate 0: any VWAP or volume/intensity family (§14 —
no data), and any cash-equity intraday EOD-flat family (closed by arithmetic at
≥8.6 bp/session).

## 17. Worked example — one discovery becomes a frozen Stage-B construct

Illustrative, with invented numbers, to show the seams:

1. **Gate 0.** F-REL. Vehicle Nifty futures, cost lane ~3.3 bp/trip ⇒ promotion
   floor ~6.6 bp. Prior exposure: pair research (2023+, mean reversion
   falsified, trending slopes measured); DayType structural. Provisional RFA at
   HOLDOUT n=988, central corner ⇒ needs a per-trade Sharpe implying ≥ ~7 bp
   mean net. Proceed.
2. **Declared map** `STAGE_A_MAP_FREL.md`, SHA'd and committed: 6 divergence
   definitions × 6 horizons × 3 conditioning states (vol tercile) = 108 cells; n
   floor 200/cell; α 0.05 on the max-stat null; mechanism = *bank-sector
   information leads index repricing*; predicted signature = *monotonic decay
   from 15→120 min*; conditional prediction = *stronger on high-vol days*.
3. **Execute** all 108 on DISCOVERY. One cell — 30-min divergence, mid-vol
   state, 60-min horizon — shows +8.1 bp gross, max-stat p 0.02, same sign in
   2012–2015 and 2016–2018, monotonic decay across 30/60/120, interior to the
   grid, n=430.
4. **P1–P7.** P2: 8.1 ≥ 6.6 (vendor-era floor) ✓, but 8.1 < 10.6 (post-2024
   floor) ⇒ **flagged era-fragile** and disclosed. P3 ✓. P4 ✓. P5 ✓. P6 ✓.
   P1 ✓ (declared). P7 — **note the circularity rule**: the band is *not* set
   from the +8.1 bp. It is defended independently (mechanism scale, the
   published lead-lag literature, the ~4.4 bp A read as an out-of-family
   anchor), which yields a central materially below 8.1; the +8.1 is disclosed
   as prior exposure. If that independent central does not clear 0.80 at n=988,
   the phenomenon is **not promotable**, and the memo says the *gate*, not the
   phenomenon, is insufficient — a materially different conclusion from "it
   failed."
5. **Promotion memo:** phenomenon, mechanism, conditional prediction,
   exploratory +8.1 bp, **reproduction tolerance ≥ 5.7 bp (0.7×)**, declared 108
   / executed 108 / reported 1, map SHA, prior-exposure record.
6. **Stage B** proceeds unchanged from the pre-registration onward, with: `m`
   argued from the map (108, and the max-stat null already priced it);
   `n_available` = 988 (HOLDOUT); TRAIN = reproduction check against 5.7 bp, no
   α; HOLDOUT = first α-bearing gate **plus** the pre-committed high-vol
   conditional test; SEALED one-shot; PAPER; LIVE.

## 18. Open decisions for the operator

| # | Decision | Recommendation |
|---|---|---|
| **D-A1** | Is DISCOVERY = TRAIN (2012–2018), permanently reclassified as the search surface? | **Yes.** It is the only partition that preserves the α-bearing budget (HOLDOUT clean; SEALED exposed only per-hypothesis — see §19), and both in-repo precedents (Carry survived, TS Basis Daily did not) point the same way. |
| **D-A2** | Adopt the RFA amendment (§8): `n_available` at the first α-bearing gate, promotion judged at the **central** corner? | **Yes**, as a Stage-A promotion requirement layered on top of the gate. No frozen declaration is invalidated and `gate.py` semantics are unchanged. |
| **D-A3** | Accept that Stage-B TRAIN becomes a no-α reproduction check for promoted constructs? | **Yes** — entailed by D-A1. The alternative is pretending DISCOVERY is still evidence. |
| **D-A4** | Single-era discovery risk: DISCOVERY is entirely the vendor era. Accept with disclosure, or require native-era replication before promotion? | **Accept with mandatory disclosure.** Requiring native-era replication would consume HOLDOUT, which defeats the design. |
| **D-A5** | Build now, or first run Gate 0 on the six candidate families? | **RESOLVED 2026-08-29 — Gate 0 was run** (`STAGE_A_GATE0_REPORT.md`). Outcome: do **not** build the six-family lab. F-OPEN is answered by A; F-VOL, F-TOD and all dense F-REL expressions are cost-dead; only **F-GAP and F-RANGE (failed breakout)** are both unmeasured and not cost-dead. See D-A6/D-A7/D-A8 below. |
| **D-A6** | Pool HOLDOUT+SEALED into **one** one-shot confirmatory gate instead of two sequential gates? | **Operator call — Gate 0 prices it, does not pick.** For: required net S_ann drops **1.219 → 0.888**, below A's ratified central corner (1.075), so a central case becomes settleable. Against: it merges the cheaper evidence stage into the terminal one, leaving **no α-bearing gate before the last** — A's era-decay would then have surfaced only after both windows were spent — and the pooled read spans three microstructure eras and two STT changes. Supersedes §4 and §13 only if taken. |
| **D-A7** | Scope the first declared map to F-GAP + F-RANGE only? | **Yes.** A two-family map, not a 250-cell scan. |
| **D-A8** | Spend one DISCOVERY read to reconcile A's TRAIN gross decomposition? | **Yes, cheap.** `A_HOLDOUT_CLOSURE.md`'s gross/fees/net figures do not reconcile with the frozen fee module (see `STAGE_A_GATE0_REPORT.md` §5.1); the reconciliation calibrates every plausibility multiple. |

## 19. Assessment of the proposed two-stage architecture

The architecture in the brief is correct and should be adopted, with three
amendments, all argued above:

1. **Gate 0 belongs at the top**, before Stage A — three free screens (cost
   floor, prior exposure, provisional RFA). A's history is the argument: the
   cost problem was discovered at HOLDOUT, after the full governance spend.
2. **The contamination boundary must be a data partition enforced in code**, not
   a labelling convention. Stage A reads DISCOVERY; the loader refuses
   everything else.
3. **Stage B's TRAIN gate must be redefined and the RFA amended**, or the design
   ships a construct into a gate whose power was never honestly declared.

**One correction to the post-Stage-A budget, so it is not overstated later.**
Stage A leaves **one clean α-bearing window (HOLDOUT, 988) plus one whose
exposure is hypothesis-specific (SEALED, 873).** SEALED is not virgin: the pair
research read 844 sessions of it across 27 ratio mean-reversion combos and
measured the direction-favourable trending slopes. For the ratio-mean-reversion
hypothesis SEALED is spent; for an unrelated hypothesis it is evaluatively
clean; for a *related* one — F-REL above is exactly this case — the exposure is
partial and must be disclosed per family in the promotion memo. Any citation of
this design that claims "two clean windows" is misreading it.

The added complexity is real and is the price of making the search countable.
The alternative is not a simpler system — it is the same system with the
multiplicity denominator left blank.

---

## 20. Record

- No code written. No data read except the substrate census in §14 (file counts
  and `max(volume)` on four dates — no returns, no rules, no P&L).
- Power figures in §8 reproduced from `scripts/rfa/power.py` and match
  `A_PHASE0_PRE_REGISTRATION.md` §3 exactly.
- `gate.py` corner behaviour read from source, not inferred.
- Cost figures quoted from `A_COST_SUBSTRATE_MEASUREMENTS.md`,
  `A_HOLDOUT_CLOSURE.md` and `ISD_PROGRAM_REASSESSMENT.md` §3.
