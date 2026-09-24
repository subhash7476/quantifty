# Options Seller-Edge Study — where only the option seller gets paid

**Date:** 2026-09-11
**Status:** Exploratory research memo. Not a pre-registration, not a gated read, no strategy code.
Scripts live in the session scratchpad and are reproduced in §9.

> **§4 was written before the 2023+ data was opened.** The discovery window (2016–2022) was
> analysed first. The predictions in §4 were then written into this file. Only after that was the
> confirmation window (2023-01 → 2026-08) run, with the same code unchanged. Anything below §4 that
> cites 2023+ numbers came after the predictions.

---

## 0. Question and data actually available

Question (operator, 2026-09-11): look at recently acquired options data for patterns tied to CAS,
expiry and similar events, and find a way to trade index/stock options where only selling can be
profitable.

| Store | Coverage | Note |
|---|---|---|
| `stock_options_bhavcopy.duckdb` | 2016-02-11 → **2026-09-10**, 366 underlyings, 99.5 M rows | the recently acquired store; monthly expiries only |
| `options_bhavcopy.duckdb` | NIFTY only, 2016-02-11 → **2026-07-17** | **ends before CAS (2026-08-03)**; no BankNifty/Sensex history |
| `futures_bhavcopy.duckdb` | FUTSTK + FUTIDX → 2026-09-10 | forward and realized-vol source |
| `wall_chain_snapshots/*.duckdb` | 2026-09-04, 07, 08, 09, 10 (+11 in progress) | intraday 5 s chains, **front expiry only**, Nifty/BankNifty/SENSEX |
| Live bid/ask snapshot (this study) | 2026-09-11 12:54, 17,433 stock options, Sep + Oct expiries, ±15 % strikes | the only bid/ask for stock options we have |

**Semantics that matter.** In bhavcopy an untraded option row (`contracts = 0`) carries the
*previous* close in `close` (99.99 % of cases) and the exchange's theoretical price in `settle`.
So entries require both legs traded. Exits use `close` if the leg traded and `settle` otherwise;
that fallback applies to 10–15 % of exits and is tested in §2.3.

## 1. What a stock option actually costs to trade (live, 2026-09-11)

Median relative bid/ask spread `(ask − bid)/mid`, two-sided quotes (94.8 % of instruments):

| moneyness | Sep-29 (near) | Oct-27 (next) |
|---|--:|--:|
| ITM > 5 % | 5.8 % | 11.8 % |
| ITM 2–5 % | 2.5 % | 20.1 % |
| **ATM ± 2 %** | **1.7 %** | 25.5 % |
| OTM 2–5 % | 2.4 % | 35.4 % |
| OTM 5–10 % | 4.5 % | 55.2 % |
| OTM 10–15 % | 14.3 % | 102 % |

