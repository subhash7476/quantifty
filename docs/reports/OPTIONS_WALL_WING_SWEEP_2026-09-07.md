# Wing-width sweep — is `wing_pct` leaving money on the table?

Ran 2026-09-07. NIFTY, EOD closes. **TRAIN 2023-01-01 → 2024-12-31, TEST 2025-01-01 →
2026-07-17.** Policy held at the current post-fix rules (TP `+0.25 × credit`, SL
`−0.50 × L0`, time stop at the DTE-1 mark); only `wing_pct` and the entry DTE band vary.

**Recommendation: do not change `wing_pct`.** The thread is real but it is a leverage dial,
not an edge.

## Predictions stated before the run

1. Wider wings raise mean P&L and tail risk together; P&L-per-margin stays roughly flat.
2. Horizon-scaling is nearly a no-op on our instrument — at DTE 2–5, `√(dte/3.5)` spans
   only 0.76–1.20, so run 3's result should not transfer.
3. Whatever cell wins on TRAIN will not hold rank on TEST.

**All three held.** (1) was slightly wrong in our favour as a warning: per-margin does not
stay flat, it *degrades*.

## Band 2–5 (our instrument)

| wing | TRAIN mean | TRAIN TP% | TRAIN SL% | TRAIN p05 | TRAIN /marg | TEST mean | TEST TP% | TEST p05 | TEST /marg |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.50% | +0.36 | 0.0 | 16.8 | −17.6 | **+0.0176** | −0.68 | 0.0 | −20.9 | −0.0278 |
| 0.75% | +0.89 | 2.6 | 16.3 | −36.2 | **+0.0182** | +0.32 | 3.8 | −39.4 | +0.0058 |
| 1.00% | +1.16 | 6.1 | 14.8 | −57.0 | +0.0145 | +1.32 | 14.1 | −55.8 | +0.0149 |
| 1.25% | +1.03 | 12.8 | 12.2 | −78.8 | +0.0089 | +2.68 | 17.9 | −68.6 | +0.0213 |
| **1.50% (incumbent)** | **+1.56** | **18.9** | **8.7** | **−95.6** | **+0.0098** | **+3.60** | **20.5** | **−80.0** | **+0.0204** |
| 2.00% | +1.95 | 25.0 | 5.6 | −125.6 | +0.0077 | +7.05 | 25.0 | −111.2 | **+0.0257** |
| 2.50% | +2.48 | 29.1 | 3.6 | −144.9 | +0.0071 | +8.50 | 26.9 | −118.4 | +0.0219 |
| 3.00% | +3.24 | 30.6 | 3.1 | −148.0 | +0.0071 | +9.40 | 26.9 | −107.5 | +0.0187 |
| 4.00% | **+3.55** | 31.1 | 0.5 | −155.9 | +0.0053 | **+10.78** | 27.6 | −130.2 | +0.0146 |

## What this actually says

**Mean P&L rises monotonically with wing width on *both* halves.** That is a far stronger
property than one cell winning in-sample — it is a direction, not a peak, and it replicates
out of sample. Tempting.

**But it is leverage, not edge.** Deriving mean margin from `mean ÷ per_margin`:

| | wing 0.75% | wing 4.00% | ratio |
|---|---:|---:|---:|
| TRAIN mean P&L | +0.89 | +3.55 | **4.0×** |
| TRAIN mean margin | 48.9 | 669.8 | **13.7×** |
| TRAIN P&L / margin | +0.0182 | +0.0053 | **0.29×** |

Capital committed rises 13.7× to buy 4× the P&L. A 4% wing on a 2–5 DTE fly is barely a
hedge at all — the structure approaches a naked short straddle, which is exactly why the
stop-out rate collapses to 0.5% and p05 blows out to −156. The apparent improvement is the
position getting bigger, and that decision belongs in `lots`, where it is visible, not
smuggled in through wing width.

**The risk-adjusted optimum is unstable, as predicted.** Per-margin peaks at **0.75% on
TRAIN** (+0.0182) and at **2.00% on TEST** (+0.0257). Two halves, two different answers,
adjacent-to-nothing in common. Rank concordance across all 35 cells is **63.8%** (50% = no
information) — some signal, nowhere near enough to select a parameter on.

**Run 3's "scaling helps" finding is now explained, and it was not about scaling.** The
DTE 10–28 improvement came from `√(dte/3.5)` producing ~3% wings. The band 10–14 and 15–28
rows show that 3–4% wings are simply where TP% reaches 50–60% in *any* band. The mechanism
is width, not horizon-adaptivity. Horizon-scaling on our own DTE 2–5 band would move wings
by a factor of 0.76–1.20 — a rounding error against the 50-point strike grid.

## Two incidental confirmations

- **Our DTE band is right.** Band 2–5 is the only band positive on both halves at nearly
  every wing. Bands 6–9, 10–14 and 15–28 are mostly negative on TRAIN. The pilot is already
  in the good part of the surface.
- **The stop we fixed this morning is live and load-bearing.** At the incumbent 1.5% it
  fires on **8.7% of TRAIN and 6.4% of TEST** trades. Under the old `−2.0 × credit` rule it
  fired on none. And TP% at 18.9/20.5 matches this morning's independent EOD estimate of
  20.5% — two studies, same number.

## Caveats

- **EOD marks.** The executor marks every ~0.9s; TP% here is a floor (measured intraday
  inflation was 1.06–1.34×).
- **NIFTY only.** The pilot also trades SENSEX; bhavcopy covers NIFTY.
- **No regime-flip exit modelled.** That exit is live and would cut some of the tail these
  numbers attribute to wide wings.
- **Neither half contains a volatility event.** 2023–2026 is broadly a calm regime for
  Indian indices. Wide wings are precisely the configuration that a gap would punish, and
  this sample cannot price that. The monotone "wider is better" result should be read with
  that firmly in mind — it is the one result here most likely to be regime-specific.
