# MM11 — Removal Ledger

**Governing document:** `docs/reports/MM11_IMPLEMENTATION_SPECIFICATION.md` §1.5 (Governance Model — Controlled Decommissioning)
**Purpose:** item-level audit trail for every deletion, relocation, or retention-with-justification decision made during MM11. This is the evidentiary basis for the Platform v1.0 declaration (spec §4, item 12) — not a summary, the source the summary is built from.

**Rule:** an entry is added *at the time* an item is removed, not reconstructed afterward. A slice is not complete if code was deleted but no entry exists here for it, regardless of test status. See spec §1.5 for the four-part proof each entry must satisfy before it is written.

**Status:** empty — MM11 execution has not started. Slices append entries below as they run.

---

## How to file an entry

Copy this template per deletion target (one item — one file, one class, one function, one DDL table — per entry; do not batch unrelated items into one entry even if removed in the same commit):

```
### <slice id> — <item name> (<file(s) or table name>)

- **What it was:** <one line — what the code/table did>
- **Disposition:** REMOVED | RELOCATED | RETAINED-WITH-JUSTIFICATION
- **Gate 1 — proof of non-use:**
  - Python-import grep result: <command + result, or "N/A — docs-only">
  - String-literal grep result: <command + result>
  - (If a guarded/reachable-in-principle branch, not a fully dead file: evidence the guard is always false in production, citing composition-root construction sites)
- **Gate 2 — proof of behavior preservation:**
  - Full-suite result BEFORE change: <pass count / fail count>
  - Full-suite result AFTER change: <pass count / fail count>
  - Diff: <identical pass/fail sets, or explain any change>
  - Characterization test added/pointed to (if constructor signature or reachable branch): <test name, or "N/A — provably dead file">
- **Gate 3 — full suite passes:** <confirm — same numbers as Gate 2 "AFTER">
- **Gate 4 — why:** <one sentence: which Planned item / spec finding justified this>
- **Change reference:** <commit hash / PR, once available>
- **Slice:** <MM11.1 | MM11.2 | ... >
- **Date:** <YYYY-MM-DD>
```

For a **RETAINED-WITH-JUSTIFICATION** outcome (e.g. MM11.5 finding a live caller, or MM11.4b confirming `option_chain_snapshot` is options-dashboard-serving), file the same entry shape with Gates 1–3 showing *why* the item is NOT dead, and Gate 4 explaining the decision to keep it. Retention decisions are still required ledger entries — §1.5 gate 4 documents decisions, not only deletions.

---

## Entries

### MM11.1 — CaptureEngine (core/analytics/capture.py)

- **What it was:** `CaptureEngine` class — snapshots market structural state at signal generation time for the Trade Learning Protocol V1 pipeline. Never wired into any production composition root.
- **Disposition:** REMOVED (file deleted)
- **Gate 1 — proof of non-use:**
  - Python-import grep: `CaptureEngine` referenced only in its own definition (capture.py) and `core/execution/handler.py` (import + constructor param + dead branch). Zero external importers outside these two files. `scripts/fno_runner.py` has zero references. `tests/` has zero references.
  - String-literal grep: `"CaptureEngine"` — zero hits outside capture.py and handler.py.
  - Guarded-branch evidence: `handler.py` guard `if self.capture_engine and ...` is always False in production — `capture_engine=` is never passed a non-None value at any construction site (verified: zero `capture_engine=` arguments in `scripts/fno_runner.py`, `tests/`, or any other file).
- **Gate 2 — proof of behavior preservation:**
  - Full-suite result BEFORE change: 1055 passed, 4 skipped
  - Full-suite result AFTER change: 1055 passed, 4 skipped
  - Diff: identical pass/fail/skip sets
  - Characterization test: N/A — provably dead file; `capture_engine` was never passed at any construction site
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.1 spec §0b; unambiguously dead code — never wired at composition root, always-false guard in handler.py, all internal methods return stubs/fallbacks
- **Change reference:** MM11.1 commit (not yet committed)
- **Slice:** MM11.1
- **Date:** 2026-07-01

---

### MM11.1 — StructuralMetricsService (core/analytics/metrics_service.py)

- **What it was:** `StructuralMetricsService` class — maintained rolling 60-day buffers for dispersion (CSAD) and volatility (ATR); provided percentile snapshots for TLP V1. Only consumer was `CaptureEngine`.
- **Disposition:** REMOVED (file deleted)
- **Gate 1 — proof of non-use:**
  - Python-import grep: `StructuralMetricsService` referenced only in its own definition (metrics_service.py) and `core/analytics/capture.py` (import + constructor param). Zero external importers outside these two files.
  - String-literal grep: zero hits outside metrics_service.py and capture.py
  - `update_daily_metrics` — the sole writer of `daily_structural_metrics` table — has zero callers anywhere
