# Options-Wall Counterfactual Structure Battery — 2026-09-04 → 2026-09-17

**Date:** 2026-09-17 · **Status:** DESCRIPTIVE, not a gated read · **Author:** Claude (operator-requested)
**Question asked:** the paper pilot trades only the ATM iron fly. Over the nine sessions of
5-second chain snapshots we hold, would any other structure have captured the daily swings?
**Script:** `scripts/research/options_wall_counterfactual/battery.py` → `data/scratch/options_wall_counterfactual.csv` (11,190 rows)

---

## 0. Verdict in four lines

1. **No non-directional structure clears fees intraday.** Short-vol wins 7 quiet days by +2–5 bp and loses the 2 swing days by −10–17 bp; long-vol is the mirror image. Net of fees every one of the six is negative. The iron fly is the *worst* of them because it is the most expensive to trade (₹270 round-trip against ₹40 mean gross).
2. **The only signal-free directional rule that wins — follow the opening drive — is A-INDEX-INTRADAY, which this repo already retired at HOLDOUT** (−0.22 bp on 988 sessions, 2019–2022). Its +7.6 bp here is two days' tails on nine sessions and cannot overturn that read.
3. **Overnight short premium (sell 15:10, buy back 09:35) is the only unexplained positive**: +5–8 bp per index-night, 72–76 % wins, on 21 index-nights. The seller-edge study found nothing for Nifty overnight on a decade of bhavcopy. Twenty-one nights do not beat that null.
4. **The pilot's own P&L is a fee story, not a signal story**: gross +₹3,446, fees ₹8,780, net −₹5,334 over 39 closed trades. ₹4,043 of that fee bill is the 19-trade regime-flip churn on Sensex 2026-09-09, since fixed (`15258d7`).

Nothing here authorizes a construct. Anything that wants to be one goes through the RFA gate as `per_trade_pnl` on ≤3 indices — the √T ≈ 1.9 wall (pilot spec §1, RS-MOM).

---

## 1. Data and method

| Item | Value |
|---|---|
| Snapshot store | `data/options/wall_chain_snapshots/{date}.duckdb`, 9 sessions (09-04 partial from 09:52; 09-08 and 09-11 from 09:41; 09-14 holiday) |
| Underlyings | Nifty 50 (weekly Tue, lot 65), SENSEX (weekly Thu, lot 20), Bank Nifty (monthly 09-29, lot 30) |
| Chain | one expiry per underlying per day — the pilot's near expiry. On Nifty/Sensex expiry days the chain is 0-DTE (43 of 285 cells) |
| Quotes | live `best_bid`/`best_ask` per leg; strike snapped to nearest *quoted* strike within ±3.5 % of spot |
| Fill | mid of bid/ask (pilot convention). A second column crosses the spread (buy at ask, sell at bid) on both entry and exit |
| Fees | `core/execution/options/fees.py` per order, 2026 rates (STT 0.15 % sell), ₹20 brokerage/order |
| Entry grid | 09:30, 10:00, … 14:30 (11 slots); exit 15:15 same day. Overnight: enter 15:10, exit next session 09:35 |
| Exit variants | fixed-time; pilot TP/SL (+50 % / −2× credit for credit structures; ±50 % of debit for debit structures) |
| Sizing | 1 lot, from the chain's `lot_size`. Cross-index metric is **bp of notional** (`net / (spot × lot)`) |
| Parameters | every threshold (offsets, 0.10 % trend threshold, times) was written into the script before the first run and not changed after |

**Structures.** Non-directional: iron fly (ATM short, ±1.5 % wings, the pilot's), short straddle, short strangle ±1 %, iron condor (±1 % / ±2 %), long straddle, long strangle ±1 %. Directional (bull shown, bear mirrored): ATM debit spread (buy ATM, sell +1 %), OTM credit spread (sell −1 %, buy −2 %), naked long ATM option. Direction rules: `trend_open` (sign of spot vs first snapshot, |move| ≥ 0.10 %), `contra_open`, `prev_day` (previous session's open→close sign), and unconditional `bull` / `bear` as hindsight benchmarks.

**Sanity check.** The counterfactual iron fly at 09:30 on 2026-09-15 (Nifty, 0-DTE) marks −₹9,838 held to 15:15; the pilot's trade 34 on the same fly stopped out at 14:15 for −₹8,144. Same structure, same legs (23450 / 23800 / 23100), difference is the exit time.

