# Stage A — Gate 0 Decision Memo

**Date:** 2026-08-29
**Screen output:** `STAGE_A_GATE0_SCREEN.md` (script-generated, `scripts/stage_a/gate0.py`)
**Design:** `STAGE_A_DISCOVERY_LAB_DESIGN.md` §6, decision D-A5
**Data read: NONE.** Fee schedules, the frozen power module, and declared
anchors only. Nothing here measures any phenomenon.

---

## Verdict

**Do not build the six-family lab. Two families are worth a scan; one is
already answered; three are cost-dead.** Gate 0 also priced a design option
that matters more than the family slate: **pooling HOLDOUT+SEALED into a single
one-shot confirmatory read lowers the demonstrability bar from 1.22 to 0.888** —
but at the cost of the only pre-terminal alpha-bearing gate. That is an operator
call (D-A6), not a recommendation.

| Screen | Result |
|---|---|
| **0a cost floor** | Round-trip cost is **3.76–4.65 bp** by era (current era 4.53 bp midpoint). Flat in notional — the ₹20 brokerage floor is already immaterial at ₹2Cr, so **there is no size lever**. |
| **0b prior exposure** | F-OPEN is effectively answered by A. Every other family is structurally exposed (DayType features) but evaluatively clean. F-REL carries a 2023+ signal-level read. |
| **0c provisional RFA** | Required **net annualized Sharpe = 1.22** at HOLDOUT n=988 — **family-invariant**. 3 of 9 scenarios clear the most generous ceiling the operator has ever ratified (2.15 gross); the other 6 are cost-dead. |

---

## 1. The governing arithmetic — and why it is family-invariant

`ncp = S_ann · √T`, so cadence cancels. The Sharpe required for power 0.80
depends **only on the gate's calendar length** — not on horizon, event density,
or how hard you condition. Trading a 15-minute event eight times a day instead
of once at the close buys exactly nothing.

| Gate | n (1 trade/session) | Required NET S_ann |
|---|---:|---:|
| **HOLDOUT 2019–2022 — first α-bearing gate under Stage A** | 988 | **1.219** |
| TRAIN 2012–2018 (if it still carried α) | 1,699 | 0.929 |
| SEALED 2023–today | 873 | 1.297 |
| SEALED at A's power floor | 1,270 | 1.075 |

Against A's ratified NET band — the only operator-approved effect band for this
substrate, compared like for like:

- pessimistic 0.70 → **below** 1.22
- **central 1.075 → below 1.22** — this is the §8 defect made concrete: under
  the amendment (judge at the central corner), the HOLDOUT gate **cannot settle
  any construct on this substrate**, whatever the family
- optimistic 1.45 → above 1.22 (why the RFA returned PROCEED at that corner)

The only same-substrate *empirical* anchor is A's realized TRAIN net,
1.271 bp/trade (`trial_ledger.jsonl`, script-generated) = **S_ann 0.20**, which
is **6.2× below** the requirement.

## 2. Where the families actually differ: fixed cost, not signal

Cost is a fixed bp charge per round trip, so its bite in Sharpe terms grows as
the horizon shrinks: `drag_ann = (cost / SD_horizon) · √cadence`.

| Family | Scenario | Horizon | Trades/yr | Cost drag | Req. GROSS S_ann | Verdict |
|---|---|---:|---:|---:|---:|---|
| F-OPEN | A's design (EOD, 1/session) | 313m | 237 | 0.70 | **1.92** | PLAUSIBLE |
| F-GAP | large-gap conditioned, EOD | 313m | 78 | 0.40 | **1.62** | PLAUSIBLE |
| F-RANGE | failed breakout | 60m | 59 | 0.80 | **2.02** | PLAUSIBLE |
| F-VOL | vol-state conditional | 120m | 190 | 1.01 | 2.23 | IMPLAUSIBLE |
| F-RANGE | breakout | 60m | 152 | 1.28 | 2.49 | IMPLAUSIBLE |
| F-OPEN | short-horizon variant | 60m | 237 | 1.59 | 2.81 | IMPLAUSIBLE |
| F-TOD | time-of-day, standalone | 60m | 237 | 1.59 | 2.81 | IMPLAUSIBLE |
| F-REL | N/BN divergence, 30m | 30m | 356 | 2.76 | 3.98 | IMPLAUSIBLE |
| F-REL | N/BN divergence, 15m | 15m | 630 | 5.20 | 6.42 | IMPLAUSIBLE |

