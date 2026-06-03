# FTMO Prop Trading Bot — Complete Battle Plan

## 1. DIAGNOSIS: Why Your Gold Bot Isn't Trading

Your XAU/USD bot has gone silent for a week. Here are the most likely causes:

**Overly tight entry filters.** If your strategy requires multiple conditions to align simultaneously (e.g., RSI + MA crossover + session filter + ATR threshold), even a slight shift in gold's regime (trending → ranging) can shut down all signals. Gold spent significant periods in March 2026 in consolidation zones where breakout-based or trend-following systems generate zero entries.

**Single-instrument dependency.** This is the core architectural flaw. If your only instrument goes quiet, your entire challenge stalls. FTMO requires minimum 4 trading days — you need signals flowing consistently.

**Session or volatility filter too aggressive.** If your bot only trades London+NY overlap and applies an ATR floor, calm market weeks can produce zero qualifying setups.

**Fix:** Don't just loosen filters — add instruments and strategy variants. That's what this plan does.

---

## 2. FTMO CHALLENGE RULES (2-Step, $100K Account)

| Parameter | Challenge (Step 1) | Verification (Step 2) | Funded Account |
|-----------|--------------------|-----------------------|----------------|
| Profit Target | 10% ($10,000) | 5% ($5,000) | None |
| Max Daily Loss | 5% ($5,000) | 5% ($5,000) | 5% ($5,000) |
| Max Total Drawdown | 10% ($10,000) | 10% ($10,000) | 10% ($10,000) |
| Min Trading Days | 4 | 4 | None |
| Time Limit | Unlimited | Unlimited | N/A |
| Profit Split | N/A | N/A | Up to 90% |
| Best Day Rule (1-Step only) | N/A | N/A | N/A |

**Critical nuances:**
- Drawdown is STATIC (floor = $90,000), not trailing. This is favorable.
- Daily loss resets at midnight CET, calculated from previous day's closing balance.
- Daily loss includes UNREALIZED losses — if equity touches -$5K at any point, even momentarily, you fail.
- All positions must be closed before profit target is reviewed.
- Leverage: up to 1:100.

---

## 3. INSTRUMENT SELECTION — The Multi-Asset Playbook

### Tier 1: Primary Instruments (trade daily)

| Instrument | Why | Avg Daily Range | Best Sessions |
|------------|-----|-----------------|---------------|
| **XAU/USD (Gold)** | High ATR, trends well, most popular FTMO instrument | 250-400 pips | London, NY, London-NY overlap |
| **EUR/USD** | Tightest spreads, cleanest price action, most liquid | 60-80 pips | London, London-NY overlap |
| **NAS100 (US Tech 100)** | Strong intraday trends, high R:R potential | 200-350 points | NY session (14:30-21:00 CET) |

### Tier 2: Secondary / Confirmation Instruments (trade when Tier 1 is quiet)

| Instrument | Why | Best Sessions |
|------------|-----|---------------|
| **GBP/USD** | Higher volatility than EUR/USD, good trends | London |
| **USD/JPY** | Clean technicals, responds well to session opens | Asian-London transition |
| **SPX500 (S&P 500)** | Lower volatility than NAS100, good for conservative setups | NY session |

### Why This Mix Works for FTMO:
- Gold alone can go quiet for days. EUR/USD rarely does during London.
- NAS100 gives you a completely different asset class (equity indices) with independent drivers.
- Having 3 primary instruments means you're almost guaranteed 1-2 quality setups per day.
- Different pip values diversify your P&L distribution (helps avoid Best Day rule violations if on 1-Step).

---

## 4. STRATEGY FRAMEWORK — Three Uncorrelated Edges

### Strategy A: London Session Breakout (Gold + EUR/USD)

**Concept:** Trade the breakout from the Asian session range during London open.

