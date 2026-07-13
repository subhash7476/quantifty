# PSB-1 Phase 1 — Second Lead Review (Prompt 1-A remediation)

**Reviewer:** Claude (Lead Reviewer). **Implementer:** DeepSeek V4.
**Under review:** commit `013aa68` (remediation of `598d8b4`).
**Prior review:** `PSB1_PHASE1_LEAD_REVIEW.md`. **Protocol:** `PSB1_PROTOCOL.md` (FROZEN Rev 2).

## Verdict

**FAIL — Phase 2 remains unauthorized. One blocking defect (R1), and it exposed a
larger one that is not DeepSeek's to fix.**

Nine of the ten remediation items are genuinely closed, and I verified each rather than
accepting the report. **R1 (the §11.3 data-integrity stop rule) is rejected**: it is not
gate-(b)'s classification, and it routes the one residue class that matters — a *missing*
corporate-action factor — to "genuine, log and continue."

Chasing that defect surfaced the real finding, which is bigger than the stop rule and is
an **operator decision, not an implementation bug**: *the harness's scored panel currently
contains ~18 fabricated returns of −49% to −99%, and C1/C2/C4 rank on them.*

## Closed and independently verified

| Item | How I verified | Result |
|---|---|---|
| **D1** C2 unit tests | re-derived the hand math: the (x,y) pattern gives β=3, α=0.01, residuals ±0.01, σ(ε)=√(52·0.0001/50), formation resid +0.01 → score negative | **PASS** — genuinely hand-computed, not asserted against the harness's own output. The 40-present/39-absent boundary and the σ(ε)=0 guard are exact. |
| **D2** §4.2 sign-flag | read `_sign_flag`; P4b asserts it fires on reversal C1 **and not** on null C1; FLAG blockquotes render for reversal C1 *and* C2 | **PASS** — detection exists, both directions tested, surfaced as a visible FLAG rather than a table cell. |
| **D3/D4** stamps | report stamps `2f7c965`, **explicitly stating it is the parent** of the commit adding the file; row count 7,030,920; unfenced max 2026-07-09 | **PASS** — honest, and the R1 line correctly says "not run on real data here." |
| **S1** determinism | two interpreters, `PYTHONHASHSEED` 0 vs 1, whole-file bytes minus the self-referential hash line (`_canonical`) → identical sha256 | **PASS** — a real cross-process proof. |
| **S2/S3** fence | `fence_check` now asserts `fenced ≤ cutoff < unfenced` and **raises "FENCE VACUOUS"** if no sealed data exists to exclude | **PASS** — the tautology is gone; the check now carries information. |
| **R2** real n\* | **recomputed independently from the real `trading_calendar`**: weekly **183**, monthly **42** | **PASS** — and the report honestly labels the in-table n\* as the synthetic artifact. (The synthetic calendar also yields 183, so this needed independent confirmation.) |
| **I1/I2** | constants block records both; `min_names_skipped` column added, 0 everywhere | **PASS** |
| footgun | `db_path` now required on `load_panel` / `evaluate_candidate` | **PASS** |
| tests | ran `pytest tests/psb1/` | **22/22 pass** |

## R1 — REJECTED (blocking)

`scan_data_integrity` halts iff a >|20%| adjusted move **lands on a documented ex-date**,
and logs everything else as "genuine." DeepSeek flagged the semantics for Lead sign-off
rather than burying them — correct instinct, and the answer is that they do not match
gate-(b).

Gate-(b)'s classifier (`scripts/csmp/audit_corporate_actions.py:279–305`) has **five**
buckets, and residue is three of them:

```
RESIDUE = ("magnitude-mismatch", "direction-mismatch", "CA-shaped-orphan")
```

- **CA-explained** — a factor spans `(ptd, td]` *and* matches in direction **and magnitude**
  (±25%) → not residue.
- **genuine** — no factor spans it *and* the surviving ratio is not CA-shaped → not residue.
- **magnitude/direction-mismatch** — a factor spans it but disagrees → **residue**.
- **CA-shaped-orphan** — **no factor spans it**, but the surviving ratio sits on a canonical
  CA ratio (0.5, 0.4, ⅓, 0.25, 0.2, ⅙, 0.1, 0.05, 0.02, 0.01 ± 0.02) → **residue: a missing
  factor.**

Acceptance is then `residue − ca_scope_exclusions` (13 documented rows).

Against that, R1 is wrong in **both** directions, and both are live in PSB-1's own deduped
ever-member panel on the dev window:

1. **It cannot detect a missing factor.** CA-shaped-orphan is precisely the "no ex-date"
   branch — the one R1 routes to *"genuine, log and continue."* There is no ratio test
   anywhere in PSB-1. **This is the failure mode §11.3 exists to halt on, and the stop rule
   is blind to it.** ~18 such moves are present (below).
2. **It can false-halt.** With no magnitude-agreement test, *any* >20% adjusted move on a
   documented ex-date halts the battery — including a legitimately adjusted CA that
   coincided with genuine news. **Up to 4** such rows exist in the panel (MMTC +21.9%,
   ENGINERSIN +20.0%, EASEMYTRIP +20.0%, KWALITY +45.9%); the two at exactly +20.0% look
   like ordinary upper-circuit days — gate-(b) deliberately screens up-moves only above
   **+25%** for exactly this reason. Classifying them is gate-(b)'s call, not mine; the
   defect is the *absent magnitude test*, not a count I can stand behind.
3. **`ca_scope_exclusions` is never consulted**, so a residue row gate-(b) explicitly
   *passed* as documented could halt the battery.
