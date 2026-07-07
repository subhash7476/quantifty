# MSRP Phase 6 — The Single Held-Out Scoring Run (Design / Spec)

**Document type:** Design specification (brainstorming output). Precedes the
implementation plan. Not a results report — nothing here records a held-out number.

**Date:** 2026-07-07

**Predecessors (all FROZEN / CERTIFIED):**
- `docs/reports/MSRP_PHASE1_RESEARCH_DOSSIER.md` — the frozen pre-registration
  (commit `d9233b1`): §3 head-to-head, §3.4 decision rule, §9 domain→method map,
  §10 post-experiment decision table, §1.1 reproducibility substrate.
- `docs/implementation/msrp/reports/MSRP_PHASE5A_CERTIFICATION.md` — the certified
  `ForwardVolatilityArtifact` (frozen HAR-RV+VIX coefficients).
- `docs/implementation/msrp/reports/MSRP_PHASE5B_CERTIFICATION.md` — the certified
  A2 `ValidationHarness` + `run_forward_vol_validation.py` runner (`--phase 6`
  mode + duplicate guard).

**Governing memory:** Phase 6 authorized by Phase 5B ("Phase 6 held-out run
authorized"). Held-out window **2026-01-01 → 2026-07-03**.

---

## 1. Framing — What Phase 6 Is and Is Not

Phase 6 **chooses nothing**. The model, label, feature set, metric, decision rule,
and bootstrap methodology were all fixed in the Phase-1 dossier and the machinery
certified in 5A/5B. Phase 6 is a **governed execution**: run the certified harness
**exactly once** on the sealed window, and record the verdict faithfully — Approved
*or* falsified. No tuning, no re-run, no second look.

The single non-negotiable invariant:

> **The held-out window (2026-01-01 → 2026-07-03) is touched exactly once — in
> Stage 2, by the official `--phase 6` run.** Every pre-flight check, rehearsal, and
> the `L` derivation operate on dev / synthetic data only. If any step would read the
> held-out window before Stage 2, it is wrong by construction.

This is not a build. No production code changes. No new harness capability. No new
research freedom. The deliverables are: one sealed validation record, one execution
attestation (review), one Phase-6 report + certification, and a KB sync + tag.

---

## 2. Open Precondition to Close First — Pinning the Block Length `L`

Dossier §1.1 requires the moving-block-bootstrap block length `L` to be **pinned from
dev-window RV autocorrelation, never held-out**. The 5B certification is explicit that
the runner's `--block-length 10` is a **placeholder only — "must be the dev-derived
value."** So `L` is **not yet pinned**. Closing this is the first Phase-6 act.

**Pre-registered derivation rule (fixed here, before the number is known):**

1. Compute the dev-window daily realized-volatility series `RV_t` (dossier §5:
   `sqrt(Σ_k r_{t,k}²)` from 1m Nifty-50 log returns) over the dev window
   **2023-01-02 → 2025-12-31** only.
2. Compute the sample autocorrelation function (ACF) of that `RV_t` series.
3. **`L` = the smallest lag `k ≥ 1` at which `|ACF(k)|` first falls below the
   significance band `1.96 / sqrt(n_dev)`** (the standard white-noise band). Pin that
   `k`.
4. **Fallback (bounded, records an override):** if *no* lag `k` within the computed
   ACF satisfies the condition — possible for a long-memory series, though unlikely at
   `n_dev ≈ 740` — pin `L = floor(n_dev / 20)` (≈ 37, ~5% of the sample) and record the
   override in the pre-flight note. This fallback is conservative in the safe
   direction: a longer block yields fewer effective blocks → a *wider* CI → a *harder*
   approval bar, so it cannot manufacture a false Approved verdict.
5. Record the full ACF table and the derivation (or the fallback override) in the
   pre-flight note. Pin `B = 10000`, `seed = 42`.

The **derivation is the pre-registered act, not the number**: whatever `k` the dev
data yields is pinned as-is (the dossier's "e.g. 10" is illustrative). If the ACF
decorrelates at lag 12, `L = 12`. This is exactly what §1.1 reserved this computation
for. `B` and `seed` are administratively pinned (the seed only needs to be fixed; `B`
follows the dossier's stated 10,000).

`RV_t` here is the raw (not log) daily series of §5 — the literal "RV autocorrelation"
the dossier names, and the persistence structure the block bootstrap must preserve.

---

## 3. Stage 1 — Pre-Flight (seal untouched)

All Stage-1 steps read **dev / synthetic** data only.

| # | Step | Purpose | Touches held-out? |
|---|------|---------|-------------------|
| 1.1 | Derive & pin `L` (§2) | Close the §1.1 open precondition | **No** — dev only |
| 1.2 | Seal-integrity check | No pre-existing `--phase 6` record (duplicate guard clean); confirm `core/msi/validations/` has no Phase-6 window record | No — inspects output dir |
| 1.3 | Provenance check | Artifact dir + harness at their certified commits; `checksum.sha256` combined hash matches; data snapshot present & hashable through 2026-07-03 | No — reads dev+meta |
| 1.4 | Dev-window rehearsal | Run the full runner `--phase 5B` on a **dev** window end-to-end; confirm it seals a sane record and the numbers are sensible (in-sample `ΔAUC_gate` comfortably > 0). Smoke test of wiring — **not** a decision input | **No** — dev window |
| 1.5 | Go/no-go gate | Present pinned substrate (`L`,`B`,`seed`), the exact staged official command, and rehearsal evidence for operator confirmation | No |

**Rehearsal note.** The rehearsal uses `--phase 5B` deliberately so it cannot write a
Phase-6 record and cannot trip (or satisfy) the Phase-6 duplicate guard. Its output is
inspected for sanity, then may be discarded; it is never cited as a result.

**Gate output.** Stage 1 ends at an explicit operator go/no-go. Nothing proceeds to
Stage 2 without confirmation.

---

## 4. Stage 2 — The Official Run (one shot)

A single command, run once:

```
python scripts/msrp/run_forward_vol_validation.py \
    --phase 6 \
    --window-start 2026-01-01 --window-end 2026-07-03 \
    --block-length <L_dev> --replicates 10000 --seed 42
```

The harness (certified 5B) then, deterministically:
- scores the candidate, fixture gate, and raw-VIX reference against `Y` over the
  held-out window;
- resolves all seven MSI-006 domains (Architectural, Scientific, Temporal, Robustness,
  Reproducibility, Operational, Calibration);
- applies the §3.4 decision rule (`ΔAUC_gate ≥ 0.03` **and** 95% MBB CI excludes 0);
- writes the sealed record directory under `core/msi/validations/<validation_id>/`
  with `reviewer=None, approval_status=None`.

The Phase-6 duplicate guard makes a second official run over the same window a hard
error — the machine enforces single-touch.

---

## 5. Stage 3 — Governance (full cycle, matching prior phases)

### 5.1 Independent review — an *execution attestation* (narrow scope)
No code changed, no harness altered, no research freedom exercised — so the review is
**not** a code review. It attests that the run executed faithfully. It verifies:

1. The sealed record's `evaluation_window` is exactly `[2026-01-01, 2026-07-03]`.
2. The Phase-6 duplicate guard was in force (single-touch upheld); exactly one Phase-6
   record exists **for the window `[2026-01-01, 2026-07-03]`**. (The guard is
   window-scoped: a future Phase-6 run on a *different* window — e.g. an extended
   held-out per §10 row 2 — is legitimate and does not violate this criterion.)
3. The pinned substrate in `methodology.json` matches the §2 pinned values (`L`, `B`,
   `seed`) and the derivation note.
4. All **seven** domains resolved, and each resolved *faithfully* (values consistent
   with the harness contract; no domain silently skipped or defaulted).
5. The machine `candidate_verdict` maps correctly to the dossier **§10 decision
   table** row for the observed `ΔAUC_gate` + CI.
6. Determinism spot-check: the record's `results_digest` is the byte-identical value the
   harness's own reproducibility domain asserts (no separate held-out re-run — the
   harness already carries the reproducibility guarantee).

**Re-sealing on PASS.** The runner already sealed the record at Stage 2 with
`reviewer=None, approval_status=None` — the `checksum.sha256` combined hash covers
`record.json`, which carries those two fields. Hand-editing them would break the seal.
So attestation is applied by **re-invoking `write_sealed_record(record, VALIDATIONS_DIR,
reviewer=<name>, approval_status="approved"|..., timestamp_iso=<run timestamp>)`**,
which overwrites all four files and recomputes the checksum consistently. Because
`validation_id` is content-addressed over inputs (excluding results and attestation)
and `results_digest` is over results only, **both are invariant under the re-seal** —
the record's identity and its scientific numbers are unchanged; only `reviewer`,
`approval_status`, and the combined hash update. The original run `timestamp` is
preserved by passing it back in. This is a *re-seal after attestation*, not a first
seal.

### 5.2 Phase-6 report + certification
Author `docs/implementation/msrp/reports/MSRP_PHASE6_*` recording: the pinned substrate
+ `L` derivation; `ΔAUC_gate`, its 95% CI, `ΔAUC_vix` + CI, held-out base rate + run
structure, calibration coverage, the pinned sub-period split; the seven-domain
pass/fail; the §10-mapped verdict and next action; and the execution attestation
result. Written **regardless of outcome**.

### 5.3 KB sync + tag
Update `docs/PROJECT_STATE.md` (new Completed entry) and `docs/CHANGELOG_PLATFORM.md`;
tag `msrp-phase6-*`. Follows the KB-sync discipline (docs kept in sync as work lands).

---

## 6. Every Outcome Is Pre-Decided (dossier §10)

The report handles whichever row lands — all four are legitimate, reportable
endpoints. **No outcome triggers a re-run or a tune.**

| Observed `ΔAUC_gate` | Verdict | Next action (recorded, not decided now) |
|---|---|---|
| `≥ 0.03` **and** CI excludes 0 | **Approved** | Phase 7 (first alpha consuming this Knowledge). Record whether `ΔAUC_vix > 0` (claim §2.1 substantiated) or `≤ 0` (beats fixture bucket only). |
| `≥ 0.03` **but** CI includes 0 | **Inconclusive (underpowered)** | Not Approved. No tuning. Re-evaluate under the *same* rule only when held-out extends with more data. |
| `0 < ΔAUC_gate < 0.03` | **Weak, below bar** | Not Approved. Record as weak edge. Enrichment = a *new* pre-registration (increment 2). |
| `≤ 0` | **Falsified** | H₀ not rejected; HAR-over-fixture rejected for this model form. Engineering deliverable still stands. |

An "inconclusive" verdict is an **expected, non-failing** outcome given the short
(~120-trading-day) autocorrelated held-out window — not a disappointment to explain
away (dossier §11).

---

## 7. Deliverables

| Deliverable | Location |
|---|---|
| Pinned-substrate / `L`-derivation note | folded into the Phase-6 report (or a short pre-flight note) |
| Sealed validation record | `core/msi/validations/<validation_id>/` |
| Execution attestation (review) | `docs/implementation/msrp/reports/MSRP_PHASE6_REVIEW.md` |
| Phase-6 report + certification | `docs/implementation/msrp/reports/MSRP_PHASE6_*` |
| KB sync | `docs/PROJECT_STATE.md`, `docs/CHANGELOG_PLATFORM.md` |
| Tag | `msrp-phase6-*` |

## 8. Non-Goals / Out of Scope

- No changes to any frozen component (artifact, harness, DRA, execution platform).
- No new harness capability, no new metric, no alternative construct.
- No re-run, no threshold tuning, no feature addition under **any** verdict.
- No Phase 7 work (alpha strategy) — only *authorized* by an Approved verdict, not
  started here.

## 9. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Accidental early read of the held-out seal | Every Stage-1 step is dev/synthetic; rehearsal uses `--phase 5B`; the official window appears only in the Stage-2 command. |
| `L` chosen with any hindsight | `L` derived by the fixed §2 rule on dev data before Stage 2; derivation recorded. |
| Second official run / duplicate | Machine-enforced Phase-6 duplicate guard; review verifies exactly one record. |
| Verdict re-interpreted favorably | §10 table is pre-committed; review attests the machine verdict maps to the correct row. |
| Silent domain skip / default | Review checks all seven domains resolved faithfully. |
