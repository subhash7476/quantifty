# FTMO Live Trader — Data Pipeline

Documents the exact data flow for both live commands:
- `python -m ftmo.cli live --login X --password Y --server Z`
- `python -m ftmo.cli rolling-live --login X --password Y --server Z`

---

## STARTUP (both commands, identical)

```
python -m ftmo.cli live ...
         │
         ▼
cmd_live() in cli.py
  → creates MT5LiveTrader(login, password, server, symbol)
  → trader.connect()
         │
         ├─ mt5.initialize()         — starts MT5 terminal process
         ├─ mt5.login()              — authenticates with FTMO broker server
         ├─ mt5.account_info()       — reads balance → AccountState.fresh(balance)
         ├─ reads cache_{sym}_m5.parquet → sets _last_cached_ts (last saved bar)
         ├─ mt5.positions_get()      — checks for open position from prior session
         │   └─ if magic==20260311 found → _open_ticket set → recovery mode
         └─ _fetch_himpact_usd_events() → HTTP GET ForexFactory CDN JSON
             └─ caches to .calendar_cache.json (refreshed once per day)
         │
         ▼
trader.run()  →  infinite loop: _tick() every 60 seconds
```

---

## EVERY 60 SECONDS — `live` (`_tick()`)

```
_tick()
  │
  ├─ 1. NEW DAY CHECK
  │     if date changed → _on_new_day()
  │       ├─ risk.new_day() — resets trades_today, daily_pnl, consecutive_losses
  │       ├─ _session1/2_scanned_today = False
  │       ├─ _session1/2_last_scan = None
  │       └─ re-fetch ForexFactory calendar
  │
  ├─ 2. SYNC ACCOUNT STATE
  │     mt5.account_info() → update equity in AccountState
  │     (truth source — reflects any manual closes, floating P&L, etc.)
  │
  ├─ 3. UPDATE DATA CACHE
  │     mt5.copy_rates_from_pos(symbol, M5, start=1, count=20)
  │     — fetches last 20 CLOSED bars (bar index 1 skips the open current bar)
  │     — filters to bars newer than _last_cached_ts
  │     — appends to cache_{sym}_m5.parquet
  │     — this cache is for BACKTEST REPLAY only, NOT used in live scanning
  │
  ├─ 4. POSITION MONITOR (if open trade)
  │     if _open_ticket is set → _monitor_position() → return (no scanning)
  │       ├─ check if position still exists in MT5
  │       ├─ _check_partial_exit() — close 50% at +1R (if enabled)
  │       ├─ _check_breakeven() — move SL to entry at +1R
  │       └─ if past NY2_END (23:00) → _close_position() (time cutoff)
  │
  └─ 5. SESSION SCAN GATE
        Session 1: 13:30–19:00 IST, not yet traded today
        Session 2: 19:00–23:00 IST, not yet traded today

        For each session:
          ├─ if last_scan is None OR (now - last_scan) >= 30min → fire scan
          └─ _scan_and_trade(session, cutoff)
```

---

## INSIDE `_scan_and_trade()` — the core data pipeline

Every scan call is **self-contained** — fetches fresh bars from MT5 from scratch.
The parquet cache plays no role here.

