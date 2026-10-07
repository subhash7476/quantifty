# Repo debugging session — 2026-10-07 (session 1)

Branch `fix/reliance-regime-panel-cache` (worktree `F:\Nifty_opsfix`), cut from `origin/main` `ca5dbb2` (PR #40 merged).
All runs were in worktrees (`F:\Nifty_opsfix`, `F:\Nifty_base`); nothing was run in the live `F:\Nifty` checkout.

## 1. The "stall at 66%" — root cause found and fixed

Both earlier full-suite runs appeared to hang at ~66%. It was not a hang.

- Position: 66% of the 3,357 collected tests falls in `tests/ptms` → `tests/reliance_regime`.
- `tests/reliance_regime` alone took **25:36**; six tests cost 147–359 s each (e.g. `test_timing_study_deterministic` 359 s).
- Cause: `scripts/reliance_regime/data.py::load_index_context()` opens one DuckDB file per session date (~3,563 files) per call
  (150–230 s). `build_panel()` had no cache and was called ≥7 times across the tests (two module fixtures, `run()` ×3, `test_signals` ×2).
- Fix (commit `2d5aa1a`): `build_panel()` loads once per process (`functools.lru_cache`) and returns an independent copy.
  Tests: `tests/reliance_regime/test_data_cache.py` (RED first). Directory now **4:18**; 25 passed.
- Full suite on this tree: **14:13** (was effectively unbounded), 3,227 passed, 72 failed, 60 skipped.

## 2. The 72 failures — classified (identical on the pre-fix baseline; 0 regressions)

Same 72 fail on `F:\Nifty_base` (09af31d, before PR #40 and this fix). Failure sets diffed: 0 only-on-branch, 0 only-on-base.

| Count | Where | Cause | Class |
|---|---|---|---|
| ~25 | `tests/msi/*` | `ArtifactIntegrityError: Checksum mismatch for 'metadata.json'` — **line endings** (see §3) | **real latent defect** |
| 30 | `tests/analog_path/*` | `NoneType … .valid/.era/.bars/.grid_prices` — no `data/market_data/...` in a worktree | environmental |
| 5 | `tests/sfb/test_f1_feasibility_screen.py`, 5 `tests/isd/test_gates.py`, `csmp/test_phase0_5`, `database/…calendar`, `runtime/…calendar` | `IOException: Cannot open … equity_bhavcopy.duckdb / futures_bhavcopy.duckdb` | environmental |
| 3 | `g1/test_g1_closure_guard` ×2, `ptms/test_gann_run_screen::test_guard_refuses_on_the_current_repository` | documented standing reds on main | known |

"Environmental" = data stores are gitignored, so a worktree has none; those tests need a data-complete checkout.

## 3. Latent defect: artifact checksums depend on the checkout's line endings

`core.autocrlf=true` (system gitconfig) converts LF blobs to CRLF in the working tree. The DRA loader checksums **raw bytes**
(`core/msi/dra/filesystem_artifact_loader.py:222`), and the two artifact sets assume opposite endings:

- `tests/msi/fixtures/test_artifact/*`: manifest matches **LF**. Fresh Windows checkout → CRLF → mismatch (25 tests). The live checkout
  passes only because its fixture files happen to be LF on disk (`i/lf w/lf`).
- `core/msi/artifacts/forward_vol_v2/*` (certified MSRP Phase 5A): manifest matches **CRLF** (raw-ok, LF-bad on the live checkout);
  committed blob is LF. It verifies only where autocrlf produces CRLF; any LF checkout (Linux/CI) fails. Used by `scripts/msrp/*`
  (research validation), not by live trading.

Not fixed: `forward_vol_v2` is a certified artifact, and normalising in the loader would break it while fixing the fixture. Options
for the operator: (a) `.gitattributes` `-text` on both artifact dirs + regenerate the `forward_vol_v2` manifest on the committed
bytes (re-certification question); (b) normalise in the loader and regenerate both manifests; (c) leave and document.

## 4. Open items for the next session

- **Gate 8** (full regression green at the window's platform commit) cannot be evidenced from a worktree. It needs a data-complete
  checkout; the only one is the live `F:\Nifty`. Decide whether to run there while the orchestrator is stopped (tests are expected to
  use `tmp_path`, but a 2026-09-11 incident deleted a live store when a test did not — see CLAUDE.md pitfalls).
- `data.py` hard-codes `F:\Nifty\data\...`; `reliance_regime` tests therefore read the live stores from any checkout.
- Live `F:\Nifty` main is still behind `origin/main` (PR #40 merged 14:59 IST); pull and re-verify the E008 hash before 09:10 on 10-08.
- Not yet examined: the failing-test classification above rests on error messages for the data-dependent groups; a data-complete
  run would confirm they pass there.

## 5. Addendum — full regression in the live checkout (data-complete), 2026-10-07 19:40–20:14

`F:\Nifty` at `f2c2d00` (main after PR #40 + #38 merged; E008 hash `b33f5c3f…` verified), orchestrator stopped, no panel-cache fix
(PR #41 unmerged, so `reliance_regime` still ran its slow path). **5 failed, 3,392 passed, 17 skipped, 33:57.**

The 5 failures are exactly the documented standing reds, i.e. none attributable to this session's changes:

- `tests/g1/test_g1_closure_guard.py` ×2 (`test_no_unwhitelisted_legacy_option_future_construction_in_core`, `test_instrument_key_absent_from_execution`)
- `tests/analog_path/test_data_layer.py::test_defect_days_invalid`, `tests/analog_path/test_reproducibility.py::test_mini_eligibility_build_excludes_multiday_file`
- `tests/ptms/test_gann_run_screen.py::test_guard_refuses_on_the_current_repository`

All other 67 worktree failures (§2) pass here, confirming they were environmental (no data stores) and the `msi` CRLF failures do not occur in this
checkout (its fixture files are LF on disk). Gate 8 allows the standing G1 red; the other three are standing on main (per memory) but are not G1 —
the operator should confirm they are accepted for the gate.

### Isolation finding: the suite writes to live data paths

A stat manifest of `data/` + `config/` (27,221 files) before vs after showed 0 new, 0 deleted, **4 changed** (all untracked, none restorable from git):

| File | Change | Writer | Assessment |
|---|---|---|---|
| `data/signal_engine/trade_intelligence/trade_intelligence.duckdb` | 2.475 → 2.541 GB; `executed_trades` 8,704 rows | `tests/trade_intelligence/test_builder.py` (`TI_DB` = live path) | derived store, rebuilt by the test; content equality with pre-run not verifiable (no baseline) |
| `data/isd/zero_row_repair_manifest.jsonl` | 207 → 208 B; now names `…\pytest-of-devou\pytest-1120\…` baseline | `scripts/isd/repair_zero_rows.py` via `tests/isd/test_gates.py` | already a test artifact before the run (same shape); real repair evidence, if any, is overwritten |
| `data/execution.db` | mtime only (81,920 B; orders 3 / fills 3 / positions 370) | tests building a handler on the default `ExecutionStore` path | not the NiftyShield store (`data/nifty_shield/execution.db`) |
| `data/reliance_regime/timing_study.json` | rewritten, same size | `scripts/reliance_regime/timing_study.py` via its test | deterministic output |

Recommended follow-up (own PR): point those tests' store/output paths at `tmp_path` (the CLAUDE.md "point every store path at `tmp_path`" rule), then
re-run this manifest diff to prove zero writes.
