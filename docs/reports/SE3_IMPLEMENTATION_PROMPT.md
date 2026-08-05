# SE-3 — Confirmatory Implementation Prompt

**For:** DeepSeek V4 (implementer)
**Author:** Claude (prompt + review only, per standing role split)
**Date:** 2026-08-05
**Authority:** `docs/reports/SE3_PRE_REGISTRATION.md`, SHA-256 `__________` *(unfilled — see §0.1)*
**Declaration:** `governance/rfa/declarations/se3.py`, SHA-256 `fd91b1d5…` — RFA PROCEED
**Context to read first, in this order:** `SE3_PRE_REGISTRATION.md` (the spec this prompt executes);
`SE3_BREADTH_PROBE_PROMPT.md` §3 (the *a priori* parameter pin, cited as A1–A14);
`SE3_BREADTH_PROBE_REPORT.md` §5 (the sd this construct must remain comparable to);
`CLAUDE.md` → RFA and Signal Engine sections (why one-shot windows are treated the way they are).

---

## 0. Status — this prompt is INERT

### 0.1 It cannot be executed yet

`SE3_PRE_REGISTRATION.md` line 3 reads **"DRAFT — awaiting operator approval. Not frozen."** Its §9
lists open items. **Nothing in this prompt may be run against the confirmatory window until all of
the following are true**, and the check is the implementer's responsibility, not the author's:

| # | Precondition | State |
|---|---|---|
| 0.1a | `SE3_PRE_REGISTRATION.md` status line reads FROZEN, and its SHA-256 is recorded in this document's header **and** in `CLAUDE.md` | **OPEN** |
| 0.1b | Pre-reg §9.1 decided — is the P&L diagnostic (D1) run at all? | **OPEN** |
| 0.1c | Pre-reg §9.2 decided — does forward spread collection start? (Independent of this run; does not block it) | **OPEN** |
| 0.1d | Pre-reg §9.3 acknowledged — S3 shortfall is a **stop-and-re-approve**, not a proceed-and-note | **OPEN** |
| 0.1e | **New item, escalated by this prompt:** `S3_MIN_USABLE_DATES` pinned to an integer by the operator (§3.4) | **OPEN** |

If any row is OPEN, **stop and report it.** Do not run Phase 1 "just to see the counts" — Phase 1
counts are structural facts about the confirmatory window and reading them early is a read.

This is not procedural fussiness. TS Basis's sealed window was opened on a gate that had not
actually held, and the read is de-authorized as a result — not because the signal was bad, but
because the authority was defective at the moment of the read. Do not create a second instance.

### 0.2 What this task is

Build and run the **one-shot confirmatory read** of SE-3 variant A on
**2016-02-11 → 2022-12-31**, per the frozen pre-registration. Two phases, hard-gated:
Phase 1 certifies the substrate with **no return, IC, or P&L computed**; Phase 2 takes the single
confirmatory read and freezes it.

### 0.3 What this task is not

- **Not a search.** Every parameter is pinned in the pre-registration (A1–A14 inherited, B1–B8 new).
  You implement them; you do not choose among them.
- **Not variant B, and not an A/B comparison** (pre-reg §1.2). See §1.3 below — B must be *absent
  from the code*, not disabled by a flag.
- **Not a build.** A PASS authorizes nothing (pre-reg §7).
- **Not re-runnable.** Phase 2 executes exactly once. See §1.6.

---

## 1. HARD CONSTRAINTS — violating any of these invalidates the work

### 1.1 Window fence — INVERTED from the probe, and two-sided

The probe's fence was `2023-01-02 → 2025-12-31`. **This run's fence is the complement:**

```
2016-02-11 <= trade_date <= 2022-12-31        (inclusive, both ends)
```

Implement as an assertion that **hard-fails** on any row outside it, applied per source, and print
observed min/max `trade_date` per source in both reports as proof.

**Out of bounds now, in both directions:**

