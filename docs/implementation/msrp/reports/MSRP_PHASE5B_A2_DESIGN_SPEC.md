# MSRP Phase 5B — A2 Validation Harness — Design Specification

**Document type:** Design specification (Phase 5B of the Market State Research Program).

**Subject:** The minimal MSI-006 **A2 Validation Harness** that validates the certified
`ForwardVolatilityArtifact` (`PublishedArtifact v2`) and produces one immutable
validation record with a resolvable `validation_id`.

**Date:** 2026-07-06

**Status:** **IMPLEMENTED — CERTIFIED (2026-07-06).** See
`scripts/msrp/run_forward_vol_validation.py` for the composition root and
`tests/msi/msrp/test_forward_vol_validation.py` for verification.

**Governing inputs (frozen, cited, not re-derived):**
- `docs/reports/MSRP_PHASE1_RESEARCH_DOSSIER.md` — the frozen pre-registration (commit `d9233b1`); §3 head-to-head, §9 domain→method mapping, §10 decision table, §1.1 reproducibility substrate.
- `docs/architecture/market_state_intelligence/MSI_006_VALIDATION_FRAMEWORK.md` — v1.0 Frozen; the seven validation domains (§6), validation evidence (§7), outcomes (§9), acceptance (§10), and MSI-6D-05 (sole owner of the Validation Identifier).
- `docs/implementation/msrp/reports/MSRP_PHASE5A_CERTIFICATION.md` — the certified artifact under validation, including the **F1 finding** (evidence rules declare non-identity transforms the certified identity-only builder rejects).
- MSI v1.0 certified components: `FilesystemArtifactLoader` (M2), `DuckDBObservationReader` (M3), `DefaultEvidenceBuilder` (M4), `DefaultArtifactEvaluator`/`DefaultKnowledgeBuilder` (M5); MM13 §4 consumer contract.

---

## 1. Purpose & Boundary

The A2 Validation Harness is a **deterministic** procedure that reads the **frozen**
`ForwardVolatilityArtifact`, evaluates it against the **seven MSI-006 domains** over an
**explicitly-passed evaluation window**, and assembles **one checksum-sealed, immutable
validation record** resolvable by a `validation_id` that MSI-006 alone mints (MSI-6D-05).

The harness **invents no research decisions**. Every model coefficient, the label `Y`, the
ROC-AUC metric, the `ΔAUC_gate ≥ 0.03` ∧ CI-excludes-0 decision rule, the moving-block
bootstrap, and the §9 domain→method mapping are already frozen by the Phase-1 dossier. The
harness *executes* the pre-registration; it does not extend or tune it.

**Phase boundary (locked).** Phase 5B **builds and verifies** the harness on **dev-window +
synthetic/fixture data only**. The harness is **never pointed at the sealed held-out window
(2026-01-01 → 2026-07-03) in Phase 5B.** The single held-out scoring run — the dossier's
"touched exactly once, at Phase 6" invariant — is a **distinct, separately-authorized Phase 6
act**. This specification defines the harness such that both phases are served by the same
code with the evaluation window supplied by the caller.

---

## 2. Components & Code Layout

| Path | Role |
|------|------|
| `core/msi/msrp/validation.py` | `ValidationHarness` — shared immutable execution state + seven domain methods + conjunctive aggregator + record assembly + `validation_id` minting + `results_digest`. |
| `scripts/msrp/run_forward_vol_validation.py` | Phase-6 composition root — wires the certified loader/reader + offline evidence path + pinned substrate, supplies the evaluation window and `phase`, enforces the Phase-6 duplicate guardrail (§7), writes the sealed record directory. In Phase 5B this script is exercised **only** on dev/synthetic windows. |
| `core/msi/validations/<validation_id>/` | Sealed output: `record.json`, `methodology.json`, `results.json`, `checksum.sha256`. Created at Phase 6; git-committed; immutable. |
| `tests/msi/msrp/test_forward_vol_validation.py` | Phase-5B verification: every domain method, the aggregator, `validation_id` determinism, `results_digest` determinism, the duplicate guardrail — all on dev/synthetic + fixtures. |

