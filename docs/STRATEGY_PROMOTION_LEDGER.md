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

### E004 — nifty_shield_v1 Stage 0 identity reservation (first external strategy)

```
2026-08-07 · nifty_shield_v1 · (unpinned@Stage1, unpinned@Stage1) · 1.0 · null → DEVELOPMENT
· docs/reports/NIFTY_SHIELD_ADOPTION_ASSESSMENT.md · 48e455a · operator · First external strategy on the ladder. Identity reserved for the NiftyShield port — a regime-adaptive weekly Nifty options premium seller — from the retired D:\BOT\root platform. Routed through the MM12.5 promotion pipeline (safety), NOT the research/RFA track (assessment §2); RFA recorded Not Applicable with reasons (§2.1). code_ref and config_hash are unpinned at Stage 0 and pinned at the Stage 1 submission (§4.0). The bundled strategy fails Stage 1 CONFORMANT as-copied (illegal core.* imports, forbidden execution/broker handles, side-effects in on_bar — assessment §4) and will be re-expressed as a dumb SignalSource; the copy-in path is void. Stage 0 grants nothing (§4.0). Binding on downstream work: the OSC-preserved unread index-options window (2016→2022) must not be backtested (assessment §3); the DayType model identity hole (§5.1) and sweep_filter (§5.4) are excluded from this identity. Per §5.2, this strategy_id is never reused if abandoned.
```

### E005 — nifty_shield_v1 Stage 1 CONFORMANT grant (first external strategy certified)

```
2026-08-08 · nifty_shield_v1 · (ebfb7ec, c5b722ff204d4e434f5cbffb1674136738a79693a3ced17bf07e46676d5336c6) · 1.0 · DEVELOPMENT → CONFORMANT
· docs/strategies/nifty_shield_v1/datasheet.md (v1, frozen), docs/reports/NIFTY_SHIELD_STAGE1_CONFORMANCE_REPORT.md, docs/reports/NIFTY_SHIELD_DECOMPOSITION_SPEC.md, docs/reports/DAYTYPE_FACTS_IMPLEMENTATION_REPORT.md, tests/strategies/test_nifty_shield_v1_conformance.py (7 conformance tests), tests/execution/test_nifty_shield_execution.py (15 execution tests) · 5594470 · Technical Lead · This is a SAFETY/CONTRACT grant, not an alpha grant — the conformance corpus is Nifty-50 index 1m bars + regime/VIX facts; no option marks, no P&L, no backtest is graded. The certified artifact is the re-expressed dumb SignalSource per NIFTY_SHIELD_DECOMPOSITION_SPEC.md (D1–D5); the bundled copy-in path is void (E004). Evidence: MM12.2 Layer 1+2 conformance PASS raw AND guard-wrapped; replay-twice byte-identical 16-signal stream; on_bar p99 0.0022 ms; §7a max-DD Rs 30,000 single / Rs 150,000 5-day streak (backtest DD excluded); margin ceiling 25%, NseMarginEngine wired (D4). config_hash reproduces exactly from strategies/nifty_shield_v1/config.py; frozen disposition — iv_default retained-inert, cost_per_lot_rs dropped, undefined_risk_stress_pts (200) retained. Prohibitions honoured: OSC index-options window 2016-02-11→2022-12-31 UNTOUCHED, no P&L presented as validation, sweep_filter excluded from the identity. STANDING PROVENANCE CAVEAT (operator-directed, carried forward): the DayType regime models are NOT trained on F:\Nifty data — they are the retired D:\BOT\root v2.0-train_thru2025 models, reused as-is; a retrain-on-F:\Nifty pass is deferred; the caveat rides each fact row via the trained_on column. LOW-2 (sizing min_lots=1 floor) is accepted as a conscious Stage-2 capital-plan note, NOT a code change. Stage 2 (PAPER VALIDATED, E006) is blocked on one prerequisite: the DayType live 13:00 publisher wired to a live bar feed — and, coupled to it, the RegimeFactsReader read-timing (it snapshots the whole facts table at on_start, when today's 13:00 fact does not yet exist) must move to a per-bar/at-13:00 read for live. Grant confers no LIVE authority.
```

### E006 — nifty_shield_v1 Stage-2-prerequisite re-certification (same identity, new code_ref)

