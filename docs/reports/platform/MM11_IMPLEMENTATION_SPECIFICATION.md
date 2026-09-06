# MM11 — Platform Consolidation & Infrastructure Freeze

## Implementation Specification

**Date:** 2026-07-01
**Author role:** System Architect
**Status:** Approved by Technical Lead, with a governance amendment (§1.5) — ready for slice-by-slice execution
**Predecessor:** `docs/ARCHITECTURE_DECISIONS.md` ADR-014 (MM11 sequencing — final, not revisited here)
**Inputs:** `docs/reports/MM11_ARCHITECTURE_REVIEW_AND_PROPOSAL.md` Part 3, `docs/PROJECT_STATE.md` Planned #2/#3/#7, `docs/PLATFORM_INVENTORY.md` (2026-06-04)
**Governance:** Controlled decommissioning, not refactoring — every deletion carries a four-part burden of proof (§1.5) and a ledger entry in `docs/reports/MM11_REMOVAL_LEDGER.md`
**Type:** Implementation specification — no code authored under this document

---

## 0. Reference Data — Verification Performed

`docs/PLATFORM_INVENTORY.md` is dated **2026-06-04** — it predates Phase 4C, MM7–MM10, and the LoopDriver build-out entirely. Per CLAUDE.md ("read before modifying," "validate, don't assume"), its file-level verdicts were re-verified against the current tree before this spec finalized scope, rather than copied forward. Two verdicts changed as a result; both are load-bearing for the WBS below. The verification method used here (§0e) is the same method §1.5 now makes mandatory, per-item, for the actual execution — this section demonstrates the method once at spec-writing time; §1.5 requires it repeated and recorded at deletion time, since the tree will have moved on by then.

### 0a. `core/data/*` — re-verified, one finding corrected

Grepping `from core\.data\.<module>` / `import core\.data\.<module>` across the whole repo (not just the 2026-06-04 pass) confirms:

| Module | 2026-06-04 verdict | Current verdict | Evidence |
|---|---|---|---|
| `market_hours`, `market_session`, `db_tick_aggregator`, `websocket_ingestor`, `recovery_manager`, `live_market_provider`, `historical_market_provider` | REMOVE (0 importers) | **Confirmed REMOVE** | 0 external importers today |
| `market_data_provider`, `duckdb_market_data_provider` | REMOVE (pending — self-referential importer) | **Confirmed REMOVE** | Sole importer is `historical_market_provider.py`, itself dead |
| `duckdb_client.py`, `schema.py` | **KEEP (verify)** — "appear live via options path" | **CORRECTED to REMOVE** | `core/data/options_provider.py` imports `duckdb` directly (`options_provider.py:19`), not `core.data.duckdb_client`; grep finds zero external importers of either file |
| `tick_aggregator.py` | not separately verdicted | **REMOVE** | zero importers anywhere, including self |
| `options_provider.py` | KEEP | **Confirmed KEEP** | live: `app_facade/options_facade.py`, `flask_app/blueprints/options.py`, `core/analytics/options_analytics.py`, `tests/data/test_options_provider_snapshot.py` |
| `MarketDataFeedV3_pb2.py` | KEEP | **Confirmed KEEP** | live: `core/database/ingestors/websocket_ingestor.py` (the canonical, non-dead ingestor) |
| `__init__.py` | KEEP | **Confirmed KEEP, but stale** | its own docstring: *"Legacy Data Package - Backward Compatibility Shim ... DEPRECATED: Use core.database instead"* — the package has been self-documenting its own obsolescence, unactioned |

**12 of 15 files in `core/data/` are dead**, not the smaller set the 2026-06-04 inventory identified. This raises the ceiling on Planned #3's actual scope and correspondingly narrows what Planned #7 ("unify market-data lineage") has left to do — see §2, MM11.3.