**Rules:**
- Define Asian range: High/Low of 00:00-07:00 CET
- Wait for London open (08:00-09:00 CET)
- Entry: Break above Asian high (long) or below Asian low (short)
- Confirmation: 15M candle close beyond range + volume spike
- Stop Loss: Opposite side of Asian range (or ATR-based if range is too wide)
- Take Profit: 1:2 R:R minimum, trail with 1H swing structure
- Filter: Skip if Asian range > 1.5x 20-day average range (already expanded)

**Timeframe:** 15M for entry, 1H for bias/structure  
**Expected frequency:** 3-5 trades per week across Gold + EUR/USD

### Strategy B: Trend Continuation Pullback (All instruments)

**Concept:** Trade pullbacks to moving averages in established trends.

**Rules:**
- Identify trend on 4H: Price above 50 EMA AND 50 EMA above 200 EMA (uptrend)
- Wait for pullback to 20 EMA on 1H timeframe
- Entry: Bullish engulfing / pin bar / hammer at 20 EMA on 1H
- Confirmation: RSI(14) between 40-55 (not overbought, showing pullback)
- Stop Loss: Below the pullback low + buffer
- Take Profit: Previous swing high (TP1), 1:3 R:R (TP2)
- Filter: Don't trade against 4H 200 EMA direction

**Timeframe:** 4H for trend, 1H for entry  
**Expected frequency:** 2-4 trades per week across 3 instruments

### Strategy C: NY Session Momentum (NAS100 + Gold)

**Concept:** Capture the initial directional move after US market open.

**Rules:**
- Wait for first 15 minutes of NY session (15:30-15:45 CET) to establish initial range
- Entry: Break of first-15-min high/low with momentum (MACD histogram expanding)
- Confirmation: Volume above 20-period average
- Stop Loss: Opposite side of 15-min range
- Take Profit: 1:2 R:R minimum, close 50% at 1:2, trail remainder
- Filter: Skip on FOMC days, NFP days (or trade with reduced size)
- Daily cutoff: No new entries after 20:00 CET

**Timeframe:** 5M for entry, 15M for structure  
**Expected frequency:** 3-5 trades per week

### Combined Expected Output:
- **8-14 trades per week** across all strategies
- **Minimum 4 trading days guaranteed** (solves FTMO requirement)
- **Diversified P&L** across instruments and strategies (no single point of failure)

---

## 5. RISK MANAGEMENT — The Non-Negotiable Framework

### Position Sizing

```
Risk per trade = 1% of current balance (not initial balance)
Max concurrent positions = 3
Max daily risk budget = 3% (hard stop trading for the day)
Max risk per instrument per day = 2%
```

### Position Size Formula

```python
def calculate_lot_size(balance, risk_pct, sl_pips, pip_value):
    """
    balance: current account balance
    risk_pct: 0.01 for 1%
    sl_pips: stop loss distance in pips
    pip_value: value per pip per lot for the instrument
    """
    risk_amount = balance * risk_pct
    lot_size = risk_amount / (sl_pips * pip_value)
    return round(lot_size, 2)

# Examples for $100K account, 1% risk:
# Gold (XAU/USD): SL = 200 pips, pip_value = $1/pip/0.01 lot
# EUR/USD: SL = 30 pips, pip_value = $10/pip/lot
# NAS100: SL = 50 points, pip_value = $1/point/0.01 lot
```

### Daily Loss Guardian

```
Daily loss tracking:
- Track realized + unrealized P&L in real-time
- WARNING at 2.5% daily loss → reduce position size by 50%
- HARD STOP at 3.5% daily loss → no new trades for the day
- This gives 1.5% buffer before FTMO's 5% daily limit
```

### Drawdown Management

```
Equity stages:
- $100K - $97K: Normal trading (1% risk)
- $97K - $95K: Reduced mode (0.5% risk, Tier 1 instruments only)
- $95K - $93K: Survival mode (0.25% risk, EUR/USD only, Strategy B only)
- Below $93K: STOP TRADING. Review and reset.
```

---

## 6. TIMEFRAMES — Matched to Strategy

