# MM12.5 — Strategy Promotion Pipeline Implementation Report

**Date:** 2026-07-02
**Milestone:** MM12.5 — Strategy Promotion Pipeline (permanent platform governance)
**Status:** COMPLETE
**Predecessor:** MM12.4 — Reference Strategy Implementation
**Architecture authority:** `docs/reports/MM12_5_STRATEGY_PROMOTION_PIPELINE_ARCHITECTURE.md`
**Authored by:** Fable 5

---

## 1. Implementation Summary

### Files Added

| File | Purpose |
|---|---|
| `docs/STRATEGY_PROMOTION_LEDGER.md` | Append-only promotion ledger with 5 governing rules, 9-field entry format, 3 exhibit entries |
| `docs/strategies/STRATEGY_DATASHEET_TEMPLATE.md` | Strategy Datasheet template — identity, config schema, certified values, risk declaration, risk gate config |
| `docs/strategies/PAPER_VALIDATION_REPORT_TEMPLATE.md` | PAPER Validation Report template — window compliance, guard cleanliness, risk metrics, journal audit, margin evidence, replay proof, grantor review |
| `docs/strategies/GO_LIVE_CHECKLIST_TEMPLATE.md` | Go-Live Checklist — 7 items (a–g), dual sign-off, Stage 3/4 separation per MM12.1 §15 |
| `docs/strategies/RUNBOOK_SKELETON_TEMPLATE.md` | Kill-switch runbook (5 activation paths) + fixed 7-step rollback procedure (§7.9) + incident response contacts |
| `docs/strategies/reference_heartbeat_v1/datasheet.md` | Reference strategy permanent dossier — datasheet with certified config, risk declaration, and gate settings |

### Files Modified

| File | Change |
|---|---|
| `docs/ARCHITECTURE_DECISIONS.md` | Added ADR-021 (Strategy Promotion Is Evidence-Gated, Ledgered, and Revocable — ACCEPTED) and ADR-022 (Automatic Revocation Triggers and the Suspension Fork — ACCEPTED) |
| `docs/CHANGELOG_PLATFORM.md` | Added MM12.5 COMPLETE entry (top of changelog) |
| `docs/PROJECT_STATE.md` | Updated MM12.5 entry from PROPOSED to COMPLETE; added implementation details and evidence references |

### Files Unchanged (Zero Diff)

All certified platform subsystems are untouched:

- `core/runtime/driver.py` — LoopDriver
- `core/execution/handler.py` — ExecutionHandler
- `core/runtime/signal_source.py` — SignalSource ABC
- `core/runtime/conformance.py` — Conformance suite
- `core/runtime/guarded_signal_source.py` — GuardedSignalSource
- `core/runtime/event_journal.py` — Runtime event journal
- `core/runtime/metrics.py` — Runtime metrics
- `core/execution/*` — All execution modules
- `core/brokers/*` — All broker adapters
- `core/risk/*` — All risk/margin modules
- `core/instruments/*` — All instrument modules
- `core/database/*` — All persistence modules
- `scripts/fno_runner.py` — Composition root
- `reference_strategies/*` — All reference strategy code
- `tests/*` — All test files

---

## 2. Promotion Governance Artifacts

### ADR-021 — Strategy Promotion Is Evidence-Gated, Ledgered, and Revocable

Records the five-stage promotion ladder (DEVELOPMENT → CONFORMANT → PAPER VALIDATED → LIVE CANDIDATE → LIVE APPROVED), two non-ladder states (SUSPENDED, RETIRED), the certification identity triple `(strategy_id, code_ref, config_hash) @ STRATEGY_CONTRACT_VERSION`, the dual-role authority model (Technical Lead + Account Owner), the permanent record scheme (ledger + dossiers), and the rule that the pipeline consumes certified systems and never modifies them (§0.1). Binds MM12.1 §14.1's two fixed rules into permanent governance.

### ADR-022 — Automatic Revocation Triggers and the Suspension Fork