Note for execution: this table is evidence gathered while writing the spec, not a substitute for the per-item proof §1.5 requires at deletion time. The 2026-06-04 inventory being wrong twice (§0a's own two corrections) is the argument for re-running the check immediately before each deletion, not for trusting this table either.

### 0b. `CaptureEngine` / TLP pipeline — verdict upgraded from REFACTOR to REMOVE (recommended)

Planned #2 (ADR-014) scoped this as "decouple `CaptureEngine`/`metrics_service` inputs from strategy-analytics tables" — a refactor, implying the component stays. Direct verification of the only live composition root (`scripts/fno_runner.py`) shows it should not stay:

- `scripts/fno_runner.py` contains **zero** references to `CaptureEngine`, `capture_engine`, or `StructuralMetricsService`. The `ExecutionHandler.capture_engine` constructor parameter (`core/execution/handler.py:164`) is never supplied a real instance in the only process that runs this platform live. The guard at `handler.py:654` (`if self.capture_engine and signal.signal_type != SignalType.EXIT`) is therefore **always false in production** — not "optional infrastructure," dead code behind an always-false branch.
- `TLPLogger` (`core/analytics/capture.py`) is never instantiated: `init_tlp_logger`, `get_tlp_logger`, and `TLPLogger(` have **zero call sites** anywhere in the repo outside their own definitions.
- The two tables `CaptureEngine.capture_context` reads (`regime_insights`, `daily_structural_metrics`) have **zero live writers**. `StructuralMetricsService.update_daily_metrics` — the only code that inserts into `daily_structural_metrics` — is defined and never called. `save_regime_snapshot` (the only writer of `regime_insights`) has zero callers outside its own re-export chain. Both reads in `capture.py` (`_get_previous_regime`, `_get_current_metrics`) hit `except: pass` and fall through to hardcoded defaults (`"UNKNOWN", 0.0` / `0.0, 0.0`) on every real invocation, and `_calculate_breadth`/`_get_index_trend` are literal stub returns (`0.5` / `"NEUTRAL"`) that were never implemented.

Net effect: even in a hypothetical world where `capture_engine` *were* wired at the composition root, `capture_context()` would return a `TradeStructuralContext` built entirely from stub and fallback values — it has never produced a real structural snapshot in this repository's lifetime. This is not "strategy-coupled infrastructure worth decoupling"; it is fully dead code with no live path to becoming otherwise. §2 (MM11.1) recommends REMOVE over REFACTOR, flagged as a deviation from ADR-014's literal wording, gated on sign-off (§6). This is also the milestone's hardest behavior-preservation case under §1.5's proof #2 (removing an always-false branch is provably behavior-neutral, but "provably" means demonstrated, not asserted — see the MM11.1 proof obligations in §2).

### 0c. New finding not in the original Planned #2/#3/#7 scope: `AnalyticsProvider`

`core/database/providers/base.py` — filed KEEP in the 2026-06-04 inventory as part of the canonical, live provider lineage — defines an `AnalyticsProvider` ABC (`get_latest_snapshot`, `get_market_regime`) whose docstring references `ConfluenceInsight`, a `TradingRunner`, and an `AnalyticsPopulator`, none of which exist anywhere in this repository (consistent with ADR-002 — strategy/analytics-populator code lives outside this repo). No implementer of `AnalyticsProvider` (`DuckDBAnalyticsProvider`, `CachedAnalyticsProvider`, `MockAnalyticsProvider` — all named only in the docstring) was found in this pass. This looks like the same category of strategy-analytics residue as Planned #2, sitting inside a file that was never audited for it because the file's *dominant* role (live bar provision) is legitimately KEEP. Given its own WBS home in MM11.5 below rather than left as a floating observation.

### 0d. Top-level docs — re-confirmed stale, one 2026-03-04 finding now factually false

`README.md:1` still reads "Nifty Market Data Repository." `PROJECT_REVIEW_SUMMARY.md` (dated 2026-03-04) flags `config/credentials.json` as committed (already resolved — gitignored/untracked today, per ADR-014 §3.2 Q4) and flags a missing `requirements.txt` (verified present today). Both documents describe a repository state that no longer exists.

### 0e. Methodology note carried into every slice below

Static Python-import grep (`from core.X import Y`) is necessary but **not sufficient** to prove a DuckDB table or module is dead: table names are also referenced as raw SQL string literals, and `flask_app/blueprints/database.py` is a generic table browser that will match almost any table name in the schema without that constituting semantic use. Every acceptance criterion in §2 that involves deleting a table or module requires **both**: (1) zero Python-import references, and (2) zero raw string-literal references to the table/symbol name outside its own definition and generic tooling (the DB browser, migration scripts) — with the DB browser explicitly excluded as a "live consumer" unless it hardcodes special handling for that specific table. §1.5 elevates this from a methodology note to a mandatory, recorded gate.

---

## 1. MM11 Architecture Specification

### 1.1 Purpose

MM11 removes verified-dead code, verified-orphaned schema, and stale top-level documentation from the platform, and declares **Platform v1.0 Complete** at close. It adds no capability. Per ADR-014, its justification is not that it unblocks anything downstream (§3.1 of the reassessment already proved it doesn't) — it is that its consumer (the codebase and its own documentation) is real and present today, and that these items have been deferred since MM7–MM8 without a milestone ever addressing them.

**Governance framing (Technical Lead amendment, incorporated):** MM11 is executed as a **controlled decommissioning project**, not a refactor. A refactor's default assumption is "this code should keep working, reshaped." A decommissioning's default assumption is "this code is being permanently retired — prove it's safe to retire, don't assume it." Every slice in §2 is written against that stricter default; §1.5 makes the proof obligation explicit and uniform.

### 1.2 Architectural motivation

- **Platform Constitution §10** ("keep the platform smaller") is the governing clause; this milestone is its first dedicated execution, not incidental cleanup folded into a feature milestone.
- **CLAUDE.md Development Conventions** — "No backwards-compatibility shims — delete unused code completely" — applies almost literally to `core/data/__init__.py`, which self-identifies as exactly that.
- **ADR-014** already fixed MM11's scope boundary (Planned #2/#3/#7 + stale docs) and its relationship to MM12 (External Strategy Integration Contract, unaffected, unblocked by this work). This document does not revisit that sequencing decision.
- **Audit-first (Constitution Principle 5):** every deletion in this milestone is preceded by a verification step, not an assumption inherited from a four-milestone-old inventory (§0 demonstrates why that inheritance would have been wrong twice) — and, per the governance amendment, followed by a recorded proof, not just a passing test run.

### 1.3 Design principles for this milestone

1. **Verify current state, not documented state.** Every slice's first acceptance step is a fresh grep/search against the live tree, per §0e's methodology — the 2026-06-04 inventory is a starting hypothesis, not a source of truth.
2. **Delete completely; do not shim.** No `# removed` comments, no re-export stubs, no deprecated-but-present wrappers. If a symbol has zero live callers, it is deleted outright.
3. **No new abstractions.** This milestone produces zero new interfaces, protocols, or configuration surfaces. Its only code changes are deletions and DDL prunes.
4. **Constructor-signature changes get extra scrutiny.** Where a slice touches `ExecutionHandler` (the execution spine), every construction site — including tests — must be audited, not just grepped for the primary import.
5. **Don't relocate working code for cosmetic reasons.** A file being in an awkwardly-named package is not, by itself, sufficient reason to move it (see MM11.3).
6. **Proof before deletion, record after deletion.** (§1.5) No item is removed on the strength of "looks unused" — it is removed once the four-part proof is satisfied and written down.

### 1.4 Boundaries

Out of scope, restated from the governing prompt and unchanged by this document: strategy development, `SignalSource` implementations, broker reconciliation, `MarginProvider`/multi-broker abstractions, deployment automation, new execution/telemetry features, and performance work not required by consolidation itself. Any item whose natural owner is MM12 (External Strategy Integration Contract, per `MM11_ARCHITECTURE_REVIEW_AND_PROPOSAL.md` Part 2) or MM14 (LIVE readiness, broker reconciliation) is explicitly not pulled forward here, including where consolidation work incidentally touches adjacent files.

### 1.5 Governance Model — Controlled Decommissioning (Technical Lead amendment)

This section is binding on every slice in §2 and every entry in the Removal Ledger (below). It supersedes any looser reading of a slice's "Acceptance criteria" as optional or advisory.

**Every deletion target — file, class, function, DDL table, or config entry — must clear all four gates before removal, and the evidence for each gate must be written into `docs/reports/MM11_REMOVAL_LEDGER.md` at the time of removal, not reconstructed afterward:**

1. **Prove the code is unused.** Both halves of §0e's methodology: zero Python-import references AND zero raw string-literal references (SQL, dynamic import, config), excluding generic tooling that doesn't hardcode the specific symbol/table. For a symbol reached only through an always-false runtime branch (e.g. `CaptureEngine`, §0b), "unused" means demonstrating the branch is unreachable in production — cite the composition-root evidence (no live construction) and the guard condition, not just "it's inside an `if`."
2. **Prove removal doesn't alter runtime behavior.** This is stronger than "the test suite is green after." Required: (a) run the full suite **before** the change and record the pass/fail set; (b) make the change; (c) run the full suite **after** and diff against (a) — the sets must be identical (same tests pass, same tests fail, none newly skipped to paper over a break); (d) for any deletion touching a constructor signature or a runtime-reachable branch (not just provably-dead code), add or point to a characterization test that exercises the code path being removed and shows its output is unchanged for every caller that remains, or explicitly show no such caller exists.
3. **Prove all tests still pass.** The full suite (not a subset) is run at the point of each deletion, not batched to the end of a slice — per-table and per-module incremental removal (already specified in MM11.4b, MM11.2) is the default working method for exactly this reason: it isolates which single removal caused a regression, if any.
4. **Document exactly what was removed and why.** A ledger entry (template below) is written for every deletion target at the time it is removed: what it was, the evidence for gates 1–3, the commit/change reference, and the one-sentence "why" (which Planned item or finding justified it). This is not the same as the slice-level summary in `docs/CHANGELOG_PLATFORM.md` (MM11.7) — the changelog entry is the milestone-level rollup; the ledger is the item-level audit trail the rollup is built from.

**Required artifact:** `docs/reports/MM11_REMOVAL_LEDGER.md`, created now (empty, templated) as part of accepting this specification, and appended to by every slice as it executes. MM11.7 does not write the ledger retroactively — it verifies the ledger is complete and matches the actual diff, then rolls it up into the changelog and closes the milestone. A slice is not "done" if code was deleted but no ledger entry exists for it, regardless of whether tests pass.

**What this changes about §2 below:** every slice's "Acceptance criteria" list is read as a *subset* of what §1.5 requires, not a replacement for it — where a slice's own criteria already name specific greps or tests, those satisfy gate 1/3 for that slice; gate 2's before/after suite diff and gate 4's ledger entry apply uniformly and are not repeated in every slice's bullet list below to avoid duplication, but are non-optional for all of them.

---

## 2. Work Breakdown Structure

Every slice below is executed under §1.5. Each slice's listed acceptance criteria are in addition to, not instead of, the four-part proof and ledger entry.

### MM11.1 — Retire the unwired TLP / `CaptureEngine` pipeline

**Objective:** Remove `CaptureEngine`, `StructuralMetricsService`, `TLPLogger`, and the `capture_engine` seam from `ExecutionHandler` — confirmed dead code, not confirmed-live-but-strategy-coupled code (§0b).

**Files affected:**
- Delete: `core/analytics/capture.py`, `core/analytics/metrics_service.py`
- Modify: `core/execution/handler.py` — remove `capture_engine` constructor parameter, the `self.capture_engine` assignment, the `if self.capture_engine and ...` branch at handler.py:654, and the `from core.analytics.capture import CaptureEngine` import
- Modify: any test construction sites passing `capture_engine=` to `ExecutionHandler` (audit required — do not assume the primary import grep found them all; keyword-argument construction can appear without importing the class in the same file)
- Modify (contingent on §0e verification): `core/database/legacy_adapter.py`, `core/database/__init__.py`, `core/database/writers.py`, `core/database/queries.py` — remove `save_signal`/`save_insight`/`save_insights`/`save_insights_batch`/`save_regime_snapshot`/`get_latest_insights` **only if** the per-symbol audit in the acceptance criteria confirms zero remaining live callers after this slice's handler.py change. Do not remove speculatively; some of `legacy_adapter.py`'s surface (`db_cursor`, `get_connection`, `get_db`) may still be used by modules that have not migrated to `DatabaseManager` directly — verify each symbol independently, do not gut the file wholesale.

**Architectural justification:** §0b. This is a deviation from ADR-014's literal "decouple" wording for Planned #2 — presented here as a recommendation, not a unilateral re-decision. See §6.

**Burden-of-proof note specific to this slice (§1.5 gate 2):** this is the milestone's one case of removing a *reachable-in-principle but always-false-in-production* branch, not a fully dead file. The proof obligation is: (a) show `capture_engine` is never passed a non-`None` value at any construction site in `scripts/` (composition roots) — satisfied by exhaustive grep, not sampling; (b) show every test that *does* pass a real `CaptureEngine` is a test of `CaptureEngine` itself (deleted alongside it) and not a test of `ExecutionHandler`'s behavior with capture enabled; if such a test exists, its disappearance is itself evidence of a behavior this deletion changes, and the slice must stop and re-scope rather than delete the test to make the diff clean.

**Acceptance criteria:**
1. Fresh grep of `scripts/fno_runner.py` and all `ExecutionHandler(` construction sites (prod + test) for `capture_engine=` — zero non-`None` construction sites confirmed before the change; zero references at all after.
2. `capture.py`, `metrics_service.py` deleted; `grep -r "CaptureEngine\|StructuralMetricsService\|TLPLogger\|capture_engine"` across the repo returns zero hits outside git history and this spec/ledger.
3. Per-symbol audit of `legacy_adapter.py`/`writers.py`/`queries.py` exports named above: each removed only if independently confirmed to have zero callers (import **and** string-literal) after step 1.
4. Before/after full-suite diff (§1.5 gate 2) attached to the ledger entry, not just a final "suite green" statement.
5. `ADR-015` drafted (see §6) recording the REFACTOR→REMOVE correction with the evidence in §0b, before this slice is marked complete.
6. Removal Ledger entries written for `CaptureEngine`, `StructuralMetricsService`, `TLPLogger`, the `capture_engine` handler seam, and each `legacy_adapter`/`writers`/`queries` symbol actually removed.

**Dependencies:** None — self-contained. Should complete before MM11.4a (regime_insights/daily_structural_metrics DDL prune), which depends on this slice's table-reader removal.

---

### MM11.2 — Remove dead `core/data/*` legacy twins

**Objective:** Delete the 12 confirmed-dead modules in `core/data/`, per §0a.

**Files affected:**
- Delete: `core/data/{market_hours,market_session,db_tick_aggregator,websocket_ingestor,recovery_manager,live_market_provider,historical_market_provider,market_data_provider,duckdb_market_data_provider,duckdb_client,schema,tick_aggregator}.py`
- Unchanged: `core/data/options_provider.py`, `core/data/MarketDataFeedV3_pb2.py` (both confirmed live, §0a)
- Modify: `core/data/__init__.py` — see MM11.3 (its docstring rewrite is sequenced there, since it depends on this slice's outcome)

**Architectural justification:** Zero external importers for all 12 files, confirmed by fresh grep (§0a), correcting two files (`duckdb_client.py`, `schema.py`) the 2026-06-04 inventory had marked "KEEP (verify)." No test imports any of the 12.

**Acceptance criteria:**
1. Per-file grep (`from core.data.<name>` / `import core.data.<name>`) confirms zero importers outside the file itself immediately before deletion — re-run at execution time, not copied from §0a, in case intervening work changed the graph. Delete one file (or one tightly-coupled cluster, e.g. the `historical_market_provider`→`market_data_provider`→`duckdb_market_data_provider` chain) at a time, per §1.5 gate 3's incremental-isolation rationale.
2. `tests/` contains no references to any of the 12 deleted modules (confirmed already in §0a; re-verify).
3. Before/after full-suite diff per deletion batch (§1.5 gate 2).
4. No raw-string references to the deleted modules' filenames in `scripts/`, `docs/`, or config (e.g. no dynamic import by string).
5. One Removal Ledger entry per file (or per tightly-coupled cluster, if deleted atomically), each with its own import/string-literal evidence.

**Dependencies:** None — fully independent of MM11.1. Must complete before MM11.3, which reasons about the post-deletion shape of `core/data/`.

---

### MM11.3 — `core/data` package retirement (rescoped Planned #7)

**Objective:** Close out Planned #7 ("unify the `core/data` ↔ `core/database/providers` market-data lineage") against what actually remains after MM11.2, rather than the broader duplication the 2026-06-04 inventory assumed existed.

**Rescoping, stated explicitly:** After MM11.2, `core/data/` contains exactly three files: `options_provider.py` (live), `MarketDataFeedV3_pb2.py` (live), `__init__.py`. There is no remaining duplicated *lineage* to unify — MM11.2 already removed the duplication. What Planned #7 has left to do is a documentation and verification closure, not a code consolidation.

**Recommendation — do not relocate `options_provider.py` or `MarketDataFeedV3_pb2.py`:** Both are correctly-functioning, tested, and explicitly documented at their current paths in CLAUDE.md's "Key Directories" table (`core/data/options_provider.py` is named there verbatim). Moving them would require updating CLAUDE.md, `app_facade/options_facade.py`, `flask_app/blueprints/options.py`, `core/analytics/options_analytics.py`, and `tests/data/test_options_provider_snapshot.py` for zero architectural benefit — a cosmetic rename that violates the "no over-engineering" convention and introduces regression risk in a live, options-dashboard-serving path for no functional gain. This is presented as a recommendation the Technical Lead can override; #7 is ADR-sanctioned scope, so if a package-boundary rename is still wanted, it is at minimum sequenced after this slice's alternative is considered and rejected explicitly, not silently.

**Files affected:**
- Modify: `core/data/__init__.py` — rewrite the docstring to describe the actual post-MM11.2 shape (two live modules: options-chain ingest + protobuf wire schema — not a "mixed legacy directory" or a "backward compatibility shim," since the shim content it described is now gone)
- Modify: `docs/PLATFORM_INVENTORY.md` — correct the Market Data and Dead Code sections to reflect §0a's verified current state, or mark the document superseded by this spec for those sections (see MM11.7)

**Architectural justification:** §0a; Constitution §10 is satisfied by MM11.2's deletion, not by a further move. This slice's role is closing the loop with accurate documentation, consistent with the "no over-engineering" and "read before modifying" conventions.

**Acceptance criteria:**
1. `core/data/__init__.py` docstring no longer claims to be a "backward compatibility shim" or references any of the 12 deleted modules.
2. `PLATFORM_INVENTORY.md`'s Market Data / Dead Code sections either corrected in place or explicitly marked superseded, pointing to this document.
3. No file moves performed unless the Technical Lead overrides the recommendation above, in which case a new acceptance criterion set is required before proceeding (not defaulted to under this spec).
4. This slice is documentation-only (no deletion target), so §1.5's four-part proof does not apply to it directly — noted here so its absence from the ledger isn't mistaken for an omission.

**Dependencies:** Requires MM11.2 complete (reasons about its output). Independent of MM11.1/MM11.4/MM11.5.

---

### MM11.4 — Prune strategy-specific schema DDL

Split into two independently-schedulable sub-slices — the original Planned #2/#3 framing implied a single coupled cleanup; verification shows the coupling is narrower than that.

#### MM11.4a — `regime_insights` / `daily_structural_metrics` DDL

**Objective:** Remove the two tables whose sole Python-level consumer is the `CaptureEngine`/`StructuralMetricsService` pair deleted in MM11.1.

**Files affected:** `core/database/schema.py`, `core/database/queries.py`, `core/database/writers.py` — remove `regime_insights`, `daily_structural_metrics` DDL and any writer/reader methods proven dead by the MM11.1 removal.

**Dependencies:** **Hard dependency on MM11.1** — must not run before it (these tables' only reader/writer is deleted there).

**Ledger note:** each table is its own deletion target under §1.5 — two ledger entries, each citing MM11.1's completion as the gate-1 precondition (the reader/writer no longer exists) plus this slice's own independent string-literal re-check (a table can have SQL-string references beyond the one Python reader that was removed).

#### MM11.4b — Remaining strategy-shaped DDL

**Objective:** Verify and, where confirmed dead, remove the remaining strategy-analytics DDL identified in `core/database/schema.py`: `ns_paper_signals`, `ns_paper_trades`, `v9_paper_signals`, `v9_paper_trades`, `stock_paper_signals`, `stock_paper_trades`, `backtest_runs`, `backtest_trades`, `scanner_results`, `scanner_symbol_results`, `fo_stocks`, `fo_stocks_master`, `commodity_strategy_snapshots`, `confluence_insights`, `regime_snapshots`, `runner_state`, `option_chain_snapshot`, `daily_oi_summary`, `gex_snapshot` — plus the orphaned duplicate `orders`/`positions` DDL already flagged in `docs/PROJECT_STATE.md` (superseded by the SQLite `data/execution.db` ledger substrate, per the Phase 0 Ledger Hygiene entry).

**Note on `option_chain_snapshot`/`daily_oi_summary`/`gex_snapshot`:** these look adjacent to the live Options Infrastructure pillar (which is explicitly KEEP and out of scope for deletion) — a first grep in this pass found no reference to them in `options_provider.py` or `options_analytics.py`, suggesting they may be orphaned rather than options-dashboard-serving, but this **must be independently re-confirmed** before removal given the cost of accidentally breaking a live, KEEP-classified dashboard feature. Do not remove without that confirmation.

**Architectural justification:** Constitution §10; these tables carry no corresponding live application code found in this pass (`writers.py`/`queries.py` have no typed methods for most of them — the DDL appears to predate or outlive its Python callers).

**Acceptance criteria (both sub-slices):**
1. Per-table application of the §0e two-sided methodology (Python import + string-literal SQL reference), explicitly excluding `flask_app/blueprints/database.py`'s generic browsing as a live consumer.
2. `option_chain_snapshot`/`daily_oi_summary`/`gex_snapshot` specifically re-verified against the live options dashboard path before inclusion in the removal set.
3. Full test suite green **before and after each individual table's removal** (§1.5 gate 2/3) — one table per commit, one ledger entry per table, so a regression is attributable to exactly one removal.
4. `docs/PROJECT_STATE.md`'s orphaned-`orders`/`positions`-DDL note is resolved (table removed or explicitly re-justified as retained) as part of this sub-slice, with its own ledger entry either way (retention-with-justification is a valid ledger outcome, not only deletion).

**Dependencies:** MM11.4b is independent of MM11.1/MM11.4a — the ~15 other tables' fate does not depend on the capture-engine removal. Can run in parallel with MM11.1/MM11.2/MM11.3.

---

### MM11.5 — Resolve the `AnalyticsProvider` strategy-coupled ABC

**Objective:** Investigate and, if confirmed dead, remove `AnalyticsProvider` (and its docstring-only implementers `DuckDBAnalyticsProvider`/`CachedAnalyticsProvider`/`MockAnalyticsProvider`, if they exist anywhere as real classes) from `core/database/providers/base.py` — a newly-discovered residue surface (§0c) inside an otherwise-KEEP canonical file.

**Files affected:** `core/database/providers/base.py`, plus wherever the named implementer classes are found (unconfirmed as of this spec — first task of this slice is locating them, if they exist at all beyond the docstring).

**Architectural justification:** Same category as Planned #2 (strategy-analytics coupling inside platform infrastructure) — surfaced only by direct file inspection during this milestone's verification pass, not previously catalogued. Consistent with Constitution §10 and the "verify current state" principle (§1.3).

**Acceptance criteria:**
1. Confirm whether `DuckDBAnalyticsProvider`/`CachedAnalyticsProvider`/`MockAnalyticsProvider` exist as real classes anywhere in the repo, or are docstring-only aspirational references.
2. If real and unimplemented-by-anything-live: remove `AnalyticsProvider` and its implementers along with the `get_market_regime`/`ConfluenceInsight`-shaped surface, with a ledger entry per removed class.
3. If a live caller is found: **stop and re-scope** — this would mean the §0c finding was wrong, and the item is escalated for a fresh decision rather than force-fit into this milestone. Record this outcome in the ledger too (a "found live, retained" entry is a valid, required record — §1.5 gate 4 documents decisions, not only deletions).
4. `core/database/providers/base.py`'s remaining, confirmed-live `AnalyticsProvider`-free surface passes the full test suite unchanged, before/after diffed.

**Dependencies:** Independent of all other slices. Low risk of touching anything else since the file's dominant (KEEP) role is untouched.

---

### MM11.6 — Top-level documentation rewrite

**Objective:** Bring `README.md` and `PROJECT_REVIEW_SUMMARY.md` in line with the platform's actual, current state.

**`README.md`:** Rewrite to describe the trading platform CLAUDE.md documents, not a "Market Data Repository." Before discarding the existing directory-layout content (reference/historical/instrument-master structure), verify against the actual `data/` tree whether it is still accurate; if so, preserve it as a relocated `docs/DATA_LAYOUT.md` reference rather than deleting genuinely-useful, still-correct material. `README.md` itself becomes the platform-level entry point: what this repository is, quickstart, pointer to `CLAUDE.md`/`docs/`.

**`PROJECT_REVIEW_SUMMARY.md`:** Recommended disposition — **relocate to `docs/reports/` with a superseded-marker header**, not rewrite in place and not delete. It is a dated, point-in-time external review of a codebase state that no longer exists (§0d); rewriting it to look "current" would misrepresent what it is (a review snapshot, like every other `docs/reports/*` artifact in this repository), and deleting it destroys a historical decision record the Audit-First principle argues for keeping. This mirrors how this repository already treats every other historical report — none of the `MM*`/`G1*` reports get rewritten as history moves past them; they get superseded by newer ones.

**Acceptance criteria:**
1. `README.md` accurately describes the platform per CLAUDE.md; no directory-layout content is deleted without first verifying its current accuracy.
2. `PROJECT_REVIEW_SUMMARY.md` relocated under `docs/reports/` with a header noting supersession and pointing to this spec and ADR-014 §3.2 Q4 for the resolved-findings context.
3. No top-level document contradicts CLAUDE.md after this slice.
4. Documentation-only — no §1.5 deletion-proof applies, but the *relocation* of `PROJECT_REVIEW_SUMMARY.md` still gets a ledger entry (moved, not deleted, with rationale) for the same audit-trail reason.

**Dependencies:** None technically, but best sequenced after MM11.1–MM11.5 so it can describe the *post-consolidation* repository accurately rather than needing a second pass.

---

### MM11.7 — Roadmap / ADR / PROJECT_STATE synchronization and Platform v1.0 declaration

**Objective:** Close the milestone. Update `docs/PROJECT_STATE.md` (Planned #2/#3/#7 → Completed), `docs/CHANGELOG_PLATFORM.md`, author `ADR-015` (§6), verify the Removal Ledger, and declare **Platform v1.0 Complete**.

**Files affected:** `docs/PROJECT_STATE.md`, `docs/CHANGELOG_PLATFORM.md`, `docs/ARCHITECTURE_DECISIONS.md` (ADR-015), `docs/PLATFORM_INVENTORY.md` (final correction pass, if not fully resolved in MM11.3), `docs/reports/MM11_REMOVAL_LEDGER.md` (verification pass, not new entries).

**Acceptance criteria:**
1. All of §4 (Definition of Done) satisfied; every prior slice's acceptance criteria confirmed green in one final full-suite run.
2. **Ledger reconciliation:** `git diff` (or equivalent) against the pre-MM11 tree is cross-checked line-for-line against `MM11_REMOVAL_LEDGER.md` — every deletion in the diff has a ledger entry, and every ledger entry corresponds to an actual deletion in the diff. Mismatches in either direction block the v1.0 declaration until resolved.
3. `CHANGELOG_PLATFORM.md`'s MM11 entry is a rollup of the ledger (references it), not a re-derivation of it.

**Dependencies:** Last slice — depends on MM11.1 through MM11.6 all being complete.

---

## 3. Dependency Analysis

```
MM11.1 (capture/TLP removal) ──┬──> MM11.4a (regime_insights / daily_structural_metrics DDL)
                                │
MM11.2 (dead core/data twins) ──> MM11.3 (core/data retirement + docs)

MM11.4b (remaining strategy DDL) ─── independent
MM11.5  (AnalyticsProvider)      ─── independent
MM11.6  (top-level docs)         ─── independent (sequenced last for accuracy, not blocked)

All of the above ──────────────────> MM11.7 (ledger reconciliation + sync + v1.0 declaration)
```

**Independently startable immediately, in parallel, with no shared file surface:**
- MM11.1 (touches `core/analytics/*`, `core/execution/handler.py`, `core/database/legacy_adapter.py`/`writers.py`/`queries.py`)
- MM11.2 (touches only `core/data/*`)
- MM11.4b (touches `core/database/schema.py`/`queries.py`/`writers.py` — **note: shares files with MM11.1's contingent legacy_adapter/writers/queries changes**; run MM11.1 first if both touch the same symbols to avoid merge conflicts, though they act on disjoint table sets)
- MM11.5 (touches only `core/database/providers/base.py`)

**Sequenced (hard dependency):**
- MM11.3 after MM11.2
- MM11.4a after MM11.1
- MM11.7 after everything, including a full ledger reconciliation pass

**File-surface caution:** MM11.1 and MM11.4b both edit `core/database/writers.py`/`queries.py`, even though they act on disjoint tables (TLP/regime tables vs. the ~15 other strategy tables). Recommend running MM11.1 to completion before starting MM11.4b to avoid a merge conflict in these shared files, even though there is no *logical* dependency between them.

**Safest execution order:** MM11.2 → MM11.3 (one track) in parallel with MM11.1 → MM11.4a (another track); MM11.4b and MM11.5 slotted in whenever convenient (independent, low risk); MM11.6 once the other tracks are far enough along to describe accurately; MM11.7 last, gated on ledger reconciliation.

---

## 4. Definition of Done

MM11 is complete only when:

1. All twelve confirmed-dead `core/data/*` modules are deleted (MM11.2); `core/data/` contains only `options_provider.py`, `MarketDataFeedV3_pb2.py`, `__init__.py` (MM11.3).
2. `CaptureEngine`, `StructuralMetricsService`, `TLPLogger`, and the `capture_engine` seam are removed from `ExecutionHandler` and the codebase (MM11.1), with `ADR-015` recording the REFACTOR→REMOVE correction.
3. `regime_insights`, `daily_structural_metrics`, and every other strategy-shaped DDL table confirmed dead under the §0e methodology are removed from `core/database/schema.py`/`queries.py`/`writers.py` (MM11.4a/b), including the previously-flagged orphaned `orders`/`positions` duplicate.
4. `option_chain_snapshot`/`daily_oi_summary`/`gex_snapshot` have an explicit, re-confirmed disposition (removed or retained-with-justification) — not silently skipped.
5. `AnalyticsProvider` and its docstring-referenced implementers in `core/database/providers/base.py` have an explicit resolution (removed, or escalated with a documented reason if a live caller is found).
6. `README.md` and `PROJECT_REVIEW_SUMMARY.md` no longer describe a repository state that doesn't exist; `PROJECT_REVIEW_SUMMARY.md` is relocated to `docs/reports/` with a supersession header.
7. `docs/PROJECT_STATE.md` Planned #2, #3, #7 are marked Completed with evidence references; `docs/PLATFORM_INVENTORY.md`'s corrected sections (or supersession note) are in place.
8. `docs/CHANGELOG_PLATFORM.md` records the milestone; `ADR-015` is accepted.
9. The full test suite passes with zero regressions, verified by a before/after diff **at every individual deletion**, not merely a single green run at the end (§1.5 gate 2/3).
10. **`docs/reports/MM11_REMOVAL_LEDGER.md` exists, is complete, and reconciles exactly against the tree diff** (MM11.7 acceptance criterion 2) — every deletion has an entry; every entry has an actual, corresponding deletion.
11. No new abstractions, interfaces, or configuration surfaces exist that didn't exist before MM11 started (§1.3).
12. **Platform v1.0 Complete is declared** in `docs/PROJECT_STATE.md`, and that declaration cites the ledger as its evidentiary basis — not just "tests pass."

---

## 5. Risk Analysis

| Slice | Architectural risk | Regression risk | Required tests | Rollback strategy |
|---|---|---|---|---|
| MM11.1 | Deviates from ADR-014's literal "decouple" wording (REMOVE vs REFACTOR) — mitigated by ADR-015 sign-off gate (§6) | `ExecutionHandler` constructor signature change; a missed `capture_engine=` construction site (esp. in tests) breaks instantiation, not just behavior | Full `tests/execution/` suite, before/after diffed; explicit grep-audit of every `ExecutionHandler(` call site before and after | Revert the single commit; the deleted files and the handler diff are independently revertible (no other slice depends on this one except MM11.4a) |
| MM11.2 | None — verified zero external importers, self-documented shim | Very low; a missed dynamic/string-based import would surface as an `ImportError` immediately on next run | Full suite per deletion batch; explicit `tests/data/` sweep | Revert the deletion commit; no other file was modified |
| MM11.3 | Recommendation (no-move) could be overridden by the Technical Lead, changing this slice's scope after the fact | If overridden and a move happens anyway: import-path churn across 4 live files + CLAUDE.md, real regression surface | If override chosen: full app_facade/options + flask_app/blueprints/options test coverage, manual options-dashboard smoke check | Revert the docstring/inventory-doc commit; trivial (no code touched under the recommended path) |
| MM11.4a | Depends correctly on MM11.1 landing first — sequencing error would delete a table still read by dead-but-not-yet-removed code | Low once MM11.1 lands; DuckDB DDL removal on dev/local files is a schema-definition change, not a data-destructive production migration | `tests/database/` schema tests; full suite before/after each table | Revert DDL removal commit (per-table, not batched) |
| MM11.4b | Highest risk of the milestone: 18+ tables, several with unconfirmed read paths (`option_chain_snapshot`/`daily_oi_summary`/`gex_snapshot` adjacent to live Options Infra) | A false-dead table taken out from under a live consumer breaks the options dashboard or DB browser silently until exercised | Incremental removal (one table per commit) + full suite between each; manual options-dashboard smoke check after touching the three ambiguous tables | Per-table commits enable single-table revert without unwinding the whole slice |
| MM11.5 | New finding, not previously scoped or reviewed — risk of scope surprise if implementers turn out to be live | If a live caller is found, this slice must stop and escalate rather than force a fit (explicit acceptance criterion #3) | Grep-confirm zero implementers before any deletion; full suite | Revert; independent of every other slice |
| MM11.6 | Discarding still-accurate `README.md` directory-layout content without verifying it first | Low (docs-only) but a wrong rewrite misleads future onboarding | None (no code) — verification is manual cross-check against `data/` tree | Revert the doc commit |
| MM11.7 | Ledger reconciliation could surface an undocumented deletion from an earlier slice, blocking the v1.0 declaration until backfilled | None directly (docs-only), but a reconciliation failure is a process signal that §1.5 wasn't followed somewhere upstream | Full suite as final gate; ledger-vs-diff reconciliation as a second, independent gate | Revert the doc commit; if reconciliation fails, the fix is backfilling the missing ledger entry, not reverting completed work |

---

## 6. Important Constraints — Explicit Deviations From the Existing Plan

Per the governing instructions for this document, deviations from ADR-014's existing scope are stated here rather than silently substituted:

1. **`CaptureEngine`/TLP: REMOVE, not REFACTOR** (MM11.1). ADR-014 scoped Planned #2 as "decouple ... inputs." Verification (§0b) shows the component has no live path to execution at all — decoupling code that is already unreachable in production adds no value over removing it, and leaving it in place after "decoupling" would still violate "no backwards-compatibility shims — delete unused code completely." **Recommended, gated on Technical Lead sign-off, recorded as ADR-015** (new — this document does not itself author ADR-015; it names it as a required deliverable of MM11.1's completion).
2. **Planned #7 is narrower than originally scoped** (MM11.3). The 2026-06-04 framing ("unify duplicated lineages") assumed more duplication existed than verification confirms remains after MM11.2. The recommended resolution is documentation-only, not a code consolidation, with an explicit no-move recommendation for the two live files.
3. **A new item is added: `AnalyticsProvider`** (MM11.5), discovered during this milestone's own verification pass, not present in Planned #2/#3/#7 or ADR-014. Justified in §0c/§2 as the same category of residue Planned #2 already targets, simply missed because it lives inside a nominally-KEEP file.
4. **`PROJECT_REVIEW_SUMMARY.md` is relocated with a supersession header, not rewritten in place** (MM11.6) — treated as a historical artifact consistent with how every other `docs/reports/*` document in this repository is treated, rather than edited to appear current.
5. **Governance model added (§1.5), per Technical Lead direction on approval.** MM11 is executed as a controlled decommissioning project: every deletion requires proof of non-use, proof of behavior preservation (before/after suite diff, not a single post-hoc green run), proof the full suite passes, and a ledger record — enforced via the new `docs/reports/MM11_REMOVAL_LEDGER.md` artifact and the reconciliation gate added to MM11.7's acceptance criteria. This does not change *what* is removed (§2's scope is unchanged) — it changes the evidentiary bar for removing it, and is why the v1.0 declaration in the Definition of Done (§4) is now conditioned on the ledger, not on a passing test run alone.

None of these deviations change MM11's boundaries from §1.4 or reopen ADR-014's sequencing decision — they are corrections to *what specific work items* fall inside the boundary ADR-014 already drew, and (per #5) a strengthening of the *evidentiary discipline* applied while doing that work, based on verified current-state evidence gathered while writing this specification and on direct Technical Lead instruction.

---

*Ref: `docs/ARCHITECTURE_DECISIONS.md` ADR-002, ADR-014; `docs/PROJECT_STATE.md` Planned #2/#3/#7; `docs/PLATFORM_INVENTORY.md`; `docs/reports/MM11_ARCHITECTURE_REVIEW_AND_PROPOSAL.md`; `docs/reports/MM11_REMOVAL_LEDGER.md`; `docs/reports/MM10_ARCHITECTURE_ROADMAP.md` (structural precedent); CLAUDE.md (Development Conventions).*
