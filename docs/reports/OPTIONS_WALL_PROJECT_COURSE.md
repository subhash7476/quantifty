# Options-Wall Intraday Scanner — Project Course

**Branch:** `feat/options-wall`
**Date:** 2026-08-13
**Status:** Working plan (not frozen). Supersedes the DW-1 pre-registration's
validation-protocol framing; this is a discovery instrument, not a pre-registered
strategy.

---

## 1. Purpose & Framing

Build an **intraday option-chain scanner** for the Nifty and BankNifty index chains.
It reads the live chain every poll cycle, applies dealer-positioning metrics to a
small set of concrete trade-decision rules, and surfaces a **ranked "farm list"** of
strikes/expiries where premium is harvestable, mispriced, or lagging the underlying.

Deliberate departures from the DW-1 pre-registration (`DW1_DEALER_WALL_PRE_REGISTRATION.md`):

| DW-1 said | This project says |
|-----------|-------------------|
| Pre-registered construct, TRAIN/HOLDOUT/SEALED gates | **No gates.** Forward-only discovery instrument. |
| 13:00 IST seam, weekly formation | **Continuous intraday scan** — every snapshot is a candidate. |
| Reuse NiftyShield execution infra | **Fully decoupled.** NiftyShield is a separate prior design; it does not feed this scanner. |
| Statistical `per_trade_pnl` / rank-IC framing | **None.** No effect-size claim is being made. |
| Single strategy hypothesis | **Three orthogonal screens** surfaced for the operator to study/act on. |

This is a **research base**: the deliverable is the ranked farm list and the
persisted scan trail, not a strategy. If a screen later proves robust on the
forward trail, a *separate* pre-registration can freeze it — that is downstream and
out of scope here.

---

## 2. Thesis

Dealer positioning (gamma posture, OI concentration, pin, walls, and vol structure)
creates short-horizon, *computable* option mispricings:

1. **Positive-GEX pinning** → price is absorbed toward the pin/walls → short-premium
   (condors/flies near pin) harvests theta + the vol risk premium.
2. **Negative-GEX amplification** → price breaking the flip/thin-gamma gap gets chased
   by dealer hedging → long-premium / directional spreads on the break.
3. **Repricing lag** → OI/IV that has not caught up to a spot move, a flip cross, or
   near-expiry charm decay is a transient opportunity.

The regime sign (net GEX) is the single conditioning variable for *which* screen is
active; each screen is scored independently and ranked on **risk-adjusted credit**.

---

## 3. Scope & Decisions

| # | Decision | Value |
|---|----------|-------|
| D1 | Universe | **Nifty (Tue) + BankNifty (Wed)** index chains only. Stock options (363 names) deferred — dealer-positioning OI mass lives in the index chains; stock options are a separate, heavier lift. |
| D2 | Cadence | Continuous — every provider poll cycle (5s). No fixed seam. |
| D3 | Screens | (a) Premium farm, (b) Imperfections, (c) Laggards (defined §5). |
| D4 | Ranking | Risk-adjusted credit = `credit / margin`, gated on IV−RV spread and a liquidity screen. |
| D5 | Short-premium guard | Never short premium into negative-GEX; never outside `[Put Wall, Call Wall]`; hard stop discipline. |
| D6 | Substrate | Live Upstox V3 chain + existing analytics. No EOD bhavcopy reconstruction in scope. |
| D7 | Execution | None. Scanner outputs a list. Trade firing is a later, separately-authorized decision. |

---

## 4. Architecture

```
Upstox chain (5s poll)
        │
        ▼
OptionsProvider ──────────────► chain_cache.duckdb  (canonical snapshot store — §6)
        │  List[OptionChainRow]
        ▼
OptionsAnalytics (exists)       GEX · flip · walls · pin · PCR · MaxPain · OI patterns
        │  OptionsStructuralData
        ▼
ChainScanner.scan_chain()  NEW  three screens → ScanResult rows
        │
        ├────────► scan_results.duckdb   (persisted farm list + scan trail)
        │
        ▼
options_publisher (exists) ────► /options/wall panel (SSE)
```

### Exists (verified)
| Layer | File |
|-------|------|
| Chain fetch + cache | `core/data/options_provider.py` (`OptionChainRow`, `fetch_option_chain`, `get_weekly_expiry`, `get_available_expiries`) |
| GEX / flip / walls / PCR / MaxPain / OI patterns | `core/analytics/options_analytics.py` (`calculate_gex`, `_find_zero_gamma_level`, `analyze_oi_changes` → `resistance_strike`/`support_strike`, `calculate_pcr`, `calculate_max_pain`, `build_structural_snapshot`) |
| Liquidity screen pattern | `core/analytics/options_selection.py` (`screen_candidate`: bid/ask/oi/volume/spread) |
| SSE push + UI | `core/messaging/options_publisher.py`, `app_facade/options_facade.py`, `flask_app/blueprints/options.py` |

