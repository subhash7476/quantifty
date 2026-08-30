# MRLC — Mean Reversion Liquidity Capture: Construct Analysis & Testability Assessment

**Date:** 2026-08-29
**Status:** ANALYSIS. Parts I–IV are illustrative/educational — **every price in the
case study is invented**. Part V is evidentiary and reads the repo's research record.
**Data read:** repo documentation + a substrate census (equity 1m coverage bounds,
14 dates). No signal-level read, no P&L, no window spent.

---

# PART I — Why the combination is asymmetric

MRLC stacks four filters that each address a *different* failure mode. The asymmetry
is geometric, not predictive — and that distinction is the whole analysis.

## 1.1 The mechanism being exploited

A clean swing low that has held for 24–48 hours is not just a chart feature. It is a
**published location of resting sell-stop liquidity**. Every participant who entered
long above it, and every textbook that says "stop below support," has contributed
orders to the same price shelf.

A market maker or systematic desk needing to accumulate size faces an inventory
problem: they cannot lift a large offer stack without paying progressively worse
prices and signalling intent. The cheapest available counterparty is the stop pool —
because stops convert to **market sell orders**, and market sell orders fill at
whatever bid exists. Pushing price through the shelf manufactures a motivated,
price-insensitive seller.

The consequence that matters: **the low print of a sweep is an inventory-acquisition
print, not a valuation print.** It carries different information content from an
ordinary low. That premise is the entire edge; if it is false, everything below is
pattern-matching.

## 1.2 What each filter contributes

| Layer | Failure mode it addresses | Why it is not redundant |
|---|---|---|
| 25-day SMA divergence | Trading reversion into an intact trend | A *positioning* filter, not a valuation one — it locates where the marginal seller is likely exhausted and short interest crowded. Requiring the SMA be **flat or falling** deliberately excludes the sharp-pullback-in-uptrend case, which is a different trade |
| VPVR HVN / POC | Reverting toward a level nothing defends | The POC is where the most contracts changed hands — the largest resting inventory, and the price the widest set of participants treats as fair. Auction theory gives it a mechanical pull; a hand-drawn line has none |
| Liquidity sweep | Entering before supply is exhausted | Converts "support" from an opinion into a tested event. The sweep is the market *asking* whether real supply exists below |
| The reclaim (close back above) | Catching the knife | The answer to that question. Reclaim = no supply found. It is the only component that supplies a **falsifiable, timestamped trigger** |

## 1.3 Where the asymmetry actually comes from

The stop is anchored to the sweep low — which is, by construction, the **extreme print
of the move**. So the distance to invalidation is minimised at exactly the moment the
distance to the reversion targets (POC, then SMA) is maximised. The R:R is inflated by
the *geometry of the setup*, not by a forecast about direction.

That is a real structural property. It is also the source of the construct's central
trap, stated here rather than buried:

> **Nominal R:R is not expectancy.** The same geometry places the entry precisely
> where realised volatility just spiked. A stop 2 ticks under a wick that was made by
> an algorithm hunting stops is sitting in the one place an algorithm has already
> demonstrated it can reach. A 5:1 nominal R:R that wins 12% of the time is a losing
> system. The tight stop generates the headline number *and* the fragility, and they
> cannot be separated.

Everything in Part II exists to raise the hit rate enough that the geometry pays.

---

# PART II — Fake vs. real: binary checklist

Score at the close of the reclaim candle. **All ten confirmations must be TRUE.
Any single veto stands the trade down** — vetoes are not weighed against confirmations.

## 2.1 Confirmations — a valid bear trap (all must be YES)

