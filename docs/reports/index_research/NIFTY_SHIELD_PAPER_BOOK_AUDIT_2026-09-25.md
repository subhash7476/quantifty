# NiftyShield PAPER — book audit, 2026-08-19 → 2026-09-25 (18 round-trips)

**Verdict.** The E008 paper window is **net-negative, and the reporting surface cannot show it.**
`metrics_report` prints **+Rs 846 / profit factor 1.16 / drawdown 0.0%**, but all three figures are
wrong for an E008 read:

- **Net P&L:** −Rs 1,641 after the ledger's own fees (Rs 2,487).
- **Uniform option fee schedule:** −Rs 1,960.
- **Net max drawdown:** −Rs 2,374.
- **Net profit factor:** 0.74.

Gross edge is ~Rs 47 per round-trip on n=18, which is indistinguishable from zero. Fixed fees are
~Rs 120 per 1-lot spread and ~Rs 300 per 2-lot fly, so they are the binding cost. The 18 trips also
are not one population: the exit rules, lot size and fee schedule changed partway through the window.

Two E008 gates are also in doubt:

- **Gate 5 (real SPAN + ELM) has not been met since 2026-09-07.** Every session since then was sized
  on the Upstox basket margin, which also contradicts ADR-011/012/013.
- **Gate 4 (drawdown) is unproven.** It is unclear whether the drawdown gate's equity survives the
  daily restarts, and its 5% limit is not the declared Rs 30K/150K rule.

Sources: `data/nifty_shield/journal.jsonl`, `data/nifty_shield/execution.db` (fills),
`data/nifty_shield/trading/trading.db` (trades — reconciles to the fills: 40 rows, fees
Rs 2,486.57, P&L Rs 846.00), `data/nifty_shield/sessions/*/metrics.json|session_summary.json`,
`logs/*.log`. Read-only audit — no code, data or frozen package touched.

## 1. The book

| Session | Structure | Exit | Gross | Fees | Net | Cum net |
|---|---|---|---:|---:|---:|---:|
| 08-19 | spread | time | 150.0 | 105.6 | 44.4 | 44.4 |
| 08-20 | spread | stop | −457.5 | 125.6 | −583.1 | −538.7 |
| 08-21 | straddle | time | 337.5 | 83.7 | 253.8 | −284.8 |
| 08-27 | straddle | time | 615.0 | 114.1 | 500.9 | 216.0 |
| 08-28 | straddle | time | −1,725.0 | 114.1 | −1,839.1 | −1,623.0 |
| 09-04 | straddle | time | 1,545.0 | 112.1 | 1,432.9 | −190.2 |
| 09-07 | spread | time | 30.0 | 108.9 | −78.9 | −269.1 |
| 09-08 | spread | manual | 208.0 | 104.6 | 103.4 | −165.7 |
| 09-11 | spread | TP | 143.0 | 100.5 | 42.5 | −123.2 |
| 09-15 | spread | TP | 139.8 | 133.4 | 6.4 | −116.8 |
| 09-16 | iron fly | time | 344.5 | 340.5 | 4.0 | −112.8 |
| 09-17 | spread | stop | −1,810.2 | 125.5 | −1,935.7 | −2,048.5 |
| 09-18 | straddle | time | 750.8 | 123.5 | 627.3 | −1,421.2 |
| 09-21 | spread | time | 562.2 | 124.0 | 438.3 | −982.9 |
| 09-22 | spread | time | −851.5 | 130.5 | −982.0 | −1,964.9 |
| 09-23 | spread | time | −74.8 | 118.5 | −193.2 | −2,158.1 |
| 09-24 | spread | TP | 1,283.8 | 119.7 | 1,164.0 | −994.1 |
| 09-25 | iron fly | stop | −344.5 | 302.0 | −646.5 | −1,640.6 |
| **Total** | | | **846.0** | **2,486.6** | **−1,640.6** | peak-to-trough **−2,374.2** |

- **Net win/loss:** 11 wins, 7 losses.
  - Net wins total Rs 4,618; net losses total Rs 6,259. Net profit factor **0.74**.
  - 4 of the 11 net wins are under Rs 50 (09-15 +6, 09-16 +4, 09-11 +43, 08-19 +44). That is fee noise.
- **08-20 / 08-21 attribution.** The 2026-08-20 restart incident (`6cc6b5e`) mis-grouped fills: by
  fills the pair is −10,018.1 / +9,688.8, and by `per_structure` it is −583.1 / +253.8. Both views
  total −329.3, so the book total is not contaminated.
- **Fee schedule drift.** Fills before `0f46f9b` (2026-09-11) were charged the non-option schedule.
  Repricing every fill through `core/execution/options/fees.py:option_order_fees` gives fees of
  **Rs 2,805.8**, not 2,486.6: the pre-fix fills were undercharged by Rs 319. On the uniform
  schedule the net is **−Rs 1,960**.

## 2. Findings

### F1 — `metrics_report` reports gross as the P&L [HIGH, blocks the E008 report]