Near-month ATM by liquidity tier (underlying's option volume): top 20 % **1.3 %**, mid 30 % 1.6 %,
bottom 50 % 2.0 %. ATM p10/p90 = 0.85 % / 4.0 %.

**Consequences:** (a) only the near month is tradeable; (b) ATM is the cheapest place to sell, and
far-OTM "lottery ticket" selling is eaten by spreads; (c) the study below prices costs as a swept
relative spread of 1–4 % paid half on entry and half on exit, plus fees. Fees are era STT on the
sell leg (0.05 % → 0.0625 % from Apr-2023 → 0.1 % from Oct-2024), exchange charges + 18 % GST on
both legs, stamp, and brokerage at ~0.3 % of premium.

## 2. Stock options — the expiry cycle (DISCOVERY 2016-02 → 2022-12)

**Construct.** For every monthly expiry E (80–81 expiries), sell the ATM straddle on every F&O stock
at the close k sessions before E. ATM is the strike nearest the same-expiry future, with both legs
traded. Buy it back at the **T-1 close**: stock F&O is physically settled, so marking to intrinsic
at expiry would backtest a trade nobody can take. Cycles with a corporate-action jump (a front-future
daily move > 25 %) or missing exit rows are dropped. The seller's return is
`(entry premium − exit premium) / entry premium`. Returns are averaged across names within each
expiry first, so the t-statistic is across expiries and cross-sectional correlation cannot inflate it.

### 2.1 Where in the cycle the seller gets paid

| entry | hold (sess) | names/exp | gross / cycle | gross / session | t (gross) | net @2 % spread | t (net) | expiries > 0 | NIFTY same window, gross (t) |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| cycle start | 18 | 160 | +6.9 % | 0.38 % | 1.98 | +4.5 % | 1.28 | 64 % | −1.5 % (−0.15) |
| 15 before | 14 | 165 | +7.9 % | 0.56 % | 2.04 | +5.5 % | 1.41 | 70 % | −0.7 % (−0.08) |
| **10 before** | **9** | **166** | **+13.8 %** | **1.53 %** | **6.05** | **+11.5 %** | **4.98** | **76 %** | +9.4 % (1.45) |
| 7 before | 6 | 165 | +9.8 % | 1.63 % | 3.70 | +7.4 % | 2.77 | 77 % | +5.7 % (0.77) |
| 5 before | 4 | 164 | +9.2 % | 2.29 % | 3.35 | +6.8 % | 2.46 | 72 % | −3.5 % (−0.43) |
| 3 before | 2 | 165 | +6.0 % | 3.01 % | 3.45 | +3.6 % | 2.04 | 70 % | +8.4 % (2.18) |

**The pattern.** The seller's edge sits in the **final two weeks** of the monthly stock-option
cycle. Per session it rises monotonically, from 0.38 % of premium at cycle start to 3.0 % in the
last two sessions. Entries 15+ sessions out earn the premium, but with tails large enough that
the t-stat is only ~2. Worst single expiry: −198 % (start) and −248 % (15 before) of premium, against
−49 % for the 10-before entry.

**"Only selling pays" holds literally here.** A straddle *buyer* has negative expectancy in every
row, and in §2.3 in every VRP bucket — even when implied vol is **below** trailing realized
(`vrp60 < 0`), sellers still net +8.1 % (t 2.7). No segment of this study shows a profitable
long-premium position after costs.

### 2.2 Stock vs index (a dispersion read)

The NIFTY monthly straddle over the same windows is **not significant** in any row (t −0.4 to
+2.2, one series, n = 80). The stock-basket-minus-NIFTY gap is positive in 5 of 6 rows but never
significant (t ≤ 1.93). So the finding is "single-stock premium decays reliably late in the cycle".
It is **not** a demonstrated implied-correlation premium. A dispersion trade (short index vol / long
stock vol) is the *opposite* sign of what the data supports, and its power is 0.14 (§3).

### 2.3 Robustness — 10-before entry, net of 2 % spread, per-expiry basket means

| cut | trades | mean | t | worst expiry | expiries > 0 |
|---|--:|--:|--:|--:|--:|
| all | 13,281 | +11.5 % | 4.98 | −49 % | 76 % |
| exit legs both traded (no `settle` fallback) | 11,998 | +14.3 % | 6.42 | −44 % | 78 % |
| entry put-call-parity error < 10 % of premium | 12,670 | +11.5 % | 4.98 | −51 % | 76 % |
| liquid half (entry option turnover) | 6,700 | +11.1 % | 4.80 | −53 % | 76 % |
| top-20 % liquidity (~33 names) | 2,704 | +10.5 % | 4.33 | −50 % | 72 % |
| top-20 % liquidity at **4 %** spread | 2,704 | +8.6 % | 3.53 | −52 % | 69 % |
| vrp60 < 0 (implied below 60-d realized) | 3,514 | +8.1 % | 2.73 | −70 % | 74 % |
| vrp60 0–0.25 | 5,746 | +11.3 % | 3.91 | −97 % | 78 % |
| vrp60 > 0.25 | 4,021 | +14.3 % | 5.95 | −61 % | 76 % |

- **Break-even relative spread: 14.0 %**, about 8× the live ATM median. Costs are not the binding
  constraint here, unlike every cash-equity battery in this repo.
- The traded-exit-only cut is *higher*, which is survivor selection: a strike still trading at
  T-1 is near the money, so the seller won. The full sample with the `settle` fallback is the honest figure.
- Cross-sectional rank IC of `vrp60 = ln(IV_straddle / RV60)` vs seller return: **+0.040, t 3.40**,
  n 80. Real, but small next to the unconditional effect. It tilts the book; it does not make it.
- Equal-weight basket P&L per cycle in % of futures notional: **mean +1.03 %, sd 1.52 %** →
  annualised Sharpe **2.34** (gross of spread, in-sample). Per-expiry skew **+0.32**
  (diversification across ~166 names). Worst expiries: May-2017 −2.6 %, **Mar-2020 −2.25 %**,
  Sep-2017 −1.8 %, Jan-2022 −1.8 %, Sep-2022 −1.7 % of notional. Cumulative max drawdown −3.3 %
  of notional.
- By year (net @2 %): 2016 +12.3 %, 2017 +4.1 %, 2018 +11.1 %, 2019 +5.5 %, **2020 +21.5 %**,
  2021 +18.0 %, 2022 +9.4 %. Positive every year, including the COVID crash year.

**Multiple testing.** Six entry offsets were examined and the 10-before row is the in-sample best.
Bonferroni at m = 6 does not threaten t = 6.05 (or t = 4.98 net). The *specific* offset is still
selected and should shrink out of sample. The robust claim is "last two weeks", not "exactly 10 sessions".

## 3. Power pre-check (repo RFA arithmetic, `scripts/rfa/power.py`, one-sided α = 0.05)

| shape | window | n | result |
|---|---|--:|---|
| **A** — index short-premium timing (weekly Nifty, DTE-0, overnight, auction window) | 2023-01 → 2026-07 | 184 weekly | S_ann 1.0 → power **0.59**; needs **S ≥ 1.3**. MSRP Phase 7 measured S 0.74 on the daily ATM short straddle (2023–25) → power 0.40. The RS-MOM/O1 wall. |
| **B-uncond** — stock basket late-cycle straddle, per-expiry P&L | 2023-01 → 2026-08 | 44 monthly | S_ann 1.0 → 0.60; **1.5 → 0.88**; 2.34 (discovery, in-sample) → 0.997. Clears if half the discovery Sharpe survives. |
| **B-IC** — vrp60 rank IC | same | 44 | δ 0.04 / sd 0.105 (discovery) → power **0.80** exactly; δ 0.02 → 0.32 |
| **C** — dispersion (stock − index) | same | 43 | discovery implies S_ann 0.31 → power **0.14**. Dead. |

A and C get no further analysis budget beyond the descriptive notes in §6/§7. B is the candidate.

## 4. Pre-stated predictions for the confirmation window (written before reading 2023+)

Confirmation window: entries 2023-01-01 → 2026-08-24 (expiries through 2026-08-25). The code is
`cycle_study.py`, unchanged. Split at 2024-11-20, the SEBI F&O reform (weekly-expiry
rationalisation, higher contract sizes, expiry-day ELM). Prior exposure: none of this study's
authors has read 2023+ single-stock option returns. MSRP Phase 7 read 2023–2025 **Nifty** daily
straddles (index side only). The Skew sleeve read stock options on TRAIN only.

| # | Prediction | Pass condition |
|---|---|---|
| P1 | 10-before stock basket earns positive gross seller return | per-expiry mean > 0, t > 1.68 |
| P2 | It survives costs | net @2 % spread per-expiry mean > 0, t > 1.68 |
| P3 | The edge is late-cycle | mean gross/session of {10,7,5,3 before} > mean of {start, 15 before} |
| P4 | Positive in both regulatory sub-windows | net @2 % mean > 0 in 2023-01→2024-10 **and** in 2024-11→2026-08 (no t hurdle; n ≈ 22 each) |
| P5 | vrp60 tilts the right way | rank IC mean > 0 (t hurdle 1.68 stated, but power is only ~0.80 even at full effect) |
| P6 | Expected shrinkage | 10-before net @2 % mean lands in **+3 % to +12 %** of premium; below +3 % counts as "decayed" even if P2 passes |
| — | Stock − NIFTY gap | **no prediction** (not significant in discovery; NIFTY store ends 2026-07-17) |

A pass on P1, P2 and P4 makes this a candidate for a proper pre-registration. It does **not**
authorise trading. A fail on P2 or P4 retires it.

---

## 5. Confirmation results (2023-01 → 2026-08, 43 expiries, ~189 names/expiry)

### 5.1 Scorecard

| # | Result | Verdict |
|---|---|---|
| P1 | 10-before gross **+10.6 %**/cycle, t **3.78** | **PASS** |
| P2 | net @2 % **+8.2 %**, t **2.90**; 77 % of expiries positive | **PASS** |
| P3 | late {10,7,5,3}: mean 1.47 %/session vs early {start,15}: 0.30 %/session | **PASS** |
| P4 | pre-reform (22 exp) **+9.6 %**, t 3.15; post-reform (21 exp) **+6.7 %**, t **1.37** | **PASS on the stated condition, weak after the reform** |
| P5 | vrp60 IC +0.014, t 1.24 | **FAIL** (right sign, not significant) |
| P6 | +8.2 %, inside +3 %…+12 % | **PASS** |

**It replicates.** It is the first construct in this repo to carry a discovery-window seller
edge through an unread window with the same code. The edge is smaller than in discovery, and
most of the shrinkage came after the 2024-11 reform.

### 5.2 Full table, confirmation window

| entry | gross / cycle | t | net @2 % | t | NIFTY gross (t) |
|---|--:|--:|--:|--:|--:|
| cycle start | +2.6 % | 0.67 | +0.1 % | 0.02 | −1.2 % (−0.08) |
| 15 before | +6.3 % | 2.14 | +3.9 % | 1.31 | +8.5 % (0.81) |
| **10 before** | **+10.6 %** | **3.78** | **+8.2 %** | **2.90** | +1.5 % (0.15) |
| 7 before | +8.9 % | 2.98 | +6.5 % | 2.15 | −2.3 % (−0.23) |
| 5 before | +5.5 % | 1.94 | +3.1 % | 1.07 | −9.0 % (−1.01) |
| 3 before | +3.7 % | 1.75 | +1.3 % | 0.58 | +10.3 % (1.64) |

Robustness for the 10-before entry, net @2 %: exit-traded-only +10.7 % (t 3.86); PCP-clean
entries +8.4 % (2.97); liquid half +7.5 % (2.54); **top-20 % liquidity +5.8 % (1.81)**;
top-20 % @4 % spread +3.9 % (1.20). Break-even spread **10.7 %**. Every vrp60 bucket is positive:
< 0 +8.1 % (3.04), 0–0.25 +8.7 % (2.76), > 0.25 +11.9 % (3.70).

Basket P&L in % of notional: mean **+0.52 %/cycle**, sd 0.97 % → annualised Sharpe **1.85**.
**Skew flipped to −1.40** (discovery +0.32). Max drawdown −4.2 % of notional. Worst expiries:
**2025-04-24 −2.95 %** (tariff shock, median |future move| 10.8 %), 2024-12-26 −1.44 %,
2026-01-27 −1.20 %, 2024-08-29 −1.04 %. By year (net @2 %): 2023 +12.5 %, 2024 +3.0 %,
2025 +7.1 %, 2026 (to Aug) +11.8 %.

### 5.3 What changed after the Nov-2024 reform

| | pre-reform 2023-01 → 2024-11 | post-reform 2024-11 → 2026-08 |
|---|--:|--:|
| 10-before net @2 % (t) | +9.6 % (3.15) | +6.7 % (1.37) |
| top-20 % liquidity net @2 % (t) | +7.2 % (2.12) | +4.3 % (0.77) |
| basket Sharpe (gross, % notional) | 3.21 | 1.19 |
| per-expiry skew | −1.11 | −1.12 |
| 3-before net @2 % (t) | −2.7 % (−0.79) | +5.0 % (2.07) |

Read honestly: the post-reform half is **positive but not yet distinguishable from zero** at n = 21.
Its single worst cycle is the April-2025 tariff crash, which alone costs ~3 % of notional. The most
liquid names — exactly the ones a real book would hold first — show the weakest post-reform edge.
The 3-before row flipping positive after the reform is noted, not claimed: it is one of six rows,
read after the fact.

### 5.4 Post-confirmation diagnostics — is it tradeable, and is it a stale-price artifact?

Added after §5.1–5.3 were read (`liquidity_diagnostics.py`; same `load()`/`net()`). Two worries:
(1) the all-names average may be carried by names nobody can trade; (2) `close` is a last-traded
price, so a stale exit print could flatter the seller.

For (2), filtering on "exit legs traded" is **not a valid check** — a T-1 leg keeps trading only
when the stock stayed near the strike, so the filter conditions on the seller winning. A first
attempt at "all four legs ≥ 100 contracts" printed +33–49 %, t 16–31, and was discarded for exactly
that reason. The valid check is a **conservative exit**: the exit premium is never below a Black-76
straddle on the T-1 future with one session left, priced at the *entry* implied vol. That raised
the exit on 50 % of trades, by a median 3.8 % of entry premium.

Net @2 % spread (t), 10-before, per-expiry basket means. Every liquidity screen is known at entry:

| cut | names/exp (confirm) | confirm, observed exit | confirm, **conservative exit** | post-reform, observed | post-reform, **conservative** |
|---|--:|--:|--:|--:|--:|
| all names | 189 | +8.2 % (2.90) | **+5.7 % (2.01)** | +6.7 % (1.37) | +4.2 % (0.86) |
| entry legs ≥ 100 contracts each | 150 | +8.9 % (3.07) | **+6.5 % (2.25)** | +7.4 % (1.49) | +5.0 % (1.01) |
| entry legs ≥ 500 contracts each | 97 | +8.2 % (2.83) | +6.0 % (2.06) | +6.9 % (1.37) | +4.6 % (0.92) |
| entry option turnover ≥ ₹50 cr | 140 | +8.3 % (2.84) | +5.9 % (2.03) | +7.0 % (1.39) | +4.7 % (0.92) |
| entry option turnover ≥ ₹200 cr | 69 | +7.5 % (2.44) | +5.2 % (1.71) | +6.3 % (1.22) | +4.1 % (0.79) |
| top-20 % by turnover *rank* (~38–42 most-traded) | 38 | +5.8 % (1.81) | +3.6 % (1.12) | +4.3 % (0.77) | +2.0 % (0.36) |

Discovery under the conservative exit: all names +8.3 % (3.62); entry ≥ 100 contracts +8.6 % (3.63).

**What this settles and what it does not:**
- **Stale prices do not create the effect.** A deliberately seller-hostile exit costs ~2.5 points
  of premium and leaves the confirmation result at t ≈ 2.0–2.3 across the ex-ante liquid universe
  of ~100–150 names.
- **After the Nov-2024 reform nothing is significant** under any cut or valuation (best t 1.49).
- **The most-traded ~40 names are consistently the weakest**, in both windows. That is the
  opposite of the usual "liquid = cleaner" pattern, and it fits the crowding story in §9.1: where
  retail and prop flow sells stock premium hardest, less of it is left. The practical implication
  is awkward — the edge lives in the broad mid-liquidity set (≥100 contracts per leg at entry,
  ~150 names), not in the handful of names that are easiest to trade.
- The rank-based "top-20 %" cut drifts with universe size (160 → 207 names). The absolute cuts
  (contracts, ₹ turnover) are the ones to carry forward.
- Fees include a flat 0.3 %-of-premium brokerage term. That is a round approximation of ₹20/order,
  which is a fixed rupee cost (~0.2–0.5 % of a stock-straddle lot premium), not a model.

### 5.5 Economics in rupees-per-notional terms (10-before, net of 2 % spread and fees)

| window | P&L per cycle, % notional | sd | ann. Sharpe | worst cycle | return on margin per cycle @ 18 % margin |
|---|--:|--:|--:|--:|--:|
| discovery 2016–22 | +0.88 % | 1.52 % | 2.00 | −2.81 % | ~4.9 % |
| confirmation 2023–26 | +0.40 % | 0.99 % | 1.42 | −3.18 % | ~2.2 % |
| post-reform 2024-11 → 2026-08 | +0.30 % | 1.25 % | 0.84 | −3.18 % | ~1.7 % |

Capital is deployed ~9 sessions a month. The 18 % margin figure is a round assumption for a stock
short straddle (SPAN + ELM less premium), not an `NseMarginEngine` computation. NSE also levies
**delivery margin on potentially in-the-money physically-settled contracts through the expiry week**,
which raises margin in exactly this holding window. Verify both with the broker before any sizing.

**Last 12 cycles** (net @2 %, % of premium): Sep-25 −12.3, Oct +20.0, Nov +17.6, Dec +18.8,
**Jan-26 −26.5**, Feb +4.5, Mar +33.0, Apr −9.6, May +18.3, Jun +17.9, Jul +26.7,
**Aug-26 (first post-CAS monthly expiry) +29.0**. One post-CAS cycle is an observation, not a result.

---

## 6. Index options — the weekly expiry cycle (Nifty weeklies, 2019-02 → 2026-07)

The ATM weekly straddle is held to cash settlement. Settlement is a **proxy**: put-call parity at the
expiry-day close on the most-traded strike, not the published final settlement price. ATM strikes
are chosen off the **near-month** future, a different maturity from the weekly contract. Both are
approximations; the "nothing significant" conclusion does not hinge on a few points of error in either. The DTE-0 entry uses the strike fixed at the prior close
and expiry-day open prices. (A first pass picked the strike off the expiry-day close — a look-ahead
that printed a 99 % win rate. It was caught and fixed; the numbers below are the fixed run.)
Gross, before costs, as a fraction of premium:

| entry | discovery 2019–22: mean (t) | win % | later 2023–26: mean (t) | win % |
|---|--:|--:|--:|--:|
| close T-4 | +3.1 % (0.53) | 62 % | −0.1 % (−0.02) | 58 % |
| close T-3 | +3.3 % (0.63) | 57 % | +2.1 % (0.36) | 63 % |
| close T-2 | +9.7 % (1.99) | 63 % | +5.0 % (0.90) | 61 % |
| close T-1 | +4.3 % (0.77) | 62 % | +5.4 % (1.03) | 60 % |
| **open T-0 (expiry-day)** | +5.1 % (1.06) | 60 % | +1.5 % (0.28) | 60 % |

Overnight vs intraday, daily ATM weekly straddle, seller return on prior-close premium:

| | discovery: overnight | intraday | full day | later: overnight | intraday | full day |
|---|--:|--:|--:|--:|--:|--:|
| all days | −0.3 % (−0.66) | +1.9 % (2.13) | +1.6 % (1.88) | +0.6 % (1.30) | +0.8 % (0.84) | +1.3 % (1.41) |
| Tue–Fri | −0.2 % | +3.7 % (3.85) | +3.5 % (3.95) | +0.6 % (1.55) | +1.4 % (1.46) | +2.0 % (1.97) |
| Monday (after weekend) | −0.5 % | −4.1 % (−2.01) | −4.7 % (−2.13) | +0.7 % | −1.5 % | −0.8 % |

**Reading.** Sellers win ~60 % of weeks at every entry point, but the mean is small against
fat tails, and nothing replicates:
- **Expiry-day (DTE-0) selling** earns +1.5–5 % of premium gross, t ≤ 1.1, before ~1–2 % of costs.
- The discovery-era "sell Tue–Fri, avoid Monday" split (the Monday loss is the market pricing
  weekend theta in on Friday) weakens to t ≈ 2 and flips sign on Mondays in the later window.
- §3 already said this family cannot be demonstrated on one index at weekly cadence (needs S ≥ 1.3).
  The data agrees.

**The contrast with §2 is the finding.** Index weeklies are the most-watched, most-sold options in
India. Their premium is priced to roughly break even for the seller. Single-stock monthlies in their
final two weeks are not. The later index window is prior-exposed (MSRP Phase 7 read 2023–25 Nifty
straddles) and the index store ends 2026-07-17, so none of this touches the CAS era.

## 7. CAS — what the closing auction does to options (post-2026-08-03 data only)

### 7.1 Index options: the options market keeps pricing an index that has stopped printing

This uses put-call parity on mid-quotes (median of the 5 strikes nearest spot) from the wall
snapshots. The spot/forward basis is calibrated on 14:45–15:14 and the result called "implied spot":

- **The index print freezes from 15:15** (1–2 distinct values per 5-minute bucket vs 55–133 in the
  preceding half hour) and **jumps to the official close at ~15:29–15:32**. This confirms the
  2026-09-10 addendum on all 5 sessions × 3 indices.
- **The options-implied index keeps moving** through the auction: 6–57 pts on Nifty, 9–56 on
  BankNifty, up to 325 on SENSEX within a single 5-minute bucket. The implied-vs-frozen gap reaches **62 bp on
  SENSEX expiry day (2026-09-10)** and 9–27 bp on Nifty.
- **Implied spot at 15:25 was closer to the official Nifty close than the frozen print on 3 of 4
  sessions**. Errors were still 18–68 pts, so it is a better reference, not a predictor.
- **After the close is published the options-implied index does not converge to it**: at 15:36 it
  sat −55 pts (09-07), −60 (09-10), +25 (09-04), −8 (09-09) from the official Nifty close. For
  non-expiring contracts derivatives price *their* view of the index, and the auction close is only
  one print. For DTE-0 contracts it is the settlement.

**Consequences.** (a) Anything spot-keyed after 15:15 must not use `underlying_ltp`. The parity-implied
spot is a **candidate** anchor for the fix Addendum 3 was waiting for. It is proven here as a
*mark*, not as a live ATM strike selector. Using it live requires two-sided quotes on at least
ATM ± 2 strikes every cycle, and a basis calibrated on the continuous window before 15:15.
It must not be wired in as settled. (b) Post-CAS, daily "close-to-close" index returns are auction-to-auction, and can sit
±25 bp from where the option market marks. Realized-vol estimates feeding an IV−RV screen inherit
that noise. (c) **No seller trade comes out of this.** The expiry-day parity/settlement gap (post-fix
arb, 15:35–15:40) needs DTE-0 sessions with poller coverage past 15:35. We have none: 09-08 stopped
15:17, 09-10 stopped 15:33. The four-day sample supports no inference.

### 7.2 Stock options through the cash auction

Live near-month (Sep-29) stock-option quotes, strikes within ±6 % of the future, ~3,500 instruments
across 210 underlyings. Snapshots were taken on 2026-09-11 (DTE 12, not an expiry week) and paired
per instrument against the 12:54 baseline (`cas_spread_compare.py`).

| snapshot | phase (cash, Category I) | two-sided | median ATM ± 2 % spread | p90 ATM | median OTM 2–6 % | paired ATM spread vs 12:54 | ATM wider than 12:54 |
|---|---|--:|--:|--:|--:|--:|--:|
| 12:54 | continuous | 99.97 % | 1.73 % | 3.99 % | 2.57 % | — | — |
| 15:05 | continuous | 99.94 % | 1.67 % | 3.81 % | 2.31 % | 0.96× | 45 % |
| 15:18 | halt / order entry I | 99.94 % | 1.87 % | 4.16 % | 2.63 % | 1.06× | 57 % |
| 15:24 | order entry II | 99.86 % | 1.97 % | 4.42 % | 2.87 % | 1.11× | 61 % |
| 15:31 | matching / close fixed | 99.74 % | 2.23 % | 4.93 % | 3.14 % | **1.28×** | 71 % |
| 15:37 | derivatives only | 99.74 % | 2.28 % | 5.50 % | 3.16 % | 1.26× | 71 % |

- **The book never goes dark.** Two-sided quotes stay above 99.7 % throughout, and the near-month
  **stock future keeps trading**: its LTP changed for 96–100 % of names in every interval from
  15:05 to 15:37. Market makers hedge the future, not the auctioning cash stock.
- **Spreads widen steadily through the auction and stay wide after it.** Pre-auction 15:05 is the
  tightest of the day (0.96× midday), 15:24 is 1.11×, and 15:31–15:37 is ~1.27×, the p90 rising
  3.8 % → 5.5 %.
- **Consequence for the §9 construct:** the backtest marks the entry and T-1 exit at the bhavcopy
  `close`, which post-CAS is formed in exactly this widened window. **Execute at ~15:00–15:10**,
  before the cash halt, rather than at the close. The cost difference is ~0.5 point of spread
  (≈ 0.25 % of premium per leg crossing) — small against a ≥ 9 % break-even, so this is an
  execution rule, not a threat to the result. It also turns the paper-trade step in §9.2 into an
  explicit comparison: fills at 15:05 vs quotes at 15:25.
- **One session, mid-cycle.** T-1 and expiry-week books (delivery-margin step-up) may behave
  differently. Re-take these snapshots on 2026-09-15 (entry) and 2026-09-28 (exit).

## 8. The forward paper record we already have (options-wall iron flies)

`wall_scan_results.duckdb`, 30 closed paper trades (2026-08-17 → 2026-09-10): **net −₹2,480**,
8 winners, mean −₹83, median −₹164. 23 of 30 exits are `regime_flip` (−₹4,701), mostly the
2026-09-09 SENSEX churn episode already audited in `OPTIONS_WALL_SENSEX_CHURN_AUDIT_2026-09-09.md`.
`manual` +₹298 (6), `tp` +₹1,923 (1). Two positions open. **n = 30 over 8 sessions supports no
inference** about the construct, in either direction. It is listed because it is the only
real-time option-selling record in the repo.

---

## 9. Verdict — the seller-only trade, and what it is not

### 9.1 The one construct that survived: late-cycle single-stock straddle selling

> **Sell the ATM straddle on F&O stocks whose ATM legs each traded ≥ 100 contracts that day, at the
> close ~10 sessions before the monthly expiry; buy it back at the close of the session before
> expiry. Never hold into expiry day.**

**The numbers that belong next to that sentence** (net of 2 % spread + fees, per-expiry basket
means, ~150 names/cycle, from §5.4):

| | observed exit | conservative exit |
|---|--:|--:|
| discovery 2016–22 | +11.2 % of premium (t 4.65) | +8.6 % (t 3.63) |
| confirmation 2023–26 (unread before today) | **+8.9 % (t 3.07)** | **+6.5 % (t 2.25)** |
| post-reform 2024-11 → 2026-08 | +7.4 % (t 1.49) | +5.0 % (t 1.01) |
| the ~40 most-traded names only, confirmation | +5.8 % (t 1.81) | +3.6 % (t 1.12) |

**Bottom line: it replicates across the broad liquid universe. After the reform it is positive but
not significant, and it is weakest in the names that are easiest to trade.**

Why a seller gets paid here, in order of evidence:
1. **It replicates on an unread window with unchanged code:** discovery t 6.05 → confirmation
   t 3.78 gross, t 2.90 net of a 2 % spread (all names), and t 2.0–2.3 under a seller-hostile exit
   valuation. No other seller construct in this repo has done that.
2. **Buyers lose everywhere in this segment.** Seller return is positive in every entry-offset row
   and every VRP bucket, in both windows — including names whose implied vol sits *below* trailing
   realized vol. There is no conditioning under which buying these straddles paid.
3. **Costs are not binding.** Break-even spread is 10.7–14.0 % against a live ATM median of 1.7 %.
   Every cash-equity battery in this repo died on the opposite fact.
4. **It is structural, not a fitted signal.** The only parameter is *when in the cycle*. The
   discovery sweep shows a monotone rise in per-session decay into expiry. The rank-IC tilt added
   nothing out of sample (P5 failed), so the book does not depend on a model.
5. **Plausible mechanism, not tested here:** single-stock options have never had weeklies, so
   the premium-selling flow that crowds index weeklies has no short-dated stock vehicle, and the
   late-cycle monthly is the only place to sell stock theta. Physical settlement also makes the last days operationally costly for both sides
   (delivery margin), which plausibly keeps sellers scarce exactly when theta is richest. Both
   explanations are hypotheses.

What it is **not**:
- **Not index-option selling.** Nifty weeklies (§6) and Nifty monthlies over the same windows
  (§2.2/§5.2) show no demonstrable seller edge. The market everyone sells is priced to break even.
- **Not dispersion.** The stock-minus-index gap is never significant, and the trade would need the
  opposite sign. Power 0.14.
- **Not a CAS trade.** CAS changes the index reference in the last 25 minutes and settlement
  mechanics. The construct exits at T-1 and never holds expiry day, so it is insulated. The first
  post-CAS cycle (Aug-2026, +29 %) is one observation.
- **Not safe.** Per-cycle skew is −1.1 to −1.4 in the confirmation window. The April-2025 tariff
  shock cost ~3 % of notional in a single cycle — about 7 average cycles of profit. A crash that
  gaps through a two-week hold is the risk you are paid for; it is not a tail you can avoid.
- **Not yet proven after the Nov-2024 reform.** Post-reform t 1.37, and weakest in the most
  liquid names. That is the open question, and forward trading answers it slowly (§9.3).

### 9.2 If the operator wants to take it forward — the order that respects this repo's gates

1. **Paper-trade it live, starting with the Sep-2026 cycle.** Expiry 2026-09-29. Sep 14 is a
   holiday (`core/database/utils/market_hours.py:67`), so **entry is the 2026-09-15 close and exit
   the 2026-09-28 close**. Record live bid/ask at both, per name. This measures the one thing the
   bhavcopy cannot: the actual crossing cost on T-10 and T-1. Execute ~15:05, before the cash halt,
   and log the 15:25 quotes alongside (§7.2: spreads are ~1.27× wider by 15:31). It also shows whether a screened, tradeable book earns anything at all post-reform
   (§5.4). That is an implementation check, not statistical confirmation.
2. **Write a proper RFA declaration + pre-registration** for the frozen construct: 10 before,
   T-1 exit, **entry legs ≥ 100 contracts** (ex-ante), live spread ≤ ~2.5 % at entry, equal
   notional, no VRP tilt, and no "most-liquid names only" shortcut (§5.4). Its Sharpe band
   must be defended independently. Honest anchors: 0.84 post-reform, 1.42 confirmation, 2.00
   discovery (in-sample). This study is prior exposure and must be disclosed as such.
3. **Know the power arithmetic before promising anything.** Forward-only at 12 cycles/year, S 1.0
   needs **76 cycles (~6 years)** for 0.80 power; S 1.5 needs 35 (~3 years). The historical
   replication in §5 is the strongest evidence this construct will ever get cheaply. Forward trading
   can falsify it fast (a few bad cycles) but can only confirm it slowly.
4. **Size to the April-2025 cycle, not to the mean.** A −3 % of notional cycle must be survivable at
   the chosen leverage, and margin must be computed through `NseMarginEngine` (with the expiry-week
   delivery-margin step-up) before any number of names or lots is chosen.

### 9.3 What remains open (not authorised, not started)

- Whether the post-reform weakening (§5.3) is regime or noise — only forward cycles can tell.
- Delta-hedging with the same-expiry future to cut the directional tail. This is a variant and
  would need its own pre-registration; it was deliberately not tried on the confirmation data.
- Results-season exposure: the 10-before window in Jan/Apr/Jul/Oct cycles often spans
  quarterly results. Not measured — the repo holds no earnings calendar.
- Expiry-day post-fix settlement arbitrage (15:35–15:40): needs full DTE-0 poller coverage first.

## 10. Reproduction

Scripts are copied to `scripts/research/options_seller_edge/` (outputs to
`data/scratch/options_seller_edge/`):

| script | produces | runtime |
|---|---|---|
| `spread_snapshot.py` | live stock-option bid/ask (market hours only) → §1, §7.2 | ~30 s |
| `build_stock_straddles.py` | trade-level straddles, 6 entry offsets × 126 expiries, stocks + NIFTY | ~40 s |
| `cycle_study.py START END [variant]` | §2 / §5 tables (the confirmation used `2023-01-01 2026-08-24 m10`) | ~10 s |
| `analyze_stock_straddles.py START END` | first-pass quintile tables (3 offsets) | ~10 s |
| `liquidity_diagnostics.py` | §5.4 ex-ante liquidity cuts × observed/conservative exit (post-confirmation) | ~15 s |
| `nifty_weekly.py` | §6 | ~10 min |
| `cas_pcp_forward.py` | §7.1 | ~1 min |

Inputs are read-only: `stock_options_bhavcopy.duckdb`, `options_bhavcopy.duckdb`,
`futures_bhavcopy.duckdb`, `wall_chain_snapshots/2026-09-0{4,7,8,9}.duckdb` + `2026-09-10`,
`candles/1d/{date}.duckdb`, `wall_scan_results.duckdb`. No store was written.