| # | Criterion | Binary test |
|---|---|---|
| C1 | **Time below** the level ≤ 3 × 15m bars (≤ 45 min) | Count of closes below `support` before reclaim ≤ 3 |
| C2 | **Sweep volume spike** ≥ 3× the 20-bar median volume | `vol ≥ 3 × median(vol, 20)` |
| C3 | **Follow-through volume contracts** — the bar after the sweep is *lower* volume | `vol[0] < vol[1]` on the post-sweep bar |
| C4 | **Sweep candle CLV ≥ 0.6** — closes in the upper 40% of its own range | `(close − low) / (high − low) ≥ 0.6` |
| C5 | **Penetration depth ≤ 1.0 × ATR(14, 15m)** below the level | `(support − low) / ATR ≤ 1.0` |
| C6 | **Reclaim within 4 bars** of the first break | `bars_since_break ≤ 4` and `close > support` |
| C7 | **The break lands into an HVN**, not through a Low Volume Node | Bin volume at the sweep low ≥ 80th percentile of the profile |
| C8 | **No timestamped catalyst** in the sweep window | Manual: earnings, guidance, downgrade, regulatory, index deletion — none |
| C9 | **Broad tape not breaking in sympathy** | Index/sector has not broken its own equivalent 24–48h structure |
| C10 | **Divergence is at an extreme percentile**, not merely large | Current SMA divergence ≥ 90th pct of that name's trailing 2-year divergence |

C10 is the one most often skipped and it is load-bearing. A stock in secular decline is
*permanently* 15% below its 25-SMA. Absolute thresholds select for structurally broken
names — exactly the population you are trying to exclude. Percentile-rank the divergence.

## 2.2 Vetoes — a true structural breakdown (ANY one = stand down)

| # | Veto | Binary test | What it means |
|---|---|---|---|
| V1 | **≥ 3 consecutive 15m closes** below the level | count ≥ 3 | The level is being *accepted*, not probed. Acceptance is the definition of a real break |
| V2 | **Volume expanding on each successive breakdown bar** | `vol[0] > vol[1] > vol[2]` | Initiation, not exhaustion. Somebody is building a short, not covering |
| V3 | **Sweep candle CLV < 0.4** | closes in lower 40% of range | No absorption. Sellers finished the bar in control |
| V4 | **Penetration > 1.5 × ATR** | — | Too deep for a stop-run. Stop pools sit just below the level; price travelling well past it found real supply |
| V5 | **A named catalyst exists** | — | The move is information, not liquidity. Reversion logic does not apply to repricing |
| V6 | **The break travels through an LVN** | bin volume < 20th pct | Price accelerating through a volume vacuum. Nothing to catch it — the literal definition of a falling knife |
| V7 | **Lower highs on the reclaim attempt** | successive attempts fail lower | Supply is stepping down. The reclaim is failing in real time |
| V8 | **Daily 25-SMA slope steepening downward** | `slope[0] < slope[5]` | Decline is accelerating. "Flat or falling" was the entry condition; *accelerating* is disqualifying |

**The single most reliable discriminator, if you keep only one:** the **volume signature
of the bar after the sweep** (C3 / V2). Stop-runs are volume events that exhaust — the
pool is finite and empties. Real breakdowns are volume events that *recruit* — new
sellers arrive as the break confirms. One contracts, one expands. It is the cleanest
binary in the list, and unlike CLV it cannot be produced by a single wick.

---

# PART III — Simulated case study (all prices INVENTED)

**Ticker XYZ.** Illustrative arithmetic only — not a measurement, not a backtest.

## 3.1 Setup

**Daily / macro**
- 25-day SMA = **$118.00**, slope over trailing 5 sessions **−0.4%/day, flattening** (falling, not accelerating — V8 clear)
- Current price **$99.20** → divergence = (99.20 − 118.00) / 118.00 = **−15.93%** ✓ (>15% large-cap threshold)
- Divergence percentile vs trailing 2 years: **94th** ✓ (C10)

**VPVR (500 × 15m bars ≈ 5 sessions, 50 bins)**
- **POC = $104.50**; HVN shelf spans **$102.00–$106.00** (bins ≥ 80th pct)
- The shelf sits *above* current price and overlaps local action ✓
- Bin at $96.50–$97.00 is 86th percentile → the sweep lands **into** an HVN ✓ (C7 ✓, V6 clear)

**15-minute structure**
- Swing low **$98.40**, formed 31 hours ago, tested 3 times, unbroken ✓
- ATR(14, 15m) = **$1.45**

## 3.2 The sweep and trigger

