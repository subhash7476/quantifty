# Vault Mechanism Gap Map — researcher's classification

**Date:** 2026-09-28
**Inputs (only):** `docs/research/Vault_STRATEGY_CENSUS.md` + `Vault_STRATEGY_INVENTORY.csv` (5,807 rows),
treated as the worker's audited output; and this repo's existing research record under `docs/reports/`.
**Not done:** no external source consulted, no re-census, no backtest, no parameter, no experiment
proposed, no data read, no gate consumed. Vault screenshots / claimed returns are not evidence (census §7).

## Why this differs from census §8

Census §8 compared the Vault only against the programs named in `CLAUDE.md`. The research record is
wider. These programs change the classification and were missing from §8:

| Program | Record | What it covers |
|---|---|---|
| A — index intraday opening drive | `index_research/A_HOLDOUT_CLOSURE.md` | Intraday trend continuation on Nifty; TRAIN PASS → **HOLDOUT FAIL**, retired |
| ISD battery (F1 open-drive, F4 overnight gap) | `strategies/ISD_PROGRAM_REASSESSMENT.md` | Intraday continuation (sign wrong) + gap fade (IC t −6.09, **cost-killed**). The ISD RFAs cite a legacy FTMO time-series ORB/gap-fade null (0/41) as a *prior*; that system is not in this repo, so it is not an in-house test |
| Stage A Gate 0 | `strategies/STAGE_A_GATE0_REPORT.md` | Zero-data pricing of six intraday index families: F-OPEN answered by A; **F-VOL, F-TOD, F-RANGE breakout, F-REL priced infeasible (no data read)**; F-GAP + F-RANGE *failed breakout* PLAUSIBLE, unmeasured |
| MRLC | `strategies/MRLC_CONSTRUCT_ASSESSMENT.md` | Liquidity-sweep / reclaim price action; reduced to the F-RANGE failed-breakout cell |
| PTMS Gann | `ptms/PTMS_GANN_CONSTRUCT_CATALOGUE_2026-09-14.md` + Stage-1 screen | Swing-pivot price/time geometry, retracement, anniversaries catalogued. Stage-1 screened **three swing-pivot primaries (GF-1, GF-4T/R8, GF-10), all retired**. Retracement (GO-1) is Secondary, **never screened**. GT-4 fixed seasonal dates Descriptive only |
| DRA / N200 regime HMM / NiftyShield regime | `strategies/DRA_TECHNICAL_DOSSIER.md` etc. | Regime classification: "classifier works, directional strategy not profitable" |
| Options-selling programme | MSRP D1 straddle STOP, `OPTIONS_SELLER_EDGE_STUDY`, STOCK-STRADDLE-M10 (frozen, forward), Options Wall, OSC, O1 | Short-vol / VRP harvesting, index and stock |
| PSB C2/C3, Flow | PSB reports, `FLOW_RFA.md` | Volume-composition (delivery %) and OI-flow signals |

## Gap map

Key: **AR** ALREADY_RESEARCHED · **RD** RELATED / DIFFERENT IMPLEMENTATION · **NEW** APPARENTLY NEW ·
****UNC** UNCLEAR. "Repack" = the Vault item is a repackaging of a mechanism already tested here.
Rule: **AR** = the same economic mechanism was measured (or formally priced) here, at some horizon or
venue. **RD** = the mechanism is adjacent, or the Vault's form differs in breadth or instrument, e.g.
single-instrument time series vs our cross-section.

