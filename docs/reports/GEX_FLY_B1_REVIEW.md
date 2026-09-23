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

## 2. What the numbers say — the constraint is effect size, not cost

Decomposition on the same 142 B1 trades (scratch re-simulation with costs zeroed; no new window read):

| run | Sharpe, zero costs | Sharpe, zero fees, spread 0.5 % / 1 % | gross mean R | brokerage+GST R / trade |
|---|--:|--:|--:|--:|
| fly, N-gated (primary) | **+0.22** | +0.07 / −0.08 | +0.015 | 0.023 (of 0.027 total fees) |
| fly, ungated | −0.35 | −0.49 / −0.63 | −0.028 | 0.022 |
| straddle, N-gated (descriptive) | +0.54 | +0.47 / +0.40 | +0.113 | 0.019 |

- **Even at zero cost the gated fly is nowhere near demonstrable.** Power 0.80 at one-sided α 0.05 needs
  years ≈ (2.49 / S)²: **≈ 128 years at S 0.22**; the confirmation window is ≈ 3.7. The RFA's ~1.3 bar is out of
  reach at *any* cost assumption, so reducing costs (more lots per order, tighter NIFTY spreads than the 2 % stock-option
  convention) cannot change the outcome. This is the SFB-1 / RFA demonstrability wall, not the PSB fee wall.
- **N does carry into the trade.** Ungated, the fly is negative *before* costs (−0.35); gating on N turns it positive
  (+0.22). Stage A's finding is visible in P&L — the effect is simply small relative to the fly's P&L noise.
- **Fees are mostly flat brokerage:** ₹20 × 8 orders × 1.18 GST on a single lot is 0.023 of the 0.027 R per trade;
  statutory charges are ~0.004. That explains the negative break-even spread but, per the first bullet, not the verdict.
- **Exits were regime- and time-driven:** 62 regime, 74 time, 6 profit, 0 stop (§3).
- The N-gated unhedged straddle (descriptive) is the strongest gross (+0.54) but has unlimited risk and a −20.0
  drawdown, and would still need ≈ 21 years for power 0.80.

## 3. Disclosed spec error — the stop rule was unreachable

The spec (§3 stop at loss ≥ 1.0 × credit) was designed on my claim that a ±1σ fly's max loss is ~1.5–2.5× credit.
That was wrong. On the 142 B1 trades, **credit / wing width = 0.59 (range 0.51–0.62), so max loss / credit = 0.70
(range 0.60–0.96)** — the stop could never fire; the wings did the capping (worst trade −0.85 × credit gross).

This does not drive the verdict: a stop truncates losing tails, while the problem is the *average* trade's gross
edge (+0.015 R, gross Sharpe +0.22 — §2). Re-running with a reachable stop (e.g. 0.5 × credit) would be a post-hoc re-specification on
a read window and is **not** done. Lesson for any future spec: express stops as a fraction of **max loss**, and verify
the ratio on the structure before pinning.

## 4. What remains open

- **Forward paper is permitted but is not a live path to proof:** at S ≈ 0.2 it would need on the order of a century.
  Paper could only *disprove* quickly, and B1 already gives no reason to expect a positive result.
- Any successor is a new pre-registration and must clear the RFA arithmetic **first**, on a gross Sharpe band that is
  independently defended — bigger size or a different wing choice does not move a 0.2 gross Sharpe to 1.3.
- Stage A stands on its own: N predicts next-day realized vs implied, and it measurably improves the fly's P&L. Its
  size is what is not tradeable-demonstrable on the available history.