| Bar | Event | O / H / L / C | Volume | Checks |
|---|---|---|---|---|
| T−1 | Approach | 98.90 / 99.10 / 98.55 / 98.62 | 1.0× | — |
| **T** | **Sweep** | 98.60 / 98.65 / **96.85** / 98.10 | **4.2×** median | C2 ✓ · CLV = (98.10−96.85)/(98.65−96.85) = **0.69** ✓ C4 · penetration = (98.40−96.85)/1.45 = **1.07 ATR** ⚠ |
| T+1 | **Reclaim** | 98.12 / 99.05 / 98.05 / **98.95** | **0.7×** vs T | C3 ✓ · close **> 98.40** ✓ C6 (1 bar) · C1 ✓ (1 close below) |

**Note the marginal check.** Penetration 1.07 ATR breaches the C5 threshold of 1.00 —
on a strict reading this setup is a **borderline reject**. It is carried forward here
to make the arithmetic concrete, and flagged rather than quietly rounded down. A real
rule set does not get to relax a threshold because the rest of the picture is pretty;
that is precisely how a checklist decays into a narrative.

## 3.3 Levels and R:R

| Level | Price | Derivation |
|---|---:|---|
| **Entry** | **$98.95** | Close of the reclaim candle T+1 |
| **Stop** | **$96.80** | 3 ticks (tick = $0.05) below sweep low $96.85 |
| **Risk (1R)** | **$2.15** | 98.95 − 96.80 (2.17% of entry) |
| **TP1** (50%) | **$104.50** | VPVR POC |
| **TP2** (50%) | **$114.50** | 25-day SMA, drifted down from 118.00 over the ~6 sessions to target |

- **R:R to TP1** = (104.50 − 98.95) / 2.15 = **2.58 : 1**
- **R:R to TP2** = (114.50 − 98.95) / 2.15 = **7.23 : 1**
- **Blended (50/50)** = (2.58 + 7.23) / 2 = **4.91 : 1**

TP2 uses the *projected* SMA at the time of the tag, not today's 118.00. Using a falling
SMA's current value as a fixed target systematically overstates reward — a small point
that inflates published R:R across this entire strategy family.

## 3.4 Position sizing and P&L

Account $100,000, risk 1% = $1,000. Shares = 1,000 / 2.15 = **465**.
Notional at entry = 465 × 98.95 = **$46,012**.

| Outcome | Fill | P&L | In R |
|---|---|---:|---:|
| Stopped out | 465 @ 96.80 | −$1,000 | **−1.00R** |
| TP1 hit (232 sh) | 232 @ 104.50 | +$1,288 | +1.29R |
| Then BE stop (233 sh) | 233 @ 98.95 | $0 | 0.00R |
| Then TP2 (233 sh) | 233 @ 114.50 | +$3,623 | +3.62R |
| **Full run** | | **+$4,911** | **+4.91R** |

**Three-outcome expectancy** (probabilities illustrative, not measured):

| Outcome | Prob | R | Contribution |
|---|---:|---:|---:|
| Stopped before TP1 | 45% | −1.00 | −0.450 |
| TP1 → BE stop | 35% | +1.29 | +0.452 |
| TP1 → TP2 | 20% | +4.91 | +0.982 |
| **Expectancy** | | | **+0.98R** |

**Breakeven win rate** on the full-run R:R = 1 / (1 + 4.91) = **16.9%**.

## 3.5 Cost drag — and why it is deceptive here

Round-trip cost as a fraction of *risk* is what matters, not as a fraction of notional:

- Notional $46,012. Indian **delivery** equity STT is **0.1% per leg, both legs** →
  ~$92 on STT alone, plus brokerage/exchange/GST/stamp.
- $92 / $1,000 risk = **0.09R** — which looks trivially small.

It looks small **only because the stop is 2.17% wide.** Cost in R-terms scales as
`cost% / stop%`. Halve the stop distance to improve the headline R:R and you double the
cost drag in R. The two levers are coupled, and every published version of this strategy
quotes the R:R while omitting the coupling. At a 0.8% stop the same cost becomes ~0.25R —
and the multi-day hold (TP2 at the daily SMA) is what forces delivery treatment rather
than intraday rates in the first place.

---

# PART IV — Pine Script scanner: logic outline

**The critical implementation fact:** Pine Script has **no native VPVR series.**
TradingView's built-in Volume Profile is a closed indicator; its POC and value-area
levels are not exposed to Pine as data. A scanner must **bin volume into price buckets
manually** using arrays over an explicit lookback. Every published "VPVR scanner" that
skips this step is reading something else.

