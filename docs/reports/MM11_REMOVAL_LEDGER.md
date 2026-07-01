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

### MM11.2 — `historical_market_provider`, `market_data_provider`, `duckdb_market_data_provider` chain (core/data/)

- **What it was:** Three tightly-coupled legacy modules: `HistoricalMarketProvider` (reads historical OHLCV from DuckDB), `MarketDataProvider` (abstract market data provider re-exported from `core.database.providers.base`), `DuckDBMarketDataProvider` (DuckDB-backed market data provider re-exported from `core.database.providers.duckdb`). All shim/re-exports for backward compatibility with `core.database.*`.
- **Disposition:** REMOVED (3 files deleted atomically as a cluster)
- **Gate 1 — proof of non-use:**
  - Python-import grep (`from core.data.market_data_provider`): zero importers outside the 3-file chain. Only `historical_market_provider.py:8` imports `market_data_provider`, and `historical_market_provider.py:9` imports `duckdb_market_data_provider`. No external (outside `core/data/`) importer exists.
  - Python-import grep (`from core.data.historical_market_provider`): zero importers anywhere, including self-chain.
  - Python-import grep (`from core.data.duckdb_market_data_provider`): zero importers outside the chain (only `duckdb_market_data_provider.py:11` docstring).
  - String-literal grep: zero hits in `scripts/`, `docs/` (except MM11 spec), `config/`, `tests/`.
  - `tests/` contains zero references to any of the three modules.
- **Gate 2 — proof of behavior preservation:**
  - Full-suite result BEFORE change: 1055 passed, 4 skipped
  - Full-suite result AFTER chain deletion: 1055 passed, 4 skipped
  - Full-suite result AFTER all deletions: 1055 passed, 4 skipped
  - Diff: identical pass/fail/skip sets at every checkpoint
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.1 spec §0a/§2 (MM11.2); zero external importers; all three files are re-export shims with no downstream consumers; the dead chain had no test coverage
- **Change reference:** MM11.2 commit (not yet committed)
- **Slice:** MM11.2
- **Date:** 2026-07-01

---

### MM11.2 — `market_hours.py` (core/data/)

- **What it was:** Legacy backward-compatibility shim re-exporting `MarketHours` from `core.database.utils.market_hours`.
- **Disposition:** REMOVED
- **Gate 1 — proof of non-use:**
  - Python-import grep (`from core.data.market_hours`): zero importers outside the file itself (only self-referencing docstring at line 11).
  - String-literal grep: zero hits in `scripts/`, `docs/`, `config/`, `tests/`.
  - `tests/` contains zero references.
- **Gate 2 — proof of behavior preservation:**
  - Full-suite result BEFORE: 1055 passed, 4 skipped
  - Full-suite result AFTER: 1055 passed, 4 skipped
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.1 spec §0a/§2; zero external importers; re-export shim with no downstream consumers
- **Change reference:** MM11.2 commit (not yet committed)
- **Slice:** MM11.2
- **Date:** 2026-07-01

---

### MM11.2 — `market_session.py` (core/data/)

- **What it was:** Legacy backward-compatibility shim re-exporting market session utilities from `core.database.*`.
- **Disposition:** REMOVED
- **Gate 1 — proof of non-use:**
  - Python-import grep: zero importers outside the file itself (only self-referencing docstring).
  - `tests/`: zero references.
- **Gate 2 — proof of behavior preservation:** 1055/4 both before and after.
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.1 spec §0a/§2; zero external importers.
- **Change reference:** MM11.2 commit (not yet committed)
- **Slice:** MM11.2
- **Date:** 2026-07-01

---

### MM11.2 — `db_tick_aggregator.py` (core/data/)

- **What it was:** Legacy module for aggregating ticks into the database. Re-export shim from `core.database.*`.
- **Disposition:** REMOVED
- **Gate 1 — proof of non-use:**
  - Python-import grep: zero importers outside the file itself.
  - `tests/`: zero references.