- `2023-01-02 → 2025-12-31` — the burned probe surface. **Do not read it**, not for calibration, not
  for a comparison plot, not to "check the code works on the window we already have." Any use of it
  to inform a choice inside this run is rule-discovery leaking into the confirmatory read.
- `2026-01-01 → 2026-07` — the deliberately reserved forward tail (pre-reg §2.1). It is the only
  forward check that will ever exist for this construct. Leave it.

**`expiry_dt` is not fenced** — only `trade_date` is. A contract selected on 2022-12-28 with a
January-2023 expiry is legitimate; its `settle` is only ever read on in-fence trade dates. Do not
write an assertion that rejects it.

### 1.2 Warmup comes from inside the fence, and it is RV-driven

Variant A's binding warmup is **A10: 21 trailing trading days of front-month FUTSTK returns, ≥18
observations.** That is the only trailing window in the construct.

**Do not inherit the probe's first-usable-date logic.** The probe's first usable date (2023-03-28)
was set by variant B's 60-trading-day β window. B does not exist here. If you copy that logic you
silently discard ~40 formation dates, the usable-date count fails to reconcile against 1,701, and
you trip the §3.4 stop for a reason that is an artifact of your own code.

Compute the first usable formation date, do not hardcode it, and report it with the arithmetic that
produced it. NSE F&O history does not predate 2016-02-11, so no warmup source outside the fence
exists — but the assertion must still be present.

### 1.3 Variant B must be ABSENT from the code

Not flagged off, not `if VARIANT == "A"`, not dead-but-present. **Absent.**

`scripts/se3/run_confirmatory.py` and its Phase-1 sibling must contain:

- no reference to `data/market_data/options_bhavcopy.duckdb`,
- no `richB`, no `BETA_WINDOW`, no trailing-β regression of name IV on index IV,
- no import that transitively opens the index-options database.

A `tests/se3/` test asserts this mechanically over the module source. The reason is pre-reg §1.2:
the δ band is anchored on Cao & Han's `VOL_deviation`, which is variant A's construction. B has no
anchor, and computing it is an undeclared second test.

**Consequence for the ledger, and state it plainly in both reports:** variant A reads *only* stock
options, stock futures, and MCWB membership. **The NIFTY index-option leg 2016-02-11 → 2022-12-31 is
not read by this run and remains unread afterward.** That is a fact to record, not a credit to
spend — it does not license a second construct on the index leg.

### 1.4 No tuning, and "stop and report" is a success outcome

Every filter, band, window and functional form is pinned by pre-reg §3.A/§3.B. If a pinned choice
produces something broken — inversion fails on most cells, too few names survive, expiry selection
empties a month — **stop and report it.** Do not substitute a choice of your own and continue.

Pre-reg §3.B closes with: *"If implementation reveals a genuinely unspecified case, it is reported
and the run stops — it is not resolved by the implementer's judgement."* That is binding. §3 below
resolves the three cases where the pre-reg's wording is genuinely ambiguous; anything **not** listed
there and not pinned in the pre-reg is a stop.

**One scoped exception, for D1 only** (§5): the cost diagnostic cannot falsify anything (pre-reg
§4), so an undated statutory-charge component is reported as a labelled assumption in the ladder
table rather than halting the run. This exception applies to **D1 alone** and to nothing feeding
G1, G2, D2 or D3.

### 1.5 Read-only

No writes anywhere under `data/`. Outputs go to `docs/reports/` only.

### 1.6 Phase 2 runs exactly once

`run_confirmatory.py` must **refuse to run** if `docs/reports/SE3_CONFIRMATORY_SNAPSHOT.json`
already exists, and refuse to run if `docs/reports/SE3_SUBSTRATE_CERTIFICATION.md` is absent or does
not record **S3 PASS** (§3.4). Both refusals are hard exits with a printed reason — not warnings,
not overwrite prompts, and not bypassable by a CLI flag.

This mirrors `scripts/signal_engine/carry/run_sealed.py`. A one-shot read enforced only by
discipline is not enforced.

### 1.7 Reuse the tested Black-76 code; do NOT modify or import the probe