4. Minor: gate-(b) spans an ex-date over the interval `ptd < ex ≤ td`; R1 tests `d1 == ex`,
   so an ex-date on a non-trading day (or a day the name didn't trade) is missed entirely.

**Fix:** rebuild R1 on gate-(b)'s actual classification — the interval span, the magnitude
agreement test, the CA-ratio test, and the `ca_scope_exclusions` lookup — rather than a
two-bucket proxy.

## The finding that outranks R1 — for the operator

**R1 is the tripwire. The loader is the wound.**

`load_panel` selects from `equity_bhavcopy_adjusted` with **no `ca_scope_exclusions` /
`ca_evidence_exceptions` filter** (unlike the CSMP consumers, for which that adjusted view
is documented as authoritative *"excluding the symbols in the two exception tables"*). So
the unadjusted corporate-action moves are in the **scored panel right now**, independently
of the stop rule. A perfect R1 would only *halt*; it would never clean the panel — and
documenting a row in `ca_scope_exclusions` makes the gate pass while the −99% stays in the
data.

Probing the panel exactly as `load_panel` builds it (`rn=1` turnover-primary dedup,
ever-member entities, dev-fenced) I find **365** moves >|20%|, of which **18 sit on a
canonical corporate-action ratio with no spanning factor** — every one of them a large
**negative** move:

| Entity | Date | Adjusted move | Ratio |
|---|---|---:|---:|
| BAJAUTOFIN | 2010-09-29 | **−99.0%** | 0.0098 |
| AURUM (ex-MAJESCO) | 2020-12-23 | **−98.8%** | 0.0124 |
| PAISALO | 2018-01-24 | −95.3% | 0.0472 |
| SUVEN | 2020-01-21 | −94.7% | 0.0529 |
| ANGELBRKG | 2021-11-11 | −90.1% | 0.0988 |
| GFLLIMITED | 2019-08-06 | −89.1% | 0.1089 |
| ADANIENT | 2015-06-03 | −82.8% | 0.1723 |
| COFORGE | 2020-08-20 | −80.1% | 0.1985 |
| SHRIRAMFIN | 2022-12-20 | −79.8% | 0.2025 |

(plus PHILIPCARB, ANDHRAPAP, CHOLADBS, SINTEX, MASTEK, ARVIND, JSL, VAKRANGEE, DEWANHOUS)

These are **indicative, not authoritative** — my symbol-level ex-date join and ratio test
approximate gate-(b)'s `classify()`. What is certain is that **the adjusted jumps are
physically present in the panel and sit on canonical CA ratios**. Most are demergers,
special capital returns, and splits that gate-(b) never adjusted — **by charter, not by
bug**: gate-(b)'s scope was splits/bonuses/rights, and demergers were explicitly carried
forward as a documented exclusion.

**Why it corrupts the reversal trio specifically.** C1's score is `s = −r(t−5, t)`. A
fabricated −99% one-day return makes that name **the single most extreme loser in the
cross-section**, which is the **highest possible C1 score** — so it goes straight into the
top-quintile long book, on a price move that never happened. Its actual forward return is
ordinary (the price has already re-based), so it contributes noise while displacing a real
name, and it anchors the Spearman IC ranking. C2 and C4 inherit the same 5-day return.
Roughly one weekly formation date per event (~18 of 572), one name of ~200 each.

**C5 is touched too, least and in the opposite direction:** a single −99% day inflates that
name's 252-day σ for a full year, pushing it *out* of the low-volatility quintile (~12
monthly formations per event). Not clean — and since C5 is the only candidate whose
eligibility is not fee-dominated (first review), "least" still matters.

## The decision this forces — operator, not implementer

§11.3 says **HALT** on undocumented residue. Applied correctly, the battery therefore halts
on ~18 known, long-understood corporate actions and **cannot run at all** until each is
dispositioned. There is no mechanical way out: adding demerger factors is new adjustment
work (and plausibly the ingestion that operator decision **D4** prohibits), and documenting
the rows in `ca_scope_exclusions` clears the *gate* without cleaning the *data*.

**My recommendation** (not a decision — this needs ratification): treat a return that spans
an unadjusted corporate action as a **missing input under the §4.1 formation-complete
rule** — the name is simply not scorable across that one window, exactly as if a price were
absent. §4.1 already excludes names whose required inputs are absent, and an adjusted price
that does not describe a continuous claim on the same asset *is* an absent input. That
reading needs no new parameter.

**The §9 question I am flagging rather than deciding:** it nonetheless changes results, and
"is this faithfulness to §4.1 or a new exclusion rule?" is exactly the sort of call §9
forbids me to make after results exist. **No candidate result exists yet — which is the only
moment this can be settled for free.** It must be settled now, recorded in the ledger, and
the affected (entity, window) rows carried in a register.

## Still standing from the first review

The **fee-dominance finding is unchanged and independent of all of the above**: on a strong
planted signal (gross +9.8%/yr) the harness still nets **−3.1%/yr**, so §8 eligibility (ii)
imposes a ~13pp/yr gross hurdle on C1–C4 and ~0.4pp/yr on C5. Two live operator-facing facts
now: **the weekly candidates are fee-dominated, and the reversal candidates score on
fabricated returns.** Neither buries the other.

## Required before Phase 2

**Blocking:** R1 rebuilt on gate-(b)'s classification (**Prompt 1-B**), and an **operator
ruling on the panel's disposition of unadjusted corporate actions**, recorded in the ledger
before any candidate result exists.

Everything else from Prompt 1-A is closed and verified.