- **Gate 2 — proof of behavior preservation:** 1055/4 both before and after.
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.1 spec §0a/§2; zero external importers.
- **Change reference:** MM11.2 commit (not yet committed)
- **Slice:** MM11.2
- **Date:** 2026-07-01

---

### MM11.2 — `websocket_ingestor.py` (core/data/)

- **What it was:** Legacy WebSocket data ingestor module.
- **Disposition:** REMOVED
- **Gate 1 — proof of non-use:**
  - Python-import grep: zero importers outside the file itself.
  - `tests/`: zero references.
- **Gate 2 — proof of behavior preservation:** 1055/4 both before and after.
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.1 spec §0a/§2; zero external importers.
- **Change reference:** MM11.2 commit (not yet committed)
- **Slice:** MM11.2
- **Date:** 2026-07-01

---

### MM11.2 — `recovery_manager.py` (core/data/)

- **What it was:** Legacy recovery manager module for data recovery workflows.
- **Disposition:** REMOVED
- **Gate 1 — proof of non-use:**
  - Python-import grep: zero importers outside the file itself.
  - `tests/`: zero references.
- **Gate 2 — proof of behavior preservation:** 1055/4 both before and after.
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.1 spec §0a/§2; zero external importers.
- **Change reference:** MM11.2 commit (not yet committed)
- **Slice:** MM11.2
- **Date:** 2026-07-01

---

### MM11.2 — `live_market_provider.py` (core/data/)

- **What it was:** Legacy live market data provider shim re-exporting from `core.database.providers`.
- **Disposition:** REMOVED
- **Gate 1 — proof of non-use:**
  - Python-import grep: zero importers outside the file itself.
  - `tests/`: zero references.
- **Gate 2 — proof of behavior preservation:** 1055/4 both before and after.
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.1 spec §0a/§2; zero external importers.
- **Change reference:** MM11.2 commit (not yet committed)
- **Slice:** MM11.2
- **Date:** 2026-07-01

---

### MM11.2 — `duckdb_client.py` (core/data/)

- **What it was:** Legacy DuckDB client backward-compatibility shim re-exporting `db_cursor`/`get_connection` from `core.database.legacy_adapter`. Corrected from "KEEP (verify)" in the 2026-06-04 inventory to REMOVE by §0a fresh verification.
- **Disposition:** REMOVED
- **Gate 1 — proof of non-use:**
  - Python-import grep (`from core.data.duckdb_client`): zero importers outside the file itself (only self-referencing docstring at line 11). `core/data/options_provider.py` imports `duckdb` directly, not `core.data.duckdb_client`.
  - String-literal grep: zero hits in `scripts/`, `docs/` (except MM11 spec), `config/`, `tests/`.
  - `tests/`: zero references.
- **Gate 2 — proof of behavior preservation:** 1055/4 both before and after.
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.1 spec §0a/§2; §0a corrected the 2026-06-04 verdict; zero external importers confirmed by fresh grep at execution time.
- **Change reference:** MM11.2 commit (not yet committed)
- **Slice:** MM11.2
- **Date:** 2026-07-01

---

### MM11.2 — `schema.py` (core/data/)

- **What it was:** Legacy schema backward-compatibility shim re-exporting `BOOTSTRAP_STATEMENTS`/`INDEX_STATEMENTS` from `core.database.schema`. Corrected from "KEEP (verify)" in the 2026-06-04 inventory to REMOVE by §0a fresh verification.
- **Disposition:** REMOVED
- **Gate 1 — proof of non-use:**
  - Python-import grep (`from core.data.schema`): zero importers outside the file itself (only self-referencing docstring at line 11). `scripts/` and `core/database/writers.py` import directly from `core.database import schema`, never from `core.data.schema`.
  - String-literal grep: zero hits in `scripts/`, `docs/` (except MM11 spec), `config/`, `tests/`.
  - `tests/`: zero references.
