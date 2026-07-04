# Collaborator Brief: What These Two Strategies Are Doing

This note explains the two live paper strategies in plain English so another developer or collaborator can understand the intent, the decision flow, and where to work in the codebase.

Prepared from the current codebase on 2026-04-02.

## 1. Executive Summary

I am currently running two separate strategy ideas:

1. `stock_day` / `stock_daytype`
   A multi-stock intraday equity strategy that classifies each tracked stock around 10:00 AM and takes directional cash-equity trades only in names that look like they will trend for the rest of the day.

2. `Nifty Shield`
   A Nifty weekly options premium-selling strategy that uses the DayType regime plus India VIX to decide what options structure to sell, how much to size, and when to exit.

These are different in purpose:

- `stock_daytype` is a directional intraday stock strategy.
- `Nifty Shield` is a volatility-selling index options strategy.

## 2. Important Current-State Notes

These points matter because older docs and the current code are not fully identical:

- I often refer to the stock basket as "50 stocks", but the current live loader reads `45` unique symbols from `data/features/day_type/stocks_universal_labels.csv`.
- `stock_daytype` currently enters around `10:01 AM`.
- `Nifty Shield` currently uses the `13pm` checkpoint and, in the active JSON config, enters immediately at that checkpoint because `entry_after_minutes = 0`.
- `Nifty Shield` is not a directional prediction system. It is a structure-selection and premium-harvesting system.

## 3. Strategy A: `stock_daytype` (multi-stock intraday directional)

### 3.1 Objective

The goal is to find stocks that are likely to continue trending after the first 45 minutes of trade, then hold those trades intraday with defined stop, target, and time exit rules.

### 3.2 Core idea

For each tracked stock, I look only at the first 45 one-minute bars of the session. From that opening behavior, I classify the day into:

- `BullTrend`
- `BearTrend`
- `Choppy`

I only trade the directional classes:

- `BullTrend` -> go `LONG`
- `BearTrend` -> go `SHORT`
- `Choppy` -> no trade

### 3.3 What the model uses

The active stock model is a lightweight classifier built on three 10:00 AM features:

- `e_ret`: return from session open to 10:00
- `e_range`: normalized high-low range of the first 45 minutes
- `e_close_loc`: where the 10:00 close sits inside the opening range

The model artifacts live under:

- `models/daytype/stock_1000am/`

### 3.4 Trading flow

Per symbol, the live logic is:

1. Collect 1-minute bars from the open.
2. At bar 45, classify the symbol.
3. If prediction is `BullTrend` or `BearTrend`, check confidence threshold.
4. Enter at bar 47 open, roughly `10:01 AM`.
5. Manage with fixed stop, fixed target, and trailing stop.
6. Force exit near end of day if still open.

### 3.5 Actual risk and execution rules in code

- Universe: current loader reads `45` symbols.
- Entry side:
  - `BullTrend` -> long
  - `BearTrend` -> short
- Confidence filter:
  - trade only if `confidence >= 0.50`
- Position sizing:
  - max capital per trade = `Rs 50,000`
  - quantity = `floor(50000 / entry_price)`
  - skip if even 1 share exceeds max capital
- Portfolio cap:
  - max simultaneous open positions = `10`
- Stop loss:
  - default `1%`
- Target:
  - default `2%`
- Trailing rule:
  - once price moves by 1 stop distance in favor, stop starts trailing
- Time exit:
  - exit around `15:28`

### 3.6 What else is being recorded

This strategy also stores context for later review:

- regime state derived from VIX
- breadth ratio at entry
- Nifty return at entry
- 11:00 AM dispersion snapshot
- MAE / MFE
- exit efficiency

So in practice this strategy is not just trading; it is also generating a structured post-trade learning dataset.

### 3.7 How I would describe it to a collaborator