```pine
//@version=5
indicator("MRLC Scanner", overlay = true, max_bars_back = 1000)

// ══ INPUTS ═══════════════════════════════════════════════════════
smaLen         = input.int(25,     "Daily SMA length")
divThreshold   = input.float(15.0, "Min % below SMA")   // 30.0 for high-beta / crypto
vpvrLookback   = input.int(500,    "Profile lookback (15m bars)")
vpvrBins       = input.int(50,     "Profile bins")
supportLook    = input.int(96,     "Support search (96 = 24h of 15m)")
pivotL         = input.int(3), pivotR = input.int(3)
sweepVolMult   = input.float(3.0,  "Sweep volume multiple")
reclaimMaxBars = input.int(4,      "Max bars break -> reclaim")
maxPenetrATR   = input.float(1.0,  "Max penetration (ATR)")

// ══ 1. MACRO GATE (daily, causal) ════════════════════════════════
// lookahead_off is MANDATORY: with it on, the scanner sees the daily
// close before the day ends and the entire backtest becomes fiction.
dSMA   = request.security(syminfo.tickerid, "D", ta.sma(close, smaLen),
                          lookahead = barmerge.lookahead_off)
dSMA5  = request.security(syminfo.tickerid, "D", ta.sma(close, smaLen)[5],
                          lookahead = barmerge.lookahead_off)
dSMA10 = request.security(syminfo.tickerid, "D", ta.sma(close, smaLen)[10],
                          lookahead = barmerge.lookahead_off)

divergence      = (close - dSMA) / dSMA * 100.0
slopeNow        = dSMA  - dSMA5
slopePrev       = dSMA5 - dSMA10
flatOrFalling   = slopeNow <= 0
notAccelerating = slopeNow >= slopePrev          // VETO V8 if false
macroGate       = divergence <= -divThreshold and flatOrFalling and notAccelerating

// ══ 2. VPVR — MANUAL BINNING (no native series exists) ═══════════
// Gate this block on macroGate: it is O(lookback x bins) per bar and
// will exhaust Pine's execution budget if it runs unconditionally.
profHi = ta.highest(high, vpvrLookback)
profLo = ta.lowest(low,  vpvrLookback)
binW   = (profHi - profLo) / vpvrBins

var profile = array.new_float(vpvrBins, 0.0)
if macroGate and barstate.isconfirmed
    array.fill(profile, 0.0)
    for i = 0 to vpvrLookback - 1
        loBin = math.max(0,            math.floor((low[i]  - profLo) / binW))
        hiBin = math.min(vpvrBins - 1, math.floor((high[i] - profLo) / binW))
        // spread each bar's volume evenly across the bins its range spans
        per   = volume[i] / (hiBin - loBin + 1)
        for b = loBin to hiBin
            array.set(profile, b, array.get(profile, b) + per)

pocBin   = array.indexof(profile, array.max(profile))
pocPrice = profLo + (pocBin + 0.5) * binW
maxBinV  = array.max(profile)

binAt(p) => array.get(profile,
              math.max(0, math.min(vpvrBins - 1, math.floor((p - profLo) / binW))))

hvnNear = pocPrice > close and (pocPrice - close) / close < 0.12

// ══ 3. SUPPORT LEVEL ═════════════════════════════════════════════
// NOTE: pivotlow(3,3) confirms 3 bars LATE. The level is only known 3
// bars after it forms. Causally fine — but never plot or evaluate it
// as though it were known at the pivot bar.
pl         = ta.pivotlow(low, pivotL, pivotR)
supLevel   = ta.valuewhen(not na(pl), pl, 0)
supBarsAgo = ta.barssince(not na(pl))
// require >= 2 touches within tolerance -> the level is "obvious" to retail
touches    = math.sum(low <= supLevel * 1.002 and low >= supLevel * 0.998 ? 1 : 0, supportLook)
supValid   = supBarsAgo <= supportLook and touches >= 2

// ══ 4. SWEEP DETECTION (stateful) ════════════════════════════════
atr       = ta.atr(14)
brokeDown = low < supLevel and close < supLevel
volSpike  = volume >= sweepVolMult * ta.median(volume, 20)
penetr    = (supLevel - low) / atr
clv       = (close - low) / math.max(high - low, syminfo.mintick)

var float sweepLow    = na
var int   barsSinceSw = na
var int   closesBelow = 0

if brokeDown and volSpike and penetr <= maxPenetrATR and clv >= 0.6 and na(sweepLow)
    sweepLow    := low
    barsSinceSw := 0
    closesBelow := 1
else if not na(sweepLow)
    barsSinceSw += 1
    sweepLow    := math.min(sweepLow, low)
    closesBelow += close < supLevel ? 1 : 0

// ══ 5. VETOES ════════════════════════════════════════════════════
vetoAccept = closesBelow >= 3                                                  // V1
vetoVolExp = brokeDown and volume > volume[1] and volume[1] > volume[2]        // V2
vetoCLV    = brokeDown and clv < 0.4                                           // V3
vetoDeep   = not na(sweepLow) and (supLevel - sweepLow) / atr > 1.5            // V4
vetoLVN    = not na(sweepLow) and binAt(sweepLow) < 0.20 * maxBinV             // V6
vetoSlope  = not notAccelerating                                               // V8
anyVeto    = vetoAccept or vetoVolExp or vetoCLV or vetoDeep or vetoLVN or vetoSlope
// V5 (catalyst) and C9 (broad tape) are NOT codable here — see note 5

// ══ 6. TRIGGER — confirmed bars only, or it repaints ═════════════
volContract = volume < volume[1]                                               // C3
reclaim = barstate.isconfirmed and not na(sweepLow)
          and barsSinceSw >= 1 and barsSinceSw <= reclaimMaxBars
          and close > supLevel and volContract

signal = macroGate and hvnNear and supValid and reclaim and not anyVeto

// ══ 7. LEVELS + SANITY GUARD ═════════════════════════════════════
entry = close
stop  = sweepLow - 3 * syminfo.mintick
tp1   = pocPrice
tp2   = dSMA
rr1   = (tp1 - entry) / (entry - stop)
// reject degenerate geometry: POC already passed, or a stop too tight to be real
valid = rr1 >= 1.5 and (entry - stop) / entry >= 0.004

alertcondition(signal and valid, "MRLC setup", "MRLC reclaim confirmed")

if signal or barsSinceSw > reclaimMaxBars or anyVeto
    sweepLow := na
    barsSinceSw := na
    closesBelow := 0
```

