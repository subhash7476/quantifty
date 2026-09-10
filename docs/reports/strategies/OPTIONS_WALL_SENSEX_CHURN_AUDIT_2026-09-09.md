# Options-Wall — the SENSEX book churned itself into a fee pump, 2026-09-09

Audit of today's SENSEX paper trading. All numbers from the live pilot stores
(`data/options/wall_scan_results.duckdb`, `data/options/wall_chain_snapshots/2026-09-09.duckdb`)
and the poller log. No code changed.

**Scope.** "Today's SENSEX trade" is 19 separate round trips, not one. Trade 8 (opened
2026-09-08 09:58, closed today 09:27, net −₹1,067) is a *different* failure — a real
overnight adverse move on a position held ~23 hours — and is excluded from the churn
analysis below. Including it, the day's SENSEX total is **−₹3,985**.

---

## 1. What happened

19 SENSEX iron flies opened and closed between 09:39 and 14:28. **Every single one exited on
`regime_flip`.** Zero `tp`, zero `sl`, zero `time_stop`.

| | |
|---|---:|
| Round trips | 19 |
| **Gross P&L** | **+₹1,125** |
| **Fees** | **−₹4,043** |
| **Net P&L** | **−₹2,918** |
| Median hold | **166 seconds** |
| Shortest hold | **12 seconds** |
| Winners, gross | 12 / 19 |
| Winners, net | **2 / 19** |

Six trades were held under a minute. Trade 21 lived 12 seconds and lost ₹206 — it earned
₹6.50 of gross and paid ₹212 in fees.

The position was never the problem. Spot ranged 477 points (0.64%) against ±1.5% wings, the
short strike oscillated only between 75,100 and 75,200, and the index pinned all session.
Quiet, pinned, IV-rich — **precisely the regime the farm screen selects for** — and it still
bled ₹2,918.

### The cost is fixed per round trip, and it is mostly brokerage

`option_order_fees` on the traded legs at qty 20:

| leg | fee | of which brokerage |
|---|---:|---:|
| SELL 75200 CE @229.7 | 32.40 | 20.00 |
| SELL 75200 PE @263.1 | 33.67 | 20.00 |
| BUY 76300 CE @18.1 | 23.76 | 20.00 |
| BUY 74000 PE @16.9 | 23.75 | 20.00 |
| **entry** | **113.58** | 80.00 |
| **round trip (8 orders)** | **≈212** | **160 (75%)** |

**₹160 of every ₹212 is flat ₹20/order brokerage** — wholly independent of hold time,
premium, and position size. Against a ~₹8,800 credit, each round trip burns **2.4% of the
credit** before the market does anything.

Bid/ask crossing is *not* a material contributor here, contrary to what one might assume.
Measured median spreads on the traded legs over the session: 75200 CE 0.50, 75200 PE 0.55,
76300 CE 0.10, 74000 PE 0.10 — **1.25 points total across four legs**, or ~₹25 per round trip
at qty 20 (~₹475 over 19 trades). Fees exceed spread by 8.5×. The SENSEX weekly book was
liquid; this is a fee problem, not a liquidity problem.

---

## 2. Mechanism — a bang-bang controller with no dead band

Entry (`ChainScanner._farm_screen`, `chain_scanner.py:110`):

```python
if "Positive" not in (structural.gex.regime or ""):
    return []
```

Exit (`PaperExecutor._manage`, `paper_executor.py:90`):

```python
if "Negative" in (structural.gex.regime or ""):
    reason = "regime_flip"
```

The two gates are the same bare sign test on `net_gamma_total`, read in opposite directions.
There is **no hysteresis, no minimum hold, no confirmation dwell, and no re-entry cooldown**
anywhere in the options-wall stack (grep for `cooldown|min_hold|hysteres|dwell|debounce`
across `core/` and `scripts/` returns nothing in this subsystem). So the executor is a
bang-bang controller sampling a noisy sign, and each oscillation costs a full ₹212 round trip.

### The true flip rate is worse than the persisted river shows

`SCAN_PERSIST_INTERVAL_S = 30` throttles the regime river, but the executor evaluates every
poll cycle (~13.7s per underlying with three underlyings on a 5s loop). The river's 597 rows
therefore **undersample what the executor acted on**.