### New
| Layer | Need |
|-------|------|
| Scanner | ✅ `core/analytics/chain_scanner.py` — `scan_chain()` + `ScanResult` |
| Snapshot store | ✅ `core/data/options_wall_store.py` — `append_snapshot` / `latest_snapshot` / `snapshot_timestamps` |
| Realized vol | ✅ `core/analytics/realized_vol.py` — `session_realized_vol_pct` (percent units, 1m bars, intra-session returns only) |
| Engine | ✅ `core/options_wall/engine.py` — `scan_indices()` (load-or-fetch → structural → RV → quotes → scan) |
| CLI | ✅ `scripts/options_wall_scan.py` — prints the ranked farm list |
| Skew / term-structure kinks | multi-expiry chain fetch + 25Δ put/call IV |
| OI rotation since open | 09:15 baseline store (current `oi_change` is vs prev close only) |
| Laggard detector | flip-cross recency + charm cascade wired; repricing-lag needs the 09:15 baseline (Phase 2) |
| Pin conviction | argmax of `gamma_by_strike` + mass-concentration ratio |
| Persistence | `scan_results` table + daily regime row + baseline snapshots |
| UI | `/options/wall` panel — farm list, regime river, per-strike detail |

---

## 5. The Three Screens

### (a) Premium Farm — "where do we harvest theta"
Active only when `GEX regime == Positive`.
- **IV − RV gap**: sell premium only where `IV − realized_vol > threshold`. This is
  the actual edge; raw premium without the gap is a coin flip with a left tail.
- **Pin/wall box**: candidate shorts near the pin strike or inside `[Put Wall, Call Wall]`.
- **Structure**: iron fly at pin (high pin conviction) or short strangle `[PW, CW]`.
- **Rank**: `credit / margin`, then IV−RV gap desc.

### (b) Imperfections — "where is the chain structurally wrong"
Regime-agnostic, always scored.
- **Skew anomaly**: 25Δ put IV vs call IV vs its own recent rolling history.
- **Term-structure kink**: front ATM IV vs back ATM IV inverted/dislocated → calendar
  candidate, and a "do not sell the dislocated leg" guard.
- **Call-put IV asymmetry**: CE IV vs PE IV diverging against PCR (one side lagging).
- **Single-strike vol outlier**: a strike's IV out of line with its neighbours.

### (c) Laggards — "what hasn't caught up yet"
Regime-agnostic, always scored.
- **Repricing lag**: spot moved Δ% but a strike's IV/OI has not rotated in kind.
- **Gamma-flip lag**: spot just crossed the flip level but OI rotation/IV hasn't
  confirmed — the dealer-hedging chase is still ahead.
- **Charm cascade**: 1–2 DTE strikes where delta-bleed forces dealer rebalance.
- **OI-vs-price divergence**: OI building into a move (writers trapped) = fuel.

---

## 6. Data Reality Check

| Item | State |
|------|-------|
| Live Nifty chain | ✅ `chain_cache.duckdb` (`option_chain_snapshot`) — but **only 1 snapshot** (2026-08-13); recording has not accumulated. |
| Live BankNifty chain | ✅ provider/`OptionsProvider` supports `NSE_INDEX|Nifty Bank`; live chain resolves (dashboard already lists BankNifty expiries). |
| Index-option bhavcopy | Nifty only (`options_bhavcopy.duckdb`, 5.49M rows, 2016→2026); **no BankNifty history**; Nifty weeklies only from Feb 2019. Not in scope for this scanner (live-only), but relevant if a screen is ever backtested. |
| Bid/ask on `OptionChainRow` | ❌ absent — chain endpoint returns ltp/oi/volume only. Liquidity screen must use `UpstoxMarketData.fetch_quotes_batch` (the pattern already in `options_selection.py`). |
| OI change semantics | `oi_change = oi − prev_oi` (vs prev close), **not** vs 09:15. "Since open" needs a baseline store. |
| Realized vol | ✅ 1m index candles exist (Nifty/BankNifty) — compute RV directly. |

**Wiring — RESOLVED (Phase 0, 2026-08-14).** Three cache artifacts exist and none of
them is the wall store:

| Path | Owner | Model | Coverage |
|------|-------|-------|----------|
| `data/options/chain_cache.duckdb` | `scripts/nifty_shield_paper/chain_poller.py` | **single-snapshot overwrite** (fresh DB per 5s cycle, atomic `os.replace`) | Nifty only, latest cycle only |
| `data/market_data/options_poller.duckdb` | `OptionsProvider` default (dashboard facade, `read_only=True`) | append | **file does not exist on disk** — dead path |
| **`data/options/wall_chain_snapshots.duckdb`** | **`core/data/options_wall_store.py`** (this project) | **append-only, multi-symbol** | Nifty + BankNifty, full trail |

