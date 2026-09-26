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
- **Gate 4 (drawdown) cannot trip.** Confirmed 2026-09-26 (§5 R2): a restart restores positions but
  never cash, and the gate only runs on entry signals, so it never sees a realised loss.

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

### F2 — the drawdown gate cannot see realised losses [HIGH, confirmed 2026-09-26, E008 gate 4]

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

- The limit itself is correct: `nifty_shield_gates.py:76` sets `max_drawdown_limit = 30000 /
  initial_capital`, the declared Rs 30,000 single-day figure. *(The first draft of this audit wrongly
  quoted the 0.05 default.)* The Rs 150,000 5-day streak is a stressed declaration, not a gate.
- `metrics.json` is not a valid drawdown source either way, which is part of F1.

**Confirmed (2026-09-26).**

- `handler.py:_replay_state` (317-361) replays orders, fills, positions and groups, but **never cash**.
  So every start re-seeds `cash_balance = max_equity = initial_capital` (`handler.py:252-253`).
- The gate is evaluated only for non-EXIT signals (`handler.py:673`), i.e. at the 13:00 entry, once a
  session.
- The loss lands at the exit and the process restarts before the next entry, so the gate never sees a
  realised loss.

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
| R2 | See §5. **Book paper P&L into runtime equity**, so the handler drawdown gate sees losses. Add a drill that forces a breach. | F2. Gate 4 is vacuous without it. | Medium; execution code, not the frozen package. |
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

## 5. Fix plan for R1–R7 (2026-09-26)

> **Status (2026-09-26): R1–R6 implemented. R7 is deferred.**
>
> - **R4 did not go as planned.** `NseMarginEngine` cannot price option structures: v400 has
>   one risk array per underlying, looked up by contract symbol, so every option leg raises
>   `MissingRiskArray`. The operator chose ADR-025 (basket sizing for options) over building
>   options SPAN.
> - **The working SPAN ingest was never on main.** It was `98ce531`, stranded on an unmerged
>   branch; it has been cherry-picked. 35 sessions were backfilled and the fetch is now nightly.
> - **The backfill uncovered a bug.** With SPAN loadable, the handler would have raised on every
>   option leg and failed every entry. The handler now drops `span_snapshot`.
> - **R2 also found that the kill switch blocks exits** (`handler.py:655`), so a breach flattens
>   first and then arms the switch.
> - **The R3 window restarts on 2026-09-28** under the identity `616011bc…`.

Order of work: **R4 → R2 → R5 → R6 → R3**, with R7 deferred.

- R4 and R2 are the two E008 gates.
- R5 closes a silent failure.
- R6 is bookkeeping.
- R3 is a governance entry, filed only once R2, R4 and R5 have landed. Each of them is an execution
  change, so the count restarts from the last of them rather than from 09-16.

All of it is execution, ops or reporting code. `strategies/nifty_shield_v1/` and `config_hash` are
untouched.

### R1 — net reporting · DONE