I recomputed GEX from the raw chain snapshots at full executor cadence via
`OptionsAnalytics.calculate_gex(..., dealer_side="inferred")` — the production path.
**Validated against the persisted river: 100.00% regime agreement and 0.0000 maximum
`net_gex_cr` difference across 572 matched rows**, so the figures below are on the real
computation, not an approximation.

| | persisted river (30s) | **executor cadence (13.7s)** |
|---|---:|---:|
| Regime changes, 09:30–15:00 | 40 | **55** |
| Negative episodes | — | **28** |
| Median Negative episode duration | — | **28 seconds** |
| Median Positive episode duration | — | **93 seconds** |
| Negative episodes lasting one poll | — | **10** |

**The median regime state survives 28–93 seconds.** A ₹212 fixed cost cannot be paid by a
position whose exit trigger has a sub-two-minute half-life.

---

## 3. The dead band already exists — it is mis-scaled by ~3 orders of magnitude

This is the cheapest lever, and it is not a missing feature.

`options_analytics.py:364` already implements a neutral band, and it is live
(`DEALER_SIDE = "inferred"` in `engine.py:35`):

```python
if dealer_side == "inferred" and abs(net_gex_cr) < OptionsAnalytics.NEUTRAL_BAND_CR:
    regime = "Neutral"
```

`NEUTRAL_BAND_CR = 100.0`. Today's session median |net_gex_cr| was **139,195** — the band is
**~1,400× too small to ever engage.** The regime river contains zero `Neutral` rows all day.
Even the *closest-to-zero* reading inside any flip episode was 2,118 cr, still 21× the band.

The band is the right shape for the job. Because `Neutral` satisfies **neither** the exit test
(`"Negative" in regime`) **nor** the entry test (`"Positive" in regime`), a correctly-scaled
band yields a Schmitt trigger for free, with no new state and no new code path.

In-sample counterfactual on today's SENSEX series (see caveats — this is one day, and any
number read off this table is fitted to it):

| band (cr) | flips | reduction |
|---:|---:|---:|
| 100 *(current)* | 55 | 0% |
| 5,000 | 45 | 18% |
| 10,000 | 37 | 33% |
| 25,000 | 25 | 55% |
| 50,000 | 17 | 69% |
| 150,000 | 7 | 87% |

---

## 4. The flip signal is real but far too small to pay for

Worth establishing, because "the exit rule is noise" would be an overclaim. It is not noise —
it is cheap information bought at an expensive price.

Forward absolute spot move conditional on the regime the executor saw (1,441 evaluations):

| state | n | median 5-min move | median 10-min move |
|---|---:|---:|---:|
| Positive GEX (Stable) | 1,060 | 23.1 pts | 32.4 pts |
| Negative GEX (Volatile) | 381 | **25.2 pts** | **40.6 pts** |

Ratio 1.09× at 5 min, 1.25× at 10 min; Mann-Whitney p = 0.014 / 0.015.

So `Negative` genuinely precedes more movement. But the edge is **2.1 points of additional
expected index movement at the 5-minute horizon** — on a pinned ATM fly whose wings sit ~1,100
points out, the P&L that 2.1 points can produce is a small fraction of the ₹212 it costs to
act on it. (For scale in matched units: ₹212 at qty 20 is **10.6 points of net fly premium**,
which a 2-point spot move on a near-delta-neutral structure cannot generate.) **The exit rule
pays ~₹212 to act on ~2 points of expected index movement.** That is the whole failure in one
line.

*(These p-values use overlapping forward windows and so are optimistic; the direction is
credible, the significance is not load-bearing for the conclusion.)*

---

## 5. Why only SENSEX

Churn needs two things at once: a flipping regime **and** a continuously-armed entry gate.
Only SENSEX had both today.

| index | regime flips | premium_farm rows |
|---|---:|---:|
| NSE_INDEX\|Nifty Bank | **0** | 0 |
| NSE_INDEX\|Nifty 50 | 46 | **0** |
| BSE_INDEX\|SENSEX | 40 *(55 at executor cadence)* | **157** |

