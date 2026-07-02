# Strategy Datasheet — `<strategy_id>`

**Template version:** 1.0 (MM12.5)
**Created at:** Stage 0→1 (CONFORMANT submission)
**Purpose:** The promises every validation window is validated against. Frozen at Stage 1 grant; any change produces a new identity (§2).

---

## 1. Identity

| Field | Value |
|---|---|
| `strategy_id` | `<strategy_id>` |
| `code_ref` | `<commit hash of strategy package>` |
| `config_hash` | `<SHA-256 of build_signal_source(config) dict>` |
| `STRATEGY_CONTRACT_VERSION` | `1.0` |
| Package/repository | `<URL or path to external strategy repo>` |
| Factory export | `build_signal_source(config)` |

## 2. Config schema

| Parameter | Type | Default | Description |
|---|---|---|---|
| `<param>` | `<type>` | `<default>` | `<description>` |

## 3. Certified config values

The exact config dict used for Stage 1 conformance certification:

```json
{
  "<key>": "<value>"
}
```

## 4. Universe

| Field | Value |
|---|---|
| Symbols | `<list of NSE symbols or instrument keys>` |
| Derivative types | `<equity | futures | options | mix>` |
| Underlyings (F&O) | `<e.g. NIFTY, BANKNIFTY>` |

## 5. Session behavior

| Field | Value |
|---|---|
| `on_bar` signals per bar (max) | `<max signals emitted in a single bar>` |
| Entry frequency band | `<e.g. 1-5 entries per day>` |
| Exit frequency band | `<e.g. 1-5 exits per day>` |
| Max simultaneous positions | `<integer>` |
| Session bounds | `<e.g. 09:15-15:30 IST, all trading days>` |

## 6. Latency budget

| Field | Value |
|---|---|
| `on_bar` p99 latency budget | `<milliseconds>` |

## 7. Risk declaration

| Field | Value |
|---|---|
| Max drawdown (Rs) | `<Rs amount>` |
| Max drawdown (% of allocated capital) | `<percentage>` |
| Per-trade risk (`risk_r` semantics) | `<description: e.g. fixed Rs, % of equity, ATR multiple>` |
| `sl_distance` semantics | `<description: e.g. fixed percentage, ATR multiple, Rs>` |
| Max margin utilization | `<Rs amount or percentage>` |
| Allocated capital (Stage 3+) | `<Rs amount>` |

## 8. External backtest reference

| Field | Value |
|---|---|
| Backtest period | `<start date> – <end date>` |
| Backtest report path | `<committed path or external reference>` |
| Key metrics (filed, not graded) | `<win rate, profit factor, max DD, total trades>` |

## 9. Risk gate configuration (for validation windows)

| Gate | Setting | Source |
|---|---|---|
| Drawdown limit | `<from risk declaration>` | Handler drawdown gate |
| Daily trade limit | `<from entry frequency band>` | Handler daily-limit gate |
| Max positions | `<from max simultaneous>` | Handler stacking gate |
| Margin budget | `<from max margin utilization>` | Handler margin gate |
| Greek limits | `<if applicable>` | Handler Greek gate |
