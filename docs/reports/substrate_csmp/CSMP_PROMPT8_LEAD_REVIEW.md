# CSMP Prompt 8 — Lead Review: A1 artifact + A2 validation harness

**Date:** 2026-07-12
**Reviewer:** Claude (Lead Reviewer)
**Implementer:** DeepSeek V4
**Subject:** Phase 5 (A1) + A2 harness + VOID precondition + dev dry run — **the last build before the sealed read**
**Verdict:** **NOT PASSED — one HIGH finding (F1).** Eight of nine acceptance criteria pass. **Criterion 3 (byte-identical re-run) fails**, and the failure has put a **false fact into the FROZEN dossier**. The fix is small and mechanical, but it is **blocking**: this defect must not reach Phase 6, because Phase 6 cannot be repeated.

> **The good news first, because it is the substantive part:** `results.json` is **byte-identical across runs**. Every number is deterministic, and the harness **reconciles exactly** with the frozen dossier. The science is sound. **F1 is a provenance/identity defect, not a computational one** — but it is precisely the class of defect that becomes permanent and unfixable the moment the seal is broken.

---

## 1. What I verified independently (nothing accepted on report)

### 1.1 The sealed rebalance grid — re-derived from scratch, **exact match**

The pinned 42-date grid entered the **FROZEN** dossier from an **ad-hoc query with no persisted script**. Since a wrong grid means Phase 6 scores the wrong months — with no second chance — I re-derived it myself from `trading_calendar` (`trade_date` + `n_symbols` only; **no price or return column touched** — the non-price calendar-fact exception §1.1 authorises):

```
count = 42     first = 2022-12-30     last = 2026-05-29
pinned count = 42
EXACT MATCH  = True
```

**Verified.** The count equals the pre-registered target (**42**), so it is not a tuning lever. The dates are genuine NSE calendar facts — spot-checked: `2025-03-28` (Mar 31 was Eid), `2026-02-27` and `2026-05-29` (month-ends fell on weekends). **This was the single highest-stakes unverified claim in the deliverable, and it holds.**

### 1.2 The dev dry run — reconciles exactly

Re-ran `run_a2_validation.py` myself:

```
VOID screen [2012-01-01..2022-12-31]: true_moves=4587 residue=6 (documented=6) UNDOCUMENTED=0 -> PASS
Sealed fence OK: observed MAX(trade_date)=2022-12-30 <= price_cutoff=2022-12-31
verdict = Approved & Deployable
```

| | frozen dossier | A2 harness | |
|---|---|---|---|
| n | 131 | 131 | ✓ |
| mean IC | 0.0457 | 0.0457 | ✓ |
| rule-1 / rule-2 | 21 / 1 | 21 / 1 | ✓ |
| net spread (fees) | +6.24% | +6.24% | ✓ |
| net spread (+ slippage) | +5.95% | +5.95% | ✓ |

**`results.json` is byte-identical across my two runs.** The computation is deterministic and agrees with the frozen pre-registration. *(The dev verdict "Approved & Deployable" is expected and carries no evidential weight — dev is where the edge was found. It proves the pipeline renders a verdict, nothing more.)*

### 1.3 A retracted false alarm

My first grep for the shared `fwd()` returned empty, and I briefly took it for a criterion-2 breach. **My pattern was wrong, not the code:** the runner does `import phase1_prereg_analysis as pa` and calls `pa.fwd(...)` at lines 131 and 151. **One §5.2 implementation. Criterion 2 passes.** Recorded because a reviewer's false alarm belongs in the record as much as a real finding does.

---

## 2. F1 (HIGH, BLOCKING) — the reproducibility substrate attests to a commit that does not contain the code

### The defect

`run_a2_validation.py`'s `git_commit()` shells out to `git rev-parse HEAD` **at run time, with no dirty-tree check**. It flows into `methodology.substrate.commit` → `methodology_fingerprint()` → **`validation_id`**.

**DeepSeek ran the harness while the harness itself was uncommitted.** HEAD was `42797043` — the *"issue Prompt 8"* commit. So:

```
$ git ls-tree -r --name-only 42797043 | grep -E "core/msi/csmp|xs_momentum_v1|run_a2_validation"
(empty)
```

**The commit now pinned into the FROZEN dossier §1.1 as the reproducibility substrate contains no artifact, no validation module, and no runner.** Anyone who checks out `42797043` to reproduce the record finds that **the code does not exist**. The pin is not stale — it is **false**.

**Second-order consequence:** because `commit` sits inside the `validation_id` preimage, the record's identity **drifts with every later commit**. My re-run produced a different `validation_id` purely because HEAD had advanced to `49513fe7`. There are now **two records in `csmp_a2_records/` for one computation** — and the only field that differs between them is the commit.

### The failure scenario — why this is blocking, not bookkeeping

> Phase 6 runs. The sealed window is read **once**. The record is emitted, naming whatever HEAD happened to be — from a tree that may be dirty, as it was this time. **The window is now spent.**
>
> Later, someone tries to audit the one result the entire program exists to produce. They check out the commit the record names. **The scoring code is not there.** They re-run at current HEAD and get a **different `validation_id`**, so the natural audit — *"re-run and compare the ID"* — fails, and fails in a way that looks like tampering.
>
> **The single most important run in the program becomes permanently unverifiable, and it cannot be repeated, because the seal is gone.**

This is the exact failure mode the A2 harness exists to prevent. **Reproducibility is one of the seven MSI-006 domains** — and the record whose job is to attest reproducibility is not itself reproducible.

### Required fix (Prompt 9 — all four, before Phase 6)

