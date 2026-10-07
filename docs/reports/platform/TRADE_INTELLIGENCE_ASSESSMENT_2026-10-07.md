# Does Trade Intelligence help make better trades? — assessment, 2026-10-07

**Verdict: no evidence that it has improved any trade, and the data it holds today could not show it either way.**
This is an evidence audit. No new study was run (a "does context X predict outcomes" read is a new research read and needs an RFA first),
and no protected window was touched: the TS Basis Daily sealed window (2023-01-01 → 2026-07-24) stays unspent, and `analyze_trade_intelligence.py`
and the historical builder were not run.

## 1. By design it decides nothing
`docs/implementation/trade_intelligence/README.md`: "a pure observer … produces no trading decisions". "Helping" can therefore only mean insights
that were validated out of sample and then changed a rule. Nothing in the repo shows that.

## 2. The store is ~99% test and replay rows
`data/signal_engine/trade_intelligence/trade_intelligence.duckdb`, `executed_trades` (read-only, 2026-10-07 20:2x): **8,704 rows**,
capture running since 2026-08-26.

| Source | Rows |
|---|---|
| Real forward capture since 2026-08-19 (`nifty_shield_v1` PAPER 48, `A_W45_PAPER` 2) | **50** (0.6%) |
| Test-fixture strategy names (`test_mm9_2_s*`, `g1*`, `mm7c`, `test_margin`, `test_strat`, `synthetic`, `syn`, `test_greek`, `mm13_knowledge_reader`), dated 2026-02-27 / 06-05 / 06-09 | 3,647 |
| Other `nifty_shield_v1` rows (entry dates 2023-01 → 2026-06 and later: replay/drill/test sessions) | 5,007 |
| **Total** | **8,704** |
| of which added by the 2026-10-07 live regression (`strategy_version` = `f198aa6`, `event_ts` 19:44–20:13) | 238 |

Root cause: `ExecutionConfig.trade_recorder_enabled` defaults True and `TradeRecorder()` defaults to the live DuckDB path, so every handler
a test or replay built recorded into the live store. Fixed for tests in the isolation PR (`tests/conftest.py`); replay/drill still write there
(runner/replay path is inside the E008 hash — reported, not changed).

## 3. Capture of real trades is incomplete: exits and P&L are missing
Same period, NiftyShield PAPER:

| | Trades | Closed | Realised P&L |
|---|---|---|---|
| Execution ledger `data/nifty_shield/trading/trading.db` | 54 | 52 | Rs +729 |
| Trade Intelligence `executed_trades` | 48 | **2** | Rs 208 (one day, 09-08) |

Entries are captured; ~96% of exits never are, so outcome columns (`realized_pnl`, `days_held`, `exit_reason`) are empty for almost every real trade.
TI cannot inform decisions about outcomes it does not record. Cause not investigated (candidate: the multi-leg `close_group` path vs the
single-position close detection in `TradeRecorder.on_fill`). The recorder is called from `handler.py`, inside the E008 hash.

## 4. The one place TI analytics drove tuning has no out-of-sample support
TS Basis Daily rules chosen from TI-style analysis — `basis_reverting`, TP@0.5%, an ML filter, a sector cap — were selected on TRAIN and checked on
HOLDOUT, so both are selection surfaces; the construct is research-only with no promotion path (CLAUDE.md, "TS Basis Daily" row;
`docs/reports/TS_BASIS_REAUTHORIZATION_ASSESSMENT.md`). Its TRAIN/HOLDOUT numbers (+60% / +41% net) are in-sample or selection-contaminated.
There is no clean read showing a TI-derived rule helped. The ts_combo forward book was not assessed here (n would be small, and whether it
uses the TI-derived rules was not verified).

## 5. Prerequisites before TI can be judged
1. Isolation (isolation PR) so new rows are real.
2. Segregate or clean the store: copy-first baseline, committed re-runnable code, explicit approval. Tonight's 238 rows are identifiable by `strategy_version = f198aa6`.
3. Fix exit capture (new E008 identity if it touches `handler.py`).
4. Any TI-derived rule goes through RFA and pre-registration on forward data, not TRAIN/HOLDOUT.
