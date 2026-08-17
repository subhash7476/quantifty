# Options-Wall — Phase 0 + Phase 1 Implementation Report

**Branch:** `feat/options-wall`
**Date:** 2026-08-14
**Status:** COMPLETE — Phase 0 (wiring reconciliation) and Phase 1 (scanner core)
implemented and verified live.

---

## Scope

Two phases of the Options-Wall intraday scanner project
(`docs/reports/OPTIONS_WALL_PROJECT_COURSE.md`):

- **Phase 0** — pin the canonical snapshot store; confirm the live chain and
  bid/ask feed actually resolve for both indices.
- **Phase 1** — build the three-screen scanner core, wire realized vol and
  bid/ask enrichment, and drive it off the store through a runnable engine + CLI.

---

## Phase 0 — Wiring Reconciliation

### Finding: three cache artifacts, none of them the wall store

| Path | Owner | Model | Coverage |
|------|-------|-------|----------|
| `data/options/chain_cache.duckdb` | `scripts/nifty_shield_paper/chain_poller.py` | single-snapshot **overwrite** (fresh DB per 5s cycle, atomic `os.replace`) | Nifty only, latest cycle only |
| `data/market_data/options_poller.duckdb` | `OptionsProvider` default (dashboard facade `read_only=True`) | append | **file does not exist on disk** — dead path |
| **`data/options/wall_chain_snapshots.duckdb`** | **`core/data/options_wall_store.py`** (this project) | **append-only, multi-symbol** | Nifty + BankNifty, full trail |

### Decision

The wall scanner owns `wall_chain_snapshots.duckdb` via
`core/data/options_wall_store.py` (`append_snapshot` / `latest_snapshot` /
`snapshot_timestamps`). It is append-only and accumulates, because the scan trail
and regime river need history that the NiftyShield overwrite cache deliberately
does not retain. `chain_poller.py` is left untouched (decoupled).

### Live confirmation (token valid, market open)

- **BankNifty chain resolves**: Wed expiry `2026-08-25`, 167 strikes,
  `underlying_ltp` 57528.5, IV present on 219/334 rows.
- **Nifty chain resolves**: Tue expiry `2026-08-18`, 105 strikes,
  `underlying_ltp` 24366.0.
- **Bid/ask available**: `UpstoxMarketData.fetch_quotes_batch` returns
  `best_bid` / `best_ask` from market depth, keyed by `NSE_FO|<token>`.
- **Store round-trips**: appended live Nifty (210 rows) + BankNifty (334 rows) and
  read both back through `latest_snapshot`.

### Caveat recorded

Upstox gamma coverage is **partial** (near-ATM only): ~73/210 Nifty, ~99/334
BankNifty rows carry gamma. GEX / flip / pin / wall inherit this limit
(`calculate_gex` already skips null/zero gamma). Deep-ITM rows carry `iv=0.0`
(treated as missing).

---

## Phase 1 — Scanner Core

### Files

| File | Purpose |
|------|---------|
| `core/analytics/chain_scanner.py` | `ChainScanner.scan_chain()` — three screens, `ScanResult` / `ScanConfig` |
| `core/analytics/realized_vol.py` | `session_realized_vol_pct()` — 1m-bar RV in percent units |
| `core/options_wall/engine.py` | `scan_indices()` — load-or-fetch → structural → RV → quotes → scan |
| `scripts/options_wall_scan.py` | CLI — prints the ranked farm list |

### Screens implemented

1. **Premium farm** — positive-GEX only; near-pin or inside `[Put Wall, Call Wall]`;
   gated on `IV − RV > iv_rv_min_gap`; spread-gated via bid/ask quotes; ranked by
   `credit / margin`.
2. **Imperfections** — ATM CE/PE IV asymmetry; single-strike vol outliers (near-ATM
   band only).
3. **Laggards** — flip-cross recency; charm cascade (≤2 DTE, top-5 by |theta|).
   `repricing_lag` deferred: it needs the 09:15 baseline (Phase 2), not the
   vs-prev-close `oi_change` that Upstox provides.

### Bugs found and fixed during live verification

1. **Realized-vol understated ~30×.** `sqrt(252)` was used to annualize 1-minute
   returns; the correct factor is `sqrt(252 × 375)` (375 bars/session). Also
   switched to intra-session returns only so overnight gaps never leak a fake vol
   spike. Result: Nifty ≈ 9.4%, BankNifty ≈ 11.9% (was 0.5 / 0.67).
2. **Vol-outlier screen flooded by `iv=0.0` deep-ITM artifacts.** Now requires both
   legs to carry valid IV and scans only the ±5% near-ATM band, capped to top-10.
3. **`repricing_lag` was noise.** It compared option `ltp`/`oi` against prev close,
   which flags nearly everything. Disabled until the 09:15 baseline exists.

### Live output (sane, not hallucinated)

- Nifty: `Negative GEX (Volatile)` → short-premium correctly gated **off**; one
  CE/PE IV-asymmetry row.
- BankNifty: `Positive GEX (Stable)` but ATM IV not rich vs RV → no farm candidates;
  a few near-ATM vol kinks surfaced.

This is the screens behaving as intended: no farm list is emitted when IV is not
rich relative to realized vol.

---

## Deferred (not in this commit)

- Skew and term-structure-kink screens (open question #2).
- Wall poller (replaces the manual `_load_or_fetch` in the engine) — Phase 2.
- `scan_results` persistence, daily regime row, 09:15 OI baseline — Phase 2.
- `/options/wall` UI panel — Phase 3.
- Vol-outlier threshold calibration — needs real research, not the 2pt default.
