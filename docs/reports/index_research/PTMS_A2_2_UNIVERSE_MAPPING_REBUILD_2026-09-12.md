# PTMS — A2-2: Stale Universe / Mapping Tables — Root Cause and Rebuild

**Date:** 2026-09-12 · **Authority:** operator task "A2-2 ONLY", 2026-09-12
**Scope:** A2-2 only. A2-1, A5 residuals, BSE CA, A1 and all research constructs are
out of scope and untouched.
**Baseline taken before any write:** `data/_baselines/equity_bhavcopy.pre_universe_rebuild_2026-09-12.duckdb` (705 MB).
**Before/after snapshots:** `PTMS_A2_2_BEFORE.json`, `PTMS_A2_2_AFTER.json`.

**Result: A2-2 is RESOLVED. 211 unmapped symbols → 0. The 2026-07-09 freshness boundary is
gone from all three tables.** C2 remains **NOT CERTIFIED** (§8).

---

## 1. Root cause — two independent defects, both in the canonical path

Traced, not guessed.

### Cause 1 — the builders are not in the nightly pipeline

`scripts/download_all_data.py` is the nightly chain. It runs:

```
ingest_equity_bhavcopy.py · ingest_futures_bhavcopy_v2.py · ingest_index_history.py
ingest_corporate_actions.py · ingest_stock_options_bhavcopy.py
carry/build_index_db.py · trend/build_continuous.py · refresh_all_strategies.py
```

**It never calls `build_universe.py` or `build_symbol_isin.py`.** Both are manual-only, and
their last run was ~2026-07-08/09 — which is exactly where all three tables stop.

### Cause 2 — `fetch_instrument_master()` never invalidates its cache

`build_universe.py` sources the company master from NSE `EQUITY_L.csv`, cached at
`data/market_data/universe_raw/equity_l.csv`. The logic was:

```python
if cache.exists():
    text = cache.read_bytes()...   # used unconditionally, at any age
```

The cache was written **2026-07-10 23:19**. So **even re-running the builder would have
rebuilt `instrument_master` from the stale July snapshot**, and every listing since would
still be missing. Cause 1 alone does not explain the defect; Cause 2 would have defeated the
obvious remedy.

### Why the ISIN side matters, and why `secfull` cannot fix it

`build_symbol_isin.py` reads only `legacy_*.zip` and `udiff_*.zip` from `bhavcopy_raw/`. The
archive today is **4,179 legacy · 2,444 secfull · 268 udiff**, and the *current daily format is
`secfull_*.csv`, whose header carries no ISIN column at all*:

```
SYMBOL, SERIES, DATE1, PREV_CLOSE, ..., DELIV_QTY, DELIV_PER
```

So new listings cannot acquire an ISIN from the daily feed — which is why only **1 of the 211**
unmapped symbols had a `symbol_isin` row. `build_universe.py`'s docstring already names the
intended path for this class: *`instrument_master` "resolves recent IPOs that carry no ISIN in
the cached raw payloads (ETERNAL, GROWW, SWIGGY, …)"*. That path runs through `EQUITY_L.csv` —
i.e. through Cause 2.

**A fresh source download was therefore required**, exactly analogous to the CA refresh.

## 2. Repair — canonical path, no ad-hoc script, no manual mappings

One change, in the canonical builder:

**`scripts/csmp/build_universe.py`** — added `--refresh-sources`. When passed, the stale cache
is preserved as `equity_l.superseded_<mtime>.csv` (provenance kept, never deleted) and the
builder's own existing fetch path runs. Default behaviour is unchanged, so deterministic
re-runs still work. No row was hand-edited; no mapping was added by hand.

Executed in dependency order:

```
python scripts/csmp/build_symbol_isin.py
python scripts/csmp/build_universe.py --refresh-sources
```

The audit confirms the refresh took effect — the `instrument_master` probe now reports
**`fetched HTTP 200`** where it previously reported `cached`.

## 3. Before → after

| Table | Before | After |
|---|---|---|
| `universe_membership` | 35,000 rows · 634 symbols · max **2026-07-09** | **35,400** · **638** · max **2026-09-11** |
| `symbol_entity_intervals` | 4,133 rows · 4,132 symbols · 3,615 entities · max valid_from **2026-07-08** | **4,344** · **4,343** · **3,825** · max **2026-09-11** |
| `symbol_isin` | 3,639 | **4,425** |
| `instrument_master` | 2,384 | **2,568** |
| **Unmapped symbols** | **211** | **0** |
| **Unmapped rows** | **4,175** | **0** |
| Rows outside their interval | 0 | **0** |
| Multi-interval symbols | 1 (DTIL) | **1 (DTIL)** — unchanged |

`symbol_entity_intervals` now covers **4,343 symbols — exactly the panel's distinct-symbol
count**. Every panel row resolves to an entity interval.

## 4. Tables modified

`universe_membership` · `universe_intervals` · `universe_eligibility` · `universe_probes` ·
`instrument_master` · `symbol_entity_intervals` (dropped and rebuilt by `build_universe.py`,
by its own design) and `symbol_isin` (rebuilt by `build_symbol_isin.py`).
**No price row was touched**; `equity_bhavcopy` max trade_date is 2026-09-11 before and after.

## 5. The 2026-07-09 convergence — resolved for three of four artefacts

