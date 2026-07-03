# MSI-003 Architecture Review

**Document under review:** `docs/architecture/market_state_intelligence/MSI_003_OBSERVATION_ARCHITECTURE.md` (Draft v0.2, titled "Observation Acquisition Architecture")
**Reviewer:** Claude (platform-grounded)
**Date:** 2026-07-03
**Verdict:** Changes required before freeze. One blocking architectural issue: MSI-003 specs a **parallel data-acquisition stack that duplicates infrastructure the platform already owns**. The internal spec is otherwise clean.

Graded against `docs/reports/MSI_GROUNDING_BRIEF.md`, governing `MSI-001` (Draft v0.4) and `MSI-002` (Draft v0.3), and `docs/PLATFORM_CONSTITUTION.md`. Scope is upward-consistency only.

---

## 1. What is sound

- **Point-in-time / no-look-ahead is handled well** — §6 and `MSI-OA-004` ("only information available at its recorded timestamp," "never introduce future information," replay reproduces identical streams). Fully consistent with MSI-001 `CP-004`/`CP-005`. This is actually crisper than MSI-001's original treatment.
- **Immutability** (§5, §9, `MSI-OA-005`): Observations immutable, corrections require new Observations. Consistent with MSI-002 §4.4.
- **Non-interpretation boundary** (§3, `MSI-OA-001`): acquisition does not interpret, engineer features, infer latent variables, estimate state, or produce signals. Consistent with MSI-001 §4.2 and `CP-008`, and with MSI-002's Observation ≠ Evidence separation.
- **Observation vs Evidence quality kept distinct** (§8): observation quality is measurement-process quality, explicitly "not evidence." Good — respects the MSI-002 boundary.
- Provider-independence (§4, `MSI-AD-303`) and provenance retention (§7) are the right instincts.

---

## 2. Findings

### 2.1 BLOCKING — MSI-003 reinvents data acquisition the platform already owns

MSI-003 §2/§4/§9 define a full acquisition pipeline: Observation **Sources**, **Acquisition**, **Standardisation**, **Lifecycle**, **Quality**, **Provenance**, with sources listed as exchange/broker market data, options chains, IV feeds, etc. The platform already owns exactly this:

- `core/data/options_provider.py` — Upstox V3 option-chain fetch **+ DuckDB cache**
- `core/data/upstox_market_data.py`, `core/brokers/upstox_adapter.py`, `core/brokers/paper_broker.py` — market-data + broker acquisition
- `core/instruments/` — canonical instrument master, resolver, freshness/readiness
- DuckDB market-data stores (1m candles, daily intermarket, options.duckdb) — the persisted, immutable record

Standing up a second, MSI-owned acquisition/standardisation/lifecycle stack violates the platform's core discipline:

- MSI-001 `MSI-CD-004` — Runtime MSI is **demand-driven; no speculative platform abstractions**.
- Constitution — keep platform code small; the platform must remain usable with no strategies.
- CLAUDE.md house rules — **prefer editing existing files**, no abstractions for one-time use, no duplicate subsystems.

**Fix (reframe, don't rebuild):** MSI-003 should define a thin **Observation contract / adapter that maps the platform's already-persisted market-data facts into MSI `Observation` objects** — not a new ingestion pipeline. In MSI terms, *the platform's existing point-in-time market-data facts **are** the Observations.* MSI-003 defines the read contract and standardisation view over them; it does not acquire, source, or store independently. This also keeps Runtime MSI inside "Analytics Produce Facts — runtime read-only."

### 2.2 BLOCKING — The determinism/replay guarantee is only true against a persisted immutable archive, which MSI-003 leaves unnamed

`MSI-OA-002` ("Observation Acquisition is deterministic") and §6 ("historical replay shall reproduce identical Observation streams") cannot hold for **live external acquisition** — network timing, feed gaps, and vendor revisions make live capture non-deterministic. Determinism comes only from **replaying a stored immutable archive**, and the platform already has one (the DuckDB market-data stores).

MSI-003 should state explicitly that (a) determinism and identical-replay derive from replaying the platform's immutable stored facts, not from re-acquiring live, and (b) MSI owns no separate store. As written, `MSI-OA-002` overclaims. This is the determinism corollary of 2.1 — the same fix (adapter over the platform's stored facts) resolves it.

### 2.3 NON-BLOCKING — Decision-ID scheme is inconsistent across MSI and collides with the platform ADRs

Decision namespaces so far: MSI-001 `MSI-CD-xxx`, MSI-002 `MSI-OD-xxx`, MSI-003 `MSI-AD-3xx`. The MSI-003 "**AD**" reads as **ADR** — the platform's real decision records (`docs/ARCHITECTURE_DECISIONS.md`) — which is exactly the confusion the grounding brief's "no parallel governance" constraint warns against. Adopt one consistent, non-colliding scheme across the series (e.g. per-doc `MSI-3D-xxx`), and avoid "AD."

### 2.4 NON-BLOCKING — Title inconsistency

File title (§ line 3) is "Observation **Acquisition** Architecture"; the README doc-list and roadmap call it "**Observation Architecture**." Standardize the title. (This also matters because the "Acquisition" framing is what leans the doc toward 2.1 — "Observation Architecture" better fits a read-contract-over-platform-facts.)

### 2.5 NON-BLOCKING — "confidence" wording in §8

§8 defines observation quality as "confidence in the measurement process." Clarify this is **measurement-process confidence**, distinct from MSI-002 estimate *uncertainty* and MSI-005's planned "Confidence Estimation." One qualifier avoids cross-doc term collision.

### 2.6 MINOR — Provenance/quality fields duplicate platform metadata

The §5/§7 field schema (source id, timestamps, schema version, quality dimensions) largely restates provenance the platform's instrument/source layer already carries. Once 2.1 is applied, this should reference the platform's existing provenance rather than define a fresh schema.

---

## 3. Recommendation

- **2.1 + 2.2 gate freeze.** Reframe MSI-003 from an *acquisition pipeline* to an *Observation read-contract/adapter over the platform's existing, already-persisted market-data facts.* This is the single change that brings the doc in line with MSI-001 CD-004 and the Constitution's "keep platform small / no duplicate subsystems." It shrinks the doc substantially — most of §4 (Sources) and §9 (Lifecycle) collapse into "the platform acquires and stores; MSI reads."
- **2.3–2.6** are consistency polish.
- The doc's *principles* (point-in-time, immutability, non-interpretation, provenance) are all correct and should be preserved through the reframe — the problem is scope (owning acquisition), not the invariants.
