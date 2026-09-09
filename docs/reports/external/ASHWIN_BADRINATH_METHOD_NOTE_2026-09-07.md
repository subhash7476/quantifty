# Method Note — @AshwinBadri2 (Hedgewall), Aug 27 – Sep 4 2026

Reconstructed 2026-09-07 from a self-quote chain of six public X posts covering **one
trade**. Source is promotional (every post routes to hedgewall.in); read as a marketing
narrative with real screenshots attached, not as a disclosed track record.

## The arc

| Date | Post | What changed |
|---|---|---|
| Aug 27 | "The chart says *falling*. The positioning says *not so fast*." HHI 0.85 → 0.13, net gamma kept **rising** as the market fell, PCR 0.57. "That's my cue for mean reversion." | **Entry** — "a very aggressive bullish spread in the **monthly series**" |
| Aug 28 | "Had sized up yesterday. Morning hit an MFE of 10L and now I'm down. 💀" | **Added size** to the same view |
| Aug 31 | "I'm neither directional nor non directional. What's my view of the market?" | Book now mixed |
| Sep 1 | "Initial bullish view that had gone massively long. **Referencing it with weekly bearish setup** has saved the day with a gain of 5L+ running PnL" | **Overlaid a weekly bearish structure** on the losing monthly longs |
| Sep 2 | "11.5 Cr went massively wrong directionally and the trade still refused to lose more than 0.5%" | MTM −₹1.12L (−0.1%) |
| Sep 4 | "Same payoff. Same positions. Just in a better position. **No adjustments**" | MTM +₹9.13L (+0.79%) |

## Did the position change between Sep 2 and Sep 4? No.

Both posts carry an AlgoTest Scenario Analysis screenshot. Comparing them:

| | Sep 2 | Sep 4 | reading |
|---|---:|---:|---|
| **Charges** | **₹70,928.45** | **₹70,928.45** | **identical — same legs, same lots** |
| Max loss | −₹2,57,84,591 (−22.47%) | −₹2,58,12,805 (−22.4%) | unchanged |
| Margin | ₹11,47,28,227 | ₹11,52,41,078 | unchanged |
| Breakevens | 22983 / 23745 / 24284 | 22964 / 23817 / 24280 | outer two unchanged |
| Delta | −71.86 | −54.94 | drift |
| Gamma | −0.7498 | −1.3272 | more negative |
| Theta | ₹3,60,230 | ₹4,70,851 | rising |
| Vega | ₹1,13,407 | ₹46,429 | collapsing |
| Spot | 23,872 | 23,983 | +111 |

Identical brokerage charges and an unchanged max loss are the decisive pair — a closed or
re-entered leg would move both. The Greek drift is exactly what a **fixed** short-premium
book does as expiry approaches: |gamma| up, theta up, vega decaying. No new legs.

## The method, as far as six posts support it

1. **Signal is dealer-positioning, not price.** HHI (OI concentration), net GEX level *and
   trend*, PCR. The setup is a disagreement between price action and positioning — price
   falling while net gamma rises → fade the move.
2. **Express as a spread in the monthly series**, sized very large (₹11.5 Cr margin).
3. **Scale in.** "Had sized up yesterday."
4. **When wrong, do not cut — overlay.** The Sep 1 "weekly bearish setup" was added
   *against* the losing monthly longs, not a replacement for them. This flattens delta and
   converts the book into a multi-expiry, short-gamma / long-vega / positive-theta
   structure that earns decay while the original mean-reversion thesis plays out.
5. **Then sit.** Hold without adjustment, justified by a GEX-derived pin (23,800–23,900).

So: **building and overlaying, never closing.** Across the entire eight-day arc there is
not one post showing a leg being closed. Weekly legs presumably expire or roll, but that is
inference — no post shows it.

## What the record does not contain

- **No exit.** The chain ends on a favourable mark. How the trade actually closed is unknown.
- **n = 1.** One trade over eight days is not a strategy sample.
- **No losing outcome.** Defend-by-overlay works until the pin breaks. A −22.4% max loss
  (₹2.58 Cr) on a short-gamma book held without a stop is precisely the profile in which
  that tail is eventually realised; nothing here shows what happens then.
- **Selection.** Posts are chosen by the author. The Aug 28 drawdown post is disclosed,
  which is a point in his favour, but disclosure of a drawdown that later recovered is not
  disclosure of the distribution.

## Relevance to our options-wall pilot

Same family as our premium farm — short gamma around a GEX pin — with the opposite exit
philosophy. Our executor closes on TP / SL / regime flip / time stop; he adds an opposing
structure instead of exiting and holds on conviction. Our `regime_flip` exit is close to the
automated form of the judgement he applies manually. Nothing here is portable as a rule: the
one adjustment in the arc was a discretionary overlay sized against a specific pin read.
