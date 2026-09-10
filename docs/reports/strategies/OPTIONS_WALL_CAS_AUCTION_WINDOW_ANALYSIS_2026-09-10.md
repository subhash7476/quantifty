# Options-Wall — what the CAS auction window does to option quotes and fly decay

Analysis 2026-09-10. Question: options-wall squares off at **15:15**, but index options are
**derivatives** and trade to **15:40** post-CAS. Is the 15:15 stop (a) safe to move, and
(b) costing us theta?

**Answer: yes to both.** Quotes do not degrade in the auction window, and holding past 15:15
captured positive P&L in **9 of 9** index-sessions to 15:25.

---

## 0. Sample — read this before the numbers

| session | auction coverage | usable |
|---|---|---|
| 2026-09-04 | to 15:39 | ✅ |
| 2026-09-07 | to 15:40 | ✅ |
| 2026-09-08 | **poller stopped 15:17** | ❌ |
| 2026-09-09 | to 15:40 | ✅ |
| 2026-09-10 | in progress (to 12:16 at run time) | ❌ — window hasn't happened yet |

**Three sessions × three indices = 9 index-sessions.** That is a small sample and every
conclusion below is bounded by it.

**The most important gap: there is no DTE-0 session in the sample.** 2026-09-08 was Nifty
expiry, and that is exactly the session where the poller stopped at 15:17. Expiry day is when
the 15:15–15:40 window carries the most theta *and* the most gamma, so the case that matters
most is unmeasured. **Today (2026-09-10) is SENSEX expiry with the poller running — it will
produce the first DTE-0 observation.** Re-run this after today's close before committing to
anything on expiry days.

DTE spread in the sample: 1, 1, 3, 4, 6, 6, 20, 22, 25.

---

## 1. Quote health — the auction does not degrade the option book

Every minute 15:00–15:40, ATM ±3 strikes, pooled across the 9 index-sessions
(~450 leg-observations per minute):

| minute | two-sided quotes | median rel. spread | stale |
|---|---:|---:|---:|
| 15:00–15:14 (pre-auction) | **100.0%** | 0.22–0.26% | 0–1.7% |
| **15:15–15:34 (CAS auction)** | **100.0%** | **0.25–0.30%** | 0–0.8% |
| 15:35–15:37 | 100.0% | 0.26–0.27% | 0.8–1.1% |
| 15:38 | 100.0% | 0.32% | 1.0% |
| **15:39** | 100.0% | **0.38%** | 1.3% |
| **15:40** | 100.0% | **0.96%** | 2.4% |

**Two-sided quotes were present 100.0% of the time at every single minute through 15:40.**
There is no quote gap, no dead zone, and no meaningful staleness while the cash market is in
auction. Spreads widen from ~0.24% to ~0.28% across the auction — a ~15% widening on an
already-tight book, and far inside the screen's own 5% tolerance.

**The degradation is at the very end, and it is the derivatives close, not the auction.**
Spread roughly triples into 15:39 (0.38%) and quadruples at 15:40 (0.96%), with staleness
rising. This is the one execution-relevant finding in Part 1: **do not put the square-off at
15:40.**

This clears the gate the 2026-09-09 report left open — options-wall marks from the option
chain, not from underlying 1m bars, so it does **not** inherit NiftyShield's 15:29 bar-gap
problem. The marks in Part 2 are trustworthy.

---

## 2. Theta forfeited — ₹ P&L from holding an ATM fly (1 lot) past 15:15

Fly built at the 15:15 snapshot on each index's front expiry (ATM ± 1.5% wings, the screen's
own rule), marked forward. **Positive = decay captured that the 15:15 exit throws away.**

| session | index | DTE | spot move | *control* 14:55→15:15 | 15:20 | 15:25 | 15:30 | 15:35 | 15:38 |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|
| 09-04 | SENSEX | 6 | −136 | +9 | +1 | +314 | +487 | +557 | +664 |
| 09-04 | Nifty 50 | 4 | −37 | −76 | +59 | +336 | +531 | +591 | +531 |
| 09-04 | Nifty Bank | 25 | −61 | +63 | +59 | +42 | +67 | +48 | +58 |
| 09-07 | SENSEX | 3 | +101 | −120 | +508 | +488 | +676 | +831 | +723 |
| 09-07 | Nifty 50 | 1 | +22 | +65 | +739 | +721 | +881 | +1,112 | +1,019 |
| 09-07 | Nifty Bank | 22 | +46 | +49 | +113 | +91 | +144 | +134 | +127 |
| **09-09** | **SENSEX** | **1** | **−113** | +431 | **−161** | +62 | **−79** | **−520** | **−634** |
| 09-09 | Nifty 50 | 6 | −32 | +268 | +117 | +193 | +314 | +254 | +154 |
| 09-09 | Nifty Bank | 20 | −113 | +195 | +89 | +57 | +143 | +218 | +134 |