`e7f7676` (PR #19). Reproduces −1,640.6 / PF 0.737 / DD Rs 2,374.2 on the live book.

### R2 — make the drawdown gate see losses

**Root cause (confirmed, F2):** a restart restores positions but never cash, and the gate only runs
at entry.

**Fix:**

1. **Restore cash in `_replay_state`.**
   - After step 2, fold every restored fill through the same arithmetic as `_update_equity_metrics`
     (`handler.py:1243`): cash ∓ qty·price − fee.
   - Seed `max_equity` from the running peak of that fold, not from `initial_capital`.
   - Restored equity then equals initial capital + realised net P&L. On today's book that is
     10,00,000 − 1,640.6.
2. **Make the limit a single-day rule, as declared.**
   - The datasheet says Rs 30,000 *single day*, but the handler's gate is peak-to-trough since start
     of process.
   - Add a session-start equity anchor, captured after the cash fold.
   - Trip when the anchor minus current MTM equity ≥ Rs 30,000.
   - Keep the peak rule as-is for other strategies. The new rule is NiftyShield-only, passed through
     `ExecutionConfig` from `nifty_shield_gates.py`.
3. **Evaluate the gate on every exit-loop tick, not only on entry signals.**
   - `nifty_shield_handler.py:700-742` already prices the open structure every ~15 s.
   - Compute MTM equity there and call `activate_kill_switch` on a breach. The kill switch then
     flattens through the existing close-only path.
   - Without this, an intraday loss is never checked, because no second entry signal arrives in a
     session.
4. **Persist the kill switch.**
   - `activate_kill_switch` (`handler.py:1021`) only writes `metrics.json`, and a restart clears it.
   - Journal a `KILL_SWITCH` event, and have `_replay_state` re-arm the switch if today's journal has
     one.

**Tests (TDD):**

- Replay of a fill set restores cash and peak.
- A −30,001 MTM against the session anchor trips the switch from the exit loop.
- A restart after a trip stays kill-switched.
- Forced-breach drill for gate 4 / E7-5: in REPLAY, inject marks that move a 2-lot fly Rs 30K against,
  then assert a journal CRITICAL, a flatten and no re-entry after restart.

**Cost:** medium. `core/execution/handler.py` is shared by every strategy, so the full suite must stay
green, not only NiftyShield.

### R4 — SPAN back as the sizing authority (gate 5, ADR-011/012/013)

**Root cause:** the SPAN archive stops at **2026-08-06** (`data/span/nse_fo_span_2026-08-06.parquet`),
and nothing schedules `scripts/fetch_span_params.py` (no caller in `scripts/` or the ops tasks). So
`SpanRepository.load(expected_span_date())` raises on every session from 09-07, and `f051fd3` moved
sizing onto the Upstox basket instead of failing loud.

**Fix:**

1. **Verify the fetcher runs.** Run `python scripts/fetch_span_params.py --date <last session>`. Its
   URL template (`nseindia.com/span/span_{ddmmyyyy}.zip`) is itself flagged "must be verified". The
   `data/span/staging/nsccl_*.zip` files suggest the NSCCL archive is the working source.
   - Then backfill 2026-08-07 → today, so past sessions' SPAN+ELM can be recomputed offline as
     evidence.
2. **Schedule it.**
   - Add a SPAN step to the 20:00 `DownloadAll` job (`scripts/download_all_data.py`) so the next
     session's file exists by the next morning.
   - Promote preflight's SPAN check from WARN to **BLOCK** for NiftyShield, matching gate 5.
3. **Restore the authority order.**
   - `NseMarginEngine` sizes the entry.
   - The Upstox basket is logged beside it as comparison evidence only, which is the reconciliation
     ADR-013 defers.
   - A basket outage no longer skips an entry. Remove the 09-08 "Upstox basket margin unavailable"
     skip path.
   - Keeping broker sizing instead is an **ADR amendment for you to sign**. Gate 5's text then
     changes before the window resumes, not after.
4. **Tests:** an absent SPAN file blocks preflight, and sizing uses `NseMarginEngine`'s figure when
   both figures exist.

**Cost:** small code, plus one verification run against NSE.

### R5 — no silent exit skips (F6)

In the exit loop (`nifty_shield_handler.py:700-742`):

1. **Missing-leg branch.** `if not all(sym in marks …): continue` becomes a WARNING journal
   `EXIT_EVAL_SKIPPED` carrying reason `missing_leg_marks`, `group_id` and the missing symbols. It is
   rate-limited to one record per group per 60 s, plus a "resolved" record when marks return (mirror
   the edge-triggering in `_marks_are_stale`).
2. **Stale branch.** It already journals on the edge. Add the open `group_id`s to that record, so
   "stale while a structure is open" is visible as such.
3. **The `_min_interval_s` early return** is expected behaviour and stays unjournaled.
4. **Unmonitored-structure watchdog.** If a group has been open more than 60 s with no successful
   evaluation, journal a CRITICAL. That is the exact F6 symptom, whatever its cause.
5. **Diagnosis:** the next occurrence names its branch.

**Tests:**

- Marks missing a leg produce exactly one WARNING per 60 s and one resolve record.
- A group open 61 s without evaluation produces a CRITICAL.

**Cost:** small.

### R6 — restart replays out of skip/conversion counts (F7)

**Rule:** an `ENTRY_SKIPPED` whose `group_id` already has an `ENTRY_MARGIN` is a restart replay, not a
skipped structure. The `group_id` is a deterministic `uuid5`, so the replayed signal carries the same
id.

**Fix:**

- In `metrics_report.risk_metrics_report`, split `skips` into `replays` and `skips` using that rule.
- Report `restart_replays` as its own count, and compute `structures_skipped`, `structures_attempted`
  and `signal_fill_conversion` without the replays.
- Apply the same split in `audit.py` wherever it counts skips.

**Test:** the 09-25 shape (one entry and two skips with the same `group_id`) gives entered 1, skipped
0, replays 2. On the live book: 18 entered, 7 skipped, 2 replays, conversion 0.72 (was 0.67).

**Cost:** small.

### R3 — freeze and restart the count (governance)

1. **Freeze once R2, R4 and R5 are merged.**
   - Record the execution identity: the commit, plus a hash over
     `core/execution/options/nifty_shield_*.py`, `core/execution/handler.py`,
     `scripts/nifty_shield_paper/` and `scripts/nifty_shield_paper_runner.py`.
   - Put it in a note under E008 in `docs/STRATEGY_PROMOTION_LEDGER.md`.
2. **Declare the window start** as the first session on that identity, before it starts (runbook §8.1
   forbids deciding after seeing the count).
   - R2 and R4 change risk and sizing behaviour, so the 8 σ-bracket trips (09-16 → 09-25) become
     history, not window.
   - Keeping them would need 09-16 as the declared start and R2/R4/R5 shipped as evidence-only. That
     is not possible for R4, since it changes sizing.
3. **Enforce it in code.**
   - Add `WINDOW_START` and the execution hash to `assemble_report.py`.
   - A session counts only if it is on or after `WINDOW_START` **and** its recorder's
     `platform_commit` carries the frozen execution hash.
   - Otherwise it prints as "off-identity", the way `sessions_counting` already excludes unclean
     sessions.
4. **Cost:** a ledger note plus a small `assemble_report` change. At about one trip per session, ~30
   sessions (~6–7 weeks) to reach 30 round-trips.

### R7 — fee-feasibility entry gate · DEFER

**Mechanics (for later):**

- `sigma_bracket()` (`nifty_shield_pricing.py:138`) needs only leg prices, spot, DTE and the fee
  floor. The credit gate already holds pre-entry marks at 13:00, so the bracket can be sized from marks
  before the fill, and the structure skipped when `tp_enabled` is False.
- About 20 lines, next to the credit-floor gate.

**Why defer:**

- Runbook §9 forbids tuning toward returns, and three trades (09-16, 09-18, 09-25) split 2–1 on
  whether it would have helped.
- Adopting it mid-window restarts the count again.

**Right path:** run it as a **shadow gate**, journaling `WOULD_SKIP` at entry without acting on it.
That is observe-only and changes no behaviour. Then pre-declare it as a cost-feasibility rule for a
post-E008 identity, judged on the forward trades it would have skipped.