Import `black76_price`, `black76_delta`, `black76_vega`, `implied_vol` from
`scripts/osc/sd_probe.py` (pre-reg A14). Do not reimplement them.

**Do not import from, and do not edit, `scripts/se3/breadth_probe.py`.** It is a completed artifact
whose output is a governance report; its `build_panel()` is monolithic, loads the index-options
database inline, and computes `richB` — so it cannot be reused without dragging variant B and the
probe's own fence constants in with it. Write the confirmatory module standalone.

The duplication that creates is handled by a **cross-check test, not by an import**: assert that the
confirmatory module's `_newey_west`, expiry-picking, front-month RV, and `N_eff` helpers return
values identical to `breadth_probe.py`'s on synthetic input. That converts a copy-paste risk into a
checked invariant.

### 1.8 State the §6 predictions before running

Record HELD / FAILED per row. Do not revise a prediction after seeing a result.

---

## 2. Window ledger — what this run SPENDS

State this table verbatim in **both** reports, updated to post-run state. The stale-ledger finding
from an earlier lead review must not recur.

| Leg | Window | State entering this run | State after |
|---|---|---|---|
| **OPTSTK stock options** | **2016-02-11 → 2022-12-31** | Skew-exposed 2016-07→2020-12 (25Δ risk-reversal, monthly, TRAIN FAIL); **unspent** 2021-01→2022-12 | **SPENT — this is the confirmatory read** |
| NIFTY index options | 2016-02-11 → 2022-12-31 | Unread, 1,701 dates | **Unread — variant A does not touch the index leg (§1.3)** |
| OPTSTK stock options | 2023-01-02 → 2025-12-31 | **Spent** by the breadth probe | Unchanged — out of bounds here |
| NIFTY index options | 2023-01-02 → 2025-12-31 | Already burned (MSRP triage, OSC probe) | Unchanged — out of bounds here |
| Both legs | 2026-01-01 → 2026-07 | Unread | **Preserved — deliberately reserved (pre-reg §2.1)** |

**The permissive reading is what is being spent.** Under it, Skew's 2016–2020 TRAIN is disclosed
prior exposure rather than a spent window (operator decision 2026-08-05,
`SE3_BREADTH_PROBE_REVIEW_2.md`). The falsification condition on that reading is pre-reg §2.2:
**if the signal drifts toward wing or skew features, n falls to ≈495 and the permissive reading is
void.** §1.3 and A7's `|ln(strike/F)| ≤ 0.10` band are what hold it. Do not widen the band, and do
not add a wing feature — not as a diagnostic, not as a robustness check.

---

## 3. Specification — by reference, plus three resolved ambiguities

### 3.1 The spec is the pre-registration, not this document

Implement **pre-reg §3.A A1–A14** and **§3.B B1–B8** exactly as written. They are not restated here:
one source of truth, cited by number. Where this prompt and the pre-registration disagree, **the
pre-registration wins and the disagreement is a defect in this prompt — report it.**

### 3.2 Resolved ambiguity 1 — the skip-a-day subscript convention

B1 pins the target as *richness at `t` vs the delta-hedged return over `t+1 → t+2`*. A12 writes the
return with subscript `t`. Read literally the two are inconsistent about **which date sets the
hedge ratio and the vega scaling.**

**Resolution — reproduce the probe's corrective run exactly**, verified against
`scripts/se3/breadth_probe.py:637–708`:

```
richness            evaluated at t      (per-date OLS residual, A11)
option contract     selected at t+1     (A3 expiry rule + A4 forward + A7 band + A8 ATM, applied at t+1)
Delta, vega, IV     evaluated at t+1    (Black-76 at t+1, T = DTE as of t+1)
V, F                read at t+1 and t+2
dh_return_scaled    = ((V_{t+2} - V_{t+1}) - Delta_{t+1} * (F_{t+2} - F_{t+1})) / max(vega_{t+1}, 1e-6)
```