**Pooled:**

| hold to | mean | median | min | max | positive |
|---|--:|--:|--:|--:|--:|
| 15:20 | +169 | +89 | −161 | +739 | 8/9 |
| **15:25** | **+256** | **+193** | **+42** | +721 | **9/9** |
| **15:30** | **+352** | **+314** | **−79** | +881 | 8/9 |
| 15:35 | +358 | +254 | **−520** | +1,112 | 8/9 |
| 15:38 | +308 | +154 | **−634** | +1,019 | 8/9 |

### What this says

- **The 15:15 stop is leaving money on the table, and the amount is material.** Median
  +₹193 to +₹314 per lot. For scale, a full 4-leg round trip costs ~₹212 in fees — so the
  forfeited decay is on the order of an entire round trip's cost, given up for free every
  session on every open position.
- **15:30 dominates 15:35.** Nearly the same mean (+352 vs +358), a *better* median
  (+314 vs +254), and a tail six times smaller (−79 vs −520). Extending past 15:30 buys
  essentially no additional expected decay and buys a materially worse worst case.
- **Past 15:35 it is strictly worse** on every measure — mean falls, median falls, tail
  worsens, and Part 1's spreads widen.
- **The single loser is the gamma case, as expected.** 09-09 SENSEX at DTE 1 with spot
  −113 points is the only negative column, and it degrades monotonically with holding time
  (−161 → −79 → −520 → −634). Low DTE plus an adverse move is exactly where a short fly
  should lose; the window does not protect against direction.

### Is the auction window *unusually* good for decay? — suggestive, not established

Against the control (the same fly over the preceding 20 minutes, 14:55→15:15):

- mean **+₹358 vs +₹98 — a 3.6× ratio**
- paired difference: mean +₹260, median +₹85, **6/9 positive**
- Wilcoxon signed-rank, one-sided: **p = 0.086**

So the ratio is eye-catching but **does not clear significance at n=9**, and the mean is
pulled by a few large values. The defensible claim is the weaker one: *decay in the auction
window is reliably positive*, not *the auction window decays faster than normal*. A plausible
mechanism — the cash underlying stops trading continuously, so theta accrues with less
offsetting spot movement — is consistent with the data but is **not** tested here.

---

## 3. Recommendation

**Move the square-off from 15:15 to 15:30.**

Rationale, in order of evidential strength:
1. Quotes are 100% two-sided and tight through the whole window (n large, unambiguous).
2. Holding past 15:15 was positive in 8–9 of 9 index-sessions at every cutoff.
3. 15:30 captures ~98% of the mean decay available at 15:35 with a tail 6× smaller.
4. 15:39–15:40 spreads blow out, so the derivatives close is the wrong target.

**Caveat on the specific minute: 15:30 is chosen from this table and is therefore in-sample
at n=9.** The robust findings are directional — *15:15 is too early*, and *15:40 is wrong on
execution grounds*. Anywhere in 15:25–15:35 is defensible; do not treat 15:30 as tuned.

**On the bare-constant rule.** `CLAUDE.md` requires session windows to come from
`core/market/session_schedule.py`, never a bare constant — and 15:30 is not a segment
boundary post-CAS (`derivatives` is 09:15–15:40, `cash_auction` 15:15–15:35). The right
resolution is that the square-off is a **strategy parameter, not a session boundary**: it
should be *bounded* by `session_window("derivatives", d)` read from the schedule — asserting
it is inside the segment and not in the final two minutes — while the value itself stays
config. That keeps the constitution's intent (no hardcoded session truth) without pretending
a tuned exit time is a market fact.

