# NiftyShield Sealed 2026 — Pre-Registered Acceptance Bar

**Branch:** `feat/niftyshield-model-retrain`
**Committed:** before the 2026 sealed summary was read (this commit is the proof).
**Author of bar:** Claude (reviewer); operator ratifies.

## Pre-registration statement

At the time of this commit, **the 2026 sealed summary (`--start 2026-01-01 --end 2026-07-31`)
has NOT been read.** Only the 2025 consistency-check summary has been seen. These thresholds
are fixed now so the 2026 verdict cannot be fit to the result. To change any number, it must
be amended **before** the 2026 summary is opened; once read, this bar is frozen.

## What is being judged

The corrected sealed harness's `summary.json` for **2026-01-01 → 2026-07-31**, produced by the
bundle whose `bull_put_spread` wing sign is fixed (Finding 5). Metrics are **per single Nifty
lot (75)** and **GROSS** — the harness uses `close` for entry/exit with no fees, slippage, or
bid/ask (disclosed harness limitation D5). Fee-survival is therefore **not** decided here; it
is a separate Phase-6 analysis. This bar tests whether a *gross* edge exists on the unread
window worth carrying to a fee/slippage study.

## Acceptance criteria — ALL THREE must hold

| # | Metric (`summary.json` key) | Threshold |
|---|---|---|
| 1 | `total_pnl_rs` | **> 0** (gross, per lot) |
| 2 | `sharpe` | **≥ 0.80** |
| 3 | `max_drawdown_rs` | **≥ −15000** (i.e. not worse than −₹15,000) |

Plus two integrity gates that must also hold (else the run is invalid, re-run):
- `total_trades + sum(skipped.values()) == sessions_attempted` (exact reconciliation)
- `by_regime` contains all three of BearTrend / BullTrend / Choppy with `count > 0`

## Verdict logic

- **All three criteria + both integrity gates hold → PASS** → proceed to Phase 6 re-cert
  (swap `TRAINED_ON`, republish facts, re-run conformance, ledger entry) *and* a fee/slippage
  study before any capital.
- **Criterion 1 fails (`total_pnl_rs ≤ 0`) → STOP.** Keep the old provenance; the retrain does
  not earn promotion. (A gross-negative half-year cannot survive fees.)
- **Criterion 1 holds but 2 or 3 fails → INCONCLUSIVE** → not a PASS; record and decide whether
  a longer forward paper window is warranted before re-judging.

## Reference (already-read 2025 consistency year, for calibration only)

`total_pnl_rs` +25,601 · `sharpe` 1.47 · `win_rate` 0.665 · `max_drawdown_rs` −9,833 ·
all three regimes traded · reconciliation exact. The 2026 thresholds are deliberately set
**below** these (Sharpe 0.80 vs 1.47; DD −15K vs −9.8K) to allow for a weaker, shorter,
truly-unseen half-year without being trivially passable.

## Rationale for the numbers

- **`total_pnl_rs > 0`** is the minimal honest hurdle: a gross-negative result is disqualifying
  regardless of Sharpe, since fees only subtract.
- **`sharpe ≥ 0.80`** — roughly half the 2025 read, a floor that rejects a barely-positive,
  high-variance outcome while not demanding the (likely optimistic) 2025 level on a 7-month window.
- **`max_drawdown_rs ≥ −15000`** — ~1.5× the 2025 drawdown, bounding tail risk on the per-lot book.