**Decision:** the wall scanner owns `wall_chain_snapshots.duckdb` via
`core/data/options_wall_store.py` (`append_snapshot` / `latest_snapshot` /
`snapshot_timestamps`). It is append-only and accumulates every cycle, because the
scan trail and regime river need history — which the NiftyShield overwrite cache
deliberately does not retain. NiftyShield's `chain_poller.py` is left untouched
(decoupled); note this means Nifty is currently polled by *both* writers once the
wall poller runs — a consolidation question deferred to Phase 2.

---

## 7. Phased Milestones

### Phase 0 — Wiring reconciliation ✅ DONE (2026-08-14)
- ✅ Canonical store pinned: `data/options/wall_chain_snapshots.duckdb` via
  `core/data/options_wall_store.py` (append-only, Nifty + BankNifty). Verified
  end-to-end: appended live Nifty (210 rows) + BankNifty (334 rows) and read both
  back through `latest_snapshot`.
- ✅ BankNifty chain + expiries resolve live (Wed expiry 2026-08-25, 167 strikes,
  `underlying_ltp` 57528.5, IV present on 219/334 rows).
- ✅ Bid/ask confirmed: `UpstoxMarketData.fetch_quotes_batch` returns `best_bid` /
  `best_ask` (from market-depth), keyed by the option `instrument_key` (`NSE_FO|<token>`).
- ⚠️ Gamma coverage is partial: Upstox returns gamma on ~73/210 Nifty and ~99/334
  BankNifty rows (near-ATM only). GEX/flip/pin/wall are only as good as this
  coverage; `calculate_gex` already skips null/zero gamma. Deep-ITM rows carry `iv=0.0`
  (treated as missing).

### Phase 1 — Scanner core ✅ DONE (2026-08-14)
- ✅ `core/analytics/chain_scanner.py`: `scan_chain(chain, structural, realized_vol,
  quotes) -> List[ScanResult]`, three screens, ranked by `credit / margin`.
- ✅ `core/analytics/realized_vol.py`: annualized 1m RV in percent units (fixed the
  sqrt(252)-only annualization bug — it understated RV by ~30x; now Nifty ≈ 9.4%,
  BankNifty ≈ 11.9%).
- ✅ `core/options_wall/engine.py` + `scripts/options_wall_scan.py`: live run
  produces a sane ranked list. Bid/ask enrichment via `fetch_quotes_batch` gates the
  farm screen on `max_spread_pct`.
- ⚠️ Screen semantics settled this pass: vol-outlier scans only the near-ATM band
  (deep-wing IV is garbage/illiquid); `repricing_lag` disabled until the 09:15
  baseline exists (Phase 2); charm capped to top-5 by |theta|. Skew and term-structure
  kinks remain unimplemented (open question #2).

### Phase 2 — Persistence
- `scan_results` table (append-only, timestamped).
- Daily regime row (`session_regime`): net GEX, flip, pin, walls, IV, RV.
- 09:15 OI baseline store for the "since open" rotation.

### Phase 3 — Surface
- `/options/wall` blueprint + template: ranked farm list, regime river, per-strike detail.
- SSE push of new `ScanResult` rows (reuse `options_publisher.py`).

### Phase 4 — (deferred, not authorized here)
- Forward paper execution. Only if a screen proves it surfaces actionable setups on the
  forward trail, and only under a fresh pre-registration.

---

## 8. Open Questions (decide at each phase gate)

1. **Realized-vol window** for the IV−RV gap (5-min? 1-hour? same-day session?).
2. **Thresholds**: IV−RV minimum spread, skew-anomaly z-score, laggard Δ% tolerance.
   Start as constants with sane defaults; treat as display parameters, not tuned fits.
3. **Pin conviction** definition: mass-at-pin / total-mass, or distance-weighted concentration?
4. **Margin authority**: credit-per-margin needs `NseMarginEngine` per structure — confirm
   the scanner can compute it read-only without a SPAN snapshot (or fall back to a
   notional/credit ratio when SPAN is unavailable).
5. **Snapshot depth**: keep all 5s snapshots, or thin to N-min for the scan trail?

---

## 9. Non-goals & Guardrails

- **No auto-trading, no sizing, no broker orders.** Output is a list.
- **No backtest, no pre-registration, no sealed window.** Forward-only.
- **No NiftyShield integration.** This is a clean-room scanner.
- **Short premium is negative-skew.** The farm screen must always rank on risk-adjusted
  credit and carry a hard stop discipline; never farm into negative-GEX.
- **No over-engineering.** One scanner, one farm list, one panel. Add vanna/charm/term
  structure only when a screen actually needs them, not up front.
