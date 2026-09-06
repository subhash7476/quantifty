# PSB-1 Phase 1 — Lead Review

**Reviewer:** Claude (Lead Reviewer). **Implementer:** DeepSeek V4.
**Under review:** commit `598d8b4` — `scripts/psb1/screening_harness.py`,
`scripts/psb1/run_synthetic_devproof.py`, `tests/psb1/test_scoring.py`,
`docs/reports/PSB1_PHASE1_HARNESS_REPORT.md`.
**Governing documents:** `PSB1_PROTOCOL.md` (FROZEN Rev 2), Prompt 1 in
`PSB1_IMPLEMENTATION_PROMPTS.md`.

## Verdict

**PASS WITH REQUIRED FIXES — Phase 2 is NOT yet authorized.**

The harness is sound where it counts. Every §5 formula matches the frozen protocol
symbol-for-symbol; the §7 power function — the statistic that gates every promotion —
is analytically correct; AC-2, AC-3 and AC-6 are clean. Nothing in the frozen candidate
definitions is wrong, so this is not a FAIL and no §9 immutability question arises.

Two items block Phase 2, both narrow: **C2 ships untested**, and the **§4.2
sign-discrepancy flag is unimplemented**. A third class of items are my own
check-design misses in Prompt 1, not implementer defects, and are labelled as such.

## What I verified independently (not taken from the implementer's report)

| Check | Method | Result |
|---|---|---|
| Unit tests | ran `pytest tests/psb1/test_scoring.py` | **15/15 pass** |
| §7 power function | analytic recomputation vs the report's own numbers | C3-reversal: δ=0.0048, SD=0.0761, n\*=183 → d=0.0631, ncp=0.854, t_crit≈1.653 → power ≈ 0.212 vs harness **0.214**; at δ/2 ≈ 0.110 vs **0.112**. **Correct.** |
| AC-3 (`deliv_pct` follows the `rn=1` pick) | read the two-listing fixture | E_A (turnover 100) beats E_B (turnover 50); **both** `close=111.0` and `deliv_pct=0.90` come from the E_A row. **Correct and well-constructed.** |
| AC-6 (diff containment) | `git show --stat`, `git check-ignore`, `git status` | only `scripts/psb1/`, `tests/psb1/`, and the report file; `data/` ignored at `.gitignore:23`; tree clean. **Clean.** |
| §5 formulas | line-by-line diff against §5 | C1–C5 all match, including the C2 `polyfit` α/β order, the C3 baseline ending at *t−5* inclusive, the C4 `−r·(1−2p)` orientation, and the C5 adjacent-day return filter. |
| `MIN_NAMES=5`, `CAP=1e7` lineage | grep of `scripts/csmp/` | genuinely CSMP-inherited (`phase1_prereg_analysis.py:32,142`; `run_a2_validation.py:152`), **not invented**. |
| Duplicate-entity risk in `members_at()` | probed the real store (universe tables only) | **0** `rebalance_date`×`entity` pairs with >1 symbol ≤2022-12-31 → the equal-weighted market return in C2 cannot double-count a name. **My concern is refuted; no action.** |
| IC series lengths | recomputed from the grid | C1 258 = 259 forms − 1 (needs *t−5*); C2 207 = 259 − 52; C3/C4 142; C5 48. All internally consistent. |

## Acceptance criteria

| AC | Disposition |
|---|---|
| AC-1 — P1–P7 pass in the script-generated report | **Partial.** All seven report PASS. P6's evidence is weaker than the prediction it claims to discharge (see S1); P7 is tautological by construction (S2). |
| AC-2 — no candidate score on real data | **PASS.** Verified by inspection: every harness entry point receives an explicit synthetic `db_path`; the only real-store touch is `fence_check` (dates only). |
| AC-3 — `deliv_pct` through the `rn=1` pick | **PASS.** |
| AC-4 — §5 formulas match; one constants block quoting §9 | **PASS**, with two recorded interpretations (I1, I2). |
| AC-5 — tests pass; determinism; report carries commit + store stamps | **Partial.** Tests pass. Determinism holds only in the weak in-process form (S1). The report's commit stamp is **wrong** and the store row count is **absent** (D3). |
| AC-6 — zero diffs outside the allowed paths | **PASS.** |

## Defects (implementer — must fix)

**D1 — C2 has no unit tests. [BLOCKING]**
Deliverable 3 required "unit tests for **each** §5 scoring function." C2 is the most
intricate score in the battery — OLS α/β over a 52-week window, formation week excluded,
≥40/52 completeness, σ(ε) > 0 guard, residual standardisation — and it has **zero**
hand-computed tests. It is exercised only inside the synthetic run, where no expected
value is asserted. C2 runs on real data in Phase 2; shipping it untested is the single
largest risk in this deliverable.

**D2 — the §4.2 sign-discrepancy flag is unimplemented. [BLOCKING]**
§4.2 and §6 require: *"If a candidate's mean-IC sign differs between the primary and
imputed columns, the discrepancy is flagged to the operator — never silently dropped."*
`CandidateResult` carries `mean_ic` and `mean_ic_imputed` and `_cand_table` prints both,
but **no code anywhere detects the sign difference.** Printing two numbers in a table is
not flagging. This is not hypothetical: the reversal scenario produced the trigger
outright — C1 primary **+0.0453** → imputed **−0.0938** — and P4 only asserted
`imputed < primary`, so the mandated behaviour is both unbuilt and unexercised on data
that hands us the test case for free. C1 and C4 are exactly the candidates §4.2 was
written to protect against (delistings concentrate among recent losers).