| Strategy | Higher TF (Bias) | Entry TF | Management TF |
|----------|-------------------|----------|----------------|
| A: London Breakout | 1H | 15M | 15M |
| B: Trend Pullback | 4H | 1H | 1H |
| C: NY Momentum | 15M | 5M | 5M |

**Why these timeframes:**
- 15M/1H is the sweet spot for FTMO — frequent enough for signals, large enough to avoid noise
- 5M only for NY momentum (high-liquidity session reduces noise)
- 4H for trend identification gives reliable structure
- Avoid 1M — too noisy, spread costs eat profits, and FTMO may flag hyperactivity

---

## 7. DATA SOURCES FOR BACKTESTING

### Free Sources (start here)

| Source | Data Type | Instruments | Format | URL |
|--------|-----------|-------------|--------|-----|
| **Dukascopy** | Tick + M1 | Forex, Gold, Indices | CSV | dukascopy.com/swiss/english/marketwatch/historical/ |
| **HistData.com** | M1 + Tick | Major FX pairs, Gold | CSV (ASCII) | histdata.com/download-free-forex-historical-data/ |
| **Kaggle** | Daily/Hourly | XAU/USD 2004-2026 | CSV | kaggle.com (search "XAUUSD historical") |
| **MetaTrader 5** | M1 to Monthly | All FTMO instruments | Direct in platform | Built into MT5 History Center |
| **Yahoo Finance (yfinance)** | Daily | Indices, some FX | Python API | `pip install yfinance` |

### Best Approach for Python Backtesting

```python
# Option 1: Pull directly from MT5 (best for matching FTMO's feed)
import MetaTrader5 as mt5
import pandas as pd

mt5.initialize()
rates = mt5.copy_rates_range(
    "XAUUSD", 
    mt5.TIMEFRAME_M15,
    datetime(2023, 1, 1),
    datetime(2026, 3, 25)
)
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')

# Option 2: Dukascopy via Python (for tick data)
# Use: pip install duka
# duka XAUUSD -s 2023-01-01 -e 2026-03-25 -t tick

# Option 3: HistData.com CSVs (M1 data, good for initial testing)
# Download manually, parse with pandas
```

### Minimum Backtesting Requirements

- **Period:** 2+ years (Jan 2024 - Mar 2026 minimum)
- **Resolution:** M1 for 15M/1H strategies, Tick for 5M strategies
- **Include:** Spread simulation (add 2-3 pips for gold, 1 pip for EUR/USD)
- **Include:** Swap/overnight costs for positions held past rollover
- **Sample size:** 200+ trades minimum per strategy before going live
- **Walk-forward:** Train on 2024, validate on 2025, forward-test on 2026 Q1

---

## 8. EXECUTION PLATFORM & BROKER

### For FTMO Challenge:
- **Platform:** MetaTrader 5 (MT5) — best Python API support
- **Broker:** FTMO provides their own MT5 credentials after registration
- **Python connection:** `pip install MetaTrader5` (Windows only for live; use VPS)

### For Development & Backtesting:
- **Backtesting:** Custom Python engine (pandas + vectorized backtest)
- **Libraries needed:**
  ```
  MetaTrader5          # MT5 API
  pandas               # Data handling
  numpy                # Calculations
  ta-lib / pandas-ta   # Technical indicators
  matplotlib           # Visualization
  schedule             # Task scheduling
  logging              # Trade logging
  ```

### VPS Requirement:
- Bot must run 24/5 on a Windows VPS (MT5 Python API is Windows-only)
- Recommended: ForexVPS, Beeks, or AWS Lightsail Windows
- Minimum specs: 2 vCPU, 4GB RAM, SSD

---

## 9. BOT ARCHITECTURE FOR CLAUDE CODE

### File Structure

