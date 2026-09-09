# Implementer Prompt — RFA v2 Task 5: Documentation Corrections

**Author:** Claude (review role) · **Date:** 2026-07-21 · **For:** DeepSeek
**Predecessor:** `docs/reports/RFA_V2_REMEDIATION_PROMPT.md` (Tasks 1–4 complete — see below)
**Source finding:** `docs/reports/RFA_GATE_O1_REVIEW.md`

> **This is a documentation-only task. Do not modify any `.py` file.** The code work is finished
> and verified. Your job is to correct four documentation defects and write the close-out report.

---

## What is already done — do not redo or re-verify beyond a smoke check

Tasks 1–4 landed in commits `43c5d46`, `3767c21`, `d7fa9c8`. I verified all of it:

| Item | Status |
|---|---|
| O1 PROCEED withdrawn (banner on `O1_RFA.md`, body preserved) | ✅ done |
| Contract v2 — Sharpe band for `per_trade_pnl`, delta/sd rejected for that metric | ✅ done |
| `METHODOLOGY_VERSION` → `2.0.0`; `o1_vrp` (1.0.0) now hard-fails | ✅ done |
| `report.py` — conditional independence claim for `rank_ic`, no-crossed-corner text for PnL | ✅ done |
| Tests | ✅ **42 passing** (34 original + 8 new in `tests/rfa/test_contract_v2.py`) |
| `o1_vrp.py` digest guard | ✅ still `25d4a723679ade9dedcabcf94d9968074e3e0e350f158630e301f697b64f2dad` |
| Gate reproduces the reference table | ✅ Sharpe 0.601→0.4908 ABANDON · 1.0→0.8540 (n_req 323) · 1.442→0.9877 (n_req 156) |

**The implementation is correct.** `scripts/rfa/gate.py:63-95` implements `ncp = S√T` exactly as
specified. Do not "improve" it.

Smoke check before you start (should print `42 passed`):
```
python -m pytest tests/rfa/ -q
```

---

## Background you need — one paragraph

The RFA gate is a data-free pre-registration check: given the formations available and a defended
effect-size band, can a construct ever reach statistical power 0.80? The first real declaration
(O1, Nifty variance risk premium) returned PROCEED at power 0.9877 — but that verdict was an
artifact. O1 derived its mean band **from** its SD band via a Sharpe translation, making the two
coupled; the gate assumed they were independent and evaluated the **crossed** corner
(`delta_hi`, `sd_lo`), which implied an annualized Sharpe of **1.442** — above the declarant's own
stated ceiling of 1.0. Read coherently, both declared endpoints sit at Sharpe ≈ 0.59 → power ≈ 0.49
→ **ABANDON**. Contract v2 fixed this by making Sharpe the declared quantity for PnL metrics, since
`ncp = (delta/sd)·√n = S·√T` — **SD cancels**, and so does cadence.

---

## Guards

- **No `.py` edits.** If you believe code is wrong, write it in the report; do not change it.
- **Do not edit `governance/rfa/declarations/o1_vrp.py`** — its digest is recorded in a published
  report and must still verify.
- **Do not re-declare O1 or propose a successor.** O1 is withdrawn. Nothing is authorized by it.
- **Do not delete `docs/reports/OPTIONS_STRATEGY_RESEARCH.md`** — it is current research
  (dated 2026-07-17), not legacy cruft. It is annotated, not removed.
- Keep edits surgical. Match surrounding tone and formatting; this file is read every session.

---

## Task 5a — Delete the stale `DayTypeEngine` section from `CLAUDE.md`

**Location:** `CLAUDE.md` lines **100–114** — the `## DayTypeEngine — Feature Blocks` section,
through to just before `## Production Strategy Status` (line 116).

**Delete the whole section.** It documents a component that does not exist. Verified absent:

| Claimed by CLAUDE.md | Reality |
|---|---|
| `DayTypeEngine` class | No `.py` file in the repo contains it — zero hits |
| `scripts/build_intraday_features.py` | Missing |
| `scripts/train_daytype_classifier.py` | Missing |
| `logistic_13pm_prod` (41 features, 80% val accuracy) | No model artifact anywhere |
| `v9_pm_runner` | Only in `docs/archive/` |

It is pre-SALVAGE residue that survived the migration in docs but not in code, and it directly
contradicts CLAUDE.md's own **"Production Strategy Status"** section (line 116), which states no
production strategy exists and that historical designs "were not ported during the SALVAGE
migration." Check the `Key Directories` and `Data Layout` tables for any dangling reference to the
deleted section and clean those too (e.g. the BankNifty/Block-H framing in `Data Layout`) — but
**keep the factual BankNifty data-coverage lines**, which are about the data store, not the engine.

---

## Task 5b — Update the RFA section in `CLAUDE.md` for contract v2

**Location:** `CLAUDE.md` lines **284–317** (`## RFA — Research Feasibility Assessment`).

Add, in the existing voice:

- **Contract v2 / `METHODOLOGY_VERSION` 2.0.0.** For `metric="per_trade_pnl"` the declared
  quantity is an **annualized Sharpe band plus `cadence_per_year`** — *not* separate delta and SD
  bands. Supplying both is rejected. `rank_ic` keeps delta/SD bands, where independence is
  defensible because IC mean and IC dispersion are separately estimable.