---

## 2. What the market did

| Session | Nifty open→close | Nifty range | Bank Nifty o→c | Sensex o→c | Character |
|---|--:|--:|--:|--:|---|
| 09-04 (Fri, from 09:52) | −0.14 % | 0.43 % | −0.04 % | −0.20 % | quiet |
| 09-07 | −0.32 % | 0.51 % | −0.29 % | −0.35 % | quiet, down |
| 09-08 (Nifty expiry) | −0.19 % | 0.38 % | −0.29 % | −0.23 % | quiet, down |
| 09-09 | −0.31 % | 0.59 % | −0.35 % | −0.39 % | early up, then down |
| 09-10 (Sensex expiry) | −0.02 % | 0.42 % | +0.10 % | +0.03 % | quiet |
| **09-11** | **+0.66 %** | 0.88 % | **+1.37 %** | +0.75 % | **swing up** |
| **09-15** (Nifty expiry) | **−1.65 %** | 1.70 % | −1.61 % | −1.55 % | **swing down** |
| 09-16 | +0.03 % | 0.70 % | +0.40 % | +0.05 % | quiet |
| 09-17 (Sensex expiry) | +0.07 % | 0.71 % | −0.25 % | −0.01 % | quiet |

Seven quiet sessions, two swing sessions, and a drift from 23,932 to 23,118 (−3.4 %) across the window. Any unconditional bear position looks brilliant here; that is hindsight and is labelled as such below.

---

## 3. The pilot as traded (plumbing findings, spec §11)

| | Trades | Gross | Fees | Net | Notes |
|---|--:|--:|--:|--:|---|
| All closed | 39 | +3,446 | 8,780 | **−5,334** | fees = 2.5 × gross |
| Sensex 09-09 alone | 19 | +1,125 | 4,043 | −2,918 | 19 regime-flip exits + immediate re-entries; regime flickered through **41 segments** that day |
| Nifty | 11 | | | −472 | 64 % wins |
| Sensex | 29 | | | −4,862 | 24 % wins |

- The spec's fee estimate ("≈3 % of net credit") is true and irrelevant. What matters is fee **against realized gross**, and an ATM fly held a few hours realizes ₹40–140 gross against a ₹230–270 round trip.
- The regime-flip exit was removed as an exit (`15258d7`, flip now gates entry only). Correct fix; the 09-09 record stands as the evidence for it.
- The four TP exits made ₹9,879; the one SL (09-15, −₹8,144) gave most of it back. That is the whole pilot.

---

## 4. Non-directional structures, intraday

All entry slots, fixed 15:15 exit, n = 285 per structure (9 sessions × 3 indices × up to 11 entries).

| Structure | Gross | Fees | **Net (mid)** | Net (cross spread) | Win | Mean bp | Fee/trade | Gross/trade |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| short strangle ±1 % | +35,807 | 35,386 | **+421** | −10,847 | 64 % | −0.5 | 124 | 126 |
| short straddle | +38,737 | 43,979 | **−5,242** | −23,147 | 67 % | −0.9 | 154 | 136 |
| iron condor | +16,417 | 66,669 | **−50,252** | −69,487 | 39 % | −1.3 | 234 | 58 |
| **iron fly (pilot)** | +11,513 | 76,916 | **−65,403** | −92,415 | 46 % | −1.7 | 270 | 40 |
| long strangle ±1 % | −35,807 | 35,333 | **−71,140** | −82,408 | 23 % | −0.9 | 124 | −126 |
| long straddle | −38,737 | 43,922 | **−82,658** | −100,563 | 24 % | −0.9 | 154 | −136 |

The pilot TP/SL variant changes nothing material (short strangle +4,491; long straddle −95,406).

**Quiet days vs swing days** (mean bp of notional, intraday):

| Structure | 7 quiet days | 2 swing days |
|---|--:|--:|
| short straddle | +3.4 | −15.9 |
| short strangle | +2.1 | −9.9 |
| iron fly | +0.8 | −10.5 |
| iron condor | +0.2 | −6.3 |
| long straddle | −5.1 | +14.0 |
| long strangle | −3.6 | +8.4 |

