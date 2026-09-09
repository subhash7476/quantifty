# CAS Impact Assessment — SEBI Closing Auction Session vs. this platform

**Date:** 2026-08-27
**Status:** Research memo (not a gated artifact). Numbers in §3 are ad-hoc measurements from our own 1m store, method stated inline; regulatory facts sourced from SEBI/NSE/broker publications listed in §7.

---

## 1. The rule

SEBI circular **HO/47/11/11(3)2025-MRD-POD2/I/2765/2026, dated 2026-01-16**, introduced a **Closing Auction Session (CAS)** in the equity cash segment, **operative 2026-08-03** (pre-open auction alignment follows separately from 2026-09-07). Phase 1 covers only **Category I stocks = stocks with F&O contracts** on NSE and BSE; all other stocks (Category II) keep the old last-30-min VWAP close and trade continuously to 15:30.

### Session timeline (Category I stocks), effective 2026-08-03

| Window | What happens |
|---|---|
| 09:15–15:15 | Continuous trading (was 09:15–15:30) |
| 15:15–15:20 | Transition/halt. Reference price = last-30-min VWAP. Carried-forward orders except stop-loss, iceberg, and orders >3% from reference |
| 15:20–15:25 | Order Entry I — market + limit orders; exchange continuously disseminates **indicative equilibrium price, buy/sell quantities, imbalance, and indicative index value** |
| 15:25–15:28/15:30 | Order Entry II — **limit orders only**; random close between 15:28 and 15:30 |
| 15:30–15:35 | Matching; **equilibrium price becomes the official closing price** (max executable quantity; ties → smaller imbalance → closest to reference) |

### Derivatives segment

- **F&O trading extended to 15:40** (from 15:30) — a 5–10 min buffer *after* the cash equilibrium is fixed.
- Index options/futures have **no auction of their own**; they simply keep trading to 15:40.
- Broker MIS auto-square-off times moved earlier for CAS stocks (Zerodha: ~15:12 for Category I cash; F&O contracts ~15:26).
- Stop-loss/IOC/iceberg orders are rejected during CAS.

### Settlement consequences

- A CAS stock's official close = auction equilibrium price → **stock F&O expiry settlement flows from the CAS price**, not VWAP.
- Index closing values (Nifty, BankNifty, Sensex, Bankex) are computed from constituent closes; since essentially all index heavyweights are F&O stocks, **index F&O expiry settlement now derives from constituent CAS equilibrium prices**, published ~15:30–15:35 — while the index derivatives themselves trade until 15:40.

### Expiry-day map (current regime, for reference)

- NSE: **Nifty weekly Tuesday**; all NSE monthlies (incl. **BankNifty — monthly only**, weeklies discontinued Nov-2024) last Tuesday.
- BSE: **Sensex weekly Thursday**; Sensex/Bankex monthlies last Thursday (**Bankex monthly only**).

---

## 2. What happened in the first month (live evidence)

1. **Aug 3 (Mon, day 1) and Aug 4 (Tue, first Nifty weekly expiry under CAS):** Nifty moved **+200.8 and +152.0 points** in the 15:14→15:29 window (our data, §3) — both beyond the *maximum* such move in the previous 141 sessions of 2026 (100.6). BankNifty: **+567 and +414** vs pre-CAS max 130. Press reported the Aug 4 auction surge "caught several market participants off guard."
2. **Aug 6 (Thu, first Sensex weekly expiry under CAS):** passed "largely without disruption" — close 0.2% above the 15:15 level (Bloomberg).
3. **Aug 13 (Thu, Sensex weekly expiry): the auction was allegedly gamed.** SEBI surveillance found three indicative-Sensex spikes (+362 pts in 2s at 15:20:41; +133 pts in 12s at 15:24; +405 pts in 28s at 15:25:49). Per SEBI's **46-page ex-parte interim order of 2026-08-19**:
   - **Copthall Mauritius Investment (JPMorgan-linked)** placed ~₹66.58 Cr of buys at the CAS price band across Sensex constituents (99.91% of buy orders in the first spike) while holding synthetic-long expiring option positions (long calls / short puts at 77,500–78,500). Cash loss ~₹57 lakh; derivatives wrongful gain ~₹2.96 Cr. Settlement printed 78,080 vs ~77,840 estimated fair.
   - **Mansi Share and Stock Broking** placed ~₹145.65 Cr of sells 1.5–3% below reference in RIL/SBI/L&T/ICICI/Infosys to depress the indicative index, exited puts at favorable prices, then **cancelled ₹143.44 Cr of sells in 3 seconds** (15:26:02–05), popping the indicative +233 pts. Wrongful gain ~₹71.65 lakh.
   - Both barred; ~₹3.68 Cr impounded. SEBI noted CAS *improved* detection: cross-constituent manipulation leaves "a very visible footprint."
