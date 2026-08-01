# CB-N50 HOLDOUT Report — Out-of-Sample IC Confirmation
Generated: 2026-08-01

**Window:** 2020-01-01 to 2022-12-31
**Trading days:** 748
**IC observations:** 746
**Active features:** reversal, basis (momentum dropped in TRAIN)

## Combined Signal (frozen from TRAIN)

- Mean IC: 0.029355
- IC Std: 0.182629
- AC1: -0.0062
- NW SE: 0.006748
- NW t-statistic: 4.3502
- p-value: 0.000015
- **Significant at alpha=0.05: YES**

## TRAIN Comparison

- TRAIN Mean IC: 0.058674 (t=11.4, n=983)
- HOLDOUT Mean IC: 0.029355 (t=4.4, n=746)
- Change: -0.029319

**G3 Gate: PASS**

## Disposition

G4 (futures P&L via breadth) is NOT evaluated. TRAIN already showed
the breadth->futures directional check fails — spending the HOLDOUT
read on a P&L gate we can predict fails is not productive, and the
SEALED window is preserved for a future construct that can clear its
own per_trade_pnl RFA.

The real result is the +0.029 cross-sectional IC —
a constituent-level signal that predicts next-day open-to-open returns
across the Nifty 50 cross-section, confirmed out-of-sample. Its
tradeable home is a long-short constituent book (fresh pre-registration
with per_trade_pnl metric and its own RFA), not Nifty futures via breadth.