```
ftmo_bot/
├── main.py                  # Entry point, scheduler
├── config.py                # All parameters, instrument configs
├── strategies/
│   ├── __init__.py
│   ├── london_breakout.py   # Strategy A
│   ├── trend_pullback.py    # Strategy B
│   └── ny_momentum.py       # Strategy C
├── core/
│   ├── __init__.py
│   ├── mt5_interface.py     # MT5 connection, order execution
│   ├── risk_manager.py      # Position sizing, daily loss tracking
│   ├── data_fetcher.py      # Historical + live data from MT5
│   └── indicators.py        # Technical indicator calculations
├── backtesting/
│   ├── __init__.py
│   ├── backtest_engine.py   # Vectorized backtester
│   ├── data_loader.py       # Load CSV/MT5 data
│   └── performance.py       # Metrics: Sharpe, drawdown, profit factor
├── utils/
│   ├── __init__.py
│   ├── logger.py            # Trade + system logging
│   ├── notifier.py          # Telegram/email alerts
│   └── session_filter.py    # Trading session time windows
├── data/                    # Historical data CSVs
├── logs/                    # Trade logs, system logs
└── tests/                   # Unit tests for each module
```

### Config Structure

```python
# config.py
INSTRUMENTS = {
    "XAUUSD": {
        "pip_value": 1.0,      # per 0.01 lot
        "spread_avg": 25,      # in points
        "strategies": ["london_breakout", "trend_pullback", "ny_momentum"],
        "max_lots": 1.0,
        "sessions": ["london", "ny"]
    },
    "EURUSD": {
        "pip_value": 10.0,     # per 1.0 lot
        "spread_avg": 8,
        "strategies": ["london_breakout", "trend_pullback"],
        "max_lots": 5.0,
        "sessions": ["london", "ny"]
    },
    "NAS100": {
        "pip_value": 1.0,
        "spread_avg": 100,
        "strategies": ["trend_pullback", "ny_momentum"],
        "max_lots": 2.0,
        "sessions": ["ny"]
    }
}

RISK = {
    "risk_per_trade": 0.01,
    "max_daily_risk": 0.03,
    "max_concurrent": 3,
    "daily_loss_warning": 0.025,
    "daily_loss_hard_stop": 0.035,
    "drawdown_reduced": 0.03,    # switch to 0.5% at 3% DD
    "drawdown_survival": 0.05,   # switch to 0.25% at 5% DD
    "drawdown_stop": 0.07        # stop trading at 7% DD
}

SESSIONS = {
    "asian":  {"start": "00:00", "end": "07:00", "tz": "CET"},
    "london": {"start": "08:00", "end": "16:00", "tz": "CET"},
    "ny":     {"start": "14:30", "end": "21:00", "tz": "CET"},
    "overlap": {"start": "14:30", "end": "16:00", "tz": "CET"}
}
```

---

## 10. PHASE PLAN — EXECUTION TIMELINE

### Phase 1: Backtest Foundation (Week 1)
- [ ] Download M15 + 1H + 4H data for XAU/USD, EUR/USD, NAS100 (2024-2026)
- [ ] Build backtesting engine in Python
- [ ] Implement Strategy A (London Breakout) and backtest
- [ ] Target: 200+ trades, profit factor > 1.5, max DD < 8%

### Phase 2: Strategy Expansion (Week 2)
- [ ] Implement Strategy B (Trend Pullback) and backtest
- [ ] Implement Strategy C (NY Momentum) and backtest
- [ ] Run combined portfolio backtest (all 3 strategies together)
- [ ] Walk-forward validation on 2026 Q1 data

### Phase 3: Live Infrastructure (Week 3)
- [ ] Build MT5 interface (connect, fetch data, execute orders)
- [ ] Build risk manager (position sizing, daily loss tracking, drawdown stages)
- [ ] Build session filter and scheduler
- [ ] Paper trade on FTMO Free Trial for 1 week

### Phase 4: FTMO Free Trial (Week 4)
- [ ] Run bot on FTMO Free Trial (14 days, same rules as real challenge)
- [ ] Monitor: trade frequency, P&L distribution, drawdown behavior
- [ ] Fix any issues (execution, timing, slippage)
- [ ] Confirm: 4+ trading days with trades, no rule violations