Seven quiet days at +3.4 bp are 24 bp; two swing days at −15.9 are −32 bp. Short-vol is not paid enough on quiet days for the swing days it eats, and long-vol pays too much theta on quiet days for the two swing days it catches. The two sides are mirror images, which is what "no edge" looks like.

Other cuts, none of which changes the picture:

- **By index.** Short straddle/strangle were slightly positive on Bank Nifty (+0.3 / 0.0 bp) and negative on Nifty and Sensex. Every long structure is negative on every index.
- **0-DTE cells (43).** Iron fly −7.8 bp, short straddle −7.1 bp, long straddle +5.7 bp — expiry-day gamma, driven by 09-15. The pilot's DTE ≥ 1 rule is right.
- **GEX regime at entry.** Short structures do worse when entered under `Negative GEX` (straddle −2.4 bp vs −0.8 under Positive; n = 32 vs 249); long straddle +0.4 vs −1.0. Direction agrees with the wall thesis, magnitude is within noise.
- **Entry slot.** No slot is positive for any short structure after fees; 11:30 and 14:30 are the least negative.

---

## 5. Directional structures

Intraday, fixed 15:15 exit, net of fees at mid.

| Rule | Structure | n | Net | Win | Mean bp | Quiet 7d (bp) | Swing 2d (bp) |
|---|---|--:|--:|--:|--:|--:|--:|
| `bear` (hindsight) | long ATM put | 285 | +239,747 | 63 % | +5.1 | | |
| `bear` (hindsight) | bear debit spread | 285 | +133,585 | 60 % | +3.0 | | |
| **`trend_open`** | **long ATM option** | 201 | **+191,766** | 54 % | +7.6 | **−4.1** | **+34.4** |
| `trend_open` | debit spread | 201 | +110,713 | 53 % | +4.2 | −1.3 | +16.8 |
| `trend_open` | credit spread | 201 | +12,503 | 55 % | +0.6 | −0.7 | +3.7 |
| `prev_day` | long ATM option | 255 | +70,581 | 56 % | +1.7 | | |
| `prev_day` | debit / credit spread | 255 | −1,802 / −13,923 | | ≈0 | | |
| `contra_open` | long ATM option | 201 | −192,914 | 31 % | −6.7 | | |
| `bull` (hindsight) | long ATM call | 285 | −322,406 | 19 % | −6.0 | | |

Two things are true about `trend_open` and both matter:

1. **It is the only rule that captured both swing days without knowing their direction** (09-11 +30.8 bp, 09-15 +37.5 bp on the naked option), and its best slots are 09:30–10:00 (+17–18 bp). On this window it looks like exactly what the operator asked for.
2. **It is A-INDEX-INTRADAY** — opening-drive continuation on Nifty, window 09:15–10:00, entry 10:01, exit 15:14 (`A_CONSTRUCT_DEFINITION.md`). That construct passed TRAIN (+1.27 bp, n = 1,699, 2012–2018) and **failed HOLDOUT (−0.22 bp, p 0.133, n = 988, 2019–2022)** and is **retired** (`A_HOLDOUT_CLOSURE.md`: "no successor is authorized"). Expressing it through a long ATM option instead of a future adds convexity, but the option's premium prices that convexity, and the direction statistic underneath is the one that measured zero out of sample on a thousand sessions.

Nine sessions, of which two carry the whole result, do not reopen a construct closed on 988. The 09:30–10:00 profile is precisely the A window — this battery re-found A on A's own sealed window (see §7).

---

## 6. Overnight (enter 15:10, exit next session 09:35)

21 index-nights (8 session pairs × 3 indices, minus one Sensex expiry roll). The 09-11 → 09-15 pair spans a long weekend and lands on Nifty's expiry morning, so it is shown both ways.

| Structure | n | Net | Win | Mean bp | Mean bp **ex 09-11** (n = 18) | Fees / gross |
|---|--:|--:|--:|--:|--:|--:|
| short straddle | 21 | +32,205 | 76 % | +8.2 | +5.2 | 10 % |
| short strangle ±1 % | 21 | +22,336 | 76 % | +5.8 | +3.5 | 11 % |
| iron fly (pilot) | 21 | +11,875 | 62 % | +2.9 | +1.6 | 33 % |
| iron condor | 21 | +7,654 | 62 % | +1.8 | +0.8 | 40 % |
| long straddle | 21 | −38,957 | 19 % | −10.0 | −7.0 | |
| `bear` long put (hindsight) | 21 | +38,009 | 62 % | +6.2 | | |

