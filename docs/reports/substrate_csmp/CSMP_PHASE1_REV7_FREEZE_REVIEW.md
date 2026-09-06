# CSMP Phase 1 — Lead Review: Rev 7 freeze diff (mechanical fidelity)

**Date:** 2026-07-12
**Reviewer:** Claude (Lead Reviewer)
**Subject:** Prompt 7 — fold Phase-2 F1/F2/F3 + the record correction; stamp Rev 7 FROZEN
**Implementer:** DeepSeek V4
**Verdict:** **PASS.** All 8 acceptance criteria met. **The dossier is FROZEN at Rev 7.** One out-of-scope defect was correctly flagged rather than silently fixed, and is closed separately below.

**Scope of this review is mechanical fidelity only:** did the ratified decisions get applied, and did anything else move? It is **not** a re-litigation of F1/F2/F3 (settled) or of the construct (cleared by the independent Phase-2 review).

---

## 1. The one claim I refused to take on faith: the selected gate

The gate is the whole artifact. I re-ran `scripts/csmp/phase1_ci_coverage.py` myself rather than accept the report.

```
dev IC: n=131 mean=0.0457 SD=0.2079 skew=-0.20  (sealed-fenced <= 2022-12-31)

method        | 2s cover | 2s Type-I | 2s power | 1s Type-I | 1s power
Student_t     |    0.957 |     0.024 |    0.285 |     0.049 |   0.397
iid_perc      |    0.949 |     0.027 |    0.307 |     0.053 |   0.416
mb_L12        |    0.809 |     0.098 |    0.469 |     0.129 |   0.539
stationary_L3 |    0.924 |     0.038 |    0.347 |     0.065 |   0.452
NOMINAL       |    0.950 |     0.025 |          |     0.050 |

D-i SELECTION (ratified rule — one-sided Type-I closest to 0.05; calibration NOT narrowness):
  Student_t      1s Type-I=0.049  distance=0.001
  iid_perc       1s Type-I=0.053  distance=0.003
  mb_L12         1s Type-I=0.129  distance=0.079
  stationary_L3  1s Type-I=0.065  distance=0.015
  >> SELECTED GATE: Student_t  (1s Type-I distance 0.001 from 0.05)
  two-sided-coverage reading (REPORTED, NON-GATING) would select: iid_perc
```

**Prediction vs. outcome — the falsifiable statement was made before the run, and it held:**

| Predicted (pre-run) | Observed |
|---|---|
| dev IC 0.0458 → ~0.0457 | **0.0457** ✓ |
| table moves negligibly | **≤ 0.002** on every cell ✓ |
| selection does **not** flip | **Student-t retained** ✓ |

**The stop condition was live and correctly not triggered.** Had the selection flipped, Rev 7 would not have frozen.

**A margin worth recording.** The F1 danger was that `iid_perc` sat **0.001** from nominal on two-sided coverage — knife-edge — while Student-t sat 0.007 away. **On the ratified metric the margin is not knife-edge: 0.001 vs 0.003, a 3× separation.** The disambiguation did not merely pick a side of a coin-flip; it selected on an axis where the winner is unambiguous. That is materially stronger footing for a frozen gate than the pre-F1 state, and it is the direct payoff of fixing F2 *before* resolving F1.

---

## 2. The 8 acceptance criteria