| Artefact | Before | After |
|---|---|---|
| CA archive / `corporate_actions` | 2026-07-31 | **2026-09-11** (previous task) |
| `universe_membership` | 2026-07-09 | **2026-09-11** |
| `symbol_entity_intervals` | 2026-07-08 | **2026-09-11** |
| Arm A recent cluster | 5 items ≥ 2026-07-31 | §7 |

The convergence was **not one bug**: the CA archive was stale for want of a downloader, and the
universe/mapping tables for want of a pipeline call *plus* a never-invalidated cache. Two
distinct causes producing one date, because both were last serviced in the same manual session.

## 6. Universe audit (existing check, not a replacement)

`scripts/csmp/audit_universe.py` → `docs/reports/CSMP_GATE_C_UNIVERSE_AUDIT.md`.
**177 rebalances, 2012-01-31 → 2026-09-11, every one carrying exactly 200 members, 0 shortfall
dates in any year.** The membership rule remains the charter-locked mechanical
top-200-by-turnover; the official PIT change-history probe still returns HTTP 404 and the
`niftyindices` CSV still answers a wrong-content 200 (HTML shell) — unchanged, and the reason
the mechanical rule exists.

## 7. Classification

**CLASS A — stale expectations / environmental noise**
- The contract suite's frozen row-count expectation (7,030,920) and its missing backup-file
  precondition. Unchanged by this work, still noise.

**CLASS B — resolved by this rebuild**
- 211 unmapped symbols → **0**; 4,175 unmapped rows → **0**.
- `universe_membership`, `symbol_entity_intervals`, `symbol_isin`, `instrument_master` all
  fresh to 2026-09-11.
- The never-invalidating `EQUITY_L.csv` cache (Cause 2) — repaired in the canonical builder.

**CLASS C — genuine remaining substrate defects**
- **Cause 1 is only half-repaired.** `build_universe.py` and `build_symbol_isin.py` are still
  absent from `download_all_data.py`, so these tables will go stale again. Adding them is a
  change to the nightly pipeline and was **not** in this task's scope.
- **380 store symbols carry no ISIN** ("listed outside both payload eras", per the builder's
  own output). They resolve to entities via `instrument_master`, so A2-2 is closed, but the
  ISIN gap is real and is the `secfull`-has-no-ISIN consequence.
- `symbol_isin` cannot be extended for future listings from the daily feed at all.

**CLASS D — out of scope for A2-2**
- A2-1 (DTIL interval endpoint) — still exactly 1 multi-interval symbol, untouched and
  unadjudicated, as instructed.
- A5 Arm A residuals, BSE CA refresh, A1 circularity, all PTMS research constructs.

## 8. C2 status — unchanged verdict

**C2 remains NOT CERTIFIED.** A2-2 improving does not certify C2.

| Arm | Status |
|---|---|
| A1 `pit_membership` circularity | **FAIL — permanent.** Untouched by this work |
| A2-1 DTIL interval endpoint | **OPEN** — out of scope here |
| **A2-2 stale mapping/universe** | **RESOLVED** (this task) |
| A3 issuer-prefix linkage | CERTIFIED |
| A4 `prev_close` identity | PASS |
| A5 adjusted-series continuity | §9 |
| A6 sector/thematic PIT | NOT PIT — unusable |

## 9. A5 re-run after the rebuild

`symbol_entity_intervals` is an input to the contract arms, so A5 was re-run. Raw output:
`PTMS_A5_CONTRACT_SUITE_POST_UNIVERSE_2026-09-12.md`.

**The first attempt died with a DuckDB `OutOfMemoryException`** — CLASS A, environmental, not a
substrate finding. The suite hardcodes `memory_limit='4GB'` / `threads=2`, and the rebuild
widened its joins (entities 3,615 → 3,825). Raising that limit means editing the closed PSB-1
battery, which is out of scope; a clean retry succeeded, so no change was needed.

| Check | Post-CA-rebuild | **Post-universe-rebuild** |
|---|---|---|
| **Arm B** cross-symbol handoff | PASS — **4** splice fabrications (4 dispositioned) | **PASS — 0 splice fabrications** |
| Structural: intervals | 4,133 rows · 1 multi-interval (DTIL) | **4,344 rows** · 1 multi-interval (DTIL) |
| Structural: row count | 7,154,268 | **7,158,443** |
| Arm A | HALT — 5 undocumented · 2,733 large_genuine | HALT — **5 undocumented** · 2,742 large_genuine |
| Arm C / Arm D | PASS / PASS (16/16) | PASS / PASS (16/16) |
| DVL→DTIL re-key, all regressions | PASS | PASS |

**Two independent confirmations that A2-2 closed:**

1. **Arm B went from 4 splice fabrications to zero.** The cross-symbol handoff arm is now
   completely clean — the refreshed entity intervals eliminated the splices outright rather
   than dispositioning them.
2. **The suite's row count rose from 7,154,268 to 7,158,443** — exactly the direct `count(*)`.
   The suite drops rows whose symbol has no entity interval, so its previous 4,175-row shortfall
   *was* the unmapped-symbol count. That shortfall is now zero, measured from the suite's side.

Arm A is unchanged at 5 undocumented items — the ETF-split and adjudication residue, out of
A2-2 scope. The row-count and backup-file cells remain CLASS A stale expectations.

## 10. Exact next action

**Add `build_symbol_isin.py` and `build_universe.py` to `download_all_data.py`** (Class C,
Cause 1's other half). Without it this task's result decays and the same four-artefact
convergence reappears at the next manual-run date. That is a nightly-pipeline change and needs
its own authorization.
