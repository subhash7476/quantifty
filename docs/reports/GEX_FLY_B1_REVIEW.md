# GEX Fly Stage B — B1 review (hand-written interpretation)

**Date:** 2026-09-23 · **Branch:** `research/options-hedging-scenarios`
**Reads:** `GEX_FLY_B1_DEV.md` (script-generated, code rev `2ffa32e`). Spec:
`docs/superpowers/specs/2026-09-23-gex-fly-stage-b-design.md`. Numbers are quoted, not recomputed, except §3's
credit/width check (scratch script over the same B1 trades; no new window read).

## 1. Verdict

**B1 STOP — the N-gated iron fly is not demonstrated on 2019-02 → 2022-12 history.** Stop rule 1 fires: net Sharpe
−0.75 @ 2 % spread (−0.46 @ 1 %, −1.32 @ 4 %), 142 trades, mean R −0.054 per trade, every year negative. No RFA, no
sealed read. Per the interpretation rule (spec §2) this is a statement about that window, not about the construct in
today's market.

## 2. What the numbers say

- **N does carry into the trade — just not enough.** Stop rule 2 does *not* fire: gated −0.75 vs ungated −1.23;
  mean R −0.054 vs −0.097; max drawdown −10.1 vs −21.8 risk units. That is Stage A's finding showing up in P&L.
- **Costs are the binding constraint, by a wide margin.** Gross mean R ≈ +0.015 per trade (§3); fees 0.027 plus spread
  0.043 per trade (≈ 0.069) are ~4.5× the gross. **Break-even spread is −0.5 %** — fees alone exceed the gross edge,
  so no spread assumption rescues it. Short holds (2.7 sessions, 8 orders per round trip) make this structural.
- **Exits were regime- and time-driven:** 62 regime, 74 time, 6 profit, 0 stop.
- **Descriptive structures** (not part of the rule): the N-gated unhedged straddle is the only positive one
  (Sharpe +0.15, break-even spread 3.1 %) but with a −20.0 drawdown and unlimited risk; the condor is −0.27.
  This matches the seller-edge study's pattern: the wings' cost is paid every trade, the tail they insure rarely arrives
  within a 3-session hold.

## 3. Disclosed spec error — the stop rule was unreachable

The spec (§3 stop at loss ≥ 1.0 × credit) was designed on my claim that a ±1σ fly's max loss is ~1.5–2.5× credit.
That was wrong. On the 142 B1 trades, **credit / wing width = 0.59 (range 0.51–0.62), so max loss / credit = 0.70
(range 0.60–0.96)** — the stop could never fire; the wings did the capping (worst trade −0.85 × credit gross).

This does not drive the verdict: a stop truncates losing tails, and the gap here is cost vs. gross on the *average*
trade (0.069 vs 0.015). Re-running with a reachable stop (e.g. 0.5 × credit) would be a post-hoc re-specification on
a read window and is **not** done. Lesson for any future spec: express stops as a fraction of **max loss**, and verify
the ratio on the structure before pinning.

## 4. What remains open

- **Forward paper is still permitted** (spec §2, §7) and is the only evidence about today's market — but B1 gives no
  reason to expect it to clear fees at this holding period.
- A construct that could plausibly survive would need **far fewer round trips per unit of edge** (longer holds, fewer
  legs) — that is a new design with its own pre-registration, not a Stage B variant. The cost wall is the same one
  PSB-1/PSB-2 hit in cash equity, here in options: short-horizon edges of a few bp per day do not survive 8 orders.
- Stage A stands on its own: N predicts next-day realized vs implied. It is a real descriptive fact whose P&L
  expression at a ~3-session fly horizon is not demonstrated.