- **Gate 2 — proof of behavior preservation:**
  - Full-suite result BEFORE change: 1055 passed, 4 skipped
  - Full-suite result AFTER change: 1055 passed, 4 skipped
  - Diff: identical pass/fail/skip sets
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.1 spec §0b; only consumer was `CaptureEngine` (also deleted); `update_daily_metrics` has zero live callers
- **Change reference:** MM11.1 commit (not yet committed)
- **Slice:** MM11.1
- **Date:** 2026-07-01

---

### MM11.1 — TLPLogger (core/analytics/capture.py)

- **What it was:** `TLPLogger` class + `init_tlp_logger`/`get_tlp_logger` module-level functions — unified trade outcome logger for TLP V1. Defined in capture.py alongside CaptureEngine.
- **Disposition:** REMOVED (contained in capture.py which was deleted)
- **Gate 1 — proof of non-use:**
  - Python-import grep: `TLPLogger`, `init_tlp_logger`, `get_tlp_logger` — zero references anywhere in the repo outside their own definitions in capture.py
  - String-literal grep: zero hits
- **Gate 2 — proof of behavior preservation:**
  - Full-suite result BEFORE change: 1055 passed, 4 skipped
  - Full-suite result AFTER change: 1055 passed, 4 skipped
  - Diff: identical pass/fail/skip sets
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.1 spec §0b; `init_tlp_logger` has zero call sites; `TLPLogger` is never instantiated anywhere
- **Change reference:** MM11.1 commit (not yet committed)
- **Slice:** MM11.1
- **Date:** 2026-07-01

---

### MM11.1 — `capture_engine` seam in ExecutionHandler (core/execution/handler.py)

- **What it was:** `capture_engine: Optional[CaptureEngine] = None` constructor parameter, `self.capture_engine = capture_engine` assignment, and the `if self.capture_engine and signal.signal_type != SignalType.EXIT:` dead branch (including `tlp_context` variable and its metadata attachment).
- **Disposition:** REMOVED (parameter, assignment, branch, and tlp_context metadata removed from handler.py)
- **Gate 1 — proof of non-use:**
  - Python-import grep: `capture_engine` as a keyword argument — zero construction sites pass it (`scripts/fno_runner.py`, `tests/`, all `ExecutionHandler(` call sites checked)
  - The guard at line 654 was always False in production — the branch was never reachable
- **Gate 2 — proof of behavior preservation:**
  - Full-suite result BEFORE change: 1055 passed, 4 skipped
  - Full-suite result AFTER change: 1055 passed, 4 skipped
  - Diff: identical pass/fail/skip sets
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.1 spec §2; removing an always-false branch and its unreachable parameter is behavior-neutral by construction
- **Change reference:** MM11.1 commit (not yet committed)
- **Slice:** MM11.1
- **Date:** 2026-07-01

---

### MM11.1 — `save_signal` (core/database/legacy_adapter.py, core/database/writers.py TradingWriter)

- **What it was:** `legacy_adapter.save_signal()` function and `TradingWriter.save_signal()` method — persisted signal records to the signals database.
- **Disposition:** REMOVED
- **Gate 1 — proof of non-use:**
  - Python-import grep: `save_signal` referenced only in its own definition (legacy_adapter.py:75, writers.py:272) and the `__init__.py` re-export. Zero external callers.
  - String-literal grep: zero non-self-referential hits
- **Gate 2 — proof of behavior preservation:**
  - Full-suite result BEFORE change: 1055 passed, 4 skipped
  - Full-suite result AFTER change: 1055 passed, 4 skipped
  - Diff: identical pass/fail/skip sets
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.1 spec §2 (contingent removal); confirmed zero live callers after handler.py changes
- **Change reference:** MM11.1 commit (not yet committed)
- **Slice:** MM11.1
- **Date:** 2026-07-01

---

### MM11.1 — `save_insight` / `save_insights` / `save_insights_batch` (core/database/legacy_adapter.py, core/database/writers.py AnalyticsWriter)

- **What it was:** `legacy_adapter.save_insight()`, `legacy_adapter.save_insights()`, and `AnalyticsWriter.save_insight()`/`save_insights_batch()` — persisted confluence insights to the signals database.
- **Disposition:** REMOVED
- **Gate 1 — proof of non-use:**
  - Python-import grep: all referenced only in their own definitions and the `__init__.py` re-export chain. Zero external callers.
  - String-literal grep: zero non-self-referential hits