```
2026-08-08 · nifty_shield_v1 · (89fcdd6, c5b722ff204d4e434f5cbffb1674136738a79693a3ced17bf07e46676d5336c6) · 1.0 · CONFORMANT → CONFORMANT
· docs/reports/NIFTY_SHIELD_STAGE2_PREREQ_HAND_BACK.md, docs/reports/NIFTY_SHIELD_STAGE2_PREREQ_IMPLEMENTATION_PROMPT.md, docs/strategies/nifty_shield_v1/datasheet.md (§1 code_ref bumped), tests/runtime/test_driver_publish_hook.py, tests/runtime/test_publish_hook_live_dry_run.py, tests/daytype/test_daytype_facts.py, tests/strategies/test_nifty_shield_v1_lazy_facts.py · 89fcdd6 · operator · Re-certification of the SAME identity at a new code_ref — same strategy_id + same config_hash (c5b722ff…536c, UNCHANGED, reproduces from config.py) + new code_ref (89fcdd6). Per MM12.5 §5.2 a re-cert is never a new strategy_id. This takes the E006 slot for the re-cert (superseding the E005 note's projection of E006 as the PAPER VALIDATED grant); PAPER VALIDATED now lands at E007. WHY: the Stage-2 blocker named in E005 — the DayType live 13:00 publisher wired to a live bar feed, coupled to moving RegimeFactsReader off its on_start whole-table snapshot to a per-bar/at-13:00 read — is now built (DS2-1 lazy re-queryable reader + source gate; DS2-2 additive strategy-agnostic LoopDriver publish seam, publish_hook + publish_checkpoint_time, fires once per session at/after the 13:00 tick before on_bar; DS2-3 intraday vix_at_checkpoint column, live rows carry the 13:00 India-VIX 1m close with vix_close NULL; DS2-4 NULL-VIX/thin-feed session skip). DS2-1 ACCEPTANCE GATE HOLDS: over the unchanged frozen corpus, replay-twice byte-identical 16-signal stream, guard-wrapped Layer 1+2 conformance PASS raw AND guarded, on_bar p99 within the 0.05 s budget, 431 strategy/daytype/runtime tests PASS (full suite 1599 PASS, one pre-existing unrelated main failure test_g1_closure_guard). Because config_hash, the 16-signal stream, and conformance all hold, the read-timing change is a PROVABLE OFFLINE NO-OP. DS2-2 driver seam reviewed CLEAN (additive-only; both new params default None → loop byte-for-byte unchanged, 418 runtime+strategy tests green untouched; correctly layered — no strategy knowledge in the driver; broad except logged not swallowed). STANDING SEMANTICS NOTE (config_hash cannot detect, DS2-3): the certified VIX gates (skip 20.0 / reduce 16.0 / iron_fly 14.0) now act on a 13:00 VIX in LIVE rows — a live-only behavior NEVER exercised in conformance, to be observed in E006-successor PAPER, explicitly NOT claimed equivalent to Stage-1 EOD-VIX gating. The E005 STANDING PROVENANCE CAVEAT rides forward unchanged: the DayType regime models are the retired D:\BOT\root v2.0-train_thru2025 models reused as-is (not retrained on F:\Nifty), the caveat carried on each fact row's trained_on column; retrain deferred. Prohibitions honoured: OSC index-options window 2016-02-11→2022-12-31 UNTOUCHED; no P&L presented as validation; frozen corpus NOT regenerated (no vix_at_checkpoint backfilled); no frozen platform component modified. Grant confers NO PAPER VALIDATED and NO LIVE authority — it only re-pins CONFORMANT to 89fcdd6 so PAPER round-trip counting (datasheet §10) accumulates against ONE code_ref. PAPER validation (E007) begins after this entry.
```

### E007 — nifty_shield_v1 retrained-model production swap (re-cert — same identity, new code_ref)

> **GRANTED by operator 2026-08-11.** Numbering per the E006 precedent: a re-cert consumes the
> next numeric slot (E007), so the PAPER VALIDATED grant shifts down to **E008**. Load-bearing
> checks verified at grant: `config_hash` reproduces exactly from `config.py` (`c5b722ff…536c`,
> MATCH) and `model_hash` reproduces (`bd0d6826…54be7`, MATCH). **`code_ref` is `fe87363`, NOT
> the retrain commit `d2410be`:** `d2410be` committed the retrained model but left three trailing
> files stale — a clean checkout was **test-red** (`test_regime_fact_version_reflects_metadata`
> asserted the old `dt-v2.0-train_thru2025`) and its `publish_facts.py:TRAINED_ON` still named the
> `D:\BOT` vintage, contradicting this entry's provenance claim. `fe87363` is the completion commit
> (`TRAINED_ON` → F:\Nifty string, version pins corrected) that makes the retrain green and
> self-consistent; the certified `day_type_facts.duckdb` was republished from it (`produced_by =
> offline@fe87363`). A CONFORMANT `code_ref` must be the commit carrying the certified GREEN
> artifact, not merely the branch head — the E006 "branch head" only served because it happened to
> be that commit. Granted on-branch; no merge-commit substitution.