### Phase 5: Live Challenge (Week 5+)
- [ ] Purchase FTMO 2-Step Challenge ($100K, ~€540)
- [ ] Run bot with human oversight (review trades daily)
- [ ] Target: 10% profit over 4-8 weeks, conservative approach
- [ ] DO NOT rush — unlimited time is your advantage

---

## 11. KEY METRICS TO TRACK

```
Per Strategy:
- Win rate (target: > 45%)
- Average R:R (target: > 1:2)
- Profit factor (target: > 1.5)
- Max consecutive losses (target: < 5)
- Average trades per week (target: 3-5)

Portfolio (Combined):
- Total profit factor (target: > 1.8)
- Max drawdown (target: < 6%)
- Max daily loss (target: < 3%)
- Sharpe ratio (target: > 1.5)
- Recovery factor (net profit / max DD, target: > 3)
- Trade frequency (target: 8-14/week)
```

---

## 12. CLAUDE CODE PROMPT (Use This to Start Building)

```
Build a Python automated trading bot for the FTMO prop trading challenge with this architecture:

OVERVIEW:
- Multi-instrument (XAU/USD, EUR/USD, NAS100), multi-strategy trading bot
- Connects to MetaTrader 5 via the MetaTrader5 Python package
- Three independent strategies: London Breakout (15M), Trend Pullback (1H), NY Momentum (5M)
- Comprehensive risk management with daily loss tracking and drawdown stages
- Full backtesting capability before going live

START WITH PHASE 1 — BACKTESTING ENGINE:

1. Create the project structure:
   ftmo_bot/ with strategies/, core/, backtesting/, utils/, data/, logs/

2. Build core/indicators.py:
   - EMA (periods: 20, 50, 200)
   - RSI (14)
   - ATR (14)
   - MACD (12, 26, 9)
   - Session range calculator (high/low between two timestamps)

3. Build backtesting/backtest_engine.py:
   - Event-driven backtester (not vectorized) for accurate simulation
   - Inputs: OHLCV DataFrame, strategy object, risk parameters
   - Track: entries, exits, P&L, drawdown, daily P&L
   - Simulate spread costs (configurable per instrument)
   - Enforce FTMO rules: 5% daily loss limit, 10% max drawdown
   - Output: trade log DataFrame + performance metrics dict

4. Build backtesting/data_loader.py:
   - Load CSV files (HistData format and MT5 export format)
   - Resample M1 data to M5, M15, H1, H4
   - Handle timezone conversion to CET
   - Merge multi-timeframe data for strategies that need it

5. Build strategies/london_breakout.py:
   - Calculate Asian session range (00:00-07:00 CET)
   - Entry: 15M candle close beyond range during 08:00-10:00 CET
   - Filter: Skip if range > 1.5x 20-day average
   - SL: Opposite side of range
   - TP: 1:2 R:R (close 50%), trail remainder on 1H structure

6. Build core/risk_manager.py:
   - Position size calculator (balance, risk%, SL distance, pip value)
   - Daily loss tracker (realized + unrealized)
   - Drawdown stage manager (normal → reduced → survival → stop)
   - Max concurrent position enforcer

7. Build backtesting/performance.py:
   - Calculate: win rate, profit factor, Sharpe, max DD, recovery factor
   - Generate equity curve plot
   - Daily P&L distribution chart
   - Monthly returns table

Use pandas, numpy, and matplotlib. No external backtesting frameworks.
Config in config.py with all parameters easily adjustable.
Type hints on all functions. Docstrings on all classes/methods.
Logging throughout (not print statements).
```

---

## SUMMARY

The fundamental shift from your current setup:

**Before:** Single instrument (Gold), single strategy, hoping for signals  
**After:** 3 instruments × 3 strategies = up to 9 signal sources, guaranteeing consistent trade flow

The bot doesn't need to be perfect. It needs to be *consistent* — generating 8-14 trades per week with a slight edge (profit factor > 1.5) while never breaching FTMO's risk limits. That's the formula that passes challenges.