Records the fixed revocation trigger table (6 events × 2 stages): any guard event, DD breach, strategy-attributable kill-switch trip or reconciliation divergence, and non-replay-explainable live trade are binary failures in PAPER (Stage 2 failure) and automatic suspension triggers in LIVE. Records the suspension fork: strategy-attributable cause → new identity → Stage 0; external cause → grantor sign-off → resume at prior stage. Resolves MM12.1 open question #3 (escalating contract-violation counts to quarantine) for promotion purposes: the first post-certification `SIGNAL_CONTRACT_REJECTED` is certification-voiding, enforced by the pipeline reading the existing journal — no guard code change.

### Strategy Promotion Ledger — `docs/STRATEGY_PROMOTION_LEDGER.md`

| Feature | Specification |
|---|---|
| **Governing rules** | 5 rules: append-only, every transition requires entry, ledger is index not evidence body, complete-field requirement, correcting-entry protocol |
| **Entry format** | 9 fields: date, strategy_id, (code_ref, config_hash), contract version, from-state→to-state, evidence links, platform commit, grantor role(s), note |
| **Exhibit entries** | E001 — Reference strategy registration (born-retired per ADR-020); E002 — Reference strategy CONFORMANT certification; E003 — Fault fixtures registration |

### Dossier Convention — `docs/strategies/<strategy_id>/`

Four committed templates + one populated dossier:

**Strategy Datasheet template (9 sections):**
1. Identity (strategy_id, code_ref, config_hash, contract version, package, factory)
2. Config schema (parameter, type, default, description)
3. Certified config values (exact JSON dict)
4. Universe (symbols, derivative types, underlyings)
5. Session behavior (max signals per bar, entry/exit frequency, max positions)
6. Latency budget (on_bar p99 target)
7. Risk declaration (max DD Rs and %, risk_r semantics, sl_distance semantics, max margin, allocated capital)
8. External backtest reference (period, report path, key metrics — filed not graded)
9. Risk gate configuration (drawdown, daily limit, max positions, margin, Greek limits)

**PAPER Validation Report template (11 sections):**
1. Identity (triple, platform commit, window dates)
2. Window compliance (≥20 sessions, ≥30 round-trips)
3. Guard cleanliness (STRATEGY_ERRORS=0, STRATEGY_QUARANTINE_EVENTS=0, SIGNAL_CONTRACT_REJECTIONS=0)
4. Risk metrics (max DD, peak exposure, peak margin, signal→fill conversion, win rate, profit factor)
5. Telemetry archive (per-session counters, continuity assessment)
6. Journal audit (intent vs. reality, shadow-state divergence)
7. Margin evidence (NseMarginEngine usage, SPAN/ELM figures)
8. Kill-switch drill (date, type, observed behavior, journal record)
9. Restarts and anomalies (cause, disposition)
10. Replay evidence (corpus ref, signal stream match, ledger fields match)
11. Grantor review (reviewer, role, decision, date)

**Go-Live Checklist template (7 items + dual sign-off):**
- (a) Broker reconciliation proven live
- (b) Broker margin reconciliation report
- (c) Credential/token lifecycle
- (d) Process supervision
- (e) Kill-switch runbook verified
- (f) Rollback runbook walked through
- (g) Capital plan
- Stage 4 grant entry reference

**Runbook Skeleton template (3 parts):**
- Part 1: Kill-switch runbook (5 activation paths, observable consequences, post-activation checklist)
- Part 2: Fixed 7-step rollback procedure per §7.9 (halt intake → assess positions → disposition → stop process → ledger demotion → investigate → re-entry)
- Part 3: Incident response contacts

---

## 3. Evidence Storage and Tracking

Promotion evidence is stored via committed artifact chains:

```
Ledger entry
  └─ evidence links field ──→ dossier document
                                  └─ platform commit
                                  └─ strategy code_ref
                                  └─ config_hash
                                  └─ corpus identity (for replay evidence)
                                  └─ report paths
```

**Auditability principle** (§9.3): every decision is reconstructable from committed artifacts alone. The ledger entry names the evidence; the evidence names the corpus, the platform commit, and the identity triple; the corpus and the code are re-runnable. Auditing a grant = re-running its evidence.