```
2026-08-11 · nifty_shield_v1 · (fe87363, c5b722ff204d4e434f5cbffb1674136738a79693a3ced17bf07e46676d5336c6) · 1.0 · CONFORMANT → CONFORMANT
· docs/reports/NIFTY_SHIELD_PHASE6_RECERT_IMPLEMENTATION_PROMPT.md, docs/reports/NIFTY_SHIELD_DAYTYPE_PARITY_REPORT.md, docs/reports/NIFTY_SHIELD_13PM_RETRAIN_FIX_IMPLEMENTATION_PROMPT.md, docs/reports/NIFTY_SHIELD_E007_COMPLETION_COMMIT_PROMPT.md, docs/strategies/nifty_shield_v1/datasheet.md (§1 code_ref bumped), scripts/daytype/parity_check_13pm.py, scripts/daytype/publish_facts.py, tests/daytype/test_daytype_facts.py, tests/strategies/test_nifty_shield_v1_lazy_facts.py · fe87363 · operator · Re-certification of the SAME identity at a new code_ref — same strategy_id + same config_hash (c5b722ff…536c, UNCHANGED, reproduces from config.py — verified at grant) + new code_ref (fe87363, the completion commit; see the DEFECT note in the blockquote — the earlier-drafted d2410be was test-red and provenance-stale, so it is NOT the code_ref). Per MM12.5 §5.2 a re-cert is never a new strategy_id. This takes the E007 slot for the re-cert (superseding the E006 note's projection of E007 as the PAPER VALIDATED grant); PAPER VALIDATED now lands at E008. WHAT CHANGES: the DayType 13pm production model is swapped from the D:\BOT vintage (known 13%-flip train/serve skew) to the honest retrained v2.0-train_thru2023 artifact — 38 features (3 engine-unavailable orphans dropped so trained == served), engine↔CSV feature parity PASS (30/30 sampled 2024–2025 sessions within 1e-6), deployed 2025 holdout accuracy 69.8%, Train 66.2%/Val 70.7%/Holdout 70.6%. STANDING PROVENANCE CAVEAT (E005/E006 "models NOT trained on F:\Nifty data") is now RESOLVED: TRAINED_ON = "F:\Nifty reference 1m 2012-2023 + DuckDB store; retrained v2.0-train_thru2023" rides every fact row. day_type_facts.duckdb republished: 840 rows, model_hash bd0d6826…54be7, regime_fact_version dt-v2.0-train_thru2023. ACCEPTANCE GATE HOLDS: config_hash unchanged, conformance corpus untouched (frozen fixture), conformance + execution + DS2 driver/facts suites PASS (full suite 2055 PASS, two pre-existing unrelated failures: test_live_publisher_not_ready_without_data [live buffer present in tree] and test_g1_closure_guard). NO alpha, NO PAPER VALIDATED, NO LIVE authority conferred — this only swaps the model input and re-pins CONFORMANT. The retrain's 2026 sealed read was INCONCLUSIVE (no promotion implied); promotion to capital is gated by the sealed verdict, not this re-cert.
```

---

## Open entries (reserved for future use)

*E004 consumed 2026-08-07, E005 consumed 2026-08-08, E006 consumed 2026-08-08, E007 consumed 2026-08-11 (GRANTED — see Entries above). The following slots remain reserved for `nifty_shield_v1`'s onward promotion path (or, if it is abandoned, the next external strategy's — a retired id is never reused, §5.2):*

- E008 — (first external strategy Stage 2 PAPER VALIDATED grant)
- E009 — (first external strategy Stage 3 LIVE CANDIDATE grant)
- E010 — (first external strategy Stage 4 LIVE APPROVED grant)
- E011+ — (suspension, incident, audit, cap-raise entries)

---

## Cross-reference

- Evidence format and dossier conventions: `docs/reports/MM12_5_STRATEGY_PROMOTION_PIPELINE_ARCHITECTURE.md` §9.2
- Grant authority definitions: `docs/reports/MM12_5_STRATEGY_PROMOTION_PIPELINE_ARCHITECTURE.md` §8
- Automatic revocation triggers: `docs/reports/MM12_5_STRATEGY_PROMOTION_PIPELINE_ARCHITECTURE.md` §7.6
- Suspension and re-entry fork: `docs/reports/MM12_5_STRATEGY_PROMOTION_PIPELINE_ARCHITECTURE.md` §3.1, §5.1
- ADR-021 (promotion is evidence-gated, ledgered, revocable)
- ADR-022 (automatic revocation triggers and suspension fork)
- ADR-020 (reference strategy permanently PAPER-confined)