`scripts/nifty_shield_paper/metrics_report.py:140-190` has three problems:

- It sums `pnl` and reads `fees` from `trading.db` but never subtracts the fees.
- It classifies wins and losses and computes `profit_factor` on gross.
- It reads `max_drawdown_pct` from the runtime `metrics.json` `drawdown` key, which is 0.0 (see F2).

As written, `assemble_report` would print **+Rs 846, PF 1.16, DD 0%** for a book that is −Rs 1,641,
PF 0.74, DD −Rs 2,374. Every gross-positive trade under ~Rs 130 is scored a "win" that lost money
after fees.

### F2 — the drawdown gate's equity input is unproven [MEDIUM, unverified, E008 gate 4]

`data/nifty_shield/metrics.json` reads `cash_balance = total_equity = max_equity = 1,000,000.0`,
`drawdown = 0.0`, `trades_executed = 0`. Its `last_update` of 13:25:58 is the last STARTUP, so this is
a **startup snapshot**, not the live state.

In memory, `handler.py:1243` `_update_equity_metrics` does move cash on each fill. The open question
is whether that equity **persists across restarts**:

- The session restarts daily, and several times on some days.
- `max_equity` is seeded from `initial_capital` (`handler.py:252`).
- If cash is re-seeded on each start, the gate (`handler.py:673-683`) only ever sees intra-session
  losses.

Two further points:

- The gate's limit is `max_drawdown_limit = 0.05`, i.e. Rs 50,000 on Rs 10 lakh. The declared E008
  limits are **Rs 30,000 single / Rs 150,000 5-day**, which are a different rule.
- `metrics.json` is not a valid drawdown source either way, which is part of F1.

**Not established in this audit.** R2's forced-breach drill is the test.

### F3 — sized on broker margin, SPAN unavailable every session since 2026-09-07 [HIGH, E008 gate 5 + architecture]

- From 09-07 onward, 33 STARTUP lines on 14 sessions say "SPAN snapshot unavailable — entries are
  sized on the Upstox basket margin." (`b45f2e7` made the downgrade loud; `f051fd3` introduced
  broker basket margin.)
- Gate 5 requires "real SPAN + ELM against real marks" on every entry, so it is unmet.
- **This also contradicts the platform's margin architecture.** CLAUDE.md, ADR-011/012/013 make
  `NseMarginEngine` the sole sizing authority in every mode, with broker RMS "never consulted for
  sizing". `docs/ARCHITECTURE_DECISIONS.md` contains no basket-margin amendment.
- The broker figure has also become a hard entry dependency: the 09-08 entries were skipped as
  "Upstox basket margin unavailable".
- The fix is either to restore SPAN and size on `NseMarginEngine`, or to file an ADR amendment by
  explicit operator decision.

### F4 — the window is not one population [HIGH for interpretation]

The session recorders show ~22 distinct platform commits across 24 sessions. The rule changes that
alter trade outcomes:

| Era | Change | Round-trips | Gross | Net (ledger) |
|---|---|---:|---:|---:|
| 08-19 → 09-04 | lot 75, original max-loss stop, 15:16 exit | 6 | 465 | −190 |
| 09-07 → 09-15 | `b45f2e7` (09-07) lot 65 + reachable stop; `f051fd3` (09-08) broker margin + 15:35 exit; `0f46f9b` (09-11) option fees | 4 | 521 | 73 |
| 09-16 → 09-25 | σ bracket (`9eacbc6`) | **8** | −140 | −1,524 |

The σ-bracket era starts on **09-16**, not 09-15. The 09-15 trade has no `ENTRY_BRACKET` line and ran
on `a970d9c`, which only added the design doc.

`git log 9eacbc6..HEAD -- core/execution/options/ scripts/nifty_shield_paper/ core/execution/handler.py`
returns one commit, `e98915d`, a stale-lock fix. So **09-16 onward is one execution identity.**

E008 gate 1 counts "≥30 round-trips". Pooling trips taken under three different exit rules produces a
count, not a sample. Straddles (5 trips, net +976) against spreads (11 trips, net −1,974) is equally
uninformative at these sizes. **Draw no structure-level conclusion.**

### F5 — the fee floor disables the take-profit but not the entry [MEDIUM, design]

The 09-16 audit found that a narrow fly "could not earn its round-trip fees intraday by
construction." Today repeated the pattern, and this time it lost:

| Session | Structure | TP | SL | Round-trip fees | Outcome |
|---|---|---|---|---:|---|
| 09-16 | iron fly | Rs 94 (off) | Rs 359 | 340 | time exit, net +4 |
| 09-18 | straddle | Rs 0 (off) | Rs 931 | 124 | time exit, net **+627** |
| 09-25 | iron fly | Rs 1 (off) | **Rs 328** | 302 | stop, net −646 |

When the take-profit is off, the structure keeps only its loss side. On the flies that stop is about
1× the round-trip fee, so a 1σ adverse move closes the trade at roughly twice the fee, while an
equal favourable move is worth only the theta the bracket does not count.