**Evidence rules** (§1.2): every mandatory item is the output of an existing platform instrument (conformance suite, journal, telemetry archive, ledger query, replay diff). Narrative claims carry zero weight.

**Evidence expiry** (§4.2): PAPER evidence expires after 60 calendar days; a 5-session re-confirmation is required before a stale-grant Stage 3→4 promotion.

---

## 4. Documentation Updated

| Document | Change |
|---|---|
| `docs/ARCHITECTURE_DECISIONS.md` | ADR-021 and ADR-022 appended (Status: ACCEPTED) |
| `docs/CHANGELOG_PLATFORM.md` | Newest entry: 2026-07-02 — MM12.5 — Strategy Promotion Pipeline (COMPLETE) |
| `docs/PROJECT_STATE.md` | MM12.5 entry moved from PROPOSED to COMPLETE; header date updated |

---

## 5. Repository Impact Report

| Metric | Value |
|---|---|
| Platform code files modified | 0 |
| Platform code files added | 0 |
| Test files modified | 0 |
| Test files added | 0 |
| Documentation files modified | 3 |
| Documentation files added | 6 |
| Frozen subsystem changes | **Zero** |
| ADRs added | 2 (ADR-021, ADR-022) |

---

## 6. Test Report

| | Baseline | Final | Change |
|---|---|---|---|
| Passed | 1125 | 1125 | 0 |
| Skipped | 4 | 4 | 0 |
| Failed | 0 | 0 | 0 |
| New tests | — | 0 | 0 |

**Existing conformance remains unchanged.** Reference Strategy remains promotable (holds CONFORMANT). Replay evidence is identical. No frozen platform behaviour changes.

---

## 7. Deviations from Architecture

**None.** All approved architectural requirements were implemented exactly as specified:

- ADR-021 and ADR-022 authored and accepted (§10)
- `docs/STRATEGY_PROMOTION_LEDGER.md` created with append-only rules, entry format, reference strategy exhibit (§9.1)
- Dossier convention + 4 templates committed (§9.2)
- Go-Live Checklist explicitly separates Stage 3/4 (MM12.1 §15 exit criterion, verified verbatim)
- Zero code changes; zero diffs in frozen files (§0.1, §12)
- PROJECT_STATE.md and CHANGELOG_PLATFORM.md synced (§12)
- Full test suite unchanged (1125 passed, 4 skipped) (§12)

No architectural conflict was encountered. The implementation is pure documentation/governance — no runtime code changes were required, as the architecture specification anticipated (§0.1).

---

## 8. Roadmap Context

| Slice | Status |
|---|---|
| **MM12.5a** (this milestone) — Architecture ratification, ADR-021/022, ledger, templates | **COMPLETE** |
| MM12.5b — Ops runbooks (credential lifecycle, process supervision, alert path) | Deferred |
| MM13 — First external strategy PAPER validation | Unchanged |
| MM14 — LIVE readiness + broker margin reconciliation | Unchanged |

---

## 9. Success Criteria Verification

| Criterion | Status |
|---|---|
| Promotion pipeline matches the approved architecture | ✓ |
| ADR-021 and ADR-022 are implemented | ✓ |
| Promotion governance artifacts exist | ✓ |
| Promotion evidence is auditable | ✓ |
| Reference Strategy satisfies promotion requirements | ✓ (CONFORMANT, born-retired per ADR-020) |
| No certified platform subsystem has been modified | ✓ |
| Full regression suite passes unchanged | ✓ (1125 passed, 4 skipped) |
| Runtime behaviour unchanged except where explicitly required | ✓ (no runtime changes required) |

---

*This milestone completes the Strategy Integration Framework (MM12).*
*Ref: docs/reports/MM12_5_STRATEGY_PROMOTION_PIPELINE_ARCHITECTURE.md;*
*docs/ARCHITECTURE_DECISIONS.md ADR-021/022;*
*docs/STRATEGY_PROMOTION_LEDGER.md; docs/strategies/;*
*ADR-020; PLATFORM_CONSTITUTION.md §5–§7.*
