# Strategy Datasheet — `reference_heartbeat_v1`

**Created at:** Stage 0→1 (CONFORMANT, 2026-07-02)
**Status:** CONFORMANT, permanently PAPER-confined per ADR-020

---

## 1. Identity

| Field | Value |
|---|---|
| `strategy_id` | `reference_heartbeat_v1` |
| `code_ref` | `e5e44d4` |
| `config_hash` | `sha256:47de...` (default config) |
| `STRATEGY_CONTRACT_VERSION` | `1.0` |
| Package/repository | `reference_strategies/heartbeat/` (in-repo reference implementation) |
| Factory export | `reference_strategies.heartbeat.build_signal_source(config)` |

## 2. Config schema

| Parameter | Type | Default | Description |
|---|---|---|---|
| `entry_period_bars` | `int` | 60 | Number of bars before a BUY is emitted when flat |
| `holding_period_bars` | `int` | 15 | Number of bars before an EXIT is emitted when long |
| `sl_distance_pct` | `float` | 0.01 | SL distance as fraction of close price (1%) |
| `risk_r` | `float` | 500.0 | Fixed risk amount in Rs per trade |

## 3. Certified config values

```json
{
  "entry_period_bars": 60,
  "holding_period_bars": 15,
  "sl_distance_pct": 0.01,
  "risk_r": 500.0
}
```

## 4. Universe

| Field | Value |
|---|---|
| Symbols | Single equity symbol (e.g. `NSE_EQ|INE...`) |
| Derivative types | Equity only |
| Underlyings (F&O) | N/A (equity-only reference) |

## 5. Session behavior

| Field | Value |
|---|---|
| `on_bar` signals per bar (max) | 1 |
| Entry frequency band | 1 entry every ~60 bars |
| Exit frequency band | 1 exit every ~15 bars (when long) |
| Max simultaneous positions | 1 per symbol |
| Session bounds | All trading days, all market hours |

## 6. Latency budget

| Field | Value |
|---|---|
| `on_bar` p99 latency budget | < 1 ms (fixed-cadence, no I/O) |

## 7. Risk declaration

| Field | Value |
|---|---|
| Max drawdown (Rs) | 5000 (10 × risk_r) |
| Max drawdown (% of allocated capital) | 10% |
| Per-trade risk (`risk_r` semantics) | Fixed Rs 500 per trade |
| `sl_distance` semantics | Percentage of close price (default 1%) |
| Max margin utilization | 50000 Rs |
| Allocated capital (Stage 3+) | N/A (PAPER-confined) |

## 8. External backtest reference

N/A — reference strategy is non-alpha canary per ADR-020. No backtest evidence is offered or required.

## 9. Risk gate configuration

| Gate | Setting | Source |
|---|---|---|
| Drawdown limit | 5000 Rs | Risk declaration |
| Daily trade limit | 20 | Entry frequency band |
| Max positions | 5 | Stacking gate |
| Margin budget | 50000 Rs | Risk declaration |
| Greek limits | N/A (equity only) | N/A |
