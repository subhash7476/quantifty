# Dependency Analysis — `core/runner.py` (extraction feasibility)

**Date:** 2026-06-04  **Basis:** full read of `D:\BOT\root\core\runner.py` (543 lines) + verification of three coupling points against `core/execution/handler.py` and `F:\Nifty`. **No strategy modules inspected. No code written. No migration performed. No redesign proposed.**

**Question:** does `runner.py` contain reusable platform infrastructure (deterministic loop, heartbeat, staleness watchdog, telemetry) that can be salvaged into `F:\Nifty` cleanly, or is it inseparable from strategy logic?

---

## 1. Import inventory (every import, what uses it, classification)

| Import | Line | Used by | Classification |
|---|---|---|---|
| `typing, datetime/timedelta, dataclasses(dataclass,replace), traceback, time, json, tempfile, os` | 7–14 | throughout | **INFRA (stdlib)** — `replace` only in strategy body |
| `providers.base.MarketDataProvider` | 16 | `_process_symbol` (`get_next_bar`), `run` (`is_data_available`) | **INFRA** |
| `providers.base.AnalyticsProvider` | 16 | `__init__`, `_process_symbol` (`get_latest_snapshot`, `get_market_regime`) | **STRATEGY-analytics** |
| `strategies.base.BaseStrategy, StrategyContext` | 17 | `__init__`, `_validate_setup`, `_process_symbol`, `_update_runner_state`, `_publish_telemetry` (count) | **STRATEGY** |
| `execution.handler.ExecutionHandler` | 18 | heartbeat, staleness, telemetry, `_process_symbol`, `_get_stats` | **INFRA** (required by all 4 capabilities) |
| `execution.position_tracker.PositionTracker` | 19 | telemetry, `_process_symbol`, `_get_stats` | **INFRA** |
| `events.OHLCVBar` | 20 | bar typing | **INFRA** |
| `events.SignalEvent, SignalType` | 20 | `_check_exit_conditions` (EXIT emit), `_process_symbol`, `_log_signal` | **INFRA** (shared event types) |
| `events.TradeEvent` | 20 | referenced only in a comment (line 441) | **DEAD IMPORT** |
| `clock.Clock` | 21 | `run`, `_process_symbol` (`set_time`), `_log_*`, `_get_stats`, `stop` | **INFRA** (determinism backbone) |
| `database.manager.DatabaseManager` | 22 | `__init__`, **only** `_update_runner_state` (`config_writer`) | **STRATEGY-state** |
| `database.utils.market_hours.MarketHours` | 23 | staleness, heartbeat, telemetry | **INFRA** (required by 3 of 4 capabilities) |
| `database.legacy_adapter.save_signal` | 24 | `_process_symbol` (persist signal) | **STRATEGY-output** |
| `messaging.telemetry.TelemetryPublisher` | 25 | telemetry, `_log_*` | **INFRA** |
| `alerts.alerter.alerter` | 26 | staleness | **INFRA** |
| `logging.setup_logger` | 27 | all | **INFRA** |
| `hashlib.sha256` (inline) | 274 | signal-id in `_process_symbol` | INFRA logic, located in strategy body |
| `execution.order_models.NormalizedOrder` (inline) | 442 | `_log_trade` | **INFRA** |

---

## 2. Imports that exist solely because of strategy coupling

Four imports (plus one dead one) are present **only** to serve the strategy-processing body — none of the four target capabilities touch them:

1. `strategies.base.BaseStrategy, StrategyContext` (17) — the strategy iteration in `_process_symbol` (253–319), `_validate_setup` (108–111), `_update_runner_state` (483), and the one count in `_publish_telemetry` (398).
2. `providers.base.AnalyticsProvider` (16) — `get_latest_snapshot` / `get_market_regime` feed `StrategyContext` (249–251). (Its sibling `MarketDataProvider` on the same line **is** infra — they must be split.) `AnalyticsProvider` was already dropped from `F:\Nifty` as strategy-analytics.
3. `database.legacy_adapter.save_signal` (24) — persists strategy signals (285).
4. `database.manager.DatabaseManager` (22) — used by **nothing except** `_update_runner_state` (516), which writes the `runner_state` table keyed by `strategy_id`. None of heartbeat/staleness/telemetry use the DB.
5. `events.TradeEvent` (20) — **dead** (comment-only). Drop on sight.

**Everything else is platform infrastructure.**

---

## 3. Per-capability dependency breakdown