```
_scan_and_trade(session=1, cutoff=19:00)
  │
  ├─ STEP 1: NEWS BLACKOUT CHECK
  │     compares now_ist against today's high-impact USD events
  │     Tier-1 (CPI/NFP/FOMC/PCE): ±90 min window
  │     Tier-2 (all others):        ±30 min window
  │     → if blocked: print NEWS_BLACKOUT, return
  │
  ├─ STEP 2: FETCH BARS FROM MT5 (LIVE FEED)
  │     mt5.copy_rates_from_pos(symbol, TIMEFRAME_M5, start=0, count=300)
  │     ← direct call to MT5 terminal's price server
  │     ← 300 bars = ~25 hours of M5 data (covers multi-day history)
  │     ← returns: [time(unix), open, high, low, close, tick_volume, ...]
  │     ← the parquet cache is NOT involved at all in this fetch
  │     → convert unix timestamp → IST datetime
  │     → rename tick_volume → volume
  │     → sort ascending
  │
  ├─ STEP 3: ENRICH WITH INDICATORS
  │     enrich_with_indicators(df_300_bars)
  │       ├─ M5 ATR  (Wilder's EWM, period=14) on all 300 bars
  │       ├─ resample M5 → M15 (OHLCV aggregation, 3 bars per M15)
  │       ├─ M15 ATR (Wilder's EWM, period=14) on M15 bars
  │       └─ map M15 ATR back to each M5 bar (floor timestamp to 15min)
  │     result: df_m5 with [timestamp, open, high, low, close, volume, atr, m15_atr]
  │
  ├─ STEP 4: DATA FRESHNESS GUARD
  │     age = now_utc − latest_bar_timestamp
  │     if age > 15 minutes → stale feed → return
  │     (catches weekends, broker disconnects, market closed)
  │
  ├─ STEP 5: SLICE TODAY'S BARS (date-filtered)
  │     df_today = df_m5 where date == today_ist_date
  │     ← the date filter prevents prior-day bars contaminating the scan
  │     ← without this: Friday bars would appear in Monday's session slices
  │
  │     Session 1 slices from df_today:
  │       pre_bars = bars where time in [09:30, 13:30)   ← Asian range
  │       ny_bars  = bars where time in [13:30, 19:00)   ← London session
  │
  │     Session 2 slices from df_today:
  │       pre_bars = bars where time in [13:30, 19:00)   ← London range
  │       ny_bars  = bars where time in [19:00, 23:00)   ← NY session
  │
  ├─ STEP 6: MINIMUM BARS GUARD
  │     if pre_bars < 2  → return (range not yet formed)
  │     if ny_bars < 12  → print WAITING, return (retry in 30min)
  │     ← 12 bars = 1 hour of session bars minimum before scanning
  │     ← at 13:32 IST: 2 session bars → WAITING (not permanent, retries at 14:02)
  │     ← at 14:02 IST: 14 session bars → proceeds to scan
  │
  ├─ STEP 7: COMPUTE RANGE AND ATR
  │     pre_high = max(pre_bars["high"])      ← e.g. Asian session high
  │     pre_low  = min(pre_bars["low"])       ← e.g. Asian session low
  │     m15_atr  = ny_bars.iloc[0]["m15_atr"] ← ATR at session open bar
  │
  ├─ STEP 8: SWEEP CLASSIFIER GATE (optional)
  │     clf = sweep_clf_s1 or sweep_clf_s2 (loaded from .pkl at startup)
  │     passed into scan_session() — each detected sweep goes through it
  │     if is_valid() returns False → sweep skipped entirely
  │     if .pkl absent → clf = None → no filtering (all sweeps pass through)
  │
  └─ STEP 9: scan_session(ny_bars, pre_high, pre_low, m15_atr, cutoff, clf)
              │
              ├─ detect_sweeps(ny_bars, pre_high, pre_low, m15_atr)
              │     loops every bar in ny_bars
              │     HIGH_SWEEP: bar.high > pre_high AND extension >= 0.25 × m15_atr
              │     LOW_SWEEP:  bar.low  < pre_low  AND extension >= 0.25 × m15_atr
              │     only first sweep per direction (HIGH and LOW) counted
              │
              ├─ [if clf] sweep_classifier.is_valid(df_ny, sweep_bar_idx, ...)
              │     checks K-line token histogram of 20 pre-sweep bars
              │     returns True/False → sweep dropped if False
              │
              ├─ detect_structure_shift(bars_after_sweep, sweep, m5_atr, cutoff)
              │     HIGH_SWEEP → _detect_bearish_shift():
              │       scan for lower high (price fails to re-reach sweep extreme)
              │       then find bearish displacement candle body >= 1.2 × M5 ATR
              │     LOW_SWEEP → _detect_bullish_shift():
              │       scan for higher low, then bullish displacement candle
              │
              └─ compute_trade_setup(sweep, shift, bars_after_shift, m15_atr, cutoff)
                    displacement zone = [shift.open, shift.close]

                    SHORT setup (after HIGH_SWEEP):
                      entry_price = bottom of displacement candle body
                      stop_loss   = sweep_high + 0.15 × m15_atr
                      risk_points = stop_loss − entry_price
                      take_profit = entry_price − 2 × risk_points   (2R)
                      trigger     = first bar where bar.high >= entry_price (pullback touch)

                    LONG setup (after LOW_SWEEP):
                      entry_price = top of displacement candle body
                      stop_loss   = sweep_low − 0.15 × m15_atr
                      risk_points = entry_price − stop_loss
                      take_profit = entry_price + 2 × risk_points   (2R)
                      trigger     = first bar where bar.low <= entry_price

                    returns TradeSetup (all prices are from HISTORICAL bars in ny_bars)
```

