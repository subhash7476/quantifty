# CSMP Prompt 11 — Lead Review: reporting-layer remediation

**Date:** 2026-07-12
**Reviewer:** Claude (Lead Reviewer) · **Implementer:** DeepSeek V4
**Verdict:** **NOT PASSED — one HIGH finding.** Nine of ten criteria pass, including the dispositive one. **The Lead-Review amendment was not implemented**, and it is the single load-bearing safeguard of the whole fix.

---

## 1. What passes (verified independently)

**C1 — dispositive, and it holds.** The reporting fix moved **no number**. Verified against my *own*
snapshot taken during the Prompt-9 review, not against DeepSeek's report:

```
d0651e10…/results.json  sha256 = be662698dc5eb793f612b67378a8fd5e99747e4b73cb3021117a239e4538d955   (old — my Prompt-9 snapshot)
65cefc37…/results.json  sha256 = be662698dc5eb793f612b67378a8fd5e99747e4b73cb3021117a239e4538d955   (new)
```

**Byte-identical.** n=131, mean_IC 0.0457, rule-1/2 21/1, +6.24% / +5.95% — unmoved. The record's *name*
changed (content-addressed by design); its *content* did not. That is exactly the guardrail working.

Also passing: report path parameterized (sealed → `CSMP_PHASE6_SEALED_READ.md`); the false *"was not read"*
claim is gone from the sealed path; the ~59% disclosure is present; the dev-reconciliation block is
dev-only and unchanged; `assert_grid_shape()` exists and raises; construct fence held (dossier diff = the
§1.1 row only); **exactly one dev record** (`65cefc37…`); Prompt 10 Step 0 re-pinned; the dev tripwire
reproduces at `code_commit 8889e70`; fence asserted and printed at `2022-12-30`. **The sealed window was
not read.**

## 2. F1 (HIGH, BLOCKING) — the sealed/dev switch is still a free-text string

The Lead Review's standing amendment was explicit: **do not key `sealed` on the phase label; derive it from
the data.** It was not done.

```
scripts/csmp/run_a2_validation.py:356   sealed = str(args.phase).startswith("6")
core/msi/csmp/validation.py:49          if str(phase).startswith("6") and n != expected:
```

There is **no `PhaseWindowMismatchError`** and **no data-derived `sealed`**. The entire dev/sealed
distinction — the report's destination, the truthfulness of the report's own central claim, and whether the
`n == 42` guard arms at all — hangs on a **prefix match against a CLI string that a human types.**

**Demonstrated (no sealed data read):**

| `--phase` value | `startswith("6")` | report written to |
|---|---|---|
| `6/sealed-read` | True | `CSMP_PHASE6_SEALED_READ.md` |
| **`sealed-read`** | **False** | **`CSMP_A2_DEV_DRYRUN.md` — overwrites the tripwire** |
| **`phase6`** | **False** | **`CSMP_A2_DEV_DRYRUN.md` — overwrites the tripwire** |
| **`Phase 6`** | **False** | **`CSMP_A2_DEV_DRYRUN.md` — overwrites the tripwire** |

**And the fence does not save you.** `run_a2_validation.py:82` asserts only
`observed_max <= price_cutoff`. With `--price-cutoff 2026-06-30`, that assertion **passes while sealed rows
are being read**. The fence bounds *how far* the read goes; it says nothing about *whether the read is
sealed*.

### The failure scenario

> Phase 6 is run as `--phase sealed-read --eval-hi 2026-06-30 --price-cutoff 2026-06-30`.
>
> The sealed window **is read** — the window is now **spent, irreversibly**. But `sealed` is `False`, so:
> the `n == 42` guard **never arms**; the report is written to **`CSMP_A2_DEV_DRYRUN.md`, destroying the
> tripwire**; the report is titled *"Dev-Window Dry Run"*; it runs the dev reconciliation and prints
> `✗ MISMATCH` on every row; and it states — in the artifact produced *by the very run that read the sealed
> window* — **"The sealed window (2023-01 → 2026-06) was not read."**
>
> **Every defect Prompt 11 was written to eliminate returns at once, triggered by a typo, on the one run
> that cannot be repeated.**

This is not a style objection. It is the precise failure Prompt 11 exists to prevent, re-entering through
the switch that decides whether Prompt 11's protections apply at all.

### Required fix (Prompt 12 — small, and the last thing before Phase 6)

Derive sealedness from **the data**, which is authoritative — it is the actual condition under which sealed
rows enter the computation:

```python
sealed = (price_cutoff > DEV_HI) or (eval_hi > DEV_HI)
```

Then **cross-check the label against it and raise on disagreement**, catching both directions — a sealed
window labelled as dev, and a dev window labelled Phase 6:

```python
if str(phase).startswith("6") != sealed:
    raise PhaseWindowMismatchError(...)
```

Key `assert_grid_shape()` off the **same derived `sealed`**, not off the label. Then a mislabelled sealed
run **cannot** happen: it raises before anything is scored, written, or read.

---

## 3. Verdict

**NOT PASSED.** One HIGH finding. Everything else — including the science guardrail — is clean, and the fix
is a few lines.

**The pattern is worth naming.** Prompt 11 was itself a remediation for a defect (`n == 42`) that had been
*"a sentence in a prompt, not a guard in the code."* This finding is the same species: the sealed/dev
distinction is currently **an instruction to type the right string**, not an invariant the code enforces.
**A safeguard that depends on a human typing a label correctly is not a safeguard.** The lesson has now
appeared twice. Prompt 12 is where it stops.

**The sealed window (2023-01 → 2026-06) has not been read.**