`stock_daytype` is my intraday stock continuation engine. I classify each tracked stock at 10:00 AM using only opening-range information. I only trade stocks predicted to be directional, size them with a fixed capital cap, and manage them with a 1% stop, 2% target, trailing stop, and end-of-day exit. The purpose is to capture same-day trend continuation in a diversified basket rather than predict the exact path of the Nifty index.

## 4. Strategy B: `Nifty Shield` (Nifty weekly options premium selling)

### 4.1 Objective

The goal is to harvest option premium on Nifty weekly expiry structures, while adapting structure and size to market regime instead of trying to predict exact direction.

### 4.2 Core idea

This strategy assumes that implied volatility is often richer than realized volatility. Instead of making a pure directional bet, it sells premium using a structure chosen from:

- `short_straddle`
- `short_strangle`
- `iron_fly`
- `bull_put_spread`
- `bear_call_spread`

The structure is selected using:

- DayType regime
- previous India VIX close

### 4.3 Regime interpretation

The DayType output is used as a risk and structure selector:

- `BullTrend` -> use `bull_put_spread`
- `BearTrend` -> use `bear_call_spread`
- `Choppy` + high VIX -> use wider / hedged premium structures
- `Choppy` + lower VIX -> sell ATM premium more directly

So the system is saying:

- trending day -> do not sell naked ATM two-sided premium
- choppy day -> premium selling is more attractive

### 4.4 Current structure-selection logic

Current code selects:

- `BullTrend` -> `bull_put_spread`
- `BearTrend` -> `bear_call_spread`
- `Choppy` and `VIX > 16` -> `short_strangle`
- `Choppy` and `14 < VIX <= 16` -> `iron_fly`
- `Choppy` and `VIX <= 14` -> `short_straddle`

### 4.5 Current timing and risk rules

From the active config:

- Entry checkpoint = `13pm`
- Entry delay after checkpoint = `0 minutes`
- Exit time = `15:15`
- Profit target = close at `50%` premium capture
- Stop loss = close at `2x` premium loss
- Delta adjustment threshold = `0.55`
- Max lots = `2`
- Lot size = `75`
- Skip strategy entirely if `VIX > 20`
- Reduce size when `VIX > 16`

### 4.6 Position management

Once entered, the strategy monitors:

- current option premium
- mark-to-market P&L
- net delta
- time to exit

It exits on:

- profit target
- stop loss
- time exit

It can also roll a threatened short leg if its delta breaches the threshold.

### 4.7 Pricing model

This is a paper strategy, so pricing is hybrid:

- if live option LTP is available, it uses that for the short legs
- otherwise it falls back to synthetic Black-76 pricing

That means collaborators should think of this as a live-paper execution framework with synthetic fallback, not as a broker-executed production strategy.

### 4.8 How I would describe it to a collaborator

`Nifty Shield` is my regime-aware weekly Nifty premium-selling engine. It does not try to predict exact direction. It first reads the DayType regime and previous VIX context, then chooses the appropriate options structure, sizes conservatively, exits on premium-capture / stop / time rules, and can roll a short leg if delta risk gets too high.

## 5. How These Two Strategies Fit Together

They are related, but they solve different problems:

- `stock_daytype` asks: which individual stocks are likely to trend today?
- `Nifty Shield` asks: what is the safest and most appropriate way to sell Nifty weekly premium under today’s regime?

Shared philosophy:

- use regime information rather than discretionary opinions
- define entry and exit rules in code
- persist every signal and trade for later analysis
- prefer controlled, explainable logic over black-box automation

## 6. What I Need Collaborators To Understand

If someone is helping on logic, I want them to understand these boundaries:

- Do not treat `stock_daytype` as an index model. It is a per-stock classifier and portfolio selector.
- Do not treat `Nifty Shield` as a directional options-buying strategy. It is a premium-selling and structure-selection engine.
- The DayType engine is shared conceptually, but each strategy uses it differently:
  - `stock_daytype` uses it for direct directional entry
  - `Nifty Shield` uses it as a gate / structure selector