| # | Criterion | Result |
|---|---|---|
| 1 | **F2 closed in code, not prose** — one §5.2 implementation, shared | **PASS.** `phase1_ci_coverage.py:36` — `from phase1_prereg_analysis import fwd`; line 85 calls `fwd()` with rule-1/rule-2 semantics. **The old `if p12 and p1 and pa and pb` survivorship gate is gone.** No second implementation exists; the two scripts cannot drift apart again. Corrected table published with prediction and outcome side by side. |
| 2 | **F1 closed by code, not by choice** | **PASS.** The script *prints* the selected method and its distance (above). Dossier §3.4 carries the ratified rule verbatim, including *"select on calibration, NOT on narrowness."* `iid_perc` and `mb_L12` are pre-registered as **reported, non-gating** arms, and the script itself announces which method the two-sided reading *would* have selected — so both readings are visible in the frozen record and neither can be preferred after the seal. |
| 3 | **Stop condition honoured** | **PASS.** Selection did not flip; the freeze legitimately proceeded. |
| 4 | **F3 closed as an amendment** | **PASS.** `CSMP_PHASE0_CHARTER.md` carries a dated *"Amendment — §6 Approval precondition (2026-07-12, Phase-2 F3)"* with **all four controls** verbatim; §10 row 3 matches. **`grep` for "satisfied-in-substance" / "epistemic condition" across the dossier returns 0.** The framing is deleted, not softened. |
| 5 | **Record correction landed** | **PASS.** `grep` for "selected against power" in the dossier returns **0**. §3.4 now states Student-t is the **lowest-power valid candidate** (0.397, vs `iid_perc` 0.416 and stationary 0.452), chosen on one-sided calibration; the F1 ambiguity and the previously-omitted `iid_perc` foil are disclosed. **No triumphant framing was restored.** |
| 6 | **Nothing out of scope moved** | **PASS.** Every dossier hunk is in scope: status, date, §1.1 D-i row, §3.4 (rule + coverage table + record correction), §10 row 3, §13 Sources, footer. The analytic power table, the decay table, K=40, the cost model, and decision-table rows 1 / 2 / 4 are **byte-unchanged**. |
| 7 | **Diff scope** | **PASS.** Exactly three files: the dossier, `phase1_ci_coverage.py`, the charter. **0 `core/` diffs.** |
| 8 | **Determinism + fence** | **PASS.** Seed `20260711`; `assert max(d) <= DEV_END, "SEALED LEAK"` intact with `DEV_END = 2022-12-31`; output prints `sealed-fenced <= 2022-12-31`. **No sealed-window read.** |

---

## 3. The out-of-scope defect — flagged, not hidden; now closed

`scripts/csmp/build_devtruncated_store.py` pinned `CANON_COVERAGE = ["0.957", "0.049", "0.398", "0.811", "0.129"]` — a self-check asserting the coverage script's output. **Two of those five are pre-F2 values** (`0.398` → `0.397`, `0.811` → `0.809`). A rebuild of the truncated store for the Phase-6 handoff would therefore have **failed its own self-check against a perfectly correct store** — a false FAIL on a landmine that detonates precisely when it is most load-bearing.

**DeepSeek was right to leave it.** Criterion 7 fenced the diff to three files, and silently widening a scope-fenced diff is exactly the behaviour that makes a freeze untrustworthy. **Flagging it to the operator instead of quietly fixing it is the correct instinct, and it is recorded here as such.**

**Closed by the Lead Reviewer** — constants synced to `0.397` / `0.809`, with the pre-F2 values retained in a comment. This touches **no** query, filter, schema, or construct parameter — only expected-output strings in a handoff verification tool. **It is not a construct change and does not breach the freeze fence**, which binds the universe, score, K, metric, baselines, cost model, §5.2, and the inference/extension design.

---

## 4. Verdict

**PASS. `CSMP_PHASE1_RESEARCH_DOSSIER.md` is FROZEN at Rev 7 (2026-07-12), and the construct fence is now immutable.**

Any change to the universe, score, holding rule (K=40), metric, baselines, cost model, §5.2 delisting convention, or inference/extension design requires **a new pre-registration for a new increment — not an edit.**

**What the pre-registration now survives that it did not four days ago:** a gate whose confidence interval under-covered by 4×; an extension schedule whose family-wise Type-I equalled the bug it replaced; a selection rule that named no metric and pointed at two different gates; a survivorship bug living inside the very script that chose the gate; and a governance escape hatch dressed as a definition. **Every one of those was found and closed while the window was still sealed** — which is the only time any of them could be fixed for free.

The remaining honest statement stands unchanged, and it is the most important line in the document: **a valid, one-sided, correctly-covered test on 42 months is ~41% powered against the program's own point estimate, so "Inconclusive" is the single likeliest outcome even if the hypothesis is exactly true.** That was computed before the window was spent, not after.

**Next: Phase 6 — the single sealed read (2023-01 → 2026-06), subject to the §8 A1 VOID precondition. The window has not been read.**
