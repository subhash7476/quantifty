# RFA Power-Feasibility Gate — Implementation Report

**Date:** 2026-07-20 → 2026-07-21
**Status:** COMPLETE on the gate (Tasks 1-6) and the first real declaration (O1); PAUSED on the O1 backtest pending operator decision
**Scope:** Build the data-free pre-registration gate per `docs/superpowers/plans/2026-07-20-rfa-power-feasibility-gate.md`; run it against the first real candidate (O1, Nifty VRP); execute the PSB-O0 options-bhavcopy substrate extension required to inform that run.
**Method:** Task-by-task test-first implementation of the plan; script-generated numbers throughout (no hand-edited figures); corrections disclosed in-band, never silent.

---

## Top-line verdict

**The gate works as designed.** It refuses to ABANDON O1 (the optimistic corner clears power 0.9877) while making clear in the same report that the central-case estimate fails by 2.4× — exactly the "PROCEED means not provably infeasible, not clearance" semantics the spec required.

**O1 sits in the same structural position as C2 did at PSB-2 close.** Gate refuses ABANDON, central fails by a wide margin, prior-exposed evidence implies a Sharpe that projects below the power hurdle. The substrate work was correct regardless of O1's fate — it is required for any options construct (O2/O4/O5 all need it).

**Two nontrivial findings during the session**, both disclosed in their respective commits:

1. The F1 closure's "higher cadence → escapes the sample wall" claim is misleading — power is cadence-invariant for fixed Sharpe × time window (`ncp = S × √T`).
2. NSE weekly Nifty options launched **February 11, 2019**, not February 2016 — the original O1 declaration's `n=520` was corrected to `n=380` post-backfill.

---

## 1. Background — why this gate exists

PSB-1, PSB-2, and F1 each died on **demonstrability** once fee-survivable constructs were engineered. The arithmetic is fixed: at monthly cadence with IC~0.03 and SD~0.2, power 0.80 needs ~350 formations (~29 years); the dev window holds ~130. C5 (power 0.54), C4 (0.41), C2-extended (0.66), and F1 (CI includes zero) all confirmed this from different angles.

The RFA gate is the structural answer: a **data-free pre-registration gate** that returns ABANDON/PROCEED on whether a construct can reach power 0.80, **before any construct code is written**. The design spec is `docs/superpowers/specs/2026-07-20-rfa-power-feasibility-gate-design.md`; the implementation plan is `docs/superpowers/plans/2026-07-20-rfa-power-feasibility-gate.md`.

Architecture: three layers, one responsibility each.

| Layer | File | Responsibility |
|---|---|---|
| Power core | `scripts/rfa/power.py` | Pure math — noncentral-t power + binary-search inversion. No I/O. |
| Declaration contract | `governance/rfa/declaration.py` | Frozen dataclass + validation + whole-file SHA-256 digest |
| Verdict | `scripts/rfa/gate.py` | Compose the above; emit a computed (never hardcoded) decision |
| Report | `scripts/rfa/report.py` + `run_rfa.py` | Markdown output; ABANDON/PROCEED wording pinned to spec |
| Retrospective | `scripts/rfa/retrospective.py` | Tests one CLAUDE.md claim against the gate, non-binding |

Declarations live under `governance/rfa/declarations/` (governance namespace, outside `scripts/`) because they are governance records, not tunable script inputs.

---

## 2. What was built — the gate (Tasks 1-6, verbatim from the plan)

| Task | Commit | Files | Tests |
|---|---|---|---|
| 1. Power core | `80755cc` | `scripts/rfa/{__init__,power}.py`, `tests/rfa/{__init__,test_power}.py` | 7/7 |
| 2. Declaration contract | `199a01e` | `governance/{__init__,rfa/{__init__,declaration,declarations/__init__}}.py`, `tests/rfa/test_declaration.py` | 12/12 |
| 3. Verdict evaluation | `ea572e9` | `scripts/rfa/gate.py`, `tests/rfa/test_gate.py` | 7/7 |
| 4. Report generator | `bb11318` | `scripts/rfa/{report,run_rfa}.py`, `tests/rfa/test_report.py` | 4/4 |
| 5. Retrospective | `1b2187f` | `scripts/rfa/retrospective.py`, `tests/rfa/test_retrospective.py`, `docs/reports/RFA_RETROSPECTIVE.md` | 4/4 |
| 6. CLAUDE.md docs | `b5deb33` | `CLAUDE.md` (new top-level RFA section + correction to SFB-1/F1 paragraph) | — |