**The contract is held fixed across the return window.** The `(expiry_dt, strike, option_type)`
selected at `t+1` is the same one whose `settle` is read at `t+2`, and the forward at `t+2` is that
same expiry's `FUTSTK` settle — verified at `breadth_probe.py:655` (`_stock_forward(t1, u, exp)`
reuses the row's `exp`) and `:665` (`(t1, u, exp, strike, ot)`). **Do not re-apply A3/A7/A8 at
`t+2`.** Re-selecting there would pair the price of one contract against the price of another and
silently change the return.

This is not a choice — it is the construction that produced the declared `sd_IC = 0.1877`, and the
declaration's sd band is only transportable if the confirmatory construction matches it. It is also
the executable timeline: signal from the close of `t`, position opened at `t+1`, closed at `t+2`.

**Also inherited: the pairing is a per-name row shift, not a calendar-adjacency requirement.** The
probe used `groupby(underlying).shift(-1)` over that name's surviving panel rows, so a name absent
on some date pairs across the gap. Reproduce that convention — changing it would break comparability
with the declared sd.

**Report the gap distribution as a diagnostic** (median, p90, and share of pairs where the return
window is not the immediately following trading day). This is an observation, not a filter: **do not
drop gapped pairs.** If the share is material, it is a finding for the report and for any successor
pre-registration, not something to fix inside this run.

### 3.3 Resolved ambiguity 2 — the L/S direction in the P&L diagnostic

B6 pins "quintile L/S on richness, equal-weight, daily formation, vega-scaled" without naming which
end is long. **Pinned here, fixed *a priori* by the declared sign (pre-reg §1.1, expected NEGATIVE):
long the BOTTOM richness quintile (cheapest), short the TOP (richest).**

This direction is fixed before the read and **must not be flipped after seeing the IC.** If the
realized IC is positive, that is pre-reg §4's "significant, wrong sign" row — a falsification — and
the P&L is reported at the declared direction anyway, showing a loss. Reversing the legs to make the
diagnostic look better is exactly the IVOL failure mode the pre-registration names.

### 3.4 Resolved ambiguity 3 — S3 needs a number, and only the operator may set it

Pre-reg §6 Phase 1 says a usable-date count "materially below" 1,701 forces re-approval of
`n_available` before any IC is computed. **"Materially" is undefined, and left undefined it becomes
a judgement made after seeing the count — post-hoc, on the confirmatory window.**

**Escalated to the operator as precondition 0.1e.** The constraint that sets it is where the
declared band's `n_required` boundaries sit (`SE-3_RFA.md`): **288** optimistic corner / **756**
central / **2,492** pessimistic floor. A shortfall leaving n comfortably above 756 changes nothing
about which corner is demonstrable; one that drops below 756 changes the central case. The
implementer **does not pick this number** — §3.B forbids adding parameters. Run with the integer the
operator pins, as a module constant `S3_MIN_USABLE_DATES`.

**S3 is a coded stop, not a printed number.** Phase 1 must emit an explicit `S3: PASS` or
`S3: FAIL` line, and Phase 2 must refuse to start on FAIL or absence (§1.6). The repo already has a
pitfall entry for this: *a freshness value that is printed but never asserted is documentation, not
a control.*

**Expect S3 to bite.** 2016–2017 OPTSTK books are far thinner than 2023–2025. A5's
`contracts > 0 AND open_int > 0` and the ≥20-name minimum will do far more work in the early era
than the probe's "50 names every day" suggests. **A large early-era shortfall is a realistic and
legitimate outcome of this task** — report it and stop; do not relax A5 to recover dates.

### 3.5 The usable-date reconciliation — a required line item

Phase 1 must print this waterfall, as absolute counts, and reconcile the last line against 1,701:

```
trading dates in 2016-02-11 .. 2022-12-31 (from the stock-options store)   ....
  - dates before the first usable formation date (A10 RV warmup)           ....
  - tail dates with no t+1 / t+2 pair inside the fence                     ....
  - dates with < 20 names surviving A1-A11 (richness computable)           ....
  - dates with < 20 PAIRED names for the IC (A13)                          ....
  = USABLE CONFIRMATORY FORMATION DATES                                    ....
```