- **Gate 2 — proof of behavior preservation:** 1055/4 both before and after.
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.1 spec §0a/§2; §0a corrected the 2026-06-04 verdict; zero external importers confirmed by fresh grep at execution time.
- **Change reference:** MM11.2 commit (not yet committed)
- **Slice:** MM11.2
- **Date:** 2026-07-01

---

### MM11.2 — `tick_aggregator.py` (core/data/)

- **What it was:** Legacy tick aggregation module.
- **Disposition:** REMOVED
- **Gate 1 — proof of non-use:**
  - Python-import grep: zero importers anywhere, including self-referencing.
  - `tests/`: zero references.
  - String-literal grep: zero hits.
- **Gate 2 — proof of behavior preservation:** 1055/4 both before and after.
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.1 spec §0a/§2; zero external importers; no file entered any import graph.
- **Change reference:** MM11.2 commit (not yet committed)
- **Slice:** MM11.2
- **Date:** 2026-07-01

---

### MM11.3 — `core/data` package documentation update (documentation-only slice)

- **What it was:** Documentation update for the `core/data` package after MM11.2's 12-file deletion. `core/data/__init__.py` docstring rewritten from "Legacy Data Package - Backward Compatibility Shim" (referencing deleted modules) to accurately describe the remaining two live modules. `docs/PLATFORM_INVENTORY.md` Market Data and Dead Code sections marked superseded, pointing to the MM11 implementation spec and Removal Ledger.
- **Disposition:** DOCUMENTATION ONLY (no code deletions)
- **Package verification:** Remaining `core/data/` contents confirmed: `options_provider.py` (KEEP — options dashboard), `MarketDataFeedV3_pb2.py` (KEEP — protobuf wire schema), `__init__.py`, and `MarketDataFeedV3.proto` (source file). No file moves performed. No `__init__.py` compatibility shims introduced.
- **Gate 1 — proof of non-use:** N/A — documentation-only slice per spec §2 (MM11.3, acceptance criterion 4)
- **Gate 2 — proof of behavior preservation:**
  - Full-suite result BEFORE change: 1055 passed, 4 skipped
  - Full-suite result AFTER change: 1055 passed, 4 skipped
  - Diff: identical pass/fail/skip sets
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.3 spec §2; Planned #7 documentation closure; no code behaviour changed
- **Change reference:** MM11.3 commit (not yet committed)
- **Slice:** MM11.3
- **Date:** 2026-07-01

---

### MM11.4a — `regime_insights` DDL (core/database/schema.py — SIGNALS_REGIME_SCHEMA)

- **What it was:** DuckDB `regime_insights` table DDL — stored HMM regime state snapshots per symbol. Last writer was `AnalyticsWriter.save_regime_snapshot` (removed MM11.1). Last reader was `CaptureEngine._get_previous_regime` (removed MM11.1).
- **Disposition:** REMOVED
- **Gate 1 — proof of non-use:**
  - Python-import grep: `SIGNALS_REGIME_SCHEMA` referenced only in its own definition (schema.py) and `BOOTSTRAP_STATEMENTS` (schema.py). Zero external importers.
  - String-literal grep (`regime_insights`): remaining references in `queries.py:408` (dead `AnalyticsQuery` class — zero importers), `flask_app/blueprints/database.py:20` (generic DB browser — excluded per §0e), and `scripts/migrate_monolith_to_isolated.py:89` (one-time migration — excluded).
- **Gate 2 — proof of behavior preservation:**
  - Full-suite result BEFORE: 1055 passed, 4 skipped
  - Full-suite result AFTER: 1055 passed, 4 skipped
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.4a spec; MM11.1 removed the sole reader and writer; DDL prune is the logical conclusion of MM11.1's deletion
- **Change reference:** MM11.4 commit (not yet committed)
- **Slice:** MM11.4a
- **Date:** 2026-07-01

---

### MM11.4a — `daily_structural_metrics` DDL (core/database/schema.py — SIGNALS_DAILY_METRICS_SCHEMA)

