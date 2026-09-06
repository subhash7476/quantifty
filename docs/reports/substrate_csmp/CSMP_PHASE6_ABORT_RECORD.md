# CSMP Phase 6 — ABORTED RUN RECORD (infrastructure fault; window NOT spent)

**Date:** 2026-07-12
**Recorded by:** Claude (Lead Reviewer) — **written before any remediation is designed**, so that the "nothing was observed" claim carries a timestamp rather than being asserted after the fact.
**Executed by:** Claude, on explicit operator authorization. *(Role-split deviation: Prompt 10 assigns execution to DeepSeek V4; the operator directed Claude to run it. Noted for the record. The integrity property is unaffected — the verdict is rendered by code from a decision table frozen before anyone saw the data.)*

---

## 1. What was run — exactly once

```
python scripts/csmp/run_a2_validation.py --phase "6/sealed-read" \
    --eval-lo 2023-01-01 --eval-hi 2026-06-30 --price-cutoff 2026-06-30
```

Preceded by the Step-0 dev tripwire, which **passed exactly**: `validation_id a5c113dc…`,
`code_commit 983cca0`, reconciliation OK, clean tree. The harness was the one cleared by
`CSMP_PROMPT12_LEAD_REVIEW.md`.

## 2. What happened

```
=== CSMP A2 run | phase=6/sealed-read | window=2023-01-01..2026-06-30 | sealed=True (data-derived) ===
clean-tree OK; code_commit (contains the harness) = 983cca082eb3b00588844ac5d4b0d97185b692dd
VOID screen [2023-01-01..2026-06-30]: max_td=2026-06-30 true_moves=680 residue=2 (documented=2) UNDOCUMENTED=0 -> PASS
Traceback (most recent call last):
  File "scripts\csmp\run_a2_validation.py", line 343, in main
    grid, memb, px, ent_dates, observed_max = load_window(price_cutoff)
  File "scripts\csmp\run_a2_validation.py", line 73, in load_window
    WHERE a.trade_date<=?) WHERE rn=1""", [price_cutoff]).fetchall()
MemoryError
```

**A `MemoryError` in the price-loading `fetchall()`.** An infrastructure fault, not a result.

Prompt 10 anticipated this exactly: *"If it crashes on a genuine infrastructure fault (disk, memory),
report the traceback and stop — do not 'just re-run it.'"* **It was not re-run.**

## 3. The window is NOT spent — precisely why

**The crash occurred inside `load_window()` (line 343), before `build_scored()` (line 345).** Nothing
downstream of the price load ever executed:

- **No score was computed.** The artifact never evaluated.
- **No `IC_t`, no `mean_IC`, no Student-t lower bound, no `Δ_net`.**
- **No verdict was rendered.**
- **No sealed record was written.** `csmp_a2_records/` contains **only** the dev tripwire record `a5c113dc…`.
- **`CSMP_PHASE6_SEALED_READ.md` was never created.**
- **`git status` is clean.** Nothing was written at all.

**Not one statistic bearing on the hypothesis was observed by any party.** This is functionally identical to
the §8 A1 VOID path, whose rule is explicit: *the window is **re-sealed, NOT spent** — because nothing about
the hypothesis was observed.* The same reasoning applies here, for the same reason.

### What *was* observed — pre-authorized, and it is good news

The **VOID precondition ran and PASSED**:

| Quantity | Value |
|---|---|
| Sealed-window max `trade_date` | 2026-06-30 |
| True `\|move\| ≥ 20%` single-day moves | 680 |
| Residue | **2** |
| Documented (in `ca_scope_exclusions`) | **2** |
| **Undocumented residue** | **0 → PASS** |

These are **data-quality facts, not results** — §8 A1 authorizes exactly this read *precisely because* it
preserves the seal. They say nothing about `mean_IC`, `Δ_net`, or any ranking.

**And they discharge the program's scariest inherited assumption.** §12.1 named gate-(b)'s corporate-action
adjustment over the sealed window as the most dangerous unverified inheritance: *"a single wrong split factor
manufactures ±50% phantom momentum and can inject that name into the top quintile."* **Zero undocumented
residue.** The CA adjustment is clean across 2023-01 → 2026-06. That safeguard has now done its job, and the
answer was the one we wanted.

## 4. Why a fix + re-run is legitimate, and is not a re-roll

The obvious worry: *"you ran it, didn't like what happened, and now you'll change the code and run it again."*
That worry is correct in general — it is why the rule exists. It does not apply here, and the distinction is
sharp:

- **Nothing about the hypothesis was seen.** Not a partial result, not a preview, not a hint. The process died
  before the first score existed. **There is no result to have disliked.**
- **The forbidden act is a code change *after seeing the result*.** No result exists. Every remediation
  decision from here is made **blind** — in exactly the epistemic state we were in before the command was
  typed.
- **The re-run will use identical arguments.** Prompt 10 forbids *"running it more than once with different
  arguments."* The arguments do not change.
- **A guardrail already exists that makes this checkable:** the fix must leave the **dev** `results.json`
  **byte-identical at `be662698…`**, as it has been across all three previous rounds of surgery. A memory fix
  that changes a number is not a memory fix, and the Lead Review will catch it.

**This record is written before the remediation is designed**, so the claim "nothing was observed" is
timestamped, verifiable against a clean `git status`, and not a story told afterward.

## 5. State at the time of this record

| | |
|---|---|
| Records present | **only** `a5c113dc…` (the dev tripwire) |
| `CSMP_PHASE6_SEALED_READ.md` | **does not exist** |
| Working tree | **clean** |
| Sealed statistics observed | **none** |
| Sealed data-quality facts observed | VOID screen only (§8 A1 authorized) — **PASS, 0 undocumented residue** |

## 6. Next

**Prompt 13** — fix the memory fault in `load_window()`, re-clear the harness, re-run Phase 6 with the **same
arguments**. Likely cause: `load_window()` materializes the entire price history (`trade_date <=
price_cutoff`) into a Python dict via `fetchall()`; at the sealed cutoff that is the whole store (~7.03M rows)
rather than the dev subset (~5.08M), and it exceeded memory.

**The sealed window (2023-01 → 2026-06) has not been read. It remains sealed.**