BankNifty never flipped. Nifty flipped freely but its farm screen was dark all day, so no
position existed to churn.

**Nifty's farm screen went dark today for a reason unrelated to regime, and this is worth its
own look.** It produced 348 / 113 / 297 farm rows on 09-04 / 09-07 / 09-08 and **zero** today.
Replaying the 12:00 Nifty snapshot through the production path: regime Positive, DTE 6,
IV−RV gap +4.9 — all pass — but `ChainScanner._pin_strike` returned **23,700 against spot
23,489, a 0.898% distance versus the 0.5% `pin_band_pct`**, so `_farm_screen` returned `[]`.

Note the discrepancy: the persisted `session_regime.pin_strike` at that same instant was
**23,500** (0.04% from spot). The dashboard/river pin and the pin the entry gate actually
tests are **different quantities** — the scanner uses `max(gamma_by_strike)` on signed
exposure; the river persists the structural pin.

**Since traced and diagnosed** — see `OPTIONS_WALL_PIN_GATE_DEFECT_2026-09-09.md`. The two
pins agree on 0 of 1,649 Nifty snapshots today; the entry gate's pin sat 0.79% from spot all
session while the dashboard's sat 0.11%, so Nifty failed the 0.5% band **1,649 / 1,649** while
every other gate passed. It is the exact inverse of this report's defect: Sensex armed
continuously and churned, Nifty never armed at all.

---

## 6. What today does and does not establish

**Establishes:** on a near-ideal farm day, the exit rule alone converted a well-behaved
position into a fee pump, and the losses are fully explained by fixed per-round-trip cost
against a sub-two-minute trigger half-life. That claim needs no assumption about edge.

**Does not establish:** that the construct has edge. The +₹1,125 gross (≈ +₹650 after
measured spread) over 19 trades with a 166-second median hold is **not evidence of a working
strategy**. No trade was held long enough to express theta, which is the entire thesis. Today
measures churn cost and is silent on whether short premium on SENSEX works.

**Relation to prior work.** `OPTIONS_WALL_TP_NEVER_FIRES_2026-09-07.md` lowered `tp_frac` to
0.25 and re-expressed the stop as a fraction of `max_loss` specifically so TP could fire on
~21% of trades. **That fix has still never fired.** `regime_flip` preempted it on 19 of 19
trades today. This churn is **not a regression** from the `abee3a5` merge — that merge landed
at 18:28 today, after the close, and `git diff 21e2f4f HEAD -- paper_executor.py` is empty, so
the executor that ran today is byte-identical to the one now in `main`. It is a **pre-existing
defect that the TP/SL fix left untouched and that no prior report examined**:
`OPTIONS_WALL_SECOND_FLY_AND_NIFTY_NON_ENTRY_2026-09-08.md` observed a `regime_flip` exit
(Nifty, 14:44, +₹512) but treated it as correct behaviour.

---

## 7. The invariant worth fixing to

Any specific threshold chosen from today's data is in-sample and will be wrong. The durable
statement is not a parameter:

> **No exit rule may be able to fire before the position's expected P&L movement exceeds the
> round-trip cost of acting on it.**

Today: ₹212 round trip against ~₹8,800 credit, versus a trigger whose median dwell is 28–93
seconds. The system violates this **by construction**, independent of what any threshold is
set to. Whatever remedy is chosen should be justified against this invariant, and any number
attached to it should come from more than one session.

---

## 8. Options

Ordered by leverage per unit of change. These are not mutually exclusive, but they are not
equivalent: **only (D) and (B) actually bind against §7's invariant.** (A) reduces how *often*
a flip fires; it does nothing to stop a surviving flip from firing 12 seconds after entry.
(C) prevents the re-entry, not the premature exit. An operator who takes (A) alone has made
the bleeding slower, not fixed the defect.

**A. Scale `NEUTRAL_BAND_CR` to the magnitude it was meant to guard.** A mis-scaled constant,
not a new feature; buys hysteresis for free since `Neutral` gates neither entry nor exit.
Smallest possible diff. Should be expressed *relative* to a rolling |net_gex_cr| scale rather
than as a fresh absolute constant, since 100 cr was presumably right for some other index or
era and the same mistake is easy to repeat. **In-sample, this alone does not fix it** —
halving the flips still leaves ~25 round trips.