- **What it was:** DuckDB `daily_structural_metrics` table DDL — stored dispersion (CSAD) and volatility (ATR) metrics per day. Last writer was `StructuralMetricsService.update_daily_metrics` (removed MM11.1). Last reader was `CaptureEngine._get_current_metrics` (removed MM11.1).
- **Disposition:** REMOVED
- **Gate 1 — proof of non-use:**
  - Python-import grep: zero references outside schema.py definition and `BOOTSTRAP_STATEMENTS`.
  - String-literal grep: zero hits outside schema.py.
- **Gate 2 — proof of behavior preservation:** 1055/4 both before and after.
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.4a spec; sole writer and reader removed in MM11.1; no remaining consumers.
- **Change reference:** MM11.4 commit (not yet committed)
- **Slice:** MM11.4a
- **Date:** 2026-07-01

---

### MM11.4b — Strategy paper trading DDL (6 tables: ns_paper_signals, ns_paper_trades, v9_paper_signals, v9_paper_trades, stock_paper_signals, stock_paper_trades)

- **What it was:** DDL for six strategy paper-trading tables — Nifty Shield (NS), V9 PM Scalper, and Stock Day-Type paper trading schemas. Removed constants: `NS_PAPER_SIGNALS_SCHEMA`, `NS_PAPER_TRADES_SCHEMA`, `V9_PAPER_SIGNALS_SCHEMA`, `V9_PAPER_TRADES_SCHEMA`, `PAPER_SIGNALS_SCHEMA`, `PAPER_TRADES_SCHEMA`.
- **Disposition:** REMOVED (6 tables as a strategy-residue group)
- **Gate 1 — proof of non-use:**
  - Python-import grep: zero external importers for any of the 6 schema constants. Only referenced within schema.py definitions and `BOOTSTRAP_STATEMENTS`.
  - String-literal grep: `stock_paper_signals`/`stock_paper_trades` referenced only in `flask_app/blueprints/database.py:19` (generic DB browser — excluded). All other table names have zero hits outside schema.py.
  - No Python module writes to or reads from any of these 6 tables.
- **Gate 2 — proof of behavior preservation:** 1055/4 both before and after.
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.4b spec; all six tables are strategy paper-trading residue with no live writers or readers in the platform.
- **Change reference:** MM11.4 commit (not yet committed)
- **Slice:** MM11.4b
- **Date:** 2026-07-01

---

### MM11.4b — Backtest/scanner DDL (5 tables: backtest_runs, backtest_trades, scanner_results, scanner_symbol_results, backtest_run_trades)

- **What it was:** DDL for backtest and scanner tables. Removed constants: `BACKTEST_INDEX_SCHEMA`, `BACKTEST_TRADES_SCHEMA`, `SCANNER_RESULTS_SCHEMA`, `SCANNER_SYMBOL_RESULTS_SCHEMA`, `BACKTEST_RUN_TRADES_SCHEMA`.
- **Disposition:** REMOVED (5 tables as a backtest/scanner residue group)
- **Gate 1 — proof of non-use:**
  - Python-import grep: zero external importers for any of the 5 schema constants. Only referenced within schema.py definitions and `BOOTSTRAP_STATEMENTS`.
  - String-literal grep: `backtest_runs` referenced in `scripts/migrate_monolith_to_isolated.py:140,143` (one-time migration tool — excluded). All other table names have zero hits outside schema.py.
- **Gate 2 — proof of behavior preservation:** 1055/4 both before and after.
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.4b spec; no live writers or readers; backtest and scanner functionality lives outside this repository per ADR-002.
- **Change reference:** MM11.4 commit (not yet committed)
- **Slice:** MM11.4b
- **Date:** 2026-07-01

---

### MM11.4b — Orphaned strategy analytics DDL (3 tables: confluence_insights, regime_snapshots, commodity_strategy_snapshots)

