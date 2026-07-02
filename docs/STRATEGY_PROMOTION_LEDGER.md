# Strategy Promotion Ledger

**Governing document:** `docs/reports/MM12_5_STRATEGY_PROMOTION_PIPELINE_ARCHITECTURE.md` §9.1
**Purpose:** append-only, repository-committed record of every promotion, demotion, suspension, and retirement transition. Promotions without a ledger entry do not exist (§1.6). Entries are never edited or deleted — supersede with a correcting entry.

**Rules:**
1. Append-only — new entries are added to the bottom, never inserted or edited.
2. Every transition (up, down, or sideways) requires an entry.
3. The ledger is the index; evidence lives in the dossier (`docs/strategies/<strategy_id>/`).
4. An entry is complete only when all fields are populated.
5. A correcting entry (e.g., correcting a date in a prior entry) supersedes the erroneous entry — it does not edit it.

## Entry format

```
date · strategy_id · (code_ref, config_hash) · contract version · from-state → to-state
· evidence links (committed paths) · platform commit · grantor role(s) · note
```

| Field | Description |
|---|---|
| `date` | ISO date of the transition (YYYY-MM-DD) |
| `strategy_id` | The strategy identifier carried on every emitted signal |
| `code_ref` | Commit hash of the strategy package used for certification |
| `config_hash` | SHA-256 hex digest of the `build_signal_source(config)` dict |
| `contract version` | `STRATEGY_CONTRACT_VERSION` at the time of the transition |
| `from-state → to-state` | The two promotion states (DEVELOPMENT, CONFORMANT, PAPER VALIDATED, LIVE CANDIDATE, LIVE APPROVED, SUSPENDED, RETIRED) |
| `evidence links` | Comma-separated relative paths to evidence documents (dossier files, reports) |
| `platform commit` | Commit hash of the platform at the time of the transition |
| `grantor role(s)` | Technical Lead, Account Owner, or both (for dual sign-off). Automatic/demotion entries record "automatic" or "operator" |
| `note` | Free-text: rationale, findings, links to investigation reports, or pointer to superseding entry |

---

## Exhibits

### Exhibit 1 — Reference Strategy (born-retired, permanently PAPER-confined)

Per ADR-020, the reference strategy `reference_heartbeat_v1` is a permanently PAPER-confined,
non-alpha canary. It is born-retired from the promotion ladder — it holds CONFORMANT status
(verified through the MM12.2 conformance suite and MM12.4 guard-wrap proof) but is never
promotable to LIVE CANDIDATE or LIVE APPROVED. This exhibit records its fixed status as a
standing reference for the ledger format and auditability.

**Reference strategy identity triple:**
- `strategy_id`: `reference_heartbeat_v1`
- `code_ref`: `e5e44d4` (reference_strategies/heartbeat/ initial commit)
- `config_hash`: `sha256:47de...` (default config: `{"entry_period_bars": 60, "holding_period_bars": 15, "sl_distance_pct": 0.01, "risk_r": 500.0}`)
- `STRATEGY_CONTRACT_VERSION`: `1.0`

---

## Entries

### E001 — Reference strategy registration (born-retired)

```
2026-07-02 · reference_heartbeat_v1 · (e5e44d4, sha256:47de...) · 1.0 · null → DEVELOPMENT
· — · — · automatic · Reference strategy identity reserved at ledger creation. Per ADR-020: permanently PAPER-confined, never promotable beyond CONFORMANT.
```

### E002 — Reference strategy CONFORMANT certification

```
2026-07-02 · reference_heartbeat_v1 · (e5e44d4, sha256:47de...) · 1.0 · DEVELOPMENT → CONFORMANT
· docs/strategies/reference_heartbeat_v1/datasheet.md (v1), docs/reports/MM12_4_IMPLEMENTATION_REPORT.md, tests/runtime/test_heartbeat_strategy.py (4 conformance tests), tests/runtime/test_signal_source_conformance.py (full suite) · 2b3c050 · Technical Lead · HeartbeatSignalSource passes MM12.2 Layers 1+2 conformance unmodified. GuardedSignalSource wrap also passes conformance. Zero guard rejections. Permanent PAPER confinement per ADR-020; this is the terminal promotion state for this strategy_id.
```

### E003 — Fault fixtures registration (born-retired, non-promotable)

```
2026-07-02 · fault_drill · (e5e44d4, sha256:e3b0c...) · 1.0 · null → DEVELOPMENT
· — · — · automatic · Fault fixture strategy identity reserved at ledger creation. AlwaysRaisesSource and BadMetadataSource are throwaway guard-proof fixtures per ADR-020 §3. Never promotable; no CONFORMANT certification sought or granted.
```

---

## Open entries (reserved for future use)

*No entries beyond E003 exist at ledger creation time. The following slots are reserved for the first external strategy's promotion path:*

- E004 — (first external strategy Stage 0 identity reservation)
- E005 — (first external strategy Stage 1 CONFORMANT grant)
- E006 — (first external strategy Stage 2 PAPER VALIDATED grant)
- E007 — (first external strategy Stage 3 LIVE CANDIDATE grant)
- E008 — (first external strategy Stage 4 LIVE APPROVED grant)
- E009+ — (suspension, incident, audit, cap-raise entries)

---

## Cross-reference

- Evidence format and dossier conventions: `docs/reports/MM12_5_STRATEGY_PROMOTION_PIPELINE_ARCHITECTURE.md` §9.2
- Grant authority definitions: `docs/reports/MM12_5_STRATEGY_PROMOTION_PIPELINE_ARCHITECTURE.md` §8
- Automatic revocation triggers: `docs/reports/MM12_5_STRATEGY_PROMOTION_PIPELINE_ARCHITECTURE.md` §7.6
- Suspension and re-entry fork: `docs/reports/MM12_5_STRATEGY_PROMOTION_PIPELINE_ARCHITECTURE.md` §3.1, §5.1
- ADR-021 (promotion is evidence-gated, ledgered, revocable)
- ADR-022 (automatic revocation triggers and suspension fork)
- ADR-020 (reference strategy permanently PAPER-confined)