**B. Require the flip to persist before acting (confirmation dwell).** Exit only if `Negative`
has held for N seconds. Must be **time-based, not poll-count-based** — the poll cadence is
~13.7s and varies with the number of underlyings, so a threshold in polls silently changes
meaning when a fourth index is added.

**C. Re-entry cooldown after a `regime_flip` exit.** Directly breaks the pump loop. Weakest of
the four conceptually — it treats the symptom (re-entry) rather than the cause (an exit that
should not have fired), and it adds state the subsystem does not currently carry.

**D. Demote `regime_flip` from an exit to a no-new-entry condition.** The strongest option and
the one I would put first. The regime test already *is* the entry gate; using its inverse as
an exit means the position is a continuous bet on an instantaneous state variable that changes
every 28–93 seconds. Let TP / SL / time-stop own exits — which is what they are for, and what
the 09-07 fix made safe: the stop is now a real fraction of `max_loss` and can actually fire,
which was **not** true before 09-07. This is also what finally gives the TP fix a chance to be
evaluated at all.

  Be clear about the holding period (D) implies. All 19 flies were on the 2026-09-10 expiry —
  DTE 1 as of today — so with `regime_flip` demoted, the binding exit becomes
  `dte <= 1 and now >= 15:15`. A fly opened at 13:00 today would have been held **to 15:15 the
  same session**, not 166 seconds. That is the intended profile, and it is where theta can
  actually be expressed, but it is a materially larger risk window per trade and should be
  entered into deliberately rather than discovered.

**Not the remedy: TP/SL thresholds.** 19/19 exits were `regime_flip`, 0 `tp`, 0 `sl`. Moving
those numbers changes nothing while the regime exit preempts them.

**Also worth deciding, separately:** at qty 20 with ₹160/round-trip of flat brokerage, SENSEX
1-lot flies are structurally fee-heavy. That is a sizing question, not a bug, and should not
be conflated with the exit defect.

---

---

## 9. Resolution — (D) applied 2026-09-09

Operator chose **(D)**. `core/options_wall/paper_executor.py`:

```diff
-    def _manage(self, row, structural, mids, now) -> Optional[str]:
+    def _manage(self, row, mids, now) -> Optional[str]:
         fly = self._rehydrate(row)
         reason = None
-        if "Negative" in (structural.gex.regime or ""):
-            reason = "regime_flip"
-        else:
-            pnl = unrealized_pnl(fly, mids)
-            if pnl is not None and pnl >= self.cfg.tp_frac * row["net_credit"]:
-                reason = "tp"
-            elif pnl is not None and pnl <= -self.cfg.sl_frac * row["max_loss"]:
-                reason = "sl"
+        pnl = unrealized_pnl(fly, mids)
+        if pnl is not None and pnl >= self.cfg.tp_frac * row["net_credit"]:
+            reason = "tp"
+        elif pnl is not None and pnl <= -self.cfg.sl_frac * row["max_loss"]:
+            reason = "sl"
```

`structural` is dropped from `_manage` rather than left unused — no shim. The **no-new-entry
half needed no code**: `_farm_screen` already requires `"Positive" in regime`, so a Negative
regime still blocks entry. `regime_flip` is now produced nowhere; historical rows keep the
string.

Five tests, written before the change and confirmed failing against the old code
(`tests/options_wall/test_paper_executor.py`):

| test | asserts |
|---|---|
| `test_regime_flip_does_not_close_an_open_position` | Negative regime + open position → `None` |
| `test_negative_regime_still_blocks_a_new_entry` | Negative regime + flat → `None` *(passed before the change — documents the preserved half)* |
| `test_tp_fires_during_a_negative_regime` | +30% of credit under Negative → `"tp"` |
| `test_sl_fires_during_a_negative_regime` | −0.5 × max_loss under Negative → `"sl"` |
| `test_time_stop_fires_during_a_negative_regime` | DTE 1, 15:15, Negative → `"time_stop"` |