- **Gate 2 — proof of behavior preservation:**
  - Full-suite result BEFORE change: 1055 passed, 4 skipped
  - Full-suite result AFTER change: 1055 passed, 4 skipped
  - Diff: identical pass/fail/skip sets
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.1 spec §2 (contingent removal); confirmed zero live callers after handler.py changes
- **Change reference:** MM11.1 commit (not yet committed)
- **Slice:** MM11.1
- **Date:** 2026-07-01

---

### MM11.1 — `save_regime_snapshot` (core/database/legacy_adapter.py, core/database/writers.py AnalyticsWriter)

- **What it was:** `legacy_adapter.save_regime_snapshot()` and `AnalyticsWriter.save_regime_snapshot()` — persisted regime snapshot records to the `regime_insights` table.
- **Disposition:** REMOVED
- **Gate 1 — proof of non-use:**
  - Python-import grep: referenced only in its own definitions and the `__init__.py` re-export chain. Zero external callers.
  - String-literal grep: the table name `regime_insights` has SQL-string references in `flask_app/blueprints/database.py` (generic DB browser, excluded per §0e methodology) and `scripts/migrate_monolith_to_isolated.py` (migration script, not a semantic consumer). The only semantic reader `capture.py:_get_previous_regime` is deleted. The only remaining reader `queries.py:AnalyticsQuery.get_market_regime` has zero importers (dead class). The DDL in `schema.py` survives for MM11.4a.
- **Gate 2 — proof of behavior preservation:**
  - Full-suite result BEFORE change: 1055 passed, 4 skipped
  - Full-suite result AFTER change: 1055 passed, 4 skipped
  - Diff: identical pass/fail/skip sets
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.1 spec §2 (contingent removal); confirmed zero live callers after handler.py changes
- **Change reference:** MM11.1 commit (not yet committed)
- **Slice:** MM11.1
- **Date:** 2026-07-01

---

### MM11.1 — `get_latest_insights` (core/database/legacy_adapter.py)

- **What it was:** `legacy_adapter.get_latest_insights()` function — fetched recent confluence insights from the signals database.
- **Disposition:** REMOVED
- **Gate 1 — proof of non-use:**
  - Python-import grep: referenced only in its own definition and the `__init__.py` re-export chain. Zero external callers.
  - String-literal grep: zero non-self-referential hits
- **Gate 2 — proof of behavior preservation:**
  - Full-suite result BEFORE change: 1055 passed, 4 skipped
  - Full-suite result AFTER change: 1055 passed, 4 skipped
  - Diff: identical pass/fail/skip sets
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.1 spec §2 (contingent removal); confirmed zero live callers after handler.py changes
- **Change reference:** MM11.1 commit (not yet committed)
- **Slice:** MM11.1
- **Date:** 2026-07-01

---

### MM11.1 — `AnalyticsQuery` (core/database/queries.py)

- **What it was:** `AnalyticsQuery` class with `get_latest_insight`, `get_insights`, and `get_market_regime` methods — read-only queries for confluence insights and regime insights in SQLite. `get_market_regime` reads the `regime_insights` table (last semantic reader after MM11.1 removes `capture.py:_get_previous_regime`).
- **Disposition:** RETAINED-WITH-JUSTIFICATION (out of scope for MM11.1)
- **Gate 1 — proof of non-use:**
  - Python-import grep: `AnalyticsQuery` referenced only in its own definition (`queries.py:373`). Zero external importers anywhere in the repository.
  - String-literal grep: zero non-self-referential hits.
  - The `regime_insights` table name survives in `queries.py:408` — this is the correct target for the MM11.4a DDL prune (MM11.1 removes the writer; MM11.4a removes the table and its last reader).
- **Gate 2 — N/A (retained, not removed)**
- **Gate 3 — N/A (retained, not removed)**
- **Gate 4 — why investigated but retained:** `AnalyticsQuery` was discovered during the MM11.1 per-symbol audit of `queries.py`. It is a dead class (zero importers) whose only load-bearing attribute — `get_market_regime` reading `regime_insights` — is a MM11.4a concern (table DDL prune), not a MM11.1 concern. It belongs to MM11.5 (AnalyticsProvider-coupled strategy residue) for a formal evaluation. Retained in MM11.1 to respect scope boundaries.
- **Change reference:** N/A — not removed
- **Slice:** MM11.1 (investigated only)
- **Date:** 2026-07-01

---

## MM11.7 Reconciliation Record

To be completed at milestone close (spec §2, MM11.7, acceptance criterion 2): a line-for-line cross-check of the full pre-MM11 → post-MM11 tree diff against the entries above. Every deletion in the diff must have an entry; every entry must correspond to an actual change in the diff. Mismatches in either direction block the Platform v1.0 declaration until resolved.

- **Reconciliation performed:** not yet
- **Result:** —