### 2.1 Certified-component reuse (and its one qualified boundary)

The harness **reuses** certified MSI v1.0 components rather than reimplementing them:

- `FilesystemArtifactLoader` (M2) — load + checksum-verify the frozen artifact.
- `DuckDBObservationReader` (M3) — read raw point-in-time observations (1m `NSE_INDEX|Nifty 50` closes; 1d `NSE_INDEX|India VIX` close) over the evaluation window.
  - **One-extra-day load (label boundary).** The label `Y_t = 1[RV_{t+1} > M_t]` consumes
    `RV` from the *next* trading day, so scoring day `t` requires `t+1` data. The reader
    therefore loads **one trading day beyond the evaluation-window end** when the snapshot
    provides it. If the snapshot ends at the window end (as the 2026-07-03 held-out snapshot
    does), the final window day has no available `t+1` and is **explicitly dropped and
    recorded** — never silently. The Temporal domain (§4.3) records both the requested window
    and the set of scored days, so any boundary drop is auditable from the record.

**Qualified boundary — evidence construction (Phase-5A F1).** The certified
`DefaultEvidenceBuilder` (M4) is **identity-only**. This artifact's `evidence_rules` declare
**log (non-identity) transforms** on the HAR features, so end-to-end evidence-building
through the certified builder is **not applicable** to this artifact (Phase-5A finding F1,
documented as Phase-6 offline research tooling + boundary-tested). Evidence is therefore
constructed by the **Phase-6 offline research path** — the same HAR/log feature construction
the A1 authoring module (`core/msi/msrp/forward_vol.py`) already realizes — and then handed
to the artifact. The certified builder remains the reference for identity-transform
artifacts; it is intentionally bypassed here, and the bypass is the direct consequence of the
frozen artifact's evidence rules, not a harness design liberty.

### 2.2 Scientific-domain evaluation path — direct, not the DRA wrapper

The Scientific domain requires a **clean per-observation raw-prediction vector** across the
evaluation window to compute the MSI-006 statistical metrics (AUC, ΔAUC, bootstrap CI). It
therefore calls:

```
artifact.evaluate(evidence)  →  Estimate("expected_next_day_realized_vol").value
```

**directly**, per trading day, and reads the `Estimate.value` as `s^{cand}_t`. This is a
**direct evaluation path**. It is deliberately **not** the full DRA
`DefaultArtifactEvaluator` → `DefaultKnowledgeBuilder` execution path, which wraps
`evaluate()` inside:

```
EvidenceBuilder → ArtifactEvaluator → KnowledgeBuilder → KnowledgeObject
```

The DRA wrapper produces provenance-bearing `KnowledgeObject`s (the runtime knowledge-
production contract, proven by MM13) — the right shape for strategy consumption, but the
wrong shape for a per-day score vector: it emits one knowledge object per evaluation with
knowledge_id/provenance overhead and no aggregate scoring surface. The Scientific domain
needs the raw scalar estimate, so it takes the direct path. The certified **loader** and
**observation reader** are still reused (§2.1); only the knowledge-production wrapper is
bypassed, and only for statistical scoring.

---

## 3. Execution Structure — `ValidationHarness`

The seven domains have materially different input requirements (some need only the loaded
artifact; some need the full per-day score vectors; some need the pinned substrate). Forcing
a uniform standalone-function signature would drag a six-item parameter bundle through every
call. Instead the domains are **methods on a `ValidationHarness` class** that holds the
**shared immutable execution state** once:

```
ValidationHarness(
    artifact,             # loaded, checksum-verified PublishedArtifact (frozen)
    methodology,          # immutable: the §1.1 reproducibility substrate (seed, block length
                          #   L, replicate count B, lib versions, snapshot hash, commit,
                          #   harness_version) + label + decision-rule params. §8 lists it.
    dataset,              # resolved observations over the evaluation window (immutable)
    evidence,             # per-day constructed Evidence (offline path, §2.1) (immutable)
    evaluation_window,    # explicit (start, end); NEVER hardcoded
    phase,                # "5B" | "6"  (§7)
)
```