1. **Hard-fail on a dirty tree.** If `git status --porcelain` is non-empty for the artifact / harness / analysis paths, the run **refuses to emit a record**. *A record naming a commit that does not contain its own code is a false attestation, and the harness must be structurally incapable of producing one* — the same standard already applied to the VOID gate.
2. **Commit the code first, then run.** Order: commit harness → run A2 from a **clean tree** → the recorded commit genuinely contains the code that produced the numbers.
3. **Make `validation_id` HEAD-independent.** Fingerprint on **content hashes of the source files** (`model.py`, `validation.py`, `void_precondition.py`, the runner) — these identify the code exactly and are immune to later commits. Keep `commit` as recorded provenance **outside** the preimage. Otherwise the sealed record's ID silently changes every time anyone commits a docs typo.
4. **Re-pin §1.1's commit** to the commit that actually contains the harness, and regenerate the dev dry-run record.

**On editing a FROZEN dossier to do this:** §1.1's build-time row is the one place the freeze explicitly sanctions writing (*"pin at build"*), and correcting a pin to a true value is **completing that pin, not changing the construct**. The construct fence (universe, score, K=40, metric, baselines, cost model, §5.2, inference/extension design) is untouched. *The irony is worth recording: the frozen document currently carries a false fact, and the fence happens to permit fixing exactly the row that carries it.*

---

## 3. The other eight criteria

| # | Criterion | Result |
|---|---|---|
| 1 | Sealed window untouched | **PASS.** `assert observed_max <= price_cutoff, "SEALED LEAK"` asserted **and printed**; observed max `2022-12-30`. The one sealed-range query (the D5 grid pin) is **calendar-only** — `trading_calendar.trade_date` / `n_symbols`, no price table — which §1.1 and Prompt 8 D5 expressly authorise. I re-derived it and it matches exactly (§1.1 above). |
| 2 | One §5.2 implementation | **PASS.** `pa.fwd()` imported, never reimplemented (see §1.3 — my initial grep was a false alarm). |
| 3 | **Dev dry run reconciles + byte-identical** | **FAIL — F1.** It reconciles exactly, and `results.json` *is* byte-identical; **the record is not**, because `validation_id` tracks a mutable HEAD. |
| 4 | Gate applied, not chosen | **PASS.** `student_t_one_sided_lb()` is the pinned gate; `render_verdict()` implements §10 mechanically. D-i is neither re-run nor reopened. |
| 5 | `uncertainty` inert | **PASS.** Carried beside the score in a tuple (`scores[sym][0]` = value, `[1]` = uncertainty); ranking, K=40, and equal-weighting use the **value only**. Uncertainty is a passenger for the tercile test. |
| 6 | VOID precondition structural | **PASS.** `assert_void_clear()` **raises** before scoring; `harness.run()` calls it first. A VOID window yields **no verdict**, not a flagged one. |
| 7 | **Phase 6 = date change only** | **PASS.** The window is `--eval-lo` / `--eval-hi` / `--price-cutoff`, defaulting to dev; dev and sealed code paths are identical. This was the criterion most worth getting right, and it is right. |
| 8 | No shared-MSI / `core/execution` edits | **PASS.** New directories only (`core/msi/artifacts/xs_momentum_v1/`, `core/msi/csmp/`). MSI runtime, DRA, contracts, and MSRP-sealed code untouched. |
| 9 | Construct fence held | **PASS.** The only dossier diff is the two §1.1 rows that §1.1 itself marked *"pin at build"*. The grid **definition** is unchanged — only the verified list and count were added. |

---

## 4. Two disclosures worth keeping

**The uncertainty scalar is not a calibrated IC predictor.** The dev tercile test came out **non-monotonic** (0.0485 / 0.0446 / 0.0496) against §7's stated expectation of monotonically higher IC in the low-uncertainty tercile. DeepSeek disclosed this rather than burying it — correctly. **It should be stated plainly in the Phase-6 report as a negative result**, not glossed: the formation-dispersion proxy does not predict IC quality. It is **non-gating**, and it is entirely consistent with `uncertainty` being *reported-not-acted-on* in increment 1 — which is exactly why the dossier refused to let it act. **That fence is now vindicated:** had increment 1 weighted or abstained on this scalar, it would have been acting on a signal that does not calibrate.

**The grid pin has no persisted script.** Standing constraint 3 says *"the report is generated, not hand-typed."* The 42 dates now in the frozen dossier came from an unrecorded ad-hoc query. I re-derived them independently and they match exactly, so the **fact** is verified — but its **provenance** currently rests on my one-off check. **Recommend a small `scripts/csmp/pin_sealed_grid.py`** so the pin is reproducible by anyone, not merely re-verifiable by me.

---

## 5. Verdict

**NOT PASSED.** One HIGH finding, blocking. **Prompt 9 fixes F1; nothing else reopens.**

The scoring machinery is otherwise **correct, deterministic, fenced, structurally gated, and demonstrably one date-flag away from Phase 6.** DeepSeek built the right thing. What it did not do was notice that it ran that thing from a dirty tree — and then pinned the resulting falsehood into an immutable document.

**Which is precisely what this review is for.** The program's discipline has now caught, in sequence: a CI that under-covered by 4×; an extension schedule whose Type-I equalled the bug it replaced; a selection rule that named no metric; a survivorship bug inside the gate-selecting script; a governance escape hatch dressed as a definition; and now **a reproducibility attestation pointing at code that does not exist.** Every one of them was found **before** the sealed window was read — the only time any of them could be fixed for free.

**Phase 6 remains unstarted. The sealed window (2023-01 → 2026-06) has not been read.**
