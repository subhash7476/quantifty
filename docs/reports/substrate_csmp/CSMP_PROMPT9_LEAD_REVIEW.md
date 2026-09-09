# CSMP Prompt 9 — Lead Review: close F1 (false reproducibility pin)

**Date:** 2026-07-12
**Reviewer:** Claude (Lead Reviewer)
**Implementer:** DeepSeek V4
**Verdict:** **PASS — all 10 acceptance criteria met.** F1 is closed. **The A2 harness is cleared for Phase 6.**

Every claim below was **re-derived, not accepted on report.**

---

## 1. The criterion the whole prompt existed for

**C1 — the attestation is now true.**

```
$ git ls-tree -r --name-only 98bcaf2 | grep -E "model.py|validation.py|void_precondition.py|run_a2_validation.py|phase1_prereg_analysis.py"
core/msi/artifacts/xs_momentum_v1/model.py
core/msi/csmp/validation.py
core/msi/csmp/void_precondition.py
scripts/csmp/phase1_prereg_analysis.py
scripts/csmp/run_a2_validation.py

$ git ls-tree -r 42797043 | grep -cE "xs_momentum_v1|csmp/validation"   # the OLD, false pin
0
```

The pinned commit **contains the code that produced the record.** The old pin contained **none of it.** That is F1, closed.

## 2. The circularity — broken, and I proved it harder than the implementer did

DeepSeek's own test ran R₁ at `98bcaf2`, made one docs commit, re-ran at `dde1437`, and got the same ID. **I ran the stronger version: HEAD is now `a53e5e2` — two commits past R₁.**

```
$ python scripts/csmp/run_a2_validation.py
clean-tree OK; code_commit (contains the harness) = 98bcaf2f18d5120f1579a29ec553dc5c8266ed23
verdict = Approved & Deployable | validation_id = d0651e10b38157db…

$ sha256sum -c before.txt
record.json: OK   methodology.json: OK   results.json: OK   checksum.sha256: OK
>>> ALL FILES BYTE-IDENTICAL
```

**HEAD moved twice. The record did not move at all** — same `validation_id`, byte-identical across all four files, still exactly one record, tree still clean. `commit` is recorded as `98bcaf2` (the *code* commit) while HEAD is `a53e5e2`: **recorded as provenance, excluded from the identity.** The `validation_id` preimage contains no `rev-parse HEAD` value.

## 3. The dirty-tree guard — tripped, not trusted

I dirtied a harness file and ran it:

```
DirtyTreeError: DIRTY TREE — harness source uncommitted; refusing to write a record that would
attest a commit lacking its own code:
 M core/msi/csmp/validation.py
```

**It raised and wrote nothing.** Structural, exactly as the VOID gate is. The harness is now *incapable* of emitting the false attestation that caused F1.

## 4. The CRLF trap — real, and correctly closed

My amendment 1 was not theoretical. `core.autocrlf = true`, so a fresh Windows checkout rewrites source files to CRLF while the git blob keeps LF. Naive `read_bytes()` hashing would therefore yield a **different `validation_id` on a different machine** — re-introducing F1 as a platform-dependent defect, and defeating the entire point of an independent third-party audit.

Proven closed:

```
raw (LF)   normalized: db06ceffd9e4fdeddff82b916968673ab99fbfcc
CRLF checkout norm.  : db06ceffd9e4fdeddff82b916968673ab99fbfcc
>> autocrlf-IMMUNE? True
   (naive read_bytes would give db06ceffd9e4 vs ef0bfa442e5a -> DIFFERENT)
```

**A third-party auditor on any platform now reproduces `d0651e10…`.** That is what makes the Phase-6 record auditable by someone who trusts neither of us — the standard this program has held since Phase 2.

## 5. The remaining criteria

| # | Criterion | Result |
|---|---|---|
| 1 | Pinned commit contains the code | **PASS** (§1) |
| 2 | `validation_id` HEAD-independent | **PASS** — no HEAD value in the preimage |
| 3 | R₁ == R₂ byte-for-byte, same ID | **PASS** — verified two commits past R₁ (§2) |
| 4 | Dirty-tree guard structural + tested | **PASS** — raised, wrote nothing (§3) |
| 5 | Exactly one record | **PASS** — `d0651e10…`, still one after my re-run |
| 6 | **Numbers did not move** | **PASS** — n=131, mean_IC **0.0457**, rule-1/2 **21/1**, **+6.24%** / **+5.95%**. Provenance changed; computation did not. |
| 7 | `pin_sealed_grid.py` | **PASS** — calendar-only; reproduces all 42 dates, **matching my independent derivation exactly**; asserts `count == 42` |
| 8 | Construct fence held | **PASS** — the entire Prompt-9 dossier diff is **one line**: the §1.1 build-time substrate row |
| 9 | Sealed window not read | **PASS** — fence asserted and printed, observed max `2022-12-30`; the grid pin reads `trading_calendar` only |
| 10 | Phase 6 = date change only | **PASS** — `--eval-lo` / `--eval-hi` / `--price-cutoff`; identical code paths |

Tree clean; `local == remote == a53e5e2`.

---

## 6. Verdict

**PASS. F1 is closed, and the A2 harness is cleared for Phase 6.**

The record now says something **true** about the code that produced it, and says the **same true thing** on every re-run — on any machine, at any HEAD, forever. That property is not decoration: it is the only thing that will let anyone audit the single sealed read once the window is spent.

**Everything is now in place, and the machinery has been proven on data that is already spent.** The pre-registration is FROZEN (Rev 7) and independently reviewed. The gate is pinned and applied by code, not chosen by a human. The VOID precondition is structural. The delisting convention has one implementation. The rebalance grid is pinned, script-reproducible, and independently verified at 42. The harness renders its verdict mechanically from a decision table written before anyone saw the data — and it reproduces the frozen dossier's dev numbers exactly.

**Phase 6 is now what it was always supposed to be: a ceremony, not a build.** Point the same harness at 2023-01 → 2026-06, run the VOID check, run it once, and read the answer.

**The sealed window (2023-01 → 2026-06) has not been read.**