- Construction is once; all attributes are **immutable** (frozen dataclass / read-only). No
  method mutates shared state; every domain method is **side-effect-free** and returns a
  typed `DomainResult(status, evidence: dict)`.
- Each domain is a method `_evaluate_<domain>() -> DomainResult`, independently callable on a
  constructed harness — preserving 1:1 MSI-006 §6 mapping **and** per-domain testability
  (construct with fixture state, call one method).
- A single `run() -> ValidationRecord` aggregator invokes all seven, applies the **MSI-006
  §10 conjunctive (non-compensatory) rule**, derives the **candidate verdict** per the §10
  decision table, and assembles the record (§5). It does **not** seal the record or write the
  reviewer/final `approval_status` — that is the Phase-6 review's act (§6).

This is a *refinement* of the earlier "seven explicit domain functions + one aggregator"
decision — same explicit 1:1 mapping, no abstraction/registry framework — with shared state
owned by the object instead of threaded through signatures.

---

## 4. The Seven Domain Methods

Each returns `DomainResult(status ∈ {PASS, FAIL, REPORTED}, evidence: dict)`. `REPORTED`
denotes an informational, non-gating domain output (e.g. sub-period split) that carries no
pass/fail weight but is recorded.

1. **Architectural** — load the artifact via `FilesystemArtifactLoader` and checksum-verify;
   assert MSI-007 shape (metadata + evidence_rules + model + provenance + checksum) and that
   `evaluate()` emits the named estimate `expected_next_day_realized_vol` with
   `uncertainty ≥ 0`, per the MM13 §4 consumer contract. Evidence: loader success, estimate
   name/dimension, uncertainty sign.
2. **Scientific** — the dossier §3 head-to-head over the evaluation window: per day form
   `s^{cand}_t` (direct `evaluate()`, §2.2), `s^{fix}_t`, `s^{vix}_t`, and `Y_t`; compute the
   three AUCs, `ΔAUC_gate`, `ΔAUC_vix`. **Score construction (no dossier cross-reference
   needed):**
   - `s^{cand}_t` = the artifact's `expected_next_day_realized_vol` estimate value (§2.2).
   - `s^{fix}_t` = the pre-registered gate's discrete `market_regime` ∈ {0,1,2}, computed
     **directly** as `0` if `VIX_t < 15`, `1` if `15 ≤ VIX_t < 25`, `2` if `VIX_t ≥ 25`
     (higher regime ⇒ higher-vol state; used directly as the discriminant score, dossier §3.2).
     **The harness hardcodes these thresholds; it does NOT load the
     `tests/msi/fixtures/test_artifact/` fixture** — a production `core/` module must not
     depend on a `tests/` path, and the thresholds (15/25) are the fixture's entire behavior,
     frozen by the dossier. Hardcoding is behaviorally identical to and faithful to the
     certified gate.
   - `s^{vix}_t` = raw continuous `VIX_t` (secondary reference; reported, not gated).
   - `Y_t = 1[RV_{t+1} > M_t]`, where `M_t` is the trailing-20-trading-day median RV (dossier
     §3.1); requires the `t+1` data handled at §2.1.

   **CI ownership.** The 95% moving-block-bootstrap CI on `ΔAUC_gate` is a **pure deterministic
   function** of `(per-day scores, Y, L, B, seed)` — all immutable harness state — factored
   into a private `_delta_auc_ci()` helper. **Domain 2 owns the gate verdict:** it applies the
   §3.4 rule to the `ΔAUC_gate` point estimate + this CI. Domain 4 (§4.4) re-invokes the same
   pure helper and re-reports the identical CI (`REPORTED`, never gates). Because both derive
   the CI from the same immutable inputs — not from each other's outputs — each domain stays
   independently callable, and the helper's determinism guarantees byte-identical CIs.

   **Status = PASS iff** `ΔAUC_gate ≥ 0.03` **and** that CI excludes 0 (§3.4). Evidence: the
   three AUCs, both ΔAUC, CI bounds, base rate.