Ceiling used: **2.15 gross** — derived, not invented: A's ratified optimistic
NET corner (1.45) plus A's own cost drag (0.70). The verdict column is driven by
that ceiling alone. Multiples against A's *measured* gross are deliberately not
carried here — A's gross does not reconcile (§5.1), so any such multiple would
look load-bearing while resting on an untrusted figure. The screen output
reports them adjacent to the caveat.

**The structural finding, which inverts the brief's intuition.** The survivors
are the **long-horizon, low-cadence, heavily-conditioned** families. Dense
short-horizon event families — precisely the kind a "broad intraday scan across
many horizons" is built to find — are destroyed by fixed cost: F-REL at 15
minutes needs a gross Sharpe of 6.42, nearly ten times anything measured here.
**More events per day is not a route to more power; it is a route to more cost.**

## 3. Prior exposure per family (0b)

| Family | Structural exposure | Evaluative (trading-rule) exposure | Net position |
|---|---|---|---|
| **F-OPEN** | DayType partial-return features, 2012–2025 | **A: full TRAIN + HOLDOUT read, both gates spent** | **Effectively answered.** Gross ~0.68–0.89 S_ann against 1.92 required. A scan re-measures a question already asked |
| **F-GAP** | DayType gap/prev-day context features | None at index level. ISD F4 (equity gap fade) is a different instrument and level | **Genuinely unmeasured** |
| **F-RANGE** | DayType range + CLV features | None | **Genuinely unmeasured** |
| **F-VOL** | DayType realized-vol features | None | Unmeasured, but cost-dead (2.23) |
| **F-TOD** | DayType 10am/11am/13pm checkpoints | None | Unmeasured, but cost-dead and weak standalone |
| **F-REL** | DayType Block H BankNifty intermarket | Pair research 2023+: mean reversion falsified; trending slopes +1.10/+1.17 measured | Unmeasured on DISCOVERY, but the tradable expressions are cost-dead |

## 4. The design option Gate 0 priced

The §8 amendment created a problem: moving the first α-bearing gate to HOLDOUT
raises the bar from 0.929 to 1.219. Gate 0 prices the fix.

| Confirmatory design | n | Required NET S_ann | Net bp/trade at EOD hold |
|---|---:|---:|---:|
| Status quo (TRAIN α-bearing, sequential) | 1,699 | 0.929 | 6.03 |
| Stage A, sequential HOLDOUT then SEALED | 988 | **1.219** | 7.92 |
| **Stage A, HOLDOUT+SEALED pooled as ONE one-shot read** | **1,861** | **0.888** | **5.77** |
| Same, at the 2028 sealed floor | 2,258 | 0.806 | 5.23 |

Pooling 2019 → present into a single one-shot confirmatory read lowers the
demonstrability bar to **0.888** — below the status quo (0.929) and below A's
ratified central corner (1.075), which means a construct with an honestly
defended central band could actually be settled. That is the thing §8 showed is
impossible under sequential gates.

**What pooling gives up — stated properly, because the arithmetic alone is
misleading.** Under sequential gating, HOLDOUT is not a feedback stage; it *is*
evidence — it is the first α-bearing gate, exactly as the design's §8 argues.
Pooling does not remove a convenience, it **merges the cheaper of the two
evidence stages into the expensive one**, leaving no α-bearing gate before the
terminal one. The sequence becomes: DISCOVERY (no α) → TRAIN reproduction check
(no α) → one pooled read that passes or kills.

The concrete cost is A's own failure mode. A died at HOLDOUT on a ~1.3 bp gross
decay across eras, with SEALED preserved. Under pooling, that decay would have
been discovered only *after* 2019 → present was consumed in a single shot —
the construct dies either way, but the window dies with it.

**Second-order caveat: pooling is not era-neutral.** HOLDOUT alone is a single
microstructure regime; pooled 2019 → present spans the vendor tail, native, and
CAS, and straddles two STT changes (0.01% → 0.0125% → 0.02%) that move the cost
lane by ~0.9 bp per §0a. That cuts both ways — a pass is more robust, but the
pooled point estimate averages across a cost regime change rather than measuring within one.

**This is decision D-A6 — an operator call, not an adoption recommendation.**
The trade is: a materially lower bar (0.888 vs 1.219) and a settleable central
case, against losing the only pre-terminal α-bearing gate and spending both
windows together. It supersedes the sequential arrangement in the design
document's §4 and §13 only if the operator takes it.