4. **After the Aug 19 order, auction-window moves normalized** to roughly pre-CAS magnitudes (§3). The first monthly expiry under CAS (Aug 25) brought physically-settled stock F&O into the mechanism; press flagged thin-liquidity risk but no blow-up was reported.

---

## 3. Our own measurement — auction-window index moves

Method: 1m store (`data/market_data/nse/candles/1m/`), close of the 15:14 bar → close of the last bar (15:29).

> **Corrected 2026-08-27 (see `CAS_ADAPTATION_REGISTER.md` §0).** An earlier version of this line claimed the post-CAS 15:15–15:29 bars "reflect the disseminated indicative/auction values." **That mechanism claim is wrong** — we hold no indicative-index data whatsoever. Those bars are *aggregator carry-forward* (`O=H=L=C`, `volume=0`), and the entire move materializes as one discrete auction print at 15:28 or 15:29.
>
> **The table below stands.** Pre-CAS the 15:29 close sat ~4 bp from the official close (measured in `A_INDEX_SLICE_CERTIFICATION.md`); post-CAS the 15:29 close **is** the auction close (verified against bhavcopy, 92–95% exact). So "15:14 close → session close" measures the same statistic on both sides of the boundary. What changed is the decomposition: fifteen minutes of continuous drift became a single gap.

Baseline (2026-01-01 → 2026-07-31, 141 sessions): Nifty mean |move| **20.1 pts**, max **100.6**. BankNifty (Jun–Jul, 44 sessions): mean **47**, max **130**.

| Date | Day | Nifty 15:14→15:29 | BankNifty | Note |
|---|---|---:|---:|---|
| 2026-08-03 | Mon | **+200.8** | **+567** | CAS day 1 |
| 2026-08-04 | Tue | **+152.0** | **+414** | Nifty weekly expiry #1 |
| 2026-08-05 | Wed | +54.5 | +109 | |
| 2026-08-06 | Thu | +7.5 | +49 | Sensex expiry #1 |
| 2026-08-07 | Fri | +16.1 | −36 | |
| 2026-08-10 | Mon | +23.8 | +81 | |
| 2026-08-11 | Tue | +21.7 | +78 | Nifty expiry #2 |
| 2026-08-12 | Wed | +74.2 | +114 | |
| 2026-08-13 | Thu | +43.1 | +44 | Sensex expiry — manipulation day (BSE side) |
| 2026-08-14 | Fri | +11.5 | +32 | |
| 2026-08-17 | Mon | −51.9 | −214 | |
| 2026-08-18 | Tue | −10.9 | −52 | Nifty expiry #3 |
| 2026-08-19 | Wed | +29.8 | +83 | SEBI interim order issued |
| 2026-08-20 | Thu | +19.5 | +47 | |
| 2026-08-21 | Fri | +17.2 | +114 | |

Reading: a violent two-day repricing at launch, decay toward baseline within a week, and post-crackdown behavior statistically indistinguishable from the old regime at this sample size. The exploitable-looking variance was front-loaded — and the two entities that harvested it are barred.

---

## 4. Impact on this platform

### 4.1 NiftyShield v1 (PAPER)

- **Exit at 15:15 is now a feature.** The strategy is flat exactly when continuous cash trading ends and the auction regime begins. Derivatives trade to 15:40, so the 15:15 exit executes well inside continuous F&O liquidity. It is never exposed to auction-window settlement games.
- **`expiry_days_min: 2`** means it never holds same-day-expiring options — no exposure to CAS-derived settlement at all.
- Watch items: (a) broker MIS square-off shifts don't apply (paper/NRML), but any future LIVE promotion must re-verify square-off timings; (b) afternoon flow character in 13:00–15:15 may drift as closing flows migrate into the auction — the paper record straddling 2026-08-03 should be split pre/post when evaluated; (c) chain poller stops ~15:30 — see 4.3.