### Implementation notes that change results

1. **`barstate.isconfirmed` is not optional.** Without it the reclaim evaluates intrabar
   and the signal repaints — backtest results become unreproducible.
2. **`lookahead_off` on every `request.security`.** With lookahead on, the daily SMA leaks
   the session's own close into intraday bars. This one flag is the most common source of
   fictitious performance in published Pine strategies.
3. **The intraday 25-SMA is the *prior* completed day's.** That is correct and causal. Do
   not "fix" it.
4. **The profile block is expensive.** 500 × 50 = 25,000 array writes per evaluation. Gate
   it on `macroGate`, reduce the lookback, or maintain the profile incrementally (add the
   new bar, subtract the expiring one) rather than rebuilding.
5. **C8 (catalyst) and C9 (broad tape) are not expressible in Pine.** C8 needs a news feed;
   C9 needs a correlated-symbol structural test. A scanner that omits them is **not**
   implementing this strategy — it implements the codable two-thirds, and the two dropped
   filters are exactly the ones that separate traps from repricings. Treat scanner output
   as a candidate list for manual adjudication, never as a signal.
6. **Multi-symbol screening.** Pine evaluates one symbol per chart. Use the v6 Pine Screener
   or one alert per watchlist symbol; `request.security` across a large universe inside a
   single script will exceed the call limit.

---

# PART V — Has this been tested here? Can it be?

**Short answer: no, not as specified — and it cannot be tested here as specified.
The vehicle that supports the measurement cannot support the construct, and the vehicle
that supports the construct cannot support the measurement. One component — the
sweep/reclaim kernel — is testable, and is already scoped into an authorized map.**

## 5.1 Prior work — closest relatives (none is MRLC)