- **Why:** for a PnL metric, mean and SD are estimated off the same series, so "high mean **and**
  low SD" is itself a Sharpe claim. Declaring them separately is over-parameterised and lets a
  crossed corner smuggle in an effect size nobody defended.
- **O1 is WITHDRAWN** (2026-07-21) — one line, pointing at `RFA_GATE_O1_REVIEW.md`. Note that no
  successor is authorized by the withdrawal.
- Add `docs/reports/RFA_GATE_O1_REVIEW.md` and `docs/reports/RFA_V2_REMEDIATION_PROMPT.md` to the
  section's file table.

Preserve the existing **"ABANDON is dispositive; PROCEED means *not provably infeasible*"** wording
verbatim — it is pinned by a test.

---

## Task 5c — Correct the cadence claim and add the invariance lesson

**Location:** `CLAUDE.md` line **248**, in the SFB-1/F1 section. It currently reads:

> "If futures are ever revisited, the honest case is **higher cadence → more formations → escapes
> the sample wall**, *not* 'momentum works better in futures.'"

**This prescription is wrong and must be corrected.** Power depends only on Sharpe and elapsed
calendar time:

```
ncp = (delta/sd)·√n = (S/√c)·√(c·T) = S·√T
```

Cadence `c` **cancels**. Trading weekly instead of monthly multiplies your formation count by 12
but divides your per-formation Sharpe by √12 — the two exactly offset. Higher cadence buys **no**
statistical power. The only escapes from the demonstrability wall are a **longer calendar window**
or a **genuinely higher Sharpe**.

Rewrite line 248 accordingly, and add the result as a standing lesson — either in the RFA section
(5b) or `Known Pitfalls` (line 330), your judgement; state it once and cross-reference, don't
duplicate. Frame the futures case honestly: futures help (if at all) because their **fee structure**
permits strategies that cash equity cannot support — never because of cadence.

*(This result is the prior session's own finding and it is correct. Verify it yourself with a
throwaway calculation before propagating it — do not commit a script for this.)*

---

## Task 5d — Caveat the O2 candidate in `OPTIONS_STRATEGY_RESEARCH.md`

Two edits to `docs/reports/OPTIONS_STRATEGY_RESEARCH.md`:

**1. Line 50** — `### O2 — DayTypeEngine × structure selection … ★ the differentiated edge`.
Add a caveat block immediately under the heading: O2's core asset — the 80%-validation-accuracy
day-type classifier — **does not exist in this repository** (see 5a's evidence table). O2 therefore
**cannot be pre-registered** until the classifier is rebuilt and independently validated, or the
claim is dropped. Note that a rebuilt classifier's accuracy would be a **fresh** read, not the
inherited 80%.

**2. Line 78** (§4 "The find") — the executive summary claims the platform "already holds an unfair
infrastructure position: a certified SPAN engine…, live GEX/PCR/max-pain analytics, and a validated
80% day-type classifier," and that "O2 monetizes proprietary IP that already passed validation."
Correct it: **two of the three assets are real** — `core/risk/nse_margin_engine.py` and
`core/analytics/options_analytics.py` are both present and verified. The third is not. The
"O1+O2 with O3 as a shared filter" recommendation must be softened accordingly.

**Do not touch O1, O3–O7, or any other section.** O1 is separately withdrawn at the RFA layer; that
is recorded in `O1_RFA.md`, not here.

---

## Task 6 — Commit the outstanding review artifacts

These are untracked and should be committed as documentation:

```
docs/reports/RFA_GATE_O1_REVIEW.md
docs/reports/RFA_V2_REMEDIATION_PROMPT.md
docs/reports/RFA_V2_TASK5_PROMPT.md   (this file)
```

---

## Deliverable — `docs/reports/RFA_V2_REMEDIATION_REPORT.md`

Close out the whole v2 effort (Tasks 1–5), not just your half. Include:

1. **What changed and why**, task by task, with commit SHAs. Tasks 1–4 are `43c5d46`, `3767c21`,
   `d7fa9c8`; attribute them as prior work — do not claim them.
2. **Test table with script-generated numbers.** Run the suite and paste real output. No
   hand-typed figures — this repo has been burned by hardcoded PASS strings before
   (`PSB2_PROMPT3_LEAD_REVIEW.md`, MEDIUM-1).
3. **Confirmation of the two invariants:** `o1_vrp.py` digest unchanged, and
   `scripts/rfa/retrospective.py` still passes (it uses `Case` tuples, not `Declaration`, so the
   contract change should not have touched it — confirm, don't assume).
4. **A short "what is now true" section** — the state a future builder needs: O1 withdrawn, Sharpe
   band is the declared quantity for PnL metrics, cadence buys no power, DayTypeEngine does not
   exist.
5. **Anything in this prompt you found to be wrong.** If you disagree with a specification, write it
   in the report rather than silently implementing something else. **A disputed spec is a finding,
   not an obstacle.**

**Still explicitly out of scope:** four-arm contract certification of the options substrate, India
VIX backfill 2019–2023, and any new or successor declaration.