3. **Temporal** — point-in-time / no-leak audit: assert features and target use only data
   `≤ t`; assert the target-clamp invariant (`t+1 ≤ dev_end` during fit — inherited from the
   frozen artifact's fit protocol); record the exact evaluation window scored, so any held-out
   touch is auditable from the record. Evidence: clamp assertion, feature-lag assertion,
   recorded window.
4. **Robustness** — **re-reports** the 95% moving-block-bootstrap CI on `ΔAUC_gate` from the
   shared `_delta_auc_ci()` helper (§4.2 — `REPORTED`, never gates; block length `L` pinned
   from **dev-window** RV autocorrelation, never held-out); the held-out base rate `mean(Y)`
   and its run-structure; and one **pinned** sub-period split. **Sub-period split (pinned
   here, pre-registration):** the evaluation window is split **chronologically into first-half
   vs second-half by trading-day count**, cut at `floor(n_days / 2)` (the earlier half takes
   the extra day when `n_days` is odd); `ΔAUC_gate` is reported for each half. This removes
   the split as an operator degree of freedom; it is `REPORTED`-only and can never move the
   gate regardless. Evidence: CI, base rate, run structure, per-half sub-period `ΔAUC_gate`.
5. **Reproducibility** — pin and record the §1.1 substrate (block length `L`, replicate count
   `B`, seed, library versions, data-snapshot hash, commit hash); verify determinism in **two
   layers**:
   - **In-domain (safe, no recursion):** re-invoke the **pure scoring function** `_score()`
     (evidence → per-day scores → AUCs → `ΔAUC` → CI → scientific outputs) a second time from
     the same immutable evidence and assert **byte-identical `results_digest`** (§5.2). Domain 5
     does **not** call `run()` here — `run()` invokes Domain 5, so a full re-run would recurse;
     the check operates on `_score()`, which excludes the domain-aggregation layer.
   - **Test-suite (full, out-of-run):** the Phase-5B suite constructs **two independent
     `ValidationHarness` instances** from identical raw inputs, calls `run()` on each, and
     asserts identical `results_digest` — exercising constructor + offline-evidence-build
     determinism end-to-end (no recursion, because it runs outside `run()`).

   Evidence: substrate, in-domain `_score()` double-invocation equality (the test-suite
   two-instance check is recorded as a Phase-5B verification artifact, not a runtime field).
6. **Operational** — `evaluate()` is deterministic and side-effect-free: repeated evaluation
   on identical evidence yields an identical `MarketState`; execution timing recorded.
   Evidence: repeated-eval equality, timing.
7. **Calibration** — empirical coverage of the state-dependent prediction interval vs. its
   nominal level within the pre-stated tolerance (Phase-2 finding Mo2); measured on dev,
   reported once on held-out, never tuned. Evidence: nominal level, empirical coverage,
   tolerance, PASS/FAIL.

**Aggregation.** Verdict is **conjunctive** across mandatory domains (MSI-006 §10): any
mandatory `FAIL` ⇒ candidate verdict **Rejected**. `REPORTED` outputs never gate. The
candidate verdict maps the §3.4 outcome onto the §10 decision table.

---

## 5. Identity, Integrity, Reproducibility — Three Separate Mechanisms

The record carries three distinct, non-overlapping mechanisms. Keeping them separate is a
governance requirement, not an implementation detail.

| Mechanism | Question it answers | Field | Preimage / scope |
|---|---|---|---|
| **Identity** | *Which governed validation execution is this?* | `validation_id` | §5.1 preimage (inputs + harness_version) |
| **Reproducibility** | *Did the scientific outputs reproduce byte-for-byte?* | `results_digest` | §5.2 scientific outputs only |
| **Integrity** | *Has the stored record been altered?* | `checksum.sha256` | Entire record: `record.json` + `methodology.json` + `results.json` |

### 5.1 `validation_id` derivation

`validation_id = SHA-256(` canonical-JSON of `)`:

```
{
    artifact_version,          # frozen artifact version string
    artifact_checksum,         # the artifact's combined SHA-256 (from its checksum.sha256)
    dataset_snapshot_hash,     # §5.1a — hash of exactly the source candle files read
    methodology_fingerprint,   # §5.1b — SHA-256 of the substrate + label + decision-rule
                               #   params, EXCLUDING harness_version (single-owned below)
    harness_version            # semantic version of the ValidationHarness implementation;
                               #   the sole field that owns the version change (§5.1c)
}
```

`validation_id` identifies the **governed validation execution** — *which* artifact, over
*which* data snapshot, under *which* methodology, run by *which* harness version. It is
**content-addressed over inputs, not outputs.**

- **`results_digest` is deliberately excluded** from the preimage. Including it would let a
  bug-fix re-run on identical inputs mint a *different* `validation_id` even though the
  governed execution contract never changed — identity drift driven by output. Integrity of
  the specific results is handled by `checksum.sha256`; reproducibility of results is proven
  by the Domain-5 double-run. The id's job is identity alone.
- **`harness_version` is included exactly once (§5.1c)** so that any change to the harness's
  governed behavior yields a new execution identity. **Governance obligation:**
  `harness_version` **MUST be bumped on any behavior-affecting change** to the harness. If it
  is not, two genuinely different harness behaviors could share one `validation_id`.
  **Trust boundary (explicit):** this is a *process obligation with no technical guard* — no
  CI check enforces the bump. At this scale that is acceptable: the worst-case failure mode is
  modest (two behaviors share one `validation_id`) and is caught by the standard Phase-6
  governance review, not by tooling. The spec states the guarantee's limit rather than
  implying an enforcement that does not exist.
- Wall-clock `timestamp` and `reviewer` live **in `record.json`** but are **excluded from the
  preimage**, so a deterministic re-run on identical inputs mints a **byte-identical
  `validation_id`** (satisfies MSI-VF-003 deterministic replay).
- MSI-006 is the **sole minter** (MSI-6D-05). No other component derives a `validation_id`.

**§5.1a — `dataset_snapshot_hash` (concrete definition).** SHA-256 over a canonical manifest of
**exactly the source candle files the harness reads** — not the whole data directory (hashing
unrelated instruments would make the identity brittle). The file set is: the per-trading-day
1m `NSE_INDEX|Nifty 50` candle DuckDBs and the 1d `NSE_INDEX|India VIX` DuckDBs spanning
dev + held-out (including the one-extra-day boundary file, §2.1). The manifest is the lines
`"<repo-relative-path>:<per-file-sha256>\n"` sorted ascending by path; `dataset_snapshot_hash`
= SHA-256 of that concatenated string. Deterministic and scoped to actual inputs.

**Binary-stability caveat.** The hash is over the **specific binary snapshot files as frozen**,
not over logical content. DuckDB files can differ at the byte level for identical logical data
(internal metadata, page/compaction state, WAL), so *re-creating* the snapshot from source —
rather than copying the exact frozen files byte-for-byte — can change `dataset_snapshot_hash`
and therefore the `validation_id`. For the single Phase-6 run this is a non-issue: the snapshot
files are frozen and the official run reads exactly those bytes. Cross-machine reproducibility
testing must therefore copy the *same binary files*, not regenerate them; regeneration is a new
data snapshot by definition and correctly mints a new identity.

**§5.1b — `methodology_fingerprint` (excludes `harness_version`).**
`methodology_fingerprint = SHA-256(` canonical-JSON of `{ substrate_without_harness_version,
label_params, decision_rule_params }` `)`. `harness_version` is **deliberately excluded** here
because it is single-owned as its own preimage field (§5.1c). This removes the double-count
where a version bump would otherwise change the id twice (once inside the fingerprint, once
directly) and makes it unambiguous which field owns a version change. `harness_version`
remains recorded in `methodology.json` for provenance; it is simply not hashed into the
fingerprint.

**§5.1c — version ownership.** `harness_version` is the **single** preimage field that changes
when harness behavior changes. No other preimage field encodes it.

### 5.2 `results_digest` definition

`results_digest` is a **deterministic hash of the scientific outputs** in `results.json`. It
fingerprints *what the science produced*; it does not identify the execution and does not
seal the file.

- **Serialization:** canonical JSON (sorted keys), **fixed-precision float formatting to 6
  decimal places** (cross-platform-deterministic; ample resolution against the `ΔAUC ≥ 0.03`
  bar). Digest = SHA-256 of that canonical string.
- **Included fields:** evaluation window; the seven domain verdicts; candidate AUC; fixture
  AUC; VIX AUC; `ΔAUC_gate`; `ΔAUC_vix`; the 95% CI bounds (lower, upper); held-out base rate.
- **Excluded fields:** raw per-day predictions (their information is fully carried by the AUC
  aggregates, which are functions of them); timestamps; reviewer information; any other
  non-deterministic metadata.
- **Consumer:** the Domain-5 (Reproducibility) double-run compares `results_digest` for
  byte-identity across two independent runs on identical inputs.

### 5.3 `checksum.sha256`

Seals the **entire** validation record — `record.json`, `methodology.json`, `results.json` —
per-file SHA-256 plus a combined hash, mirroring the MSI-007 artifact idiom. Any post-seal
edit to any record file breaks the checksum. This is the tamper-evidence layer;
`results_digest` (scientific fingerprint) and `validation_id` (execution identity) are
orthogonal to it.

---

## 6. Verdict Flow

The harness computes all seven `DomainResult`s and a **candidate** conjunctive verdict per the
pre-registered §10 decision table. The record directory is authored in two steps but sealed
once:

1. **Harness (mechanical):** writes `results.json` (scientific outputs + `results_digest`),
   `methodology.json` (pinned substrate + harness_version + params), and a `record.json`
   carrying the candidate verdict, `phase`, `validation_id`, and the §7 fields **except**
   final `reviewer` and final `approval_status` — which remain unset/`candidate`. At this
   point the record is **unsealed**.
2. **Phase-6 independent review (attestation):** the standard MSRP independent technical
   review attests harness conformance, writes `reviewer` and the final `approval_status`
   (**Rejected** / **Provisionally Approved** / **Approved**, MSI-006 §9), and only then is
   `checksum.sha256` computed and the record **sealed** + committed.

This preserves the program's per-phase certification cadence and satisfies MSI-006 §7's
`reviewer` field without discarding the pre-registered mechanical decision table.

---

## 7. Phase Guardrail (auditability over code locks)

The design philosophy remains **auditability over code locks** — no hard-coded protection of
the held-out window. The evaluation window is always an explicit caller parameter (§3).

Two lightweight, auditable guardrails:

- **`phase` field.** Every validation record records `phase = "5B" | "6"`. Phase-5B
  verification records are `phase = "5B"`; the official held-out validation is `phase = "6"`.
- **Phase-6 duplicate-execution check.** Before executing the official validation, the Phase-6
  composition root (`run_forward_vol_validation.py`) scans existing
  `core/msi/validations/*/record.json` and **refuses to run** if any record already exists
  with `phase == "6"` **and** an identical held-out `evaluation_window`. This prevents
  *accidental duplicate* Phase-6 execution — it is a process guardrail, **not** a security
  control.

Together with each record storing the exact window it scored (Domain 3), the dossier's
"touched exactly once, at Phase 6" invariant is **auditable from the record set itself**.

---

## 8. Reproducibility Substrate (§1.1 — pinned at A2 build)

Recorded in `methodology.json` and required for deterministic replay (MSI-VF-003). All rows
except `harness_version` are hashed into `methodology_fingerprint` (§5.1b); `harness_version`
is recorded here for provenance but hashed into the `validation_id` via its own preimage field
(§5.1c), not into the fingerprint:

| Field | Source of the pin | In `methodology_fingerprint`? |
|---|---|---|
| Python version | build environment | yes |
| numpy / pandas / statsmodels / scikit-learn versions | build environment | yes |
| Moving-block-bootstrap block length `L` | chosen from **dev-window** RV autocorrelation (never held-out) | yes |
| Bootstrap replicate count `B` | pinned at build (e.g. 10,000) | yes |
| Bootstrap RNG seed | single fixed integer | yes |
| Commit hash | the commit at which the harness runs | yes |
| Label + decision-rule params | dossier §3.1 / §3.4 (median window, `ΔAUC` bar) | yes |
| Calibration params (`nominal`, `tolerance`) | pinned (Mo2 acceptance check; §4.7) — e.g. `0.90` / `0.05` | yes |
| `harness_version` | semantic version of the `ValidationHarness` implementation | **no** — §5.1c |

(`dataset_snapshot_hash` is a distinct preimage field, defined at §5.1a, not part of the
substrate table.) The only stochastic element is the moving-block bootstrap; fully pinned by
the seed ⇒ the whole harness is deterministic given (artifact, data snapshot, substrate,
harness_version).

---

## 9. Testing Strategy (Phase 5B — off-window)

All Phase-5B tests use **dev-window + synthetic/fixture data only**; none read the sealed
held-out window. Coverage:

- Each of the seven domain methods on constructed fixture state (independent invocation).
- Aggregator conjunctive logic: mandatory `FAIL` ⇒ `Rejected`; `REPORTED` never gates.
- `validation_id` determinism: identical inputs + `harness_version` ⇒ byte-identical id;
  changing any preimage field ⇒ different id; changing `results`/timestamp/reviewer ⇒ **same**
  id.
- `results_digest` determinism: canonical-JSON + 6-decimal formatting stable across runs;
  in-domain `_score()` double-invocation equality **and** the full two-independent-instance
  `run()` equality check (Domain 5, both layers).
- Shared `_delta_auc_ci()` helper: Domain 2 and Domain 4 obtain byte-identical CIs from
  identical immutable inputs (independent callability preserved).
- Sub-period split: cut at `floor(n_days/2)`, earlier half takes the extra day when odd;
  `REPORTED`-only, never affects the aggregated verdict.
- `checksum.sha256` seal: post-seal edit to any record file breaks the checksum.
- Phase-6 duplicate guardrail: a pre-existing `phase == "6"` record with the same window
  blocks a second official run.
- The direct `evaluate()` scoring path (§2.2) returns a well-formed per-day score vector;
  the offline evidence path (§2.1) is exercised (not the identity-only certified builder).

---

## 10. Governance Guarantees Preserved

- **MSI v1.0 / DRA:** certified loader (M2) and observation reader (M3) reused unchanged; the
  certified evidence builder's identity-only contract is respected by *not* misapplying it
  (§2.1). No frozen MSI runtime, contract, or interface code is modified — the harness is
  **additive**.
- **MM13 §4 consumer contract:** the Architectural domain asserts the named estimate +
  uncertainty exactly as the knowledge-consuming contract requires.
- **MSRP pre-registration:** the harness executes the frozen dossier (§3/§9/§10) and adds no
  research freedom; the held-out window stays sealed until Phase 6.
- **MSI-006:** seven domains, conjunctive acceptance, immutable evidence, `validation_id` sole-
  ownership (MSI-6D-05), and the point-in-time-fitness verdict (MSI-6D-06) are all honored.

---

## 11. Non-Goals (Phase 5B)

- No held-out scoring run (Phase 6).
- No general/reusable validation framework — D1 "minimal-but-conformant; heavier tooling
  deferred." The `ValidationHarness` is single-purpose for this hypothesis.
- No `DomainValidator` ABC / plugin registry.
- No modification of the frozen artifact, dossier, MSI specs, or certified components.
- No implementation code and no implementation plan in this document.

---

## Appendix A — Review-Resolution Log (2026-07-06)

Five review resolutions folded into this revision; all accepted (two with strengthening riders):

| # | Resolution | Disposition |
|---|---|---|
| 1 | `validation_id` preimage: remove `results_digest`, add `harness_version` (§5.1) | Accepted. Rider: `harness_version` must be bumped on any behavior-affecting change, else two behaviors share one id — recorded as a governance obligation in §5.1. |
| 2 | Define `results_digest` explicitly — canonical JSON, 6-decimal floats, include/exclude lists (§5.2) | Accepted. |
| 3 | `phase` field + Phase-6 duplicate-execution check (§7) | Accepted. |
| 4 | `ValidationHarness` class with shared immutable state (§3) | Accepted as a refinement of the earlier "seven explicit functions" choice; immutability + side-effect-free methods stated to preserve testability. |
| 5 | Direct `artifact.evaluate()` path for the Scientific domain (§2.2) | Accepted, tightened: the "reuse the evidence builder wherever applicable" clause is made concrete against the Phase-5A F1 finding — the identity-only certified builder is *not applicable* to this artifact's log-transform evidence rules (§2.1). |

**Round 2 (2026-07-06) — five non-blocking issues, all accepted:**

| # | Resolution | Disposition |
|---|---|---|
| R2-1 | Label needs `RV_{t+1}`; last window day unscorable at snapshot edge (§2.1, §4.2) | Accepted. Reader loads one extra trading day past the window end; boundary day dropped **explicitly and recorded**, never silently — Temporal domain audits it. |
| R2-2 | Fixture score `s^{fix}_t` construction unspecified (§4.2) | Accepted. §4.2 now states the harness applies VIX thresholds 15/25 to `VIX_t` → {0,1,2} used directly, plus `s^{cand}`, `s^{vix}`, `Y_t` construction inline — no dossier cross-reference needed. |
| R2-3 | `harness_version` double-counted in the preimage (§5.1, §8) | Accepted. `methodology_fingerprint` now **excludes** `harness_version` (§5.1b); `harness_version` is single-owned as its own preimage field (§5.1c); §8 table marks each field's fingerprint membership. |
| R2-4 | `dataset_snapshot_hash` undefined (§5.1) | Accepted. §5.1a gives a concrete, input-scoped definition (sorted `path:sha256` manifest over exactly the candle files read), narrower than hashing all of `data/market_data/`. |
| R2-5 | `harness_version` bump is trust-governed only (§5.1) | Accepted. §5.1c states the trust boundary explicitly — a process obligation with no CI guard; worst case is two behaviors sharing one id, caught by governance review. |

**Round 3 (2026-07-06) — five non-blocking issues, all accepted:**

| # | Resolution | Disposition |
|---|---|---|
| R3-1 | Domain 2 / Domain 4 shared-CI ownership undefined (§4.2, §4.4) | Accepted, refined beyond the two offered options: the MBB CI is a pure `_delta_auc_ci()` helper over immutable state. Domain 2 **owns the gate verdict**; Domain 4 **re-reports** the identical CI (`REPORTED`). Coupling is through shared inputs, not outputs, so independent callability holds. |
| R3-2 | Domain 5 "double-run" ambiguous (§4.5) | Accepted, corrected: a full two-instance `run()` cannot live inside Domain 5 (recursion — `run()` calls Domain 5). Two layers specified: in-domain re-invokes the pure `_score()` (no recursion); the Phase-5B **test suite** does the two-independent-instance `run()` comparison. |
| R3-3 | Sub-period split undefined (§4.4) | Accepted. Pinned here as pre-registration: chronological first-half vs second-half by trading-day count, cut at `floor(n_days/2)` (earlier half takes the odd extra day). `REPORTED`-only. Removes the operator degree of freedom. |
| R3-4 | `dataset_snapshot_hash` binary-stability risk (§5.1a) | Accepted. Added the caveat: the hash is over the **specific frozen binary files**, not logical content; regenerating DuckDB files can change it. Cross-machine reproducibility must copy the same bytes, not regenerate. |
| R3-5 | Reference-fixture source unspecified (§4.2) | Accepted. The harness **hardcodes** the VIX thresholds (`<15`/`15–25`/`≥25` → `0/1/2`) and does **not** load the `tests/` fixture — avoiding a `core/`→`tests/` dependency; behaviorally identical to the certified gate. |

---

*End of design specification. IMPLEMENTED — pending independent review (2026-07-06). This document defines the
Phase-5B A2 Validation Harness contract only; it computes no result on the sealed held-out
window. See `scripts/msrp/run_forward_vol_validation.py` and `tests/msi/msrp/test_forward_vol_validation.py`.*