`tests/options_wall/` + `tests/analytics/`: **158 passed.**

### Replay of today under the new rule

All 1,655 SENSEX snapshots re-run through the real `PaperExecutor` against a temp DB:

| | actual (old rule) | **replay (new rule)** |
|---|---:|---:|
| Round trips | 19 | **1** |
| Gross | +₹1,125 | +₹1,167 |
| Fees | −₹4,043 | **−₹215** |
| **Net** | **−₹2,918** | **+₹953** |
| Median hold | 166 s | **20,147 s (5.6 h)** |
| Exit | 19 × `regime_flip` | **1 × `time_stop`** |

Entered 09:39:12 — short 75,100, wings 76,300 / 74,000, held to the 15:15 square-off. RoM
+6.70%. Swing versus what actually happened: **+₹3,871.**

**Harness fidelity check:** the replay's entry fired at `09:39:12.642824` against live trade
10's `09:39:13.897161` — **1.3 seconds apart, inside one poll cycle (~13.7s)**, on the same
strike and wings. That agreement is the evidence the replay reproduces production, and it is
what licenses reading the table above. (The replay feeds `realized_vol` as a session constant
7.06 where the poller recomputes it per cycle; this cannot move either end — the IV−RV gate
passed with a 7.58 median gap, far from its 2.0 floor, and the time-stop exit is time-only.)

**This is a sanity check, not evidence of edge.** It is one session, and it is the same
session that motivated the change — necessarily favourable. What it establishes is narrow and
worth having: the change does what it was designed to do (one position, held, exits on a real
rule), and the gross was never the problem. Whether short premium on SENSEX pays needs forward
sessions, not this replay.

**Deployment — required:** the running poller holds `PaperConfig` and the executor in memory.
**(D) does not take effect until the poller is restarted.** Confirm no open trade is orphaned
at restart.

**One failure mode is now longer-lived, and is not covered by prior measurement.**
`unrealized_pnl` returns `None` when any of the four legs is unquoted, and TP and SL are both
silently skipped for that cycle. The *set* of reachable exits is unchanged by (D) — a `None`
P&L fell through to the time-stop check before as it does now, and `_close` always required
quotes — but the *exposure window* is not: a position that lived ~166s now lives ~5.6h, so the
interval over which a quote gap can leave TP/SL inert is ~120× longer. `TP_NEVER_FIRES`
measured 0% blind cycles over 545–672-snapshot windows; a held position spans ~1,470, which is
past the measured range. Not a defect today — an extrapolation to watch, measurable from
`wall_chain_snapshots` if a held position ever exits somewhere unexpected.

### Deliberately not done

- **No confirmation dwell (option B).** (D) alone was authorized. If a *sustained* Negative
  regime should still close a position, that is a separate pre-registered change with its
  dwell threshold fixed before the fact — not a bolt-on chosen from this table.
- **The pin-gate defect is not touched here.** See
  `OPTIONS_WALL_PIN_GATE_DEFECT_2026-09-09.md`; it must not ride along with this change.

---

## 10. Caveats

- **One session, one index.** Every counterfactual above is in-sample on 2026-09-09 SENSEX.
  Any threshold picked from the §3 table is fitted to this day.
- The forward-move test (§4) uses overlapping windows; p-values are optimistic.
- §5's Nifty pin-gate diagnosis is a snapshot replay at 12:00, not a full-session
  reconstruction. The pin divergence it surfaces is **flagged, not diagnosed**.
- The GEX recomputation (§2) is validated to exact agreement with production
  (100.00% regime match, 0.0000 max `net_gex_cr` delta, n=572), so the flip counts and dwell
  times are not reconstruction artifacts.

## Reproduction

- Trades: `data/options/wall_scan_results.duckdb` → `trades`, `underlying='BSE_INDEX|SENSEX'`,
  `cast(entry_ts as date) = '2026-09-09'`
- Regime river: same file → `session_regime`
- Raw chains: `data/options/wall_chain_snapshots/2026-09-09.duckdb` (1,655 SENSEX snapshots)
- Executor as it ran today: commit `21e2f4f`; identical to `HEAD` for
  `core/options_wall/paper_executor.py`