- **What it was:** DDL for three dead strategy-analytics tables. Removed constants: `SIGNALS_INSIGHTS_SCHEMA`, `SIGNALS_REGIME_SNAPSHOTS_SCHEMA`, `TRADING_COMMODITY_STRATEGY_SNAPSHOTS_SCHEMA`.
- **Disposition:** REMOVED (3 tables as strategy-analytics residue group)
- **Gate 1 — proof of non-use:**
  - Python-import grep: zero external importers for any of the 3 schema constants.
  - String-literal grep: `confluence_insights` referenced in `queries.py:380,398` (dead `AnalyticsQuery` class — zero importers), `flask_app/blueprints/database.py:20` (generic DB browser — excluded), and `scripts/migrate_monolith_to_isolated.py:89` (one-time migration — excluded). `regime_snapshots` and `commodity_strategy_snapshots` have zero hits outside schema.py.
- **Gate 2 — proof of behavior preservation:** 1055/4 both before and after.
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.4b spec; last reader of `confluence_insights` was `AnalyticsQuery` (zero importers, RETAINED-WITH-JUSTIFICATION in MM11.1). Last writer was `AnalyticsWriter` (removed MM11.1). Remaining two tables had zero consumers.
- **Change reference:** MM11.4 commit (not yet committed)
- **Slice:** MM11.4b
- **Date:** 2026-07-01

---

### MM11.4b — Orphaned options structural DDL (2 tables: daily_oi_summary, gex_snapshot) + indexes

- **What it was:** DDL for `daily_oi_summary` and `gex_snapshot` tables plus their associated indexes (`idx_daily_oi_date`, `idx_gex_underlying`, `idx_gex_timestamp`). Removed constants: `OPTIONS_DAILY_OI_SUMMARY_SCHEMA`, `OPTIONS_GEX_SNAPSHOT_SCHEMA`.
- **Disposition:** REMOVED
- **Gate 1 — proof of non-use:**
  - Python-import grep: zero external importers for both schema constants.
  - String-literal grep: zero hits in `options_provider.py`, `options_analytics.py`, `options_facade.py`, or `flask_app/blueprints/options.py`. Neither table is written or read by any live code. The live options dashboard uses `option_chain_snapshot` only. No other consumer found anywhere in the repository.
- **Gate 2 — proof of behavior preservation:** 1055/4 both before and after.
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.4b spec; independent re-verification confirms zero live consumers in the options dashboard path; spec's caution note resolved in favour of removal.
- **Change reference:** MM11.4 commit (not yet committed)
- **Slice:** MM11.4b
- **Date:** 2026-07-01

---

### MM11.4b — Orphaned DuckDB `orders`/`positions` duplicate DDL (core/database/schema.py — TRADING_ORDERS_SCHEMA, TRADING_POSITIONS_SCHEMA)

- **What it was:** DuckDB `orders` and `positions` table DDL — orphaned duplicate of the SQLite `execution.db` tables created by `execution_store.py`. Removed constants: `TRADING_ORDERS_SCHEMA`, `TRADING_POSITIONS_SCHEMA`.
- **Disposition:** REMOVED
- **Gate 1 — proof of non-use:**
  - Python-import grep: zero external importers for either schema constant. Not imported by `execution_store.py` (which has its own inline DDL). Only referenced within schema.py definitions and `BOOTSTRAP_STATEMENTS`.
  - String-literal grep: the live `orders`/`positions` table references are all in the SQLite execution path (`execution_store.py`, `order_repository.py`, `position_tracker.py`), none of which reference the schema.py DDL constants.
  - These were flagged as orphaned duplicates in `docs/PROJECT_STATE.md` Phase 0 Ledger Hygiene finding.
- **Gate 2 — proof of behavior preservation:** 1055/4 both before and after.
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.4b spec + PROJECT_STATE.md finding; the DuckDB `orders`/`positions` DDL in schema.py was part of the old architecture's `BOOTSTRAP_STATEMENTS` (zero consumers) and is superseded by the SQLite `execution.db` ledger substrate.
- **Change reference:** MM11.4 commit (not yet committed)
- **Slice:** MM11.4b
- **Date:** 2026-07-01