| # | Vault family (files) | Class | Mechanism it actually expresses → where we tested it |
|---|---|---|---|
| 1 | Combo multi-indicator (2,306) | Repack | AND-conjunctions of #2–7 (census §10.5). Not a mechanism |
| 2 | MA trend-transition (1,245) | **AR** | Trend persistence. Trend sleeve (TSMOM, TRAIN FAIL), A (intraday index continuation, HOLDOUT FAIL), RS-MOM (ABANDON), F1 12-1, PSB C4, DRA HMM directional (unprofitable) |
| 3 | Oscillator reversion (682) | **RD** | Short-horizon reversal. Tested cross-sectionally (CB-N50 reversal+basis combined HOLDOUT IC +0.029; PSB C1 fee-dead; ISD F4 gap fade cost-dead) and as pair MR (falsified). *Single-instrument time-series* oscillator fade is not tested in-house (legacy FTMO null is a prior only) |
| 4 | MACD / momentum (235) | **AR** | Same mechanism as #2 (difference of EMAs) |
| 5 | Volatility-stop trend (220) | **RD** | Trend persistence (#2) with a vol-scaled trailing exit. Exit machinery = F1 ATR brackets; the entry is not a distinct mechanism |
| 6 | Breakout / range (189) | **AR** | Donchian/52-wk = TSMOM (Trend). ORB = F-OPEN, answered by A. Intraday breakout **priced infeasible, no data read** (Gate 0). Failed-breakout variant = F-RANGE, scoped but unmeasured |
| 7 | Band / channel (148) | Repack | Bollinger/Keltner = z-scored distance from a moving mean → either #3 (revert) or #6 (break) |
| 8 | Pattern / price-action (121) | **RD** | Census said NEW. Swing-pivot structure was screened in Gann Stage-1 (three primaries retired). Fib/harmonic retracement = Gann GO-1, *catalogued but never screened*. Engulfing/hammer = one-/two-bar reversal after a failed extreme = #3 + F-RANGE failed breakout (MRLC kernel) |
| 9 | Grid / martingale / DCA (71) | Repack | Census said NEW (no-edge class). A grid collects no implied premium, so it does not harvest the VRP. Its P&L depends on **negative autocorrelation at the grid spacing**: time-series mean reversion (#3), with a short-gamma payoff (earns in ranges, unbounded loss in trends). It resembles options selling in risk shape, not in edge source, and links to NEW-4. Martingale is a sizing rule, not a mechanism |
| 10 | Volume / flow (43) | **RD** + sub-item | OBV/MFI/FVE/volume-confirmation relate to delivery-% (PSB C2/C3) and Flow (RFA ABANDON). VWAP/volume families were excluded at Gate 0 (index volume = 0). **Signed order-flow imbalance (CVD / volume delta) as a price-pressure signal is only named as a channel in the ISD ranking, never tested** → see NEW-3 |
| 11 | Hedge / arbitrage (42; ~10–15 genuine) | **RD** + sub-item | Spot–perp spread = basis (Carry, TS Basis, funnel audit). **Cross-venue segmentation arbitrage is not in our record** → NEW-2 |
| 12 | Ichimoku (36) | Repack | Tenkan/Kijun are Donchian mid-ranges; cloud = lagged mid-range → #2/#6 |
| 13 | ADX / DMI (19) | **RD** | Trend-strength regime gate. Regime gating researched via DRA/N200 HMM; F-VOL priced infeasible (no data read) |
| 14 | Seasonal / calendar (10) | **NEW** (partial) | Only adjacent work: Gann GT-1 pivot anniversaries (catalogued primary), GT-4 fixed dates (Descriptive, untested), F-TOD time-of-day (priced infeasible intraday). A targeted grep found no day-of-week / turn-of-month test anywhere in `docs/reports`. Day-of-week / turn-of-month / month-of-year are **not in our record** → NEW-1 |
| 15 | Parabolic SAR (5) | Repack | Vol-stop variant (#5), as census §10.4 already notes |
| 16 | Carry / funding / basis (~5) | **AR** | Carry (production-ready), TS Basis, TS Basis Daily. Funding rate is the perp analogue of basis. The Vault files are monitors, not signals |
| 17 | Options-vol selling (2) | **AR** | Our most-researched area (see programs table). The Vault files are #3 reversion rules that happen to sell options (census §10.1) |
| — | UNCLEAR (389) | **UNC** | Filename carries no mechanism. Census spot checks point to #2/#3, but that's a prior, not a classification |

### Census §9 "novel" long tail, re-read

| Item | Class | Why |
|---|---|---|
| Hurst regime gating (2) | **RD** — borderline, see NEW-4 | Regime-conditional rule switching is researched (HMM). What's different is gating on the *sign of serial dependence* (persistent vs anti-persistent) rather than a vol/trend state |
| Quadratic / regression bands (6) | Repack | Smoother + envelope = #7 |
| FVE (2) | Repack | Volume-weighted money-flow oscillator = #10 (OBV/MFI class) |
| Black-Scholes-σ breakout (3) | Repack | Vol-normalised breakout = #6; vol scaling is already in Trend |
| Z-score switching (7) | Repack | #7 / #3 |
| Calendar clock trades (10) | **NEW** | NEW-1 |
| Cross-exchange spread capture | **NEW** | NEW-2 |
| Nifty/BankNifty templates (42) | Repack / **AR** | ORB = A/F-OPEN (answered); Supertrend = #5. These are templates, not mechanisms (census §10.2) |
| VWAP + volume stack (49) | **UNC** | VWAP reversion on *equity* 1m is not in our record. Gate 0 excluded it only on the index (volume 0). The record is too thin to say whether VWAP as an anchor adds anything beyond #3 |

## Hypotheses classified as APPARENTLY NEW: the economic claim behind each

- **NEW-1 — Calendar-timed flow (day-of-week, turn-of-month, month-of-year).** Some market participants are forced to trade on a schedule that has nothing to do with information: salary-linked SIP inflows at the start of the month, month-end window dressing and rebalancing, expiry-cycle hedge unwinds, and bearing risk over the weekend. Predictable demand of that kind can shift expected returns by calendar position. Caveat: this is the most data-mined anomaly class in the literature. Our record has nothing on it, which is not the same as it being promising.
- **NEW-2 — Venue-segmentation arbitrage.** When liquidity is split across venues, the same asset can trade at different prices for a while. The spread pays whoever provides cross-venue liquidity and carries the inventory and transfer risk. It's distinct from basis, which is the price of carry over time, not of location. It sits outside our mandate and infrastructure: it rewards speed and needs multi-venue access.
- **NEW-3 — Signed order-flow imbalance → price pressure.** Net aggressor volume carries information, or at least temporarily depletes liquidity, so imbalance should predict short-horizon drift or reversal. It's distinct from our volume-composition work (delivery %) and OI flow. Neither of those observes *who initiated* a trade. We don't hold signed trade data. (Pine CVD approximates it from bar direction.)
- **NEW-4 (borderline) — Forecastable serial-dependence regime.** The claim is that the market's autocorrelation sign persists long enough to choose between a trend rule and a reversion rule ex ante. It's related to our HMM regime work but not the same claim: an HMM state conditions on volatility and drift, while this conditions on dependence structure.

## Items presented as novel that are repackaged mechanisms we've already tested

- **Grid / martingale / DCA** → time-series mean reversion (#3) carrying a short-gamma payoff. Census §8 called it NEW.
- **Pattern / price-action** → Gann swing-pivot geometry (primaries retired; retracement untested) + short-horizon reversal + F-RANGE failed breakout (MRLC kernel).
- **Band/channel, Z-score switching, regression/quadratic bands** → reversion or breakout around a moving mean.
- **Ichimoku, Parabolic SAR, σ-scaled "Black-Scholes" breakout, Supertrend** → trend persistence / breakout.
- **FVE, OBV-style volume confirmation** → volume-flow family (#10).
- **Nifty-native ORB/Supertrend templates** → A / F-OPEN (answered) and #5.
- **Options-selling files, funding monitors** → our options and basis programmes.
- **Combo (2,306 files)** → conjunctions of the above, and not one discovery.

## Conclusion

Of about 17 families, **none is a genuinely new mechanism for our program at the family level**. Some
also land on already-closed walls: intraday breakout, TOD and vol-state were priced infeasible; trend
continuation failed out of sample (A).

The smallest set of distinct hypotheses outside the existing research program is:

1. **Calendar-timed flow** (NEW-1): the only one that is both outside our record and native to our substrate
2. **Venue-segmentation arbitrage** (NEW-2): outside the record, and outside our mandate
3. **Signed order-flow imbalance** (NEW-3): outside the record; we hold no substrate for it
4. *Borderline:* **serial-dependence regime gating** (NEW-4): a different claim from our HMM regime work, but closely related to it

Two open UNCLEAR items should not be counted either way: the 389 unlabelled files, and VWAP-anchored reversion on equity 1m.

None of this is evidence. Each item carries only an idea, E1–E2 at most per the census. Any of them would restart at the RFA gate as its own pre-registration.
