# NiftyShield — how it trades (paper reference strategy)

> **Paper only. Not validated. Not advice.** NiftyShield is in a forward paper
> window (E008, started 2026-10-08) that exists to find out whether it works. It has
> no out-of-sample performance claim. Its paper runner is hard-wired to
> `ExecutionMode.PAPER` — it cannot route a real order, and the files that decide
> what it trades are frozen under an execution hash
> (`scripts/nifty_shield_paper/identity.py`). Do not edit them expecting the window
> evidence to stay comparable.

## One sentence

Once per session at **13:00 IST**, read the day's regime (from the DayType engine)
and India VIX, sell **one** weekly Nifty 50 option structure whose shape follows
the regime, and manage it to a ±1σ P&L bracket or the **15:35** hard exit.

## The daily cycle

| Time (IST) | What happens | Owner |
|---|---|---|
| 09:10 | Orchestrator starts: instrument master, Flask, token gate, ingestor, chain poller | `scripts/ops/orchestrator.py` |
| 09:15 → | Nifty 50 / Bank Nifty / India VIX 1m bars stream into the live buffer; the chain poller snapshots the Nifty option chain (marks) | `scripts/market_ingestor.py`, `scripts/nifty_shield_paper/chain_poller.py` |
| 13:00 | The DayType engine classifies the session from 09:15–13:00 bars and publishes the **13pm regime fact** | `scripts/daytype/publish_live_fact.py` → `data/features/day_type/day_type_facts.duckdb` |
| 13:00–13:30 | The signal source reads the fact and emits one structure (all legs share a `group_id`) | `strategies/nifty_shield_v1/source.py` |
| entry | Execution resolves the contracts, prices the credit, sizes on the Upstox basket margin, paper-fills | `core/execution/options/nifty_shield_*.py` |
| until exit | Every bar (and every idle tick after the underlying's last 15:29 print) the exit manager re-marks the structure | `nifty_shield_exit.py` |
| 15:35 | Hard flatten if still open | config `exit_time` |
| shutdown | Session evidence package: journal audit, telemetry, metrics, replay inputs | `scripts/nifty_shield_paper/session.py` |

## Entry rules

1. **One structure per session.** The source latches after its first decision.
2. **Entry window 13:00–13:30.** If the 13pm fact has not been published by then,
   the session is skipped.
3. **VIX hard limit.** India VIX at 13:00 above **20.0** → no trade (an absolute risk
   limit, deliberately not a percentile).
4. **Structure from regime + VIX percentile** (`structures.select_structure`):

   | Regime at 13:00 | India VIX percentile (trailing 756 sessions) | Structure | Risk |
   |---|---|---|---|
   | BullTrend | any | **bull put spread** (short ATM PE, long PE below) | defined |
   | BearTrend | any | **bear call spread** (short ATM CE, long CE above) | defined |
   | Choppy | > 59.0 | **short strangle** (short OTM CE + PE) | **undefined** |
   | Choppy | > 36.8 | **iron fly** (short ATM straddle + wings) | defined |
   | Choppy | otherwise, **or percentile unavailable** | **short straddle** | **undefined** |

   The short straddle and short strangle have **unlimited loss** if the index runs.
   The only bounds are the σ stop, the delta gate and the clock.

5. **Strikes are σ-anchored, not fixed points.** 1σ to expiry =
   `spot × (VIX/100) × √(DTE/365)`. The offsets are 0.541σ for spread wings,
   0.361σ for fly wings and 0.180σ for strangle shorts, snapped to the 50-point grid
   and never narrower than one strike.
6. **Expiry:** the nearest Nifty weekly expiry (Tuesday) at least 2 days away.
7. **Credit quality gate.** The entry is skipped if the credit actually available
   from live bid/ask marks is below **90 %** of the Black-Scholes credit for the same
   legs at their own implied vols. It catches stale or wide quotes.

## Sizing

- `lots = max(1, round(2 × regime_mult))`, where regime_mult is Choppy 1.0, trends 0.5.
  Take one lot off when VIX is above the 59th percentile (except for a strangle).
- Then lots are reduced until the structure's margin fits **25 %** of capital
  (default paper capital ₹10,00,000). Margin comes from the **Upstox basket-margin
  API** (`POST /v2/charges/margin`), which credits the hedge. If that call fails,
  the entry fails closed and does not fall back to a guess (ADR-025).
- Lot size 65 (NSE Nifty, from Sept 2026).

## Exits (priority order)

1. **Take-profit**: structure P&L ≥ the P&L at spot moving +1σ over the
   13:00→15:35 hold. Disabled if that target is below 3× round-trip fees.
2. **Stop**: structure P&L ≤ the P&L at the adverse −1σ move.
3. **Hard time**: 15:35.
4. **Delta gate**: portfolio |Δ| > 500 → flatten. There is no hedging and no
   adjustment legs.

Other risk gates: daily drawdown ₹30,000; the kill switch latches on a stale feed and
releases on the first fresh bar; one structure open at a time.

## What it needs to run

| Input | Source | If missing |
|---|---|---|
| Valid Upstox token | daily login / phone approval | nothing starts |
| Live Nifty, Bank Nifty, India VIX 1m bars | market ingestor (WebSocket) | 13pm fact not published → session skipped |
| Nifty option chain marks | chain poller → `data/options/chain_cache.duckdb` | runner refuses to start |
| India VIX daily closes, ≥ 189 (ideally 756) sessions | `scripts/bootstrap.py seed` → `data/nifty_shield/vix_history.duckdb` | **silent behaviour change:** percentile = None → Choppy always trades a **straddle** |
| DayType models | committed in `models/daytype/` | runner fails |
| SPAN file | `bootstrap.py seed` | warning only (sizing uses the broker basket) |

How the regime is produced: [DAYTYPE_ENGINE.md](DAYTYPE_ENGINE.md).

## Where to look

- Dashboard: `http://127.0.0.1:5000/nifty-shield/`
- Ledger and evidence: `data/nifty_shield/` (`journal.jsonl`, `trading/trading.db`, `sessions/{date}/`)
- Runtime journal: `logs/nifty_shield_runtime_events.jsonl`
- Preflight: `python scripts/ops/preflight.py`
- Run the session by hand (normally the orchestrator does it):
  `python scripts/nifty_shield_paper/session.py --data-root data/nifty_shield`

## Known limitations

- The regime label is a **full-session directional prior** predicted at 13:00. It is
  not a forecast of the 13:00–15:35 window. The supported evidence is a
  Bull-minus-Bear forward return separation of +0.255 pp (95 % CI +0.197…+0.312,
  n = 1,606 out-of-sample sessions). See
  `docs/reports/index_research/DAYTYPE_HORIZON_DISCLOSURE.md`.
- Undefined-risk structures (straddle, strangle) are reachable in Choppy regimes.
- The ±1σ bracket is probably too wide for a 13:00–15:35 hold: the afternoon
  carries less of the day's variance than the √t scaling assumes
  (`docs/reports/index_research/NIFTY_SHIELD_AFTERNOON_VARIANCE_2026-09-27.md`).
  A v2 change is a candidate only and is not applied, because the window is frozen.
- Parameters, derivation and audit trail: `strategies/nifty_shield_v1/config.py`,
  `docs/reports/index_research/NIFTY_SHIELD_*.md`.