09-18 is the counterexample: a TP-off straddle netted +627. An "enter only if the bracket can clear
fees" rule is therefore **not** supported by these three trades. It must be pinned before looking at
data (§3 R3).

### F6 — 7-minute window on 09-25 with no exit evaluation [MEDIUM, open]

- All four legs filled by 13:01:47.
- The lazy `structure_bracket()` (`nifty_shield_handler.py:153`) journaled nothing until 13:09:31,
  after a restart. On 09-16, 09-23 and 09-24 it journaled within seconds of the fill.
- In that window the driver processed 7 bars and the chain poller wrote the 2026-09-29 expiry every
  ~8 s (`logs/chain_poller.log`). The poller and driver were live. Whether the exit loop's marks
  reader saw a fresh snapshot is not shown.
- The exit loop (`nifty_shield_handler.py:700-742`) has two paths that skip a group silently:
  - `_marks_are_stale()` returns early, and journals only on an edge.
  - A leg is missing from `marks` (`continue`, never journaled).
- **Cause not established.** No P&L impact today (the stop fired at 14:03). But an open structure
  went unmonitored for 7 minutes with no journal line, which is a silent failure.

### F7 — restarts replay the 13:00 signal [LOW, working as intended]

- The 13:08, 13:10 and 13:25 stops today were SIGINTs: operator/ops restarts during the
  phone-approval work.
- After each restart the strategy re-emitted the 13:00 iron-fly signal.
- The handler rejected it both times ("every leg rejected by a handler gate"). That is the stacking
  guard doing its job.
- Side effect: the two replays count as 2 of the 9 "skipped" structures and depress
  `signal_fill_conversion` (0.67). Reported conversion should exclude restart replays.

## 3. What we can do

The constraints come from the frozen identity:

- Structure selection lives in `strategies/nifty_shield_v1/`, frozen under `c5b722ff…536c`. It is not
  touched.
- No historical test over 2016-02-11 → 2022-12-31 is allowed.

Every lever below is in execution or reporting.

| # | Action | Why | Cost |
|---|---|---|---|
| R1 | **DONE 2026-09-25.** On the live book it reproduces net −1,640.6, PF 0.737, DD Rs 2,374.2 (0.237%). **Make `metrics_report` net.** P&L, wins/losses and PF after fees, and drawdown from the net per-structure equity curve instead of the runtime key. Add a gross column beside it. | F1. Blocks any honest E008 report. | Small; TDD against this book's numbers (−1,640.6 / 0.74 / −2,374.2). |
| R2 | **Book paper P&L into runtime equity**, so the handler drawdown gate sees losses. Add a drill that forces a breach. | F2. Gate 4 is vacuous without it. | Medium; execution code, not the frozen package. |
| R3 | **Freeze the execution config and declare where the E008 count restarts.** Recommended: count from 09-16 (σ bracket), i.e. **8 of 30** round-trips, and ledger that choice now, before more trips arrive. | F4. Pooling three exit regimes is not a sample. | Governance only. At ~1 trip per session, ~22 more sessions (~5 weeks). |
| R4 | **Resolve SPAN or amend gate 5** by explicit operator decision. | F3. | Operator decision, plus SPAN feed repair if it is kept. |
| R5 | **Journal every silent exit skip** (stale marks, missing leg mark) at WARNING, rate-limited per group. Then diagnose F6. | F6. An unmonitored open structure must be visible. | Small. |
| R6 | **Exclude restart replays from skip and conversion counts.** | F7. | Small. |
| R7 | *(Optional, new pre-declared rule)* A fee-feasibility **entry** gate: skip when the bracket's TP is below the fee floor. Pin it in writing **before** looking at more trades. Adopting it is an execution-rule change and restarts the R3 count again. **Caution:** runbook §9 forbids "tune anything toward returns". This only qualifies if it is framed and ratified as a cost-feasibility safety rule. Otherwise defer it past E008. | F5. The evidence is mixed (09-18), so this is a choice, not a finding. | Small code; a governance restart. |

**Not recommended:**

- **Raising lots to dilute fees.** Brokerage is mostly per order, so more lots only help if a gross
  edge exists. The σ era's gross is −Rs 140 over 8 trips. Treat lots as a capital-plan lever after
  E008.
- **Tuning the σ multiple or TP/SL thresholds on these 18 trades.** That is in-sample fitting on
  n=8, the same sin that retired C2's overlays.

## 4. Bottom line

Nothing in this window is evidence of an edge, and nothing is evidence against one. The trip count is
too small and mixes three exit regimes, and gross per trip sits at noise level against fixed fees.
What the window *does* establish:

- The measurement surface overstates the result (F1).
- Gate 5 is unmet, and sizing has drifted off the platform's margin authority (F3).
- Gate 4's input is unproven (F2).

Fix those (R1, R4, R2), freeze the config and restart the count (R3), and let the next ~22 sessions
accumulate on one identity.