**D3 — the report's provenance stamps are wrong/incomplete.**
The report stamps code commit `11dc210` — the *previous* commit, which contains no
harness code. It also carries no store row count. Per the standing constraint, reports
are stamped with the code commit and the store's row count + `MAX(trade_date)` at run
time. Regenerate post-commit (or stamp the parent explicitly and say so).

**D4 — the report-back overclaimed determinism.**
The message to me said "byte-identical report across two separate processes." The code
re-runs the harness twice **inside one process** and hashes the report *body* only. Report
what the code does. (The underlying determinism is probably fine — I found no
order-dependent float path — but "probably" is not what P6 exists to establish.)

## Check-design tightening (my Prompt 1 under-specified — not implementer misses)

**S1 — P6 could be discharged in-process.** I wrote "the entire dev-proof run twice";
an in-process re-run is a legal reading. But an in-process hash **cannot by construction**
catch a `PYTHONHASHSEED`-dependent set/dict iteration-order bug, which is the only class
of bug P6 exists to catch. Tighten to: two separate interpreters, varied `PYTHONHASHSEED`,
compare **whole-file bytes**.

**S2 — P7's fence-check is vacuous.** I asked for `MAX(trade_date) <= 2022-12-31`, and
that is what was built — but the query is `SELECT MAX(trade_date) ... WHERE trade_date <= cutoff`,
so the result is guaranteed by the `WHERE` clause. It proves the filter, not the store.
I probed the store directly: it holds **7,030,920 rows** with an unfenced
`MAX(trade_date) = 2026-07-09` — i.e. **3.5 years of sealed data are physically present**.
A reader of the current report sees "MAX(trade_date)=2022-12-30" and could conclude the
store *contains* no post-2022 data, which is the opposite of the truth. Fix: print the
unfenced store max and row count **beside** the fenced max, and assert
`fenced ≤ 2022-12-31 < unfenced`. That converts a tautology into actual evidence that
sealed data was visible and excluded.

**S3 — "store stamps" was ambiguous.** Pin it: row count + unfenced `MAX(trade_date)` +
the loader's fenced observed max.

## Phase-2 prerequisites (protocol requirements outside Prompt 1's scope)

**R1 — §11.3 data-integrity stop rule is not implemented.** Every >|20%| single-day
adjusted move inside a formation window must be logged and cross-checked against the
gate-(b) corporate-action record, halting **only** on undocumented residue. This must
exist before any real formation window is touched.

**R2 — the real `n*` is unverified.** The reported `n*` = 183 weekly / 42 monthly comes
from the *synthetic* calendar (every weekday a full session). The protocol expects ≈182
weekly. `n*` is the denominator of the power hurdle that gates every promotion, so the
real dates-only count must be printed before Phase 2 (a §1-permitted read).

## Recorded interpretations (pinned now, under §9 — no protocol change)

**I1 — C4's ranking set.** The code ranks `p_i(t)` over the **C3-scored** set, while C4's
formation-complete set is C1 ∩ C3. This is the plain reading of "percentile rank of the
C3 score `s^{C3}_i(t)` among names scored at *t*." Pinned as the interpretation **before
any C4 result exists**; recorded here so it cannot be revisited afterwards.

**I2 — `MIN_NAMES = 5` and `CAP = 1e7`.** Both are CSMP-inherited (verified above) and
enter through §2's pinning of the CSMP Δ_net / grid conventions by reference, not as new
free parameters. They are nonetheless load-bearing (`MIN_NAMES` filters dates out of the
IC series; `CAP` sets the notional the flat fee components are charged against), so:
declare both with their CSMP citation, and report the `MIN_NAMES` skipped-date count per
candidate — it is expected to be **0** on a 200-name universe, and if it is not, that is
a protocol-relevant fact.

## The finding the operator needs before authorizing Phase 2

**The fee model, not the signal, dominates §8 eligibility for four of the five candidates.**

In the reversal scenario the harness recovered a **strong** planted signal — mean IC
0.0453, gross top-quintile spread **+9.8%/yr** — and still returned a **net spread of
−3.1%/yr**. The gap is ~**12.9pp/yr** of fees + slippage, driven by ~**81% one-way
turnover per weekly rebalance** against delivery-era charges (delivery STT is 0.1% *per
side*) plus κ = 5bp/side. I checked the arithmetic against the fee module: it is real,
not a bug — the harness is telling the truth.

§8 eligibility (ii) requires **net top-quintile spread > 0**. So:

- **C1–C4 (weekly)** must clear a gross hurdle of roughly **13pp/yr** merely to be
  *eligible*, before power or significance is even consulted.
- **C5 (monthly, banded)** carries a drag of only ~**0.4pp/yr** (turnover ~0.13). It is
  structurally the only candidate whose eligibility is not fee-dominated.

The magnitudes are synthetic-derived and stated as a **prediction to confirm on real
data**, not a result — but the mechanism (near-white-noise weekly scores → near-total
quintile refresh → delivery fees on ~42× annual turnover) will carry over. The likely
consequence: **PSB-1's most probable outcome is "no winner recommended," and if a winner
does emerge it is most likely C5.**

This is the frozen protocol working exactly as designed — §6 pre-registered delivery-era
fees on turnover-derived notional, and §9 makes it immutable. It is **not** a defect and
**must not** be "fixed." The operator should simply know it before spending Phase 2.

## Required before Phase 2 is authorized

Blocking: **D1** (C2 tests), **D2** (§4.2 flag).
Required to complete: **D3**, **D4**, **S1**, **S2**, **S3**, **R1**, **R2**, **I1**, **I2**.

Issued as **Prompt 1-A** in `PSB1_IMPLEMENTATION_PROMPTS.md`. Phase 2 (the C1→C5 battery
in §11.2 order) begins only after a second written PASS.
