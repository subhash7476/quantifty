# Options-Wall Paper Pilot — Runbook

**Branch:** `feat/options-wall`
**Spec:** `docs/superpowers/specs/2026-08-14-options-wall-paper-pilot-design.md`
**Plan:** `docs/superpowers/plans/2026-08-14-options-wall-paper-pilot.md`

The pilot runs one process — the wall poller — which each cycle accumulates the
Nifty + BankNifty chains (with bid/ask), then runs the premium-farm paper executor.
It is a plumbing/mechanics validation, **not** a signal read (see spec §1, §11).

---

## Start / stop

```bash
python core/options_wall/poller.py
```

- Runs foreground; `Ctrl+C` (SIGINT) or SIGTERM stops cleanly.
- Idles outside market hours; retries every 30s while the Upstox token is missing/expired.
- Single-writer: a PID lock refuses a second instance.

Optional flags: `--poll-interval` (default 5s), `--idle-interval` (30s),
`--token-retry-interval` (30s), `--max-cycles N` (testing/preflight).

**Pre-flight before enabling live (spec §8.1):** the poller makes **4 Upstox calls
per cycle** (chain + quotes × 2 indices). Confirm this stays inside Upstox rate
limits at the chosen `--poll-interval`; widen the interval if not.

**Token:** refresh the Upstox token via the Dashboard login before market open;
the poller will not fetch without a valid token (loud, not silent).

**Quote-coverage check (do not skip):** entry requires a live bid/ask on every leg
(spec §3.4) — a fly is not opened on ltp-only legs. After the first few live cycles,
confirm the trail is actually carrying quotes: `best_bid`/`best_ask` should be
non-NULL on the near-ATM strikes in `wall_chain_snapshots.duckdb`. If they are all
NULL (watch the log for `quotes error:` lines, or a `0 quoted` count), no farm trade
can ever open — check the token scope and that `fetch_quotes_batch` returns full
instrument keys (see the pre-existing keying caveat in the review).

---

## State & data files (`data/options/`)

| File | Written by | Contents |
|------|-----------|----------|
| `wall_chain_snapshots.duckdb` | poller (sole writer) | append-only chain trail incl. `best_bid`/`best_ask` |
| `wall_scan_results.duckdb` | executor / scan writers | `scan_results`, `session_regime`, `oi_baseline`, **`trades`** |
| `wall_poller_heartbeat.json` | poller | last snapshot ts + rows/underlying |
| `wall_poller.pid` | poller | single-writer lock |

The `trades` table holds one row per paper round-trip: entry/exit ts, the fly
(short strike, wings, qty), net credit, entry+exit fees, gross/net P&L, and
`exit_reason` ∈ {`tp`, `sl`, `regime_flip`, `time_stop`}. Open positions have
`exit_ts IS NULL`.

---

## Frozen parameters — do not tune mid-month

All values are pinned in `ScanConfig` / `PaperConfig`; see spec §10 for the
authoritative table. Headline: farm-only; ATM-centered iron fly; wings ±1.5% of
spot snapped to strike; positive-GEX **and** spot-near-pin (±0.5%) **and** ATM
IV−RV ≥ 2.0; entry 09:30–15:00 IST; DTE ≥ 1; ≤ 1 open fly per index; TP +50% /
SL −2× / regime-flip / time-stop 15:15 the session before expiry; 1 lot; fees via
`core/execution/options/fees.py`.

**Changing any of these during the pilot invalidates the month** (spec §1). If a
change is genuinely needed, stop the pilot and restart the clock.

---

## Month-end analysis — plumbing/mechanics only (spec §11)

Descriptive, `n≈4–8` — **not** a signal or edge claim:

- trade count and exit-reason mix
- fee drag as a fraction of gross credit (verify the ~3% estimate against realized fills)
- mark-vs-fill slippage
- regime-flip-exit frequency
- reconstruction/audit failures: missing quotes, un-markable legs, store gaps

**Explicitly out of scope:** IV−RV-realized attribution ("did the gap predict the
outcome?") and any win-rate/edge claim — the sample structurally cannot support
them, and month-1 must never seed a successor's effect-size band (spec §1, RFA
`per_trade_pnl` wall).

Output: a report on whether the loop works and the fees are real, plus a decision
on whether the screen merits a formal pre-registration — never a go-live.
