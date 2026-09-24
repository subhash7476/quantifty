# NiftyShield PAPER — 2026-09-16 trade audit: first session on the σ bracket

**Verdict:** the σ bracket (`9eacbc6`, spec `2026-09-15-nifty-shield-sigma-bracket-design.md`)
ran exactly as designed. The take-profit was **disabled at entry** (gain side Rs 94 below the
Rs 1,033 fee floor), the stop (Rs 359) was **never reached** (worst mark P&L −Rs 188.5), and the
structure closed on **`time_exit` at 15:35** for **+Rs 344.50 gross, ~Rs 4 net**. No exit fired
wrongly. What the day exposes is an **entry** property, not an exit one: this iron fly could not
earn its round-trip fees intraday by construction.

## 1. The trade

| | |
|---|---|
| Group | `1c90ac46-65c8-5247-88e1-34cceeb3e473` |
| Regime / structure | Choppy → **iron_fly**, 2 lots × 65 = 130, expiry 2026-09-22 (6 DTE) |
| Entry (13:01:11–13:01:18) | SELL 23250CE @ 170.25, SELL 23250PE @ 146.70, BUY 23400CE @ 96.60, BUY 23100PE @ 93.75 |
| Exit (15:35:13, `time_exit`) | 23250CE @ 148.35, 23250PE @ 153.80, 23400CE @ 80.20, 23100PE @ 98.00 |
| Credit | 126.60 pts × 130 = **Rs 16,458** on 150-pt wings → max loss **Rs 3,042** |
| Gross P&L (ledger) | 2,847.00 − 923.00 − 2,132.00 + 552.50 = **+Rs 344.50** |
| Fees (ledger, option schedule) | 98.15 + 92.60 + 72.74 + 77.01 = **Rs 340.50** |
| Net | **+Rs 4.00** |
| Margin (Upstox basket) | Rs 125,375.64 |

Sources: `data/nifty_shield/journal.jsonl` (ENTRY_MARGIN 13:01:20, ENTRY_BRACKET 13:01:20,
STRUCTURE_CLOSE 15:35:19), `data/nifty_shield/trading/trading.db`, intraday marks from
`data/options/wall_chain_snapshots/2026-09-16.duckdb` (712 four-leg snapshots from fill to exit,
median gap 12 s), Nifty 1m from `data/market_data/nse/candles/1m/2026-09-16.duckdb`.

## 2. The bracket at entry (journaled `ENTRY_BRACKET`, INFO)

| Field | Value |
|---|---|
| Leg IVs (fill-implied) | 0.1342, 0.1321, 0.1278, 0.1396 |
| σ over the 2.5 h hold | 123.3 pts |
| TP (gain side at ±1σ) | Rs 94.01 — **disabled** |
| Fee floor (3 × round trip) | Rs 1,033.13 (estimated round trip 344.38; ledger 340.50) |
| SL (loss side at ±1σ) | **Rs 359.24** |

The narrow fly explains both numbers. Credit is 84% of the wing width, so the structure's whole
loss range is Rs 3,042, and a 1σ move reprices it by only Rs 359 against and Rs 94 in favour —
the gain comes from theta, which the bracket (repriced with time held fixed) does not count.

## 3. What happened intraday

Nifty 13:00 → 15:29: open 23,246.75, high 23,284.75, low 23,209.80, close 23,217.60 — a ~75-pt
range against a 123-pt σ.

| Time | Mark P&L (Rs) | Spot |
|---|---:|---:|
| 13:05 | −13 | 23,258.2 |
| 13:10 (low) | **−188.5** | 23,277.6 |
| 13:35 | +169 | 23,227.7 |
| 14:05 | +175 | 23,233.8 |
| 14:35 | +117 | 23,230.5 |
| 15:05 | +266 | 23,232.1 |
| 15:32 (high) | **+494** | 23,217.6 |
| 15:35 | +312 (snapshot) / +344.50 (fills) | 23,217.6 |

| Check | Result |
|---|---|
| Stop reached (P&L ≤ −359.24) | **0 of 712 snapshots** — correctly held |
| TP threshold crossed (P&L ≥ 94.01) | 585 of 740 snapshots, but TP disabled — correctly did not fire |
| Fee floor ever reached (≥ 1,033) | **never** |
| Exit driver alive | no stale-marks CRITICAL in the journal; closed at 15:35:13 as scheduled |
| Exit fills vs snapshot marks at 15:35 | within ≤ 1.00 per leg (fills from the chain cache, marks from the wall store) |