### (a) `heartbeat.json` generation — `_write_heartbeat()` (352–384)
- **Infra deps:** stdlib (`time, datetime, json, tempfile, os`), `MarketHours.is_market_open()`, `ExecutionHandler` (`.metrics.cash_balance`, `._trades_today`, `._kill_switched`), internal state (`_bar_count`, `_data_healthy`, `_last_heartbeat_time`), const `HEARTBEAT_INTERVAL_S`.
- **Strategy deps:** **none.**
- **Verdict: CLEAN.** Atomic temp-file + `os.replace` write; self-contained.

### (b) Data-staleness watchdog — `_check_data_staleness()` (331–350) + the `_last_bar_timestamp` update (237–241)
- **Infra deps:** `datetime`, `MarketHours.is_market_open()`, `alerter.critical()`, `ExecutionHandler.activate_kill_switch()`, state (`_last_bar_timestamp`, `_data_stale_alerted`, `_data_healthy`), const `DATA_STALE_THRESHOLD`.
- **Strategy deps:** **none in the check itself.** But its **input** `_last_bar_timestamp` is written **inside** the strategy-coupled `_process_symbol` (line 237).
- **Verdict: CLEAN logic; input source is entangled** (see hidden dep #3).

### (c) Telemetry publishing — `_publish_telemetry()` (386–430) + telemetry calls in `_log_signal`/`_log_trade`
- **Infra deps:** `time`, `TelemetryPublisher` (`publish_metrics/positions/health`), `ExecutionHandler` (`.metrics.{cash_balance,max_drawdown_pct,signals_received}`, `._trades_today`, `._kill_switched`), `PositionTracker.get_all_positions()`, `MarketHours.is_market_open()`, state (`_bar_count`, `_data_healthy`, `_last_bar_timestamp`).
- **Strategy deps:** **one line** — `active_count = len(self.strategies) - len(self._disabled_strategies)` (398), a cosmetic "active strategies" metric.
- **Verdict: CLEAN except one trivial metric** (drop it, or pass an int in).

### (d) Deterministic event loop — `run()` (113–169) + `_process_symbol()` (231–329)
- **Infra (loop skeleton):** the `while self._is_running` cadence, `max_bars` guard, the three periodic hooks (`_check_data_staleness`/`_write_heartbeat`/`_publish_telemetry`), `MarketDataProvider.is_data_available` + `time.sleep(0.5)` + exhaustion handling, `_bar_count`, and the data-driven `Clock.set_time(bar.timestamp)` (243) that makes live and backtest identical.
- **Strategy (loop body, in `_process_symbol`):** `AnalyticsProvider` snapshot (249–251), the `for strategy in self.strategies` loop with `StrategyContext` + `process_bar` (253–319), `save_signal` (285), `_check_exit_conditions` TP/SL/time-stop monitoring (171–229, exit-policy), and `_update_runner_state` (strategy-state persistence).
- **Verdict: SKELETON extractable; BODY is the strategy seam.** The infra parts (clock advance, bar pull, periodic hooks, bar-arrival timestamp) are **physically interleaved** with strategy processing inside one method.

---

## 4. Minimum infra subset of `runner.py`

The platform-infrastructure portion (roughly ~150 of 543 lines) is:

- **Constants:** `DATA_STALE_THRESHOLD`, `HEARTBEAT_INTERVAL_S` (49–52); `_telemetry_interval_s` (94).
- **State fields:** `_last_bar_timestamp`, `_data_stale_alerted`, `_data_healthy`, `_last_heartbeat_time`, `_last_telemetry_time`, `_bar_count` (84–94).
- **Methods (near-verbatim, infra-clean):** `_check_data_staleness` (331–350), `_write_heartbeat` (352–384), `_publish_telemetry` (386–430, minus line 398), plus the loop scaffold from `run()` (cadence + 3 hooks + streaming/sleep/exhaustion).
- **The data-driven clock advance** (`Clock.set_time(bar.timestamp)`) and the **bar-arrival timestamp update** (237) — currently inside `_process_symbol`, logically infra.
- **Infra collaborators (objects it holds):** `ExecutionHandler`, `PositionTracker`, `TelemetryPublisher`, `Clock`, `MarketHours`, `alerter`, `MarketDataProvider`, `setup_logger`.
- **`RunnerConfig`** — but only its infra fields (`symbols`, `max_bars`); `strategy_ids`, `log_signals`, `disable_state_update` are strategy-facing.

The **strategy-infrastructure** portion (to leave behind): `_process_symbol` body, `_check_exit_conditions`, `_update_runner_state`, `_validate_setup` (strategy-id checks), `save_signal`, `AnalyticsProvider`, `BaseStrategy`/`StrategyContext`, `DatabaseManager` usage.

---

## 5. Can each capability be extracted cleanly?

| Capability | Strategy imports needed? | Clean extraction? |
|---|---|---|
| `heartbeat.json` generation | None | **YES — clean.** |
| Data-staleness watchdog | None | **YES — clean logic.** One relocation needed (its input timestamp, see #3). |
| Telemetry publishing | One cosmetic line | **YES — clean** after dropping/parametrizing the `len(self.strategies)` metric. |
| Deterministic event loop | The body does | **PARTIAL — the skeleton yes, the body no.** Extractable only by factoring strategy processing out behind a generic per-bar seam. No strategy *import* is required by the loop scaffold itself. |

**None of the three monitoring capabilities require a single strategy import.** Their only non-stdlib dependencies are `ExecutionHandler`, `PositionTracker`, `MarketHours`, `TelemetryPublisher`, and `alerter` — all platform infrastructure.

---

## 6. Hidden dependencies that complicate (but do not block) extraction

1. **Coupling to `ExecutionHandler` internals.** Heartbeat and telemetry read **private** attributes `self.execution._trades_today` and `self.execution._kill_switched`, plus the `ExecutionMetrics` dataclass — which is **defined inside `handler.py`** (line 83). Verified all fields exist (`cash_balance`, `max_drawdown_pct`, `signals_received`). This is an implementation-detail dependency on the execution module's internal surface, **not** strategy coupling, but it means these capabilities are bound to `ExecutionHandler` (or anything exposing the same surface).
2. **Staleness → `ExecutionHandler.activate_kill_switch(reason)`** — verified present (handler.py:679). The watchdog is inherently coupled to execution: it acts by tripping the kill switch. It is not a standalone module.
3. **Watchdog input is produced in the strategy-coupled method.** `_last_bar_timestamp` (the staleness signal) and the data-driven `Clock.set_time` are both updated inside `_process_symbol` (237, 243). The *act* of "a bar arrived / advance the clock" is infra, but it currently lives in the strategy loop body — extraction must relocate this "bar received" hook onto the infra bar-pull path.
4. **`MarketHours`** — required by 3 of 4 capabilities. Verified **present in `F:\Nifty`** and clean infra (no `core`/strategy imports). No blocker.
5. **Wall-clock vs deterministic clock split.** The trade path uses the data-driven `Clock` (deterministic, backtest==live), but heartbeat/staleness use real `datetime.now()` / `time.time()` (operational, wall-clock). The "deterministic" guarantee applies to the *trade* loop, not to the monitoring cadence — worth keeping straight when extracting.
6. **`RunnerConfig` mixes concerns** — infra fields (`symbols`, `max_bars`) and strategy fields (`strategy_ids`, `log_signals`, `disable_state_update`) share one dataclass.
7. **Dead import:** `TradeEvent` (line 20) — unused.

**No hidden dependency reaches into strategy code.** Every complication is either (a) coupling to `ExecutionHandler`/`ExecutionMetrics` (infra-to-infra) or (b) physical interleaving of infra logic inside the strategy-processing method.

---

## Conclusion

`runner.py` **does contain reusable platform infrastructure** worth salvaging. Concretely:

- **Heartbeat (`_write_heartbeat`), staleness watchdog (`_check_data_staleness`), and telemetry publishing (`_publish_telemetry`) are clean platform infrastructure** — they import **zero** strategy modules and depend only on `ExecutionHandler`, `PositionTracker`, `MarketHours`, `TelemetryPublisher`, and `alerter`, all of which are (or can be) in `F:\Nifty`. The only strategy touch anywhere in these three is one cosmetic count in telemetry.
- **The deterministic event loop is infrastructure in shape but interleaved in code** — the loop scaffold (cadence, clock advance, bar pull, periodic hooks) is platform, while the per-bar body is strategy. It carries no strategy *import* in its scaffold, but the scaffold and the strategy body live in the same methods (`run` / `_process_symbol`).
- **The blockers are coupling to `ExecutionHandler` internals and physical interleaving — not strategy dependency.** All three verified coupling points (`activate_kill_switch`, `ExecutionMetrics` fields, `MarketHours`) resolve to infra that exists.

**Therefore:** the heartbeat, staleness watchdog, and telemetry loop are **salvageable as platform infrastructure**; the deterministic loop is **salvageable as a scaffold** once the strategy-processing body is treated as the boundary. To leave behind: `_process_symbol` body, `_check_exit_conditions`, `_update_runner_state`, `save_signal`, `AnalyticsProvider`, `BaseStrategy`/`StrategyContext`, `DatabaseManager` usage, and the dead `TradeEvent` import. This confirms `runner.py` should be salvaged (selectively) into `F:\Nifty` before further platform planning — not migrated wholesale, and not discarded.