| Prior work | Relation to MRLC | Outcome |
|---|---|---|
| **F-RANGE "failed breakout"** (`STAGE_A_DISCOVERY_LAB_DESIGN.md` §16) | **Direct analogue of the sweep/reclaim kernel.** Mechanism recorded as *"liquidity provision around stop clusters"* — the same thesis | **Genuinely unmeasured.** Survived Gate 0 (2026-08-29) and is one of only two families scoped into the first declared map (D-A7) |
| **Nifty/BankNifty ratio mean reversion** | Mean-reversion thesis, index intraday | **Falsified.** Not cointegrated (trace 14.42 < 15.49), half-life 166 days, bootstrap p = 0.354; **all 27 intraday parameter combos negative** — the ratio *trends* (+1.10/+1.17 slopes) |
| **ISD F4** — equity overnight gap fade | Intraday reversion on cash equity | IC −0.0289, t −6.09 — **the strongest cross-sectional effect this repo has ever measured** — and **killed by the cost gate** |
| **A** — index intraday opening drive | Index intraday, EOD-flat, futures vehicle | TRAIN PASS (+1.27 bp net) → **HOLDOUT FAIL** (−0.22 bp). Retired |
| **PSB-1 C1** — weekly reversal | Reversal, cross-sectional equity | Gross +1.1% → **net −16.8%** on delivery STT |

So: the *ingredients* have been tested and mostly killed; **the MRLC conjunction has not.**

## 5.2 The vehicle matrix — five vehicles, five different blocking reasons

| Vehicle | VPVR / POC computable? | 15m sweep+reclaim testable? | Cost lane | Blocking reason |
|---|---|---|---|---|
| Nifty / BankNifty **cash index** | **NO** — `volume = 0` in every era (verified 2015-06-10, 2019-06-10, 2024-06-10, 2026-08-20; both indices, 375 bars each) | Yes — 1m from 2012 | ~4.5 bp/trip via futures | **TP1 is *defined as* the POC.** No volume, no POC. The construct here is not weak, it is *incomplete* |
| **Nifty futures** | No 1m history at any date | **No** | ~4.5 bp/trip | No intraday substrate exists in this repo |
| **Cash equity, intraday-flat** | Yes — 1m volume present from 2023-01-02 | Yes — 903 certified sessions, ~195–200 names | **≥ 8.6 bp/session floor** | ISD quadrant **closed by arithmetic**: floor 8.6 bp vs best-ever gross +6.0, under assumptions more generous than anyone would defend |
| **Cash equity, multi-day** ← *what MRLC actually specifies* | Yes | Yes | **Delivery STT 0.1% per leg, BOTH legs** | The PSB wall — ~40 bp round trip. Documented three times |
| **SSF (single-stock futures)** | Daily bhavcopy only | **No** — Upstox cannot backfill expired contracts | Favourable (no delivery STT) | The 15-minute trigger is **unbacktestable**: no intraday history at any date |

### The wall MRLC actually hits — cite it correctly

MRLC's TP2 is the **daily** 25-SMA, so the position holds overnight. It is therefore
**not** in the ISD "cash-equity intraday, **EOD-flat**" quadrant, and the ISD closure
rule does **not** apply to it. It lands instead in the **PSB delivery-STT wall**: 0.1%
STT per leg on *both* legs, ≈ 40 bp round trip, against a TP1 (the POC) that in the case
study sits 5.6% away and in typical setups sits 1–3% away. At a 1.5% TP1 the STT alone
consumes ~27% of the gross move before any other cost.

Escaping to SSF fixes the fee structure — and removes the intraday data needed to detect
the sweep at all. **That is the trap: the fee-viable vehicle has no 15m history, and the
15m-observable vehicle has fatal fees.**

## 5.3 The demonstrability arithmetic — why "more setups" does not help

Gate 0's governing result (`STAGE_A_GATE0_REPORT.md` §1), family-invariant:

> `ncp = S_ann · √T` — **cadence cancels.** The Sharpe required for power 0.80 depends
> only on the gate's **calendar length**, not on horizon, event density, or how hard you
> condition. *"Trading a 15-minute event eight times a day instead of once at the close
> buys exactly nothing."*

This is why I did **not** run a census of qualifying MRLC setups. Counting them answers a
non-binding question: a rare-event filter cuts trade count without changing the required
Sharpe. Presenting a setup count as "the feasibility test" would contradict the very
arithmetic that settles the case.