By night: overnight short premium lost only on 09-08 → 09-09 and 09-10 → 09-11 (both small gaps against, −5 to −8 bp) and made +26 bp on the long weekend. No adverse gap larger than ~0.5 % occurred in the window; the trade's loss distribution is defined by exactly those gaps and the sample contains none.

What this is and is not:

- It is where the pilot's fly actually made its money (overnight +2.9 bp vs intraday −1.7 bp), which supports the spec's multi-session hold and says the fly's edge, if any, is theta across the close, not intraday pinning.
- The naked straddle carries SPAN margin (not modelled here; roughly ₹1.3–1.5 lakh per Nifty lot) and an unbounded gap tail. A 76 % win rate on 21 nights is consistent with a positive-expectation trade and equally consistent with a short-tail trade that has not yet met its tail.
- `OPTIONS_SELLER_EDGE_STUDY_2026-09-11.md` (on branch `research/options-seller-edge`) tested Nifty overnight / weekly / 0-DTE premium selling on 2016–2026 bhavcopy and found **nothing**. The live-quote overnight here is a finer instrument than close-to-close bhavcopy, but 21 nights against a ten-year null is not evidence; it is a reason to keep the snapshot collector running.

---

## 7. Prior-exposure disclosure

- The nine sessions 2026-09-04 → 09-17 lie inside **A-INDEX-INTRADAY's SEALED window** (2023-01-01 → present). A is retired, so nothing is at stake for A itself, but the `trend_open` read should be appended to `A_INDEX_INTRADAY_PRIOR_EXPOSURE_AUDIT.md` if that construct or any opening-drive cousin is ever re-registered.
- The same nine sessions are now a read for any future index short-premium construct (overnight straddle/strangle) and any index long-gamma construct. Both are `per_trade_pnl` on ≤3 indices and face the √T wall regardless.
- Nothing was tuned: every threshold was fixed in the script before the first run, and no parameter was changed after seeing results. The `trend_open` 0.10 % threshold and the ±1 % / ±1.5 % / ±2 % offsets are the first and only values tried.

---

## 8. What is legitimate next

1. **Keep the pilot exactly as frozen** and keep collecting. The month-end plumbing report (spec §11) now has its findings: fee/gross ratio 2.5×, the regime-flip churn (fixed), 0-DTE exclusion vindicated, overnight not intraday is where the fly earns.
2. **Do not add a directional overlay to the pilot.** The only one that works here is a retired construct, and changing rules mid-month is the thing the spec forbids.
3. **If a swing-capture construct is wanted, it starts at the RFA gate**, not here. The relevant declared bands already exist for comparison: A-INDEX-INTRADAY's Sharpe band [0.70, 1.45] at cadence 237 barely cleared (max power 0.87); RS-MOM at weekly cadence did not. A long-gamma expression does not change `ncp = S·√T`.
4. **The overnight short-premium read is the one thing worth a cheap follow-up**, and the follow-up is *more nights*, not more structures: after ~60 index-nights the collector will have enough to say whether the +5 bp survives a gap. That is a standing-data question, not a research spend.

---

## Files

| File | Purpose |
|---|---|
| `scripts/research/options_wall_counterfactual/battery.py` | Battery — loads per-day snapshots, prices structures at mid and cross-spread, applies `fees.py` |
| `data/scratch/options_wall_counterfactual.csv` | 11,190 priced cells (day, index, entry, structure, rule, exit rule, gross/net/fees, MFE/MAE, legs) |
| `data/options/wall_scan_results.duckdb` → `trades` | The 40 pilot trades analysed in §3 |
| `docs/superpowers/specs/2026-08-14-options-wall-paper-pilot-design.md` | Pilot spec (§10 frozen parameters, §11 month-end scope) |
| `docs/reports/index_research/A_HOLDOUT_CLOSURE.md` | Why `trend_open` is not a candidate |
| `docs/reports/strategies/OPTIONS_SELLER_EDGE_STUDY_2026-09-11.md` (branch `research/options-seller-edge`, commits `6b20f0f`/`52b71ab`, not on this branch) | The index overnight-premium null |
