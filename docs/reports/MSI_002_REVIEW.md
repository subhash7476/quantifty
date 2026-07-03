# MSI-002 Architecture Review

**Document under review:** `docs/architecture/market_state_intelligence/MSI_002_MARKET_ONTOLOGY.md` (Draft v0.2)
**Reviewer:** Claude (platform-grounded)
**Date:** 2026-07-03
**Verdict:** Changes required before freeze. Two blocking items — both are the ontology **contradicting its own stated principles (§3)**. The rest is consistency polish.

Graded against `docs/reports/MSI_GROUNDING_BRIEF.md`, the governing `MSI-001` (Draft v0.4, reviewed), and `docs/PLATFORM_CONSTITUTION.md`. Scope is upward-consistency only (MSI-001 + Constitution) — MSI-003+ depend on this doc and cannot constrain it.

---

## 1. What is sound

- **Clean separation of Observation / Evidence / Knowledge.** §4.4–4.5 and §5 correctly bar strategies from consuming Observations or Evidence — consistent with MSI-001 `CP-008` (Strategy Independence) and the read-only Knowledge interface.
- **Point-in-time discipline is carried through.** Observation is "point-in-time" (§4.4), Market State is instant-bound (§4.7) — consistent with MSI-001 `CP-004`/`CP-005`.
- **Multidimensionality is protected** (`MSI-OD-001`): Market State is never a single categorical label. Good — this pre-empts the classic "regime = one enum" mistake.
- **Artifact-as-sole-boundary** (`MSI-OD-003`) matches MSI-001 `CD-002`. No new privileged channel introduced at the entity level.
- No reference to `DayTypeEngine` or any code as prior art. Clean.

---

## 2. Findings

### 2.1 BLOCKING — The Latent Variable → Market State chain contradicts §4.6 (violates OP-002)

This is an internal contradiction, not a stylistic compression:

- **§4.6** defines a Latent Variable as *a property of Market Reality* that "exist[s] conceptually whether or not [it] can currently be estimated." That places it on the **reality side** — independent of observation.
- **§5** then puts Latent Variable **downstream of Evidence** in the linear chain (`Evidence ↓ Latent Variable ↓ Market State`), as if Evidence *produces* it.
- **§4.7** compounds it: Market State is "the collection of **inferred** Latent Variables." You do not infer the variable — the variable is a fact of reality; you infer an **estimate** of it.

So §4.6 (Latent Variable lives in reality, independent of observation) and §5/§4.7 (Latent Variable is derived from Evidence) genuinely disagree. This violates `MSI-OP-002` ("Architectural entities shall not overlap in responsibility") — the single term "Latent Variable" is being used for both the unobservable reality-property *and* the thing inference produces.

**The missing entity is `Estimate`.** The correct shape:

```
Market Reality ──contains──> Latent Variable   (unobservable, exists in reality)
      │                              ▲
      └─> Observable ─> Observation ─> Evidence ─> Estimate (of a Latent Variable)
                                                       │  carries value + uncertainty
                                                       ▼
                                                  Market State  (collection of Estimates)
                                                       ▼
                                                  Knowledge
```

Evidence supports inference of an **Estimate of a Latent Variable**; Market State is the collection of those Estimates. Latent Variable stays on the reality side where §4.6 correctly puts it.

This is an ontology *design* change and the document is authored externally — so treat the Estimate entity as the **recommended shape of the fix**, not a mandated wording. But the contradiction itself must be resolved before freeze.

### 2.2 BLOCKING — Uncertainty is absent from the ontology (contradicts MSI-001 FA-004)

MSI-001 `MSI-FA-004` is foundational: *"Every market-state estimate contains uncertainty. Absolute certainty shall never be assumed."* MSI-002's ontology has **no entity or attribute** representing uncertainty — Market State is just a "collection of inferred Latent Variables." An ontology that cannot express uncertainty under-specifies its own governing document.

**Fix:** the same `Estimate` entity from 2.1 resolves this in one move — an Estimate carries a value **and its uncertainty**. One entity closes both blocking findings.

### 2.3 MUST-FIX (non-blocking) — One entity, two names (violates OP-001)

§2 (Scope) lists the entity as **"Market State Artifact"**; §4.9 defines it as **"Published MSI Artifact."** Both §2 and §4 have exactly nine items and this is slot 9 — it is one entity named twice, not two entities. This directly breaks `MSI-OP-001` ("every entity shall possess a single, well-defined meaning"), the doc's own first ontological principle. Standardize on **"Published MSI Artifact"** (the term MSI-001 uses). One-word fix, but it must be fixed.

### 2.4 NON-BLOCKING — "Knowledge" definition smuggles an implementation property past OP-003

§4.8 defines Knowledge as the "**deterministic** runtime representation of Market State." `MSI-OP-003` requires entities to "remain implementation independent." Keep "runtime-exposed representation" — that distinction is the whole reason Knowledge and Market State are separate entities. But **"deterministic"** is an MSI-001 `CP-003` runtime *guarantee*, not an ontological property; it belongs in the runtime/artifact specs, not baked into the entity definition here.

### 2.5 NON-BLOCKING — OD-002 wording risks reading as a new privileged channel

`MSI-OD-002` ("Knowledge is the only architectural interface exposed to strategies") is correct as a read-side statement, but should cross-reference MSI-001 `CD-003` / the README settled flow: strategies consume Knowledge through **existing platform interfaces** (the read path adjacent to `SignalSource`), not a new MSI-owned channel. One clause avoids a future misread.

### 2.6 MINOR — §6 header "Architectural Decisions" collides with the platform ADR process

The IDs are `MSI-OD-xxx` ("Ontological Decisions"); the header says "Architectural Decisions," which is easily confused with the platform's actual ADRs (`docs/ARCHITECTURE_DECISIONS.md`). Rename the header to "Ontological Decisions" to match the ID namespace. (Same class of naming fix applied to MSI-001 in review.)

---

## 3. Recommendation

- **2.1 + 2.2 gate freeze** — both are resolved by introducing an `Estimate` (value + uncertainty) entity and branching Latent Variable back onto the reality side. Send back for that one structural change.
- **2.3** must be fixed (one-word standardization) but need not block on its own.
- **2.4 / 2.5 / 2.6** are consistency polish.
- After 2.1–2.3, MSI-002 is otherwise well-scoped and consistent with MSI-001. The ontology's *intent* is right; it just needs the Estimate layer to stop contradicting itself.