What *is* binding, on the only vehicle where VPVR is computable (equity 1m, 2023-01-02 →
present, ~3.6 years): √T ≈ 1.9, putting the required net annualised Sharpe in the same
1.2–1.3 band Gate 0 computes for windows of this length — against a **measured net
S_ann of 0.20** on this substrate, and a most-generous-ever ratified ceiling of 2.15 gross.

## 5.4 What IS testable — the one open door

Strip MRLC to its kernel and it becomes measurable:

> **Failed breakdown → reclaim → reversion to a reference level**, on the **index**, as an
> **F-RANGE cell** in the Stage A map authorized 2026-08-29 — with two amputations:
>
> 1. **No VPVR.** Index volume is zero. Substitute a volume-free TP1 reference: session
>    TWAP (what the DayType pipeline already uses), prior-day close, the opening print, or
>    the range midpoint.
> 2. **No multi-day hold.** Cost forces an intraday horizon; Gate 0 prices the
>    failed-breakout cell at a **60-minute** horizon, not a multi-day SMA tag.

That is roughly **one-third of the blueprint** — the trigger mechanism, without the macro
filter's horizon or the profile-based target.

**Two caveats, so this does not read as encouragement.** Gate 0 rates F-RANGE
failed-breakout **PLAUSIBLE** at a required **gross S_ann of 2.02**, against a 2.15
ceiling that is itself the most generous figure the operator has ever ratified — and
against 0.20 measured. Gate 0's own §6.5: *"the most probable outcome of the two-family
scan is two more recorded nulls."* **PLAUSIBLE means "not provably infeasible," nothing
more.**

## 5.5 Verdict

| Question | Answer |
|---|---|
| Tested before? | **No** — not as a conjunction. Four of its five ingredients were tested separately; three were killed and one (F-RANGE) is unmeasured |
| Testable as specified? | **No.** No vehicle supports VPVR + 15m trigger + multi-day hold + a survivable cost lane simultaneously |
| Testable in part? | **Yes** — the sweep/reclaim kernel, index-level, VPVR-free, intraday-horizon, as an F-RANGE cell in an already-authorized map |
| Recommended next step | Nothing new to authorize. F-RANGE is **already** in the Stage A first map (D-A7). MRLC's contribution is a **sharper causal definition** of that cell — Part II's C1–C10 / V1–V8 translate directly into cell definitions, and the design explicitly flags that cell as *"needs a careful causal definition (failure is only known after the fact)"* |

**The honest framing:** MRLC is not a new research direction for this repo. It is a
well-specified version of a cell already scoped for measurement, wrapped in two components
(VPVR, multi-day hold) that this substrate cannot carry.

## 5.6 Documentation defect found in passing

`CLAUDE.md` → Data Layout states equity 1m coverage is **"2024-10-17 to present."**
**This is stale.** Measured this session: `2023-01-02` carries 70,459 equity rows across
~195 symbols, and every probe from 2023-01-02 onward is populated (2022-12-12 and earlier
carry index-only — 2 symbols, 0 equity rows). `ISD_PHASE1_SUBSTRATE_CERTIFICATION.md`
independently certifies **903 sessions, 2023-01-02 → 2026-08-24**.

The stated span understates available equity 1m history by **~21 months**. Worth
correcting — a feasibility assessment trusting that line would have concluded the
VPVR-bearing window was ~1 year rather than ~3.6.

---

## Record

- No signal-level read. No window spent. No P&L computed.
- Substrate census: equity 1m row counts on 14 dates (bounding coverage only).
- Sources: `STAGE_A_GATE0_REPORT.md`, `STAGE_A_DISCOVERY_LAB_DESIGN.md` §14/§16,
  `ISD_PROGRAM_REASSESSMENT.md` §3/§5, `A_HOLDOUT_CLOSURE.md`,
  `A_CONSTRUCT_DEFINITION.md`, `NIFTY_BANKNIFTY_PAIR_RESEARCH.md`,
  `ISD_PHASE1_SUBSTRATE_CERTIFICATION.md`, `CLAUDE.md`.
- Parts I–IV are illustrative. Every price in Part III is invented.