The last two overlap. Present it as a **waterfall of survivors**, each line the count remaining, not
as independent subtractions — an inclusion–exclusion error here would misreport the very number S3
gates on.

---

## 4. Phases, deliverables, gates

### Phase 1 — Substrate certification (NO returns, NO IC, NO P&L)

Structural counts only, on the SE-1 counting-pass precedent. Runs **after** the pre-registration is
frozen (§0.1); running it first would let survival counts select filter thresholds, which is tuning
on the confirmatory window through the back door.

| Check | Requirement |
|---|---|
| S1 | PIT membership resolves for every date in span; `DUMMY*`/`TMPV*` excluded **and each exclusion reported by symbol and first-seen month** |
| S2 | Names/day surviving A1–A11 — report distribution **by year**; do not adjust filters in response |
| S3 | Usable formation dates (§3.5 waterfall) vs `S3_MIN_USABLE_DATES` — **explicit PASS/FAIL** |
| S4 | Expiry coverage: no calendar month with zero admissible expiry under A3 |
| S5 | IV inversion discard rate (A9), by year |
| S6 | Fence assertion: observed min/max `trade_date` per source, inside 2016-02-11 → 2022-12-31 |

**No return, IC, or P&L may be computed in Phase 1.** A test asserts the Phase-1 module contains no
Spearman/IC call and no forward-return construction.

### Phase 2 — Confirmatory read (one shot, never re-run)

| Gate | Criterion |
|---|---|
| **G1 (primary)** | Mean daily cross-sectional Spearman rank IC significant at **α = 0.05, two-sided**, Newey–West lag 5 (B4). AC₁ reported unconditionally |
| **G2 (sign)** | Sign is **negative** as declared. A significant positive IC is a **falsification** (pre-reg §4), not a re-specification opportunity |
| D1 (diagnostic) | Quintile L/S P&L across the §5 cost ladder, at the §3.3 direction — **reported, not gating**. Run subject to precondition 0.1b |
| D2 (diagnostic) | Realized `sd_IC` vs the declared band **[0.1877, 0.26]** — the C2 check. Outside the band ⇒ report prominently; it does not retroactively invalidate G1 |
| D3 (diagnostic) | Realized `N_eff` and `rho_bar` on the raw panel, comparable to the probe's **5.9 / 0.150**. Demeaned figures may be reported only under the artifact warning, and **never quoted as breadth** |

### Deliverables

| Path | Content |
|---|---|
| `scripts/se3/certify_substrate.py` | Phase 1. Single entry point, deterministic, no tuning knobs beyond `--out` |
| `docs/reports/SE3_SUBSTRATE_CERTIFICATION.md` | **Script-generated, no hand-edited numbers.** S3 verdict explicit |
| `scripts/se3/run_confirmatory.py` | Phase 2. One-shot; refuses on existing snapshot or non-PASS S3 (§1.6) |
| `docs/reports/SE3_CONFIRMATORY_REPORT.md` | **Script-generated, no hand-edited numbers** |
| `docs/reports/SE3_CONFIRMATORY_SNAPSHOT.json` | Frozen outputs (path pinned by pre-reg §6) |
| `tests/se3/test_confirmatory.py` | See below |

**Required tests** (in addition to whatever the implementation needs):

1. **Two-sided fence** — a row dated 2023-01-03 raises; a row dated 2016-02-10 raises.
2. **Variant B absence** — module source contains no `options_bhavcopy.duckdb`, no `richB`, no
   `BETA_WINDOW` (§1.3).
3. **Skip-a-day convention** — on a synthetic panel, richness at `t` pairs with the return built
   from `V_{t+1}, V_{t+2}, Δ_{t+1}, vega_{t+1}` (§3.2), and the per-name row-shift pairs across a
   missing date rather than dropping it.
4. **One-shot guard** — Phase 2 exits non-zero when the snapshot exists, and when the certification
   report is absent or records S3 FAIL.