### 4.2 A / ISD index-intraday track (current branch) — **pre-registration disclosure required**

`A_CONSTRUCT_DEFINITION.md` pins the exit at the **15:29 bar close, EOD-flat**. As of 2026-08-03 that bar is no longer continuous trade: for the index it is the auction-indicative value; the official close fixes at 15:30–15:35; Nifty futures (the stated instrument) trade to 15:40. The entire backtest history models the old exit regime; live-forward, the exit sits inside a structurally different (and, in week 1, violently different) window. Options: move the pinned exit to the 15:14 bar close (last continuous-regime print), or keep 15:29 with a disclosed regime-break note and a widened exit-cost lane. Either way the pre-registration must state it — this is exactly the kind of silent assumption the freeze is meant to surface.

### 4.3 Ops / infrastructure

- `core/database/utils/market_hours.py: MARKET_CLOSE = time(15, 30)` and `market_session.py: SESSION_END = time(15, 30)` (+ `scripts/ingest_reference_1m.py`) encode the pre-CAS close. For the F&O segment the session now ends **15:40**; for CAS cash stocks continuous ends **15:15**. Anything gating "is market open" for options polling, live marks, or EOD triggers off these constants stops 10 minutes early for F&O.
- **NiftyShield chain poller stops ~15:30** (archive max timestamps ≈15:30:06): we capture none of the 15:30–15:40 F&O window — including the post-settlement-fix window on expiry days. Extending to 15:40 is a one-line window change that starts building the only dataset a post-15:15 construct could ever be gated on. **Sharpened 2026-08-27:** the gap is worse than "we stop at 15:30" — everything we *do* record from 15:15 onward for F&O symbols is manufactured carry-forward, not observed market data (`CAS_ADAPTATION_REGISTER.md` §0, A1).
- **1m ingest is lagging:** no `2026-08-25.duckdb` / `2026-08-26.duckdb` as of 2026-08-27 (files end 2026-08-24). Worth checking the EOD chain before it becomes a hole.
- India VIX / any EOD marks read at 15:29–15:30 now precede the F&O close by 10 minutes — a labeling issue, not a correctness bug, but should be noted wherever "close" marks feed reports.

---

## 5. Can we farm trades after 15:15?

### The window, precisely

On an expiry day the sequence is now: 15:15 cash continuous ends → 15:20–15:30 auction order entry **with live indicative index + per-stock imbalance published** while expiring index options still trade → ~15:30–15:35 equilibrium fixes (settlement value effectively known) → **options continue trading to 15:40 after settlement is determined**.

### Candidate edges, honestly assessed