- Trade persistence and post-trade analytics are part of the design, not an afterthought.

## 7. Where To Look In Code

Main files for collaborators:

- `core/strategies/stock_daytype_paper.py`
- `scripts/stock_daytype_runner.py`
- `docs/STOCK_DAYTYPE_CLASSIFIER.md`
- `core/strategies/nifty_shield_strategy.py`
- `scripts/nifty_shield_runner.py`
- `core/models/nifty_shield_config.json`
- `docs/NIFTYSHIELD_IMPLEMENTATION.md`

## 8. Suggested Hand-Off Message To Collaborators

You can share the following summary directly:

> I am currently running two paper strategies.
>
> The first is `stock_daytype`, a multi-stock intraday strategy. It classifies each tracked stock around 10:00 AM using opening-range features, trades only BullTrend and BearTrend predictions, sizes by fixed capital per trade, and exits using stop, target, trailing stop, or end-of-day rules.
>
> The second is `Nifty Shield`, a Nifty weekly premium-selling strategy. It uses DayType plus India VIX to choose whether to run a short straddle, strangle, iron fly, bull put spread, or bear call spread. It is regime-aware, size-controlled, and exits on premium capture, stop, time exit, or delta-based adjustment.
>
> If you work on these, please think in terms of regime logic, structure selection, sizing, entry timing, and post-trade analytics, not only raw prediction accuracy.

## 9. Best Next Use Of Collaborators

If I were assigning work, I would split it like this:

- one person on `stock_daytype` signal quality and portfolio construction
- one person on `Nifty Shield` structure selection, pricing realism, and adjustment logic
- one person on post-trade analytics, validation, and dashboards

That division matches how the system is already structured.

## 10. Honest Assessment And Improvement Room

Both strategies are valid enough to keep running in paper, but both still have meaningful room for improvement.

### 10.1 `stock_daytype`

What is good:

- The timing logic is much better than the older 13:00 version.
- The system is simple, explainable, and easy to audit.
- It already captures useful post-trade context for learning.

What is still weak:

- The raw predictive edge appears modest, so portfolio construction matters more than model accuracy alone.
- Risk is still handled with mostly fixed rules across all stocks.
- The strategy can still end up behaving like a blunt basket of correlated intraday bets.

Highest-priority improvements:

- rank signals cross-sectionally and take only the strongest names instead of every qualified name
- add volatility-normalized stops and targets instead of flat percentages for all stocks
- add sector and correlation caps so the book is not over-concentrated
- review whether `0.50` should remain a universal confidence threshold
- evaluate whether exits should depend on intraday regime or trend persistence instead of one fixed template

### 10.2 `Nifty Shield`

What is good:

- The architecture is stronger and closer to a complete trading system.
- Structure selection based on regime plus VIX is the right design direction.
- Risk controls, sizing logic, and adjustment hooks are already present.

What is still weak:

- Paper pricing can still be too optimistic versus real execution.
- Gap risk, skew, smile, and slippage are not modeled deeply enough yet.
- The system still needs more explicit risk budgeting in rupee terms, not only premium-percentage terms.

Highest-priority improvements:

- validate synthetic vs live option prices and measure drift by structure and regime
- make risk sizing more explicit in rupees, margin usage, and worst-case stress terms
- stress-test the current regime-to-structure map rather than treating it as fixed truth
- improve event-day handling, expiry-week behavior, and gap-risk controls
- verify whether delta-adjustment logic improves net outcomes after roll friction

## 11. Practical Priority Order

If development time is limited, I would prioritize work in this order:

1. `stock_daytype`: improve selection and portfolio construction before changing the model.
2. `stock_daytype`: replace flat stop/target logic with volatility-aware trade management.
3. `Nifty Shield`: improve pricing realism and execution assumptions.
4. `Nifty Shield`: add stronger tail-risk and event-risk controls.
5. Both strategies: use the stored trade data to decide where the actual edge exists instead of assuming it.