**Total: 34/34 tests passing across 5 modules.** Matches the plan's expected count exactly (7 power + 12 declaration + 7 gate + 4 report + 4 retrospective).

Every test expectation was independently reproduced against scipy 1.17.0 before writing the corresponding implementation. The bootstrap reference test (`test_matches_psb1_bootstrap_reference`) pins this gate's `power_at` to `scripts/psb1/screening_harness._power` at 1e-9 — the two implementations cannot drift.

---

## 3. Two plan corrections — disclosed, not silent

Both deviations are documented in their respective commits and were applied only to fix internal inconsistencies in the plan's own fixtures, never to weaken an assertion.

### 3.1 Task 3 ABANDON fixture: missing `delta_lo` override (commit `ea572e9`)

The plan's `test_abandons_when_corner_cannot_clear_hurdle` overrode `delta_hi=0.01` against a default `delta_lo=0.02`, which fails the band-ordering validation the plan itself authored. The plan's note explained the parallel `sd_hi` adjustment ("raised to 0.40 alongside `sd_lo=0.30` so the band stays ordered") but missed the same issue on `delta_lo`. Fix: added `delta_lo=0.005` to both ABANDON fixtures (Task 3 `test_gate.py` and Task 4 `test_report.py`'s mirror). Intent preserved exactly.

### 3.2 Task 5 `C2_PHASE0_5` placeholder (commit `1b2187f`)

The plan left `Case("C2_PHASE0_5", 0.0, 0.0, 0, ...)` as a placeholder, with explicit instruction to read V2 off `C2_PHASE0_5_MINIBATTERY.md` and replace before running. Filled with the verified V2 values from line 24 of the minibattery report:

```python
Case("C2_PHASE0_5", 0.022552, 0.100137, 84, False, "C2_PHASE0_5_MINIBATTERY.md"),
```

The placeholder test (`assert 0.60 < max_power < 0.70`) is correctly designed to *fail* on the unfilled `(0,0,0)` placeholder — that design worked as intended and forced the read-before-run discipline.

---

## 4. Retrospective — correcting the C5/C4/C2/F1 claim

CLAUDE.md previously implied the pre-check "would have saved the back half of C5, C4, C2, and F1." The retrospective (`docs/reports/RFA_RETROSPECTIVE.md`) tests this against committed reports and finds it **partly wrong, and the exception is informative**.

| Case | delta | SD | n | Power | Verdict | Source |
|---|--:|--:|--:|--:|---|---|
| C5 | 0.067639 | 0.246232 | 42 | 0.5422 | ABANDON | `PSB1_C5_REPORT.md` |
| C4 | 0.046550 | 0.208949 | 42 | 0.4110 | ABANDON | `PSB2_C4_REPORT.md` |
| **C2 (PSB-2, as recorded)** | **0.034892** | **0.104033** | **84** | **0.9198** | **PROCEED** | `PSB2_C2_REPORT.md:66` |
| C2 (Phase 0.5, extended TRAIN) | 0.022552 | 0.100137 | 84 | 0.6563 | ABANDON | `C2_PHASE0_5_MINIBATTERY.md:24` |
| F1 TRAIN (optimistic) | 0.0154 | 0.0767* | 83 | 0.5672 | ABANDON | `F1_FEASIBILITY_SCREEN_REPORT.md:35` |

\* SD recovered from block-bootstrap CI width via a normal-symmetric back-out (`SE = (CI_high - CI_low) / 3.92`, `SD = SE × √n`). Asymmetric percentile CI makes this an approximation adequate for a feasibility bound — not F1's actual dispersion.

**The gate fires on C5, C4, and F1; it does not fire on C2 as PSB-2 recorded it** (power 0.9198). C2 fails only on the extended-history SD re-estimate. This does not weaken the gate; it locates its dependency on the declared SD — exactly the lesson that motivated the gate's "independently defended SD" requirement.

CLAUDE.md was corrected in two places: a new top-level RFA section was added (between SFB-1/F1 and Options Analysis Dashboard), and the stale "would have saved C5/C4/C2/F1" sentence in the SFB-1/F1 successor paragraph was replaced with the tested claim.

---

## 5. First real use — O1 (Nifty VRP) declaration

### Declaration values

Declared in `governance/rfa/declarations/o1_vrp.py`, frozen at SHA-256 `25d4a723679ade9dedcabcf94d9968074e3e0e350f158630e301f697b64f2dad` (current revision; see §6.2 for the correction history).

| Field | Value | Defense |
|---|---|---|
| `delta_lo, delta_hi` | 0.002, 0.005 | Translation of Sharpe 0.5-1.0 (Bakshi-Ju 2017, Cheng 2018 JFE) at the declared SD band: `weekly_mean = (S/√52) × weekly_sd` |
| `sd_lo, sd_hi` | 0.025, 0.060 | Lower: defined-risk iron-condor structure against `NseMarginEngine` SPAN scans (~18% annualized). Upper: Moreira-Muir (2017) vol-regime clustering haircut (~43% annualized) |
| `n_available` | 380 | Weekly Nifty options Feb 2019 → Jul 2026 (see §6.2 for the correction) |
| `test_type` | one_sided | VRP predicts positive expected PnL |
| `metric` | per_trade_pnl | Per-formation PnL on SPAN margin |
| `prior_exposure` | disclosed | `OPTIONS_STRATEGY_RESEARCH.md` §3.O1 + `MSRP_PHASE7_FEE_TRIAGE.md` (+Rs 110K over 695 dev days; 2023 negative; tail unmodelled). The +Rs 158/day average translates to ~0.5% weekly on SPAN margin — inside the delta band, so the band's center is consistent with prior-exposed evidence, not independent of it. |

### Gate result

```
$ python -m scripts.rfa.run_rfa o1_vrp
O1: PROCEED (max power 0.9877) -> docs/reports/O1_RFA.md
```

| Band point | n required | Available | Status |
|---|--:|--:|---|
| Optimistic corner | 156 | 380 | clears (2.4× margin) |
| Central | 913 | 380 | fails by 2.4× |
| Pessimistic | 5566 | 380 | hopeless (14.6× short) |

**The verdict rests almost entirely on the SD band.** If the realized weekly PnL SD comes in near `sd_lo=0.025`, O1 is demonstrable. If it comes in near `sd_hi=0.060`, no amount of additional data rescues it short of a century. The MSRP Phase 7 prior-exposed Sharpe (~0.5) projects to power ~0.45 — clearly below the hurdle. This is the same structural position C2 occupied at PSB-2 close.

---

## 6. Two findings during the session

### 6.1 Power is cadence-invariant for fixed Sharpe × time window

The F1 closure's prescription read: *"higher cadence → more formations → escapes the sample wall."* Tested:

For a strategy with annualized Sharpe `S` observed over `T` years at any cadence `c` (formations per year):

```
ncp = (delta/sd) × √n
    = (S/√c) × √(c × T)
    = S × √T
```

**Cadence cancels.** Verified computationally across Sharpes {0.5, 0.8, 1.0, 1.5} × windows {3.5y, 5y, 12y} — power is identical at daily, weekly, and monthly cadences for any (Sharpe, time-window) pair.

The correct escape from the demonstrability wall is **longer time window or higher Sharpe**, not higher cadence. The "futures allow higher cadence" framing in the F1 closure is misleading: futures help because their fee structure permits strategies that don't exist in cash equities (not because higher cadence is intrinsically better). This correction does not change any prior verdict; it sharpens the prescription for future builders.

### 6.2 NSE weekly Nifty options launched Feb 11, 2019 — not Feb 2016

The original O1 declaration assumed weekly Nifty options launched Feb 2016 and set `n_available=520`. The PSB-O0 backfill (§7) surfaced the actual history: pre-2019 data contains **only monthly expiries** (~25/year). The first true weekly expiries (`2019-02-14`, 3-day span) appear in February 2019.

Corrected in commit `a11ba32`:

| | Original | Corrected |
|---|---|---|
| `n_available` | 520 | 380 |
| Window text | "Feb 2016 launch" | "Feb 2019 launch (backfill confirmed)" |
| Optimistic-corner power | 0.9982 | 0.9877 |
| Gate verdict | PROCEED | PROCEED (unchanged) |

Per CLAUDE.md's "frozen at approval" rule, declarations should not be revised in response to results. This correction is a **factual fix during the substrate build**, not result-driven tuning — no backtest had been run. The correction is fully disclosed in the declaration's `window` field and in the commit message.

---

## 7. PSB-O0 options-bhavcopy substrate extension

### What was extended

| | Before | After |
|---|---|---|
| Trade dates | 862 (2023-01-02 → 2026-07-06) | **2572** (2016-02-11 → 2026-07-17) |
| Rows | 1,351,214 | **5,490,319** |
| Distinct expiries | ~71/year | 25-83/year depending on era |
| Start date in script | `date(2023, 1, 1)` (hardcoded) | `date(2016, 2, 11)` default; CLI args `python ingest_option_bhavcopy.py [START] [END]` |

Commits: `35b3469` (script refactor — extend default start, add CLI args), `aba1bc2` (data + audit report).

### ATM liquidity audit (PASS)

Generated by `scripts/msrp/ingest_option_bhavcopy.py` → `docs/reports/MSRP_PHASE7_BHAVCOPY_AUDIT.md`:

- ATM-adjacent strikes (±200 from Nifty close): **99.9% of days have contracts > 0**
- Average ATM open interest: **828,032** (>>1000 hurdle)
- Thursday regime (739 dates): 99.9% active, 829K avg OI
- Tuesday regime (122 dates): 100% active, 822K avg OI

### Per-year coverage (no gaps)

Every full year has 218-250 trade dates (normal NSE calendar). Strike grids evolve sensibly with Nifty's growth (2016: 2700-11400; 2026: 12000-34500). Strike counts per year: 139-224 distinct.

### Two still-open prerequisites per `OPTIONS_STRATEGY_RESEARCH.md` §5

| Prerequisite | Status | Why it matters |
|---|---|---|
| Four-arm contract certification | **NOT DONE** | Lot-size changes (Nifty 75→50→25→75), strike-grid changes, Thursday→Tuesday expiry transition all corrupt notional calculations silently. MSRP audit passed but was never put through the PSB-1-style contract suite. |
| India VIX daily history | 2023-01-02 onward only | O1's regime filters use VIX term structure. Need backfill to at least 2019 to match the options data. NSE publishes this freely (not the F1 stock-futures blocker). |

---

## 8. Commits (session, oldest → newest)

| SHA | Message |
|---|---|
| `80755cc` | feat: RFA power core — noncentral-t power and formation-count inversion |
| `199a01e` | feat: RFA declaration contract — frozen bands, required provenance, whole-file digest |
| `ea572e9` | feat: RFA verdict — optimistic-corner evaluation against power 0.80 |
| `bb11318` | feat: RFA report generator and runner |
| `1b2187f` | test: RFA retrospective — gate fires on C5/C4/F1, not on C2 as PSB-2 recorded it |
| `b5deb33` | docs: document RFA gate in CLAUDE.md and correct the C5/C4/C2/F1 claim |
| `9bcb838` | feat: RFA declaration for O1 (Nifty VRP) — PROCEED at power 0.9982, central fails (520 < 913 req) |
| `35b3469` | feat: PSB-O0 — extend option bhavcopy ingestion start to 2016-02-11 (weekly Nifty launch); add CLI start/end args |
| `aba1bc2` | data: PSB-O0 — backfill NSE F&O bhavcopy 2016-02-11 to 2023-01-02 (1,351,214 → 5,490,319 rows, 862 → 2572 trade dates) |
| `a11ba32` | fix: O1 RFA — correct n_available 520→380 (weekly Nifty options launched Feb 2019 not Feb 2016); verdict unchanged PROCEED |

10 commits total. Local `main` is now 18 commits ahead of `origin/main` (6 pre-existing + 10 this session).

---

## 9. Pending decisions (operator-level)

1. **Is O1 worth a real backtest?** The gate refuses ABANDON but the central case fails by 2.4× and the prior-exposed Sharpe (~0.5) projects to power ~0.45. Same structural position as C2 at PSB-2 close. The substrate work was correct regardless of this decision.
2. **Run four-arm contract certification on the options substrate** before any options construct is trusted. Lot-size and expiry-day transitions are silent corrupters.
3. **Backfill India VIX daily history 2019-2023** to match the options data and unblock O1's regime filters.
4. **Push** — local `main` is significantly ahead of `origin/main`. No urgency, but worth noting.

---

## 10. Pointers for future builders

- **The gate reads no market data.** Any RFA run is free; running it is always cheaper than skipping it.
- **ABANDON is dispositive; PROCEED is not clearance.** The wording in `scripts/rfa/report.py` is pinned by tests (`test_proceed_is_qualified_as_not_provably_infeasible`); do not weaken it.
- **The whole declaration file is hashed.** Post-seal appends to a declaration are detected by `digest_of` (PSB-2 MEDIUM-1 lesson). Never hash a subset.
- **SD is the load-bearing input.** The C2 retrospective and the O1 declaration both confirm this. A declaration's value rises or falls on the independent defensibility of the SD band, not the delta band.
- **Methodology-version mismatch is a hard failure.** `gate.evaluate()` raises if `decl.methodology_version != METHODOLOGY_VERSION`. Bumping the methodology version requires re-approving every prior declaration.
- **Power is cadence-invariant for fixed Sharpe × time window** (§6.1). Do not propose higher-cadence constructs as an "escape" from the sample wall — they aren't.
- **NSE weekly Nifty options launch: Feb 11, 2019.** Pre-2019 options data has only monthly expiries. Don't trust `n_available` estimates that assume earlier dates.
- **The repo now has 10+ years of NSE F&O bhavcopy** (2016-02-11 onward, 5.49M rows, 2572 trade dates). It is NOT yet certified to PSB-1 contract standards — see §7.

---

## Files added/modified this session

### Added

```
docs/reports/O1_RFA.md
docs/reports/RFA_RETROSPECTIVE.md
governance/__init__.py
governance/rfa/__init__.py
governance/rfa/declarations/__init__.py
governance/rfa/declarations/o1_vrp.py
governance/rfa/declaration.py
scripts/rfa/__init__.py
scripts/rfa/gate.py
scripts/rfa/power.py
scripts/rfa/report.py
scripts/rfa/retrospective.py
scripts/rfa/run_rfa.py
tests/rfa/__init__.py
tests/rfa/test_declaration.py
tests/rfa/test_gate.py
tests/rfa/test_power.py
tests/rfa/test_report.py
tests/rfa/test_retrospective.py
```

### Modified

```
CLAUDE.md                                              (RFA section + SFB-1/F1 correction)
docs/reports/MSRP_PHASE7_BHAVCOPY_AUDIT.md             (regenerated by backfill)
scripts/msrp/ingest_option_bhavcopy.py                 (default start + CLI args)
```

### Ignored (data, not tracked)

```
data/market_data/options_bhavcopy.duckdb               (5,490,319 rows, 2572 trade dates)
```

*All numbers in this report are script-generated or sourced from committed reports. Two plan corrections disclosed in §3; two findings during the session disclosed in §6. Sealed window (2023→present) untouched by the gate itself; the O1 declaration and the substrate backfill both stop at 2026-07-17.*