## 5. Two defects flagged, neither resolved here

**5.1 A's TRAIN decomposition does not reconcile.** `A_HOLDOUT_CLOSURE.md`
reports TRAIN gross +4.41 bp, fees ~1.8 bp, slippage 1.46 bp, net +1.27 bp. But
the frozen fee module A's own `common.py` calls
(`futures_fees.breakeven_round_trip_bps` at the canonical ₹2Cr) returns a
**2.667 bp** mean over the TRAIN window, not 1.8 — and 4.41 − 4.53 is negative
where the ledger records +1.27. The closure also attributes STT 0.0125% to
2019-10-01, while the module's schedule puts that tier at 2023-04-01.

The **ledger's net figures are script-generated and trusted**; the narrative
decomposition table is not. This does not change A's outcome (its HOLDOUT point
estimate was negative on any accounting) but it means A's *gross* is unknown
within ~4.4–5.8 bp, so any multiple stated against it is indicative rather
than exact — which is why the §2 verdict rests on the ratified ceiling alone. Resolving it costs one DISCOVERY read — cheap and legitimate
under this design, but not Gate 0's job.

**5.2 The design document's cost figures were inherited, not measured.**
`STAGE_A_DISCOVERY_LAB_DESIGN.md` §6/§12 quote a 3.3–5.3 bp lane and a ~6.6 bp
P2 floor, taken from A's narrative. The measured lane is **3.76–4.65 bp** and
the current-era P2 floor is **9.07 bp**. Corrected in the design document.

## 6. Recommendation

1. **Decide D-A6 explicitly** — pooled HOLDOUT+SEALED as one one-shot gate
   (bar 0.888, settleable central case) versus sequential gating (bar 1.219,
   but keeps an alpha-bearing gate before the terminal one). Gate 0 prices both;
   it does not pick. This is independent of which families get explored.
2. **Do not build the six-family lab.** Build the minimum: **F-GAP and
   F-RANGE (failed breakout)** are the only families that are both genuinely
   unmeasured and not cost-dead. That is a two-family map, not a 250-cell scan.
3. **Drop F-VOL, F-TOD, and all dense F-REL expressions at Gate 0** on cost
   arithmetic. Record them as screened-out, with the numbers above, so they are
   not re-proposed.
4. **Treat F-OPEN as answered by A** unless the §5.1 reconciliation changes its
   gross materially. If the operator wants it re-opened, the honest framing is
   "resolve A's decomposition," not "explore a family."
5. **Set expectations explicitly:** even the two surviving families need a gross
   Sharpe well above anything this substrate has produced (required gross
   1.62–2.02 against A's net S_ann of 0.20 and a gross that does not reconcile
   below ~0.89). Gate 0
   says *not provably infeasible*; it does not say *likely*. The most probable
   outcome of the two-family scan is two more recorded nulls — which is a
   successful Stage-A run and costs an afternoon rather than a quarter.

## 7. Open decisions

| # | Decision | Recommendation |
|---|---|---|
| **D-A6** | Pool HOLDOUT+SEALED into one one-shot confirmatory gate? | **Operator call — no recommendation.** For: bar drops 1.219 → 0.888, below A's ratified central (1.075), so a central case becomes settleable. Against: it merges the cheaper evidence stage into the terminal one, leaving no alpha-bearing gate before the last, and the pooled read spans three microstructure eras and two STT changes. |
| **D-A7** | Scope the first map to F-GAP + F-RANGE only? | **Yes.** The other four are answered or cost-dead. |
| **D-A8** | Spend one DISCOVERY read to reconcile A's gross decomposition (§5.1)? | **Yes, cheap.** It calibrates every plausibility multiple in this memo and repairs a closed artifact's record. |

## 8. Record

- No market data read. Fee lanes computed from
  `core/execution/futures/futures_fees.py`; power inverted from
  `scripts/rfa/power.py`; anchors quoted from `trial_ledger.jsonl`,
  `governance/rfa/declarations/a_index_intraday.py`, and
  `A_COST_SUBSTRATE_MEASUREMENTS.md`.
- Reproduce with `python scripts/stage_a/gate0.py`.
- SD model: √-of-time scaling off the declared 100 bp / 313 min anchor.
  Intraday volatility is U-shaped, so this understates SD for opening-window
  holds and overstates it midday — a disclosed approximation, not a measurement.
