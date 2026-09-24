# PTMS — Gann Stage-1: R-11 Reader-Date / Exposure Audit (equity EOD 2023-01-02 → 2026-09-11)

**Date:** 2026-09-15 · **Branch:** `research/ptms-price-time-market-structure`

**Type:** audit of committed code, date filters, saved artifacts and git history. **No outcome
statistics were read and none are reproduced here.** Store queries were meta-level per register §1
(schema, row counts, min/max dates, and NULL-presence of a column — a data-presence predicate,
not a statistic).

**Question:** which equity-EOD dates did the 19 `scripts/signal_engine/` and 4 `scripts/mrlc_test/`
readers actually touch — and is 2023-01-02 → 2026-09-11 fresh or signal-spent? (R-11, freeze
checklist item 17 / P-1. The freshness **ruling** follows this audit and remains the operator's;
the register's "UNRESOLVED" standing of the span is not edited here.)

---

## 1. Reader enumeration (matches register §5b G-A; 19 + 4)

For the EOD store the path is a single filename token, so the literal and component-wise searches
coincide (register §5b). The 23 readers:

`lag/run_train.py` · `lag/build_lag.py` · `ivol/run_train.py` · `ivol/run_holdout.py` ·
`ivol/build_ivol.py` · `ts_basis_daily/build_ts_basis_daily.py` · `carry/build_carry.py` ·
`carry/backfill_fwd_returns.py` · `carry/cadence_decay.py` · `skew/neutralize.py` ·
`skew/build_skew.py` · `carry/certify_substrate.py` · `carry/contract_arms.py` ·
`trend/build_continuous.py` · `trend/build_trend.py` · `trend/run_train.py` ·
`carry/neutralize.py` · `carry/persistence.py` · `carry/run_train.py` — and
`mrlc_test/{daily_ext,scanner,size_split,report}.py`.

---

## 2. Code-level date filters (per reader)

| Reader | What it reads from equity EOD | Window in code |
|---|---|---|
| `carry/build_carry.py:328-356` | `equity_bhavcopy_adjusted` close at formation → fwd-formation (`fwd_ret_1m`) | `trade_date >= lo(first formation of run)` to `hi(last fwd date)`; formations run to the futures store end |
| `carry/backfill_fwd_returns.py` | same join, fills NULLs | every formation in the store (no date cap) |
| `carry/run_train.py` | signal store (its `fwd_ret_1m`) | TRAIN 2016-03-31 → 2020-12-31 |
| `carry/run_sealed.py` | signal store rows incl. `fwd_ret_1m` | **SEALED 2023-01-01 → 2026-07-20** |
| `carry/neutralize.py:100-112` | raw `equity_bhavcopy` EQ closes, beta lookback | `trade_date <= formation_date` per formation (store end 2026-08-31) |
| `carry/cadence_decay.py`, `persistence.py`, `weekly_vs_monthly.py`, `ts_basis_reversal.py` | raw closes around formations | TRAIN / HOLDOUT ≤ 2022-12-31 (constants) |
| `carry/certify_substrate.py`, `carry/contract_arms.py` | raw spot join for basis QA | read-only meta/QA over the futures span |
| `ivol/build_ivol.py` | `equity_bhavcopy_adjusted` → `fwd_ret_1m` | formations to store end (2026-07-23) |
| `ivol/run_train.py`, `run_holdout.py` | signal store | TRAIN 2017-02-28 → 2020-12-31; HOLDOUT 2021-01-31 → 2022-12-31 |
| `ivol/run_sealed.py:173-201` | signal store rows incl. `fwd_ret_1m` | **SEALED 2023-01-01 → 2026-07-20** |
| `lag/build_lag.py`, `run_train.py` | adjusted view → `fwd_ret_1m`; TRAIN only | formations to store end (2026-07-23) |
| `skew/build_skew.py`, `skew/neutralize.py` | adjusted view + raw beta | store ends **2022-12-30** (no SEALED runner) |
| `trend/build_trend.py`, `run_train.py` | adjusted view → `fwd_ret_1m`; TRAIN only | formations to store end (2026-07-20) |
| `trend/build_continuous.py` | raw EQ spot via `carry/contract_arms.build_basis_panel` | futures store span 2016-02-11 → 2026-09-11 |
| `ts_basis/build_ts_signals.py` | inherits `fwd_ret_1m` from `carry/{weekly_,}signals.duckdb` | as the carry stores |
| `ts_basis/run_sealed.py:113-116` | `ts_signals` rows incl. `fwd_ret_1m` | **SEALED 2023-01-01 → 2026-07-20** |
| `ts_basis_daily/build_ts_basis_daily.py:196-231` | `equity_bhavcopy_adjusted` → `fwd_ret_1m` | formations to store end (**2026-09-11**, live) |
| `ts_basis_daily/run_sealed.py` | **DISABLED — refuses to run** (`SEALED_LO 2023-01-01`) | preserved unspent for the aggregate read |
| `mrlc_test/daily_ext.py` | materialize adjusted view → trades | **2012-01-01 → 2022-12-31** only |
| `mrlc_test/size_split.py` | same extension + `symbol_isin` (meta) | 2012-01-01 → 2022-12-31 |
| `mrlc_test/scanner.py` 1d track | `load_recent` from `equity_bhavcopy_adjusted`, trailing 130-day lookback, sweep/reclaim rule evaluated | each nightly run; disabled 2026-09-13 (commit `05ef991`) |

---

## 3. Artifact evidence — signal stores (meta-level reads)

Formation spans and per-year presence of the score→forward-outcome linkage column
(`fwd_ret_1m`, computed from `equity_bhavcopy_adjusted` closes by every family builder):

| Store | formation span | `fwd_ret_1m` non-null through | 2023+ linkage present? |
|---|---|---|---|
| `carry/signals.duckdb` | 2016-02-29 → 2026-08-31 | 2026 (2026 non-null 1,037/1,666 rows) | **yes** |
| `carry/weekly_signals.duckdb` | 2016-02-12 → 2026-09-11 | 2026 | **yes** |
| `ivol/signals.duckdb` | 2017-02-28 → 2026-07-23 | 2026 (1,220/1,430) | **yes** |
| `lag/signals.duckdb` | 2017-02-28 → 2026-07-23 | 2026 (1,065/1,254) | **yes** |
| `skew/signals.duckdb` | 2016-07-29 → **2022-12-30** | 2022 | no |
| `trend/signals.duckdb` | 2017-02-28 → 2026-07-20 | 2026 (1,102/1,288) | **yes** |
| `ts_basis/ts_signals.duckdb` | 2016-05-06 → 2026-07-24 | 2026 (5,694/5,694) | **yes** (inherited from carry) |
| `ts_basis/ts_signals_monthly.duckdb` | 2017-02-28 → 2026-05-29 | 2026 (890/890) | **yes** (inherited) |
| `ts_basis_daily/ts_signals.duckdb` | 2016-02-11 → **2026-09-11** | 2026 (35,701/35,912) | **yes** |
| `trend/continuous.duckdb` | 2016-02-11 → 2026-09-11 | (raw/adj spot closes) | **yes** (raw EQ spot join) |

Per-year detail (non-null `fwd_ret_1m` / rows): carry 2023 = 2,233/2,235 · 2024 = 2,253/2,257 ·
2025 = 2,574/2,576 · 2026 = 1,037/1,666. The same pattern holds for ivol, lag, trend, ts_basis and
ts_basis_daily in 2023–2025 (see the audit script run of 2026-09-15; all near-complete).

---

## 4. Execution evidence (git + files, dates only)

| Event | Evidence | Date |
|---|---|---|
| Carry SEALED executed | `carry/run_sealed.py` (SEALED 2023-01-01 → 2026-07-20); `docs/reports/carry/CARRY_SEALED_REPORT.md` + `CARRY_SEALED_SNAPSHOT.json` committed | runner added and read at `6831348`, 2026-07-23 |
| TS Basis monthly SEALED executed | `ts_basis/run_sealed.py`; `TS_BASIS_SEALED_REPORT.md` + snapshot | read at `42d17fc`, 2026-07-24 |
| IVOL SEALED executed | `ivol/run_sealed.py`; `docs/reports/sleeves/IVOL_SEALED_REPORT.md` + snapshot | read at `4f875c8`, 2026-07-26 |
| TS Basis Daily SEALED | `ts_basis_daily/run_sealed.py` — docstring: disabled, refuses; store rebuilds continue to 2026-09-11 | never run |
| MRLC EOD paper (scanner 1d) | `paper.duckdb:recent` = bhavcopy snapshot 2026-04-27 → 2026-09-02; `run_log` rows 2026-09-01..03 | last run 2026-09-03; scanner disabled `05ef991` 2026-09-13 |
| Trend / LAG / Skew stores | store mtimes 2026-07-23..25; no `run_sealed.py` exists for trend/lag/skew | TRAIN-only evaluation |

---

## 5. Finding

**Audit finding: equity EOD 2023-01-02 → 2026-09-11 is signal-spent.** The freshness ruling
remains the operator's; this audit supplies the facts the ruling was commissioned to record (R-11).

1. **Three executed SEALED evaluations consumed 2023+ equity-EOD forward outcomes.** Carry, TS Basis
   monthly and IVOL each read formations 2023-01-01 → 2026-07-20 whose `fwd_ret_1m` is an
   `equity_bhavcopy_adjusted` close-to-close return (built by the family builders, selected by each
   `run_sealed.py`). Register level: **signal**.
2. **The linkage exists on 2023+ dates in every surviving store.** Trend, LAG and TS Basis Daily
   carry computed-and-stored score↔forward-return linkage through 2026-07-20 / 2026-07-23 /
   2026-09-11 respectively, even where the aggregate runner never evaluated those dates (Trend,
   LAG: TRAIN-only; TS Basis Daily: sealed runner disabled). Under register §1 the computation and
   retention of a signal linked to a forward outcome on those dates is a signal-level read of those
   dates.
3. **MRLC evaluated a trading rule on 2023+ equity-EOD dates** through its scanner 1d track
   (bhavcopy snapshot 2026-04-27 → 2026-09-02, forward paper, signal level) before the scanner was
   disabled on 2026-09-13.
4. **No 2023+ reach:** Skew (store ends 2022-12-30), `cadence_decay` / `persistence` /
   `weekly_vs_monthly` / `ts_basis_reversal` (TRAIN+HOLDOUT ≤ 2022-12-31), MRLC
   `daily_ext`/`size_split` (2012-01-01 → 2022-12-31).
5. **Consequence under GR-1.2/1.3** (freshness belongs to observations; a spent window can never be
   confirmatory): unless the operator rules otherwise, the 2023-01-02 → 2026-09-11 span cannot serve
   as a confirmatory window, cannot enter `n_available`, and cannot sit on a gate's pass path. The
   screen (2011-03-25 → 2022-12-30, already spent) is unaffected; confirmation would be
   forward-only.

**Residual (recorded, not re-audited here):** the register already carries lineage rows for the
other equity-EOD reader clusters (Q-1..Q-6; n200_regime Q-4 feature 2012–2023; pair-research I-3 on
other surfaces). None of them weakens this finding, which rests on 2023+ signal-level reads alone.
The 1m-store rows (E-1..E-6, I-*) are a different surface and out of scope.

---

## 6. Governance

- No outcome statistic was read for this audit; store queries were meta-level (counts, min/max
  dates, column-presence). No signal or return was computed.
- No store was written; no script was changed. The exposure register was **not edited** — the
  freshness ruling and any register row (e.g. R-11 rows) remain operator-owned.
- The audit script used for the store queries is session-scratch (not committed); every figure
  above is re-derivable from the stated table/column names.