| Edge | Mechanism | Verdict |
|---|---|---|
| **Indicative-vs-option convergence (15:20–15:30)** | Trade expiring options against the disseminated indicative index when premiums lag it | Real in principle, but the indicative is *manipulable* (Aug 13: ±400-pt spikes in seconds) — fading a spike risks the spike being real; chasing it risks holding the manipulator's bag. Needs the exchange auction feed (indicative EP + imbalance), which we do not ingest and Upstox may not carry |
| **Post-fix intrinsic arb (15:35–15:40)** | Once constituent equilibria publish, settlement is known; buy expiring options below / sell above intrinsic | The cleanest structural idea — near-deterministic *if* mispricings exist. But every arb desk sees the same public number; expect ~zero residual after spreads. Zero data exists to test it (nobody's, 3.5 weeks old; ours stops at 15:30) |
| **Auction-imbalance prediction** | Predict close direction from published imbalance, US MOC-imbalance style | Legitimate strategy class abroad; needs the imbalance feed + months of history. Does not exist yet in India for anyone |
| **Pushing the auction itself** | Cash orders in constituents to move settlement toward a derivatives book | **This is the Copthall/Mansi trade. It is market manipulation, SEBI demonstrated same-month detection and barring, and it is off the table — not discussed further** |
| **Pre-15:15 positioning for auction drift** | Hold into the auction window on expiry days expecting systematic drift | Our §3 table: the drift was a 2-day launch artifact. Post-Aug-19, n=2 expiries show −10.9/+21.7 — inside baseline noise |

### Data reality

- **NSE (Nifty/BankNifty):** we hold index 1m to 15:29 (indicative values post-Aug-3) and EOD options bhavcopy. **Zero intraday options data after 15:15 on any expiry day** — the wall-poller archive (Aug 14/17/19/20) misses every expiry, and all pollers stop at 15:30.
- **BSE (Sensex/Bankex):** **zero data in-repo, full stop.** Instrument master, ingest, and broker mapping are NSE-only. Sensex is where the weekly-expiry auction action is (Thursday), and studying it requires a BSE data build we have not scoped.
- **History depth:** the regime is 24 days old. n = 4 Nifty weekly expiries + 1 monthly, and the first two sit under launch chaos + an enforcement discontinuity. *Any* backtest-shaped answer is currently impossible — for us and for everyone else.

### Verdict

**Not farmable today, and not answerable from past data — the past doesn't contain this regime.** The visible fat edge (moving the auction) is manipulation with proven same-month enforcement. The legitimate edges (post-fix arb, imbalance prediction, convergence) are real strategy classes but require the auction data feed and forward accumulation of expiry-day observations that nobody yet has. The RFA discipline applies: a per-trade-PnL construct on one index with ~52 expiry-weeks/yr faces the RS-MOM wall (need Sharpe ≥ ~1.3) *unless* the trade is near-deterministic arb, in which case the gate is data existence, not power.

**Cheap, immediate, no-authorization-needed steps:**
1. Extend the NiftyShield chain poller window 15:30 → 15:40 (captures the post-fix window every day, expiry days included).
2. Record the indicative index value during 15:15–15:35 if the feed carries it (check Upstox WS for auction-period index ticks).
3. Re-run the §3 measurement after ~8–12 more expiries; only then decide whether an RFA declaration is worth writing.
4. Fix/audit the 15:30 close constants (§4.3) and the A-construct exit disclosure (§4.2) regardless.

---

## 6. Bottom line

- CAS is live (2026-08-03), replaces VWAP closes for F&O stocks, and re-plumbs index expiry settlement through constituent auctions while extending F&O trading to 15:40.
- Week 1 was violent (+152 to +567 pt auction-window index moves); it was promptly gamed on the Sensex Aug-13 expiry; SEBI barred both entities within 6 days; the window has since traded like the old regime.
- **NiftyShield is structurally insulated** (flat by 15:15, never holds expiry-day options). The **A-construct's 15:29 exit needs a pre-registration disclosure**. Ops has a real 15:30-vs-15:40 constants gap and a poller window gap.
- **Post-15:15 farming: no historical basis exists to mine — build the dataset first** (poller extension + indicative-index capture), revisit after ~3 months of expiries, and treat anything that touches the cash auction with a derivatives book as the compliance third rail it is.

---

## 7. Sources

- SEBI circular HO/47/11/11(3)2025-MRD-POD2/I/2765/2026 (2026-01-16); NSE circular CMTR73362
- Zerodha Z-Connect: "Everything you need to know about CAS"; Zerodha Support CAS FAQ
- Marketcalls: "How the SENSEX Closing Auction Was Allegedly Gamed" (SEBI ex-parte interim order, 2026-08-19)
- Bloomberg: "India's New Auction Passes Sensex Expiry Test After Chaotic Week" (2026-08-06)
- NiftyTrader: "After JPMorgan Ban, India's Auction-Based Closing Prices Head Into Monthly Expiry" (2026-08-25)
- Sahi / AngelOne / Groww / PaytmMoney CAS explainers; Sahi NSE-BSE expiry schedule 2026
- In-repo: `data/market_data/nse/candles/1m/*.duckdb` (§3 measurements), `data/options/wall_chain_snapshots.duckdb`, `data/options/chain_cache.duckdb`, `strategies/nifty_shield_v1/config.py`, `docs/reports/A_CONSTRUCT_DEFINITION.md`