---

## ORDER PLACEMENT — after a setup is found

```
setup = setups[0]   ← first valid setup chronologically in session bars
  │
  ├─ RISK GATE
  │     risk_dollar = equity × 1.0%  (or 0.3% if equity gain > 4%)
  │     check_pre_trade():
  │       ├─ FTMO overall loss < $10,000?
  │       ├─ FTMO daily loss < $5,000?
  │       ├─ Internal daily loss < $2,000 (2% of starting balance)?
  │       ├─ consecutive_losses < 2?
  │       └─ trades_today < 3?
  │     → if any fail: print BLOCKED, return (no order placed)
  │
  ├─ LOT SIZE
  │     lot_size = risk_dollar / (risk_points × point_value)
  │     point_value = 100  (XAUUSD: 1 lot = 100oz, $1 move = $100/lot)
  │     e.g. risk=$1,000, risk_points=28pts → lots = 1000 / (28 × 100) = 0.36
  │
  └─ _place_order(setup, lot_size, session)
        │
        ├─ ENTRY STALE CHECK
        │     current_price = mt5.symbol_info_tick().ask or .bid
        │     price_vs_zone = current_price − setup.entry_price
        │     if |price_vs_zone| > 0.5 × risk_points → ENTRY_STALE → return
        │     ← rejects if price moved far from the historical zone in either direction
        │     ← adverse:  structural premise broken, SL is too tight
        │     ← chasing:  price ran past zone, R:R is now broken
        │
        ├─ RECOMPUTE TP FROM ACTUAL FILL
        │     actual_tp = fill_price ± 2 × risk_points
        │     ← SL stays structural (sweep extreme + ATR buffer)
        │     ← TP shifts to fill price so R:R is always true 2:1
        │
        ├─ mt5.order_send() → MARKET ORDER sent to FTMO broker
        │     type:     BUY (LONG) or SELL (SHORT)
        │     volume:   lot_size
        │     price:    current ask/bid at execution time
        │     sl:       structural stop loss
        │     tp:       fill-adjusted take profit
        │     magic:    20260311 (strategy identifier for position recovery)
        │
        └─ on success:
              _open_ticket = result.order
              _session1_scanned_today = True   ← stops S1 rescanning for today
              _pending_log saved (entry, sl, tp, lots, ticket)
              print [ORDER] EXECUTED ...
```

---

## ROLLING-LIVE — differences from `live`

The rolling trader inherits all connection, cache, monitoring, and order logic.
Only the scan scheduling and range definition differ.