5. **Phase-1 purity** — Phase-1 module computes no IC and no forward return.
6. **Helper cross-check** — `_newey_west`, expiry picking, front-month RV and `N_eff` agree with
   `breadth_probe.py` on synthetic input (§1.7).
7. **L/S direction** — bottom richness quintile is the long leg (§3.3).

### Report ordering

Both reports, in this order: **fence proof → window ledger (§2, post-run) → attrition table in
absolute counts → §3.5 waterfall → the phase's headline numbers → diagnostics → predictions table
with HELD/FAILED → implementation notes (anything in the pre-reg that could not be implemented as
pinned).**

---

## 5. Costs — a labelled ladder, never a measurement

Pre-reg §5 established, and verified against `DESCRIBE`, that **`stock_options_bhavcopy` carries no
bid and no ask.** Cao & Han's cost result is expressed as a fraction of the quoted spread and their
effect dies at 50% of it, so the number that decides whether SE-3 is worth building **is not
recoverable from 2016–2022 data at any effort.**

D1 therefore reports net P&L across an **assumed** round-trip option cost ladder of
**0 / 25 / 50 / 100 bps of premium**, mirroring Cao & Han's 0 / 25% / 50% structure so the two are
comparable, plus statutory charges and the futures-leg hedge cost.

Binding on the implementation:

1. **Every ladder rung is labelled an assumption, in every table and every sentence that cites it.**
   It is not evidence about Indian single-stock option spreads.
2. **Statutory charges are era-dated.** Print the schedule used with effective dates and sources
   (options STT is sell-side on premium; plus exchange transaction charge, SEBI fee, stamp duty,
   GST; futures leg separately). The window spans a change in the option-sale STT rate, so a single
   flat rate across 2016–2022 is wrong. If a component cannot be dated from a citable source,
   **report it as a labelled assumption in the table** — §1.4's D1 exception — and do not halt.
3. **No weak proxies.** `val_in_lakh / contracts` and `high − low` are not quoted spreads and are
   confounded by intraday drift. Using either as if it measured cost is the "printed but never
   asserted" failure the repo already has a pitfall entry for.
4. **The honest cost answer is forward-only.** `core/analytics/options_selection.py` already screens
   live bid/ask. That collection task costs no historical window and is out of scope here
   (pre-reg §9.2).

---

## 6. Falsifiable predictions — state these in the report, then run

**Phase 1** (these are where the surprises live):

| # | Prediction |
|---|---|
| Q1 | Median names/day surviving A1–A11 in **2016–2017** is materially lower than in **2021–2022** — the early-era thinness is real, not a bug |
| Q2 | Median names/day over the whole span ≥ 20 (the A11/A13 minimum) |
| Q3 | IV inversion discard rate < 10% of cells passing A5–A7, in every year |
| Q4 | No calendar month has zero admissible expiry under A3 (S4) |
| Q5 | First usable formation date is ~21 trading days after 2016-02-11, i.e. **March 2016** — not 2023-03-28's ~60-day analogue (§1.2) |

**Not a prediction — a reporting requirement.** Every `DUMMY*` / `TMPV*` style symbol found in the
2016–2022 MCWB archives is reported by symbol and first-seen month (S1). **Zero is a valid finding.**
All four the probe found (`DUMMYREL` 2023-07, `TMPV` 2026-06, `DUMMYTATAM` 2025-10, `DUMMYHDLVR`
2026-01) are 2023-or-later, so there is no basis for predicting the practice existed in the earlier
era in either direction — a prediction here would discriminate nothing.

**Phase 2:**

| # | Prediction |
|---|---|
| Q6 | Realized `sd_IC` falls inside the declared band **[0.1877, 0.26]** (D2). A value outside it is the C2 failure mode and must be reported prominently |
| Q7 | Realized raw `rho_bar` is **above** the probe's 0.150 — the probe's own report labels its breadth an **upper** estimate (MINOR-1: idiosyncratic `V_t` noise dilutes cross-name correlation) |

