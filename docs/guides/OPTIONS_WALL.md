# Options-Wall — how it trades (paper reference strategy)

> **Paper only. A pilot, not a validated strategy. Not advice.** Its P&L is computed
> directly from chain mids by `core/options_wall/fly.py` plus the shared options fee
> model. It never touches a broker order path, so there is no live mode to switch on.

## One sentence

Every 5 seconds through market hours, snapshot the Nifty, Bank Nifty and Sensex
option chains, compute the dealer-gamma "wall" picture, and **paper-sell an ATM iron
fly** on an index when gamma is positive, spot sits on the pin strike and implied
vol is rich against realized.

## Two halves

**1. The wall (trade intelligence, always on).** `scripts/options_wall_poller.py` is
the only writer of both stores:

| Store | Contents |
|---|---|
| `data/options/wall_chain_snapshots.duckdb` | raw chain snapshots, append-only (nearest expiry per index) |
| `data/options/wall_scan_results.duckdb` | `scan_results` (farm list), `session_regime`, `oi_baseline` (09:15), `trades` |

From each snapshot it computes the board metrics (`core/analytics/wall_metrics.py`):
- net GEX regime (Positive / Negative)
- pin strike, runner-up and conviction
- call and put gamma walls
- gamma concentration (HHI)
- ATM-IV 1σ move to expiry
- the dealer hedge ladder at ±0.5/1/1.5 %
- OI added or unwound since the open

The chain scanner (`core/analytics/chain_scanner.py`) ranks three screens:
**premium farm** (actionable), **imperfections** (call/put IV asymmetry, single-strike
vol outliers) and **laggards** (fresh flip crosses, near-expiry charm). Only the farm
screen trades. The other two are discovery.

**2. The paper executor** (`core/options_wall/paper_executor.py`) runs inside the
same poll cycle.

## Entry — the premium-farm screen

An entry needs a farm row, which requires all of these:

| Condition | Value |
|---|---|
| Time | 09:30 – 15:00 IST |
| No fly already open on this index | at most one per underlying |
| Realized vol available | annualised from the last **5 sessions** of 1m bars |
| GEX regime | **Positive** (dealers long gamma → damping) |
| Spot near pin | \|spot − pin\| / spot ≤ **0.5 %** |
| ATM IV − realized vol | ≥ **2.0** vol points |
| Leg spreads | ≤ 5 % of mid where quotes exist |
| ATM credit | > 0 |

**Structure:** short ATM CE + short ATM PE, long CE and PE wings at the listed strikes
nearest **spot × (1 ± 1.5 %)**. Quantity is **1 lot**, with the lot size read from the
contract.

## Exits

| Trigger | Rule |
|---|---|
| Take-profit | unrealized P&L ≥ **25 % of net credit** |
| Stop-loss | unrealized P&L ≤ −**50 % of max loss** (max loss = wing width × qty − credit) |
| Time stop | on the session **before expiry or expiry day** (DTE ≤ 1), at 15:35, capped 2 min before the derivatives close |
| Manual | close button on the dashboard (`data/options/close_requests/`) |

**Positions are carried overnight.** There is no daily flatten. A fly opened on
Wednesday for a Tuesday expiry can be held until Monday 15:35. A GEX flip to
Negative **blocks new entries but never exits**. Net gamma's sign changes every
28–93 s, so exiting on it would just pay a round trip (~₹212) to chase noise.

## What it needs to run

| Input | Source | If missing |
|---|---|---|
| Valid Upstox token | daily login | the poller idles and retries every 30 s |
| Option chains | Upstox V3 option-chain API, polled by the wall poller | — |
| 5 sessions of 1m index bars | `scripts/bootstrap.py seed` → `data/market_data/{nse,bse}/candles/1m/` | realized vol = None → **no entries** (the wall still draws) |
| Instrument master | `bootstrap.py init` / orchestrator 09:10 | expiries cannot resolve |

## Where to look

- Wall board and farm list: `http://127.0.0.1:5000/options/wall/`
- Option-chain dashboard (PCR, net GEX, OI build-up, max pain, IV smile): `http://127.0.0.1:5000/options/`
- Expectancy by exit reason, GEX regime and IV−RV band:
  `python scripts/options_wall/evidence_report.py --index ALL` → `docs/reports/OPTIONS_WALL_EVIDENCE.md`
- Runbook: `docs/reports/strategies/OPTIONS_WALL_PILOT_RUNBOOK.md`

## Known limitations

- Ranking is by IV−RV gap. No SPAN margin enters the screen.
- "Dealer side" is inferred per contract from the OI × price grid, not observed.
- Zero farm trades on a given day is normal. All screen conditions must hold at once.