**Do not change this while a position is open mid-session.** SENSEX trade 30 expires today and
time-stops at 15:15; changing the rule under it mid-flight replaces a known behaviour with an
untested one on an expiring, low-DTE position — the exact case §2 shows is the risky one.

### Before acting on expiry days specifically

Re-run this analysis after today's close. Today is SENSEX DTE 0 with full poller coverage and
will be the **first** DTE-0 observation in the sample. The one loss in §2 is the lowest-DTE
case there, and DTE 0 is lower still — the expiry-day answer could differ in sign from the
DTE≥1 answer, and nothing here measures it.

---

## 4. Caveats

- **9 index-sessions over 3 dates.** Everything above is small-sample.
- **No DTE-0 coverage** (§0). The most important case is unmeasured.
- Marks are **mid-quotes, not fills**. A real exit crosses the spread — ~0.28% relative on
  four legs, small against the figures above but not zero, and larger at 15:39–15:40.
- The control window (14:55→15:15) is itself pre-close and may not represent typical
  intraday decay; it is a local control, not a session-wide baseline.
- Figures are **per one lot** (SENSEX 20, Nifty 65, BankNifty 30) and are not fee-adjusted —
  holding an already-open position longer incurs no additional fee, so no adjustment applies.
- Three of nine index-sessions are Nifty Bank at DTE 20–25, where decay is structurally small
  (+₹42 to +₹218); they dilute the pooled mean relative to a book of front-expiry positions.

## Reproduction

- `data/options/wall_chain_snapshots/{2026-09-04,07,09}.duckdb`
- Fly construction mirrors `core/options_wall/fly.py::build_iron_fly` (ATM nearest strike,
  wings nearest to spot·(1±0.015)); marks are `(best_bid+best_ask)/2` with `ltp` fallback,
  matching `paper_executor._mids`
- Session windows: `core.market.session_schedule.session_window`

---

# Addendum — 2026-09-10 post-close re-run (DTE 0 captured; a new defect found)

A power outage killed the poller at **15:33:27**, so today's window is **15:15 → 15:33**, not
15:15 → 15:40 (81–83 auction snapshots, 16–17 past 15:30). The 15:35 / 15:38 cutoffs are lost
for today; 15:20 / 15:25 / 15:30 — the range the recommendation turns on — are intact.

## 1. The finding that matters most: the underlying reference freezes in the auction

Part 1 measured **option** quote health and found it perfect. It did not measure the
**underlying**. It should have.

Distinct `underlying_ltp` values per bucket:

| session | index | 15:05–15:10 | 15:15–15:20 | 15:20–15:30 | 15:30–15:33 |
|---|---|--:|--:|--:|--:|
| 09-04 | all three | 13 | 1 | 1–2 | 1 |
| 09-07 | all three | 16–17 | 1–2 | 1–2 | 1 |
| 09-09 | all three | 21–22 | 1–2 | 2 | 1 |
| 09-10 | all three | 17–19 | 1–2 | 2 | 1 |

**From 15:15 the index print is effectively a single frozen number, on every index, in every
session** — the cash auction halts continuous trading, so the index is no longer computed from
live trades. Options keep quoting tightly against a reference that has stopped moving.

Caught by the DTE-0 probe: at 15:27:58 on 2026-09-10 the SENSEX 74600 CE was **453.45 / 455.75**
— a 0.5% spread, entirely healthy — having travelled 239 → 454 in ninety seconds, while
`underlying_ltp` sat at **74629.50** throughout. The option market was pricing a real move the
index print did not show.

### What this does and does not break

- **It does not affect the square-off.** `time_stop` reads only the clock; TP/SL read
  `unrealized_pnl` from option mids. Nothing on the exit path touches spot. The 15:30 change
  is unaffected.
- **It does invalidate anything keyed on spot after 15:15**: ATM and wing selection
  (`build_iron_fly`), the pin band, GEX and the regime classification, and the dashboard.
  `session_regime` rows written 15:15–15:40 are computed against a frozen reference and should
  not be read as market state.
- **It is a landmine for any future extension of `entry_end`** (currently 15:00, so entries
  are safe today). Opening a fly in the auction window would centre it on a stale spot.
- Today's `spot_move` column is itself measured off the frozen print and **understates** the
  real move.

This belongs in the CAS register; it is not there.

## 2. Decay re-run, now 12 index-sessions including DTE 0