```
_rolling_tick()   (replaces _tick())
  │
  ├─ steps 1–4 identical (new day, sync equity, cache append, position monitor)
  │
  └─ SCAN GATE (different from live)
        window:   13:00–20:00 IST  (single window, not split into two sessions)
        interval: 30 min between scans
        stop:     only if _open_ticket set (in a trade)
                  OR dedup match (_traded_levels list for today)
        ← no per-session "scanned_today" flag
        ← can take multiple trades per day (same risk engine limits still apply)
        ← uses RISK_PCT = 0.5% per trade (half of live's 1%)

_do_rolling_scan()   (replaces _scan_and_trade())
  │
  ├─ steps 1–4 identical (news, fetch 300 bars, enrich indicators, freshness)
  │
  ├─ RANGE DEFINITION (rolling, not clock-based)
  │     total = len(df_m5)
  │     session_start = total − 36        ← most recent 36 bars = 3h trade window
  │     pre_end       = session_start
  │     pre_start     = pre_end − 24      ← 24 bars before that = 2h rolling range
  │
  │     pre_bars     = df_m5[pre_start : pre_end]   ← 2h block, ended 3h ago
  │     session_bars = df_m5[session_start :]        ← most recent 3h
  │     ← no date-based slicing needed; window is entirely bar-count relative
  │
  ├─ FLAT RANGE FILTER (extra, not in live)
  │     range_size = pre_high − pre_low
  │     if range_size < 0.3 × m5_atr → skip  (dead/flat market period)
  │
  ├─ scan_session() on session_bars with rolling pre_high/pre_low
  │     same sweep → structure shift → displacement → entry logic
  │     sweep classifiers DISABLED (not trained for rolling ranges)
  │
  ├─ DEDUP CHECK (extra, not in live)
  │     for each setup found:
  │       if (direction matches AND level within 0.5 × ATR of a prior trade today)
  │       → DEDUP skip — already traded this zone today
  │
  └─ LOT SIZE SCALING
        base_lot = risk_engine.calculate_lot_size(state, risk_points, point_value)
        final_lot = base_lot × (0.5% / 1.0%) = base_lot × 0.5
        ← halved because frequency roughly doubles vs fixed-session strategy
```

---

## SIDE-BY-SIDE COMPARISON

| Step | `live` | `rolling-live` |
|------|--------|----------------|
| Bar source | `mt5.copy_rates_from_pos`, 300 bars, fresh each scan | Same |
| Cache role | Append-only log for backtest replay | Same, separate file |
| Indicators | M5 ATR + M15 ATR via `enrich_with_indicators` | Same |
| Range definition | Fixed clock windows (09:30–13:30 Asian, 13:30–19:00 London) | Rolling: last 24 bars before the last 36 bars |
| Session bars | Today's bars in [13:30,19:00) or [19:00,23:00) | Most recent 36 bars |
| Scan schedule | Every 30min per session, stops after 1 trade per session | Every 30min 13:00–20:00, stops only on open position or dedup |
| Trades per day | Max 1 per session (2 total possible) | Multiple (dedup prevents same level) |
| Risk per trade | 1% of equity | 0.5% of equity |
| Sweep classifier | S1 / S2 `.pkl` loaded at startup | Disabled |
| Flat range filter | None | `range < 0.3 × ATR` skips scan |
| Dedup | None (1 trade per session) | `_traded_levels` by (direction, level, ATR fraction) |
| Trade log | `trade_log_{symbol}.csv` | `trade_log_rolling_{symbol}.csv` |
| Bar cache | `cache_{symbol}_m5.parquet` | `cache_rolling_{symbol}_m5.parquet` |

---

## KEY ARCHITECTURAL FACTS

1. **The parquet cache has no role in live scanning.** It is written every tick (last 20 bars appended) purely for offline backtest replay. All scanning uses a direct fresh MT5 fetch.

2. **All prices in a TradeSetup are historical bar prices**, not live prices. The entry zone is where price *was* on a past bar. The actual fill happens at the current bid/ask in `_place_order`. TP is recomputed from the fill; SL is always structural.

3. **ATR is recomputed from scratch every scan** using all 300 fetched bars. There is no ATR state carried between ticks.

4. **The ForexFactory calendar is fetched once per day** at startup and on day rollover. It is cached to `.calendar_cache.json` and re-read from disk on subsequent ticks.

5. **The risk engine state does NOT persist across restarts.** On `connect()`, `AccountState.fresh(balance)` is called with MT5 balance, resetting `trades_today=0`, `consecutive_losses=0`, `daily_pnl=0`. A mid-day restart loses that day's trade count context.