## 4. Against the rule it replaced

| Rule | TP | SL | Would have closed | Result |
|---|---|---|---|---|
| Old (decay-fraction TP, 50% max-loss stop) | Rs 393.42 | Rs 1,521.00 | **take_profit at 15:20:24**, mark +Rs 403 | ≈ +Rs 60 net |
| New (σ bracket) | off (Rs 94 < floor) | Rs 359.24 | time_exit 15:35 | +Rs 4 net |

A Rs 56 difference on one session, well inside mark noise. Not evidence for either rule.

## 5. Findings

1. **Exit logic: correct.** Bracket sized, journaled once, TP disabled by the fee floor, stop held,
   clock closed the book. First live confirmation that the 2026-09-15 change works end to end.
2. **The structure could not clear its fees intraday.** Round trip Rs 340.50 on 8 fills; the best
   mark of the whole afternoon was +Rs 494 gross, and the ±1σ gain side was Rs 94. A narrow
   iron fly (wings at `wing_sigma_frac = 0.361` of σ-to-expiry) held 2.5 h earns almost nothing
   gross, so fees take it. This is an **entry-selection** question the exit bracket cannot fix:
   no gate asks whether a structure's plausible intraday P&L exceeds its costs (the credit gate
   checks price quality only). Recorded as an observation; n = 1 and not a reason to change a
   parameter.
3. **LIVE would have lost money.** Paper fills at marks. Quoted spreads were 0.20–0.40 per leg at
   entry and exit; half a spread on each of 8 fills × 130 ≈ Rs 135 more cost, turning +Rs 4 into
   about −Rs 130.
4. **Capital use.** Rs 125,376 of basket margin blocked for a structure whose maximum loss is
   Rs 3,042 and whose day earned Rs 4.
5. **Operational (unchanged, known):** the Options-Wall shadow read at entry failed on a file lock
   (`wall_scan_results.duckdb` held by the wall poller), so that observe-only diagnostic is
   missing for this trade. No effect on the trade.

## 6. Counterfactual — the same fly carried into 2026-09-17 (partial session)

Same four legs, same 09-16 entry fills, repriced on 2026-09-17's snapshots
(`wall_chain_snapshots/2026-09-17.duckdb`, 768 four-leg snapshots, **09:15:31 → 11:59:20**; the
session was still open when measured, so this is not a full day).

| | Time | Mark P&L (gross) | Spot |
|---|---|---:|---:|
| Open | 09:15:31 | **+474.5** | 23,254.3 |
| Low | 10:12:05 | +292.5 | 23,321.4 |
| High | 11:05:58 | **+968.5** | 23,236.0 |
| Latest | 11:59:20 | +572.0 | 23,307.3 |

| Threshold | First hit |
|---|---|
| Bracket SL −359.24 | never |
| Old SL −1,521 / max loss −3,042 | never |
| Fee floor +1,033 (TP would enable only above this) | never |
| Old TP +393.42 | 09:15:31 (at the open) |

Carrying earned the overnight theta the intraday hold cannot: the book opened +Rs 474.5 on a
spot 37 pts above the prior 15:29 print, and never went negative. Net of the ~Rs 340 round trip it
would stand at about **+Rs 628 at the high and +Rs 232 at 11:59**, against +Rs 4 for the actual
15:35 close.

Read with care: one session, measured mid-day; paper marks (LIVE adds ~Rs 135 of spread); the
bracket and the 15:35 flatten are intraday rules, so "carried" is not a mode the strategy has —
it would add overnight gap risk (bounded here at the Rs 3,042 max loss) and hold Rs 1.25 lakh of
margin overnight. It is evidence about where this structure's P&L comes from (time decay across
the close), not a result for the intraday rule set.

## 7. Reproduce

- Bracket and close: `journal.jsonl` events for group `1c90ac46…`.
- Mark path: the four legs of expiry 2026-09-22 in `wall_chain_snapshots/2026-09-16.duckdb`,
  P&L = Σ (entry − ltp) × 130 for SELL legs and (ltp − entry) × 130 for BUY legs, snapshots
  between 13:01:18 and 15:35:14.
- Old-rule threshold: available decay at 6 DTE = 1 − √((26.79 − 2.5) / 26.79) = 4.781%;
  0.5 × 0.04781 × 16,458 = Rs 393.42; stop 0.5 × 3,042 = Rs 1,521.