| session | index | DTE | 15:20 | 15:25 | 15:30 | 15:33 |
|---|---|--:|--:|--:|--:|--:|
| 09-04 | SENSEX | 6 | +1 | +314 | +487 | +380 |
| 09-04 | Nifty 50 | 4 | +59 | +336 | +531 | +544 |
| 09-04 | Nifty Bank | 25 | +59 | +42 | +67 | +40 |
| 09-07 | SENSEX | 3 | +508 | +488 | +676 | +708 |
| 09-07 | Nifty 50 | 1 | +739 | +721 | +881 | +964 |
| 09-07 | Nifty Bank | 22 | +113 | +91 | +144 | +66 |
| 09-09 | SENSEX | 1 | −161 | +62 | −79 | −472 |
| 09-09 | Nifty 50 | 6 | +117 | +193 | +314 | +314 |
| 09-09 | Nifty Bank | 20 | +89 | +57 | +143 | +138 |
| **09-10** | **SENSEX** | **0** | +56 | **−1,973** | **−388** | **−387** |
| 09-10 | Nifty 50 | 5 | +18 | +39 | −88 | −41 |
| 09-10 | Nifty Bank | 19 | +34 | +68 | +45 | +83 |

| hold to | mean | median | min | positive |
|---|--:|--:|--:|--:|
| 15:20 | +136 | +59 | −161 | 11/12 |
| 15:25 | +37 | +79 | **−1,973** | 11/12 |
| **15:30** | **+228** | **+144** | −388 | 9/12 |
| 15:33 | +195 | +111 | −472 | 9/12 |

By DTE, held to 15:30:

| bucket | n | mean | median | min |
|---|--:|--:|--:|--:|
| **DTE 0** | **1** | **−388** | −388 | −388 |
| DTE 1–2 | 2 | +401 | +401 | −79 |
| DTE 3–7 | 5 | +384 | +487 | −88 |
| DTE 8+ | 4 | +100 | +105 | +45 |

**The −₹1,973 is not a bad mark.** Quotes were tight throughout; the DTE-0 fly's value ranged
198.00 → 457.58 (2.3×) inside eighteen minutes. That is real expiry-day gamma, and it is why
the 15:25 pooled mean collapses from +256 to +37 on a single added row.

### What changed, and what did not

- **For DTE ≥ 1 the case is intact and if anything stronger** — DTE 1–2 mean +401, DTE 3–7
  mean +384, DTE 8+ mean +100, held to 15:30.
- **The single DTE-0 observation is negative at every cutoff past 15:20.** n = 1, so this is
  not a result — but it points the same way as the 09-09 DTE-1 loss, the theory, and the
  measured violence of the DTE-0 ATM.
- Adding today weakens the pooled picture: 15:30 goes from mean +352 / 8-of-9 to
  **mean +228 / 9-of-12**. Still positive, still the best cutoff on the table.

## 3. Recommendation — unchanged at 15:30, with the expiry-day caveat now evidenced

Keep `squareoff = "15:30"` **uniformly**. The one observed DTE-0 loss (−₹388 to 15:30) is
small against the DTE≥1 gains, and the change remains positive in expectation across the
sample.

**Do not make the square-off DTE-conditional on this evidence.** A "15:15 on expiry day,
15:30 otherwise" rule fitted to a single observation is exactly the post-hoc overlay this
repo's own history warns against. If expiry-day behaviour is worth a separate rule, it needs
several DTE-0 sessions first — SENSEX gives one per week, NIFTY one per week.

**What to watch:** the next three DTE-0 sessions. If they cluster negative to 15:30, a
DTE-conditional square-off becomes a pre-registered change with its rule fixed in advance.

## 4. Operational note

**Trade 29 (NIFTY, entered 09:30:00, short 23,450, DTE 5) is still open and unattended** — the
poller died at 15:33 and there is no process managing it. It is paper, so nothing is at risk
financially, but it will not be marked or exited until the poller is restarted.

Today's realised SENSEX book: trade 30 **+₹1,923.43** (`tp` at 12:23:55 — the first `tp` exit
in the pilot's history) and trade 31 **−₹2,495.21** (`manual` at 15:03:40), netting
**−₹571.78**. Trade 31 was a DTE-0 entry at 12:24 that ran into the same expiry-day gamma this
addendum measures.