**Q7 is deliberately stated on `rho_bar`, not on `N_eff`.** Since
`N_eff = N / (1 + (N−1)·rho_bar)`, at fixed `N` the two are the same claim, and listing both would
show one piece of evidence as two HELD rows. **Report realized `N_eff` and `N` alongside it**
without a prediction attached: §3.4 warns early-era thinness may move `N` materially, and if `N`
falls then `N_eff` and `rho_bar` genuinely can move together rather than inversely. That decoupling
is informative and must be visible rather than predicted.

**There is no prediction on the IC itself.** Pre-reg §4's outcome matrix is the pre-declared reading
of G1/G2, and predicting the primary result would invite reading the outcome as confirmation of the
predictor rather than of the hypothesis.

---

## 7. What must NOT happen

- **Do not read outside 2016-02-11 → 2022-12-31** — stated twice deliberately, and note it now cuts
  *both* ways (§1.1). The 2026 tail in particular is easy to reach for and is the only forward check
  that will exist.
- **Do not compute variant B, or any A/B comparison** (§1.3).
- **Do not add a wing, skew, or risk-reversal feature.** It voids the permissive n = 1,701 reading
  and drops n to ≈495 (pre-reg §2.2). Not even as a robustness check.
- **Do not add neutralization** beyond A11's per-date regression (B3), **do not winsorize** before
  ranking (B2), **do not band, size, or turnover-control** the P&L diagnostic (B6).
- **Do not flip the L/S direction after seeing the IC** (§3.3).
- **Do not relax A5** (`contracts > 0 AND open_int > 0`) to recover early-era dates. It is the
  substrate defence; settle-only strikes are theoretical values and inverting them fabricates IVs.
- **Do not widen the `brentq` bracket** (A9). Discard non-convergent cells and report the rate.
- **Do not quote the demeaned `N_eff` as breadth.**
- **Do not re-run Phase 2** (§1.6). If it crashes mid-run, **stop and report** — restarting a
  one-shot read after a partial execution is a decision for the operator, not a retry.
- **Do not modify `scripts/se3/breadth_probe.py`, `scripts/osc/sd_probe.py`, or any frozen
  declaration or report.**
- **Do not treat a G1 PASS as authorization to build anything** (pre-reg §7).

---

## 8. Known open problems this run does not resolve

Named here so they are not discovered late and not mistaken for implementation defects:

1. **The correlation tail.** A dispersion book reports an attractive Sharpe until correlation goes
   to one. Neither the noncentral-t gate nor a rank IC sees that, and nothing in this run measures
   it (pre-reg §7).
2. **Costs are unmeasurable historically** (§5). The ladder is an assumption; the real answer is a
   forward collection task.
3. **`N_eff` ≈ 5.9 on ~46 names.** A rank-IC PROCEED does not imply a `per_trade_pnl` PROCEED. This
   is precisely why D1 cannot falsify G1 (pre-reg §4) — and why "significant IC, negative P&L" is
   the **expected** outcome, recorded in advance as **NO-BUILD with the IC finding standing**.
4. **Implementation difficulty is rated Very High** — simultaneous single-stock option positions
   with daily delta hedging across ~46 names, at retail scale.

---

## 9. Review and handover

Return: the six deliverables, plus a short note on **anything in the pre-registration that could not
be implemented as pinned**, plus the §0.1 precondition table with its final state.

Claude reviews against this prompt and against `SE3_PRE_REGISTRATION.md`. The operator decides what,
if anything, follows. Per pre-reg §4, **no fallback branch is declared**: at one confirmatory window
a documented failure *is* the outcome.

**References:** `SE3_PRE_REGISTRATION.md` · `governance/rfa/declarations/se3.py` (`fd91b1d5…`) ·
`docs/reports/SE-3_RFA.md` · `SE3_DELTA_ANCHOR_LITERATURE.md` ·
`SE3_BREADTH_PROBE_{PROMPT,REPORT,REVIEW,REVIEW_2}.md` · `CB_N50_PRE_REGISTRATION.md` ·
`OSC_RFA_ABANDON.md` · `scripts/rfa/power.py`