---

### MM11.4b — `fo_stocks_master` DDL (core/database/schema.py — CONFIG_FO_STOCKS_MASTER_SCHEMA)

- **What it was:** DuckDB `fo_stocks_master` table DDL — duplicate of `fo_stocks` with no writers or readers.
- **Disposition:** REMOVED
- **Gate 1 — proof of non-use:**
  - Python-import grep: zero external importers. Only referenced within schema.py definition and `BOOTSTRAP_STATEMENTS`.
  - String-literal grep: zero hits outside schema.py. Live code reads `fo_stocks` (the active table), never `fo_stocks_master`.
- **Gate 2 — proof of behavior preservation:** 1055/4 both before and after.
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.4b spec; no writers or readers; `fo_stocks` (the live variant) retained.
- **Change reference:** MM11.4 commit (not yet committed)
- **Slice:** MM11.4b
- **Date:** 2026-07-01

---

### MM11.5 — `AnalyticsProvider` ABC (core/database/providers/base.py)

- **What it was:** `AnalyticsProvider` ABC with two abstract methods (`get_latest_snapshot`, `get_market_regime`) — an aspirational analytics-provider interface referencing `DuckDBAnalyticsProvider`/`CachedAnalyticsProvider`/`MockAnalyticsProvider` (docstring-only; no classes exist) and `ConfluenceInsight` (docstring-only; no class exists). Its docstring mentions `TradingRunner` and `AnalyticsPopulator` (neither exist in this repository).
- **Disposition:** REMOVED
- **Gate 1 — proof of non-use:**
  - Python-import grep (`from core.database.providers.base import AnalyticsProvider`): zero importers anywhere.
  - Subclass search (`AnalyticsProvider)` or `(AnalyticsProvider`): zero classes extend `AnalyticsProvider` anywhere in the repo.
  - Method call search (`get_latest_snapshot`, `get_market_regime` on AnalyticsProvider): zero callers anywhere. The `get_market_regime` name also exists on `AnalyticsQuery` in `queries.py` (separate dead class — RETAINED-WITH-JUSTIFICATION in MM11.1).
  - `DuckDBAnalyticsProvider`: zero hits outside docstrings. No class exists.
  - `CachedAnalyticsProvider`: zero hits outside docstrings. No class exists.
  - `MockAnalyticsProvider`: zero hits outside docstrings. No class exists.
  - `ConfluenceInsight`: zero hits outside docstrings. No class exists.
  - Test reference grep: zero hits in `tests/`.
  - Composition-root grep: zero construction sites.
- **Gate 2 — proof of behavior preservation:**
  - Full-suite result BEFORE: 1055 passed, 4 skipped
  - Full-suite result AFTER: 1055 passed, 4 skipped
  - Diff: identical pass/fail/skip sets
- **Gate 3 — full suite passes:** 1055 passed, 4 skipped
- **Gate 4 — why:** MM11.5 spec §0c; `AnalyticsProvider` is a strategy-coupled abstraction with zero implementations, zero consumers, zero tests, and no live path to execution. The three implementer names and `ConfluenceInsight` type were docstring-only aspirational references — no classes exist. Removing the ABC is the correct disposition. `MarketDataProvider` (the canonical, live interface in the same file) is untouched.
- **Change reference:** MM11.5 commit (not yet committed)
- **Slice:** MM11.5
- **Date:** 2026-07-01

---

## MM11.7 Reconciliation Record

To be completed at milestone close (spec §2, MM11.7, acceptance criterion 2): a line-for-line cross-check of the full pre-MM11 → post-MM11 tree diff against the entries above. Every deletion in the diff must have an entry; every entry must correspond to an actual change in the diff. Mismatches in either direction block the Platform v1.0 declaration until resolved.

- **Reconciliation performed:** not yet
- **Result:** —
