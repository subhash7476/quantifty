# NIFTY / SENSEX options read — do the metrics define direction? (2026-09-24)

**Source:** live Options-Wall snapshots (`data/options/wall_chain_snapshots/2026-09-24.duckdb`), captured from 13:05
(orchestrator started 13:04; no morning capture today). Expiring series only: NIFTY 2026-09-29, SENSEX 2026-09-24
(**expiry today**). Scratch scripts, not committed code; descriptive only.

**Method notes.** Vendor Greeks are rounded to 4 dp (≈ 60 % of rows show γ = 0), so gamma is recomputed from each
contract's IV with minute-precise time to 15:30 expiry (`gex_history.bs_gamma`). Net GEX uses calls +, puts − (an
assumption). Flip = strike where cumulative signed gamma crosses zero. ΔOI = the feed's `oi_change` (vs previous
close), summed over strikes within ±2 % of spot.

## 1. Session so far (last snapshot per 15-min bucket)

**NIFTY (29-Sep)**

| time | spot | ATM IV | 25Δ RR | PCR OI | PCR vol | max pain | call wall | put wall | net GEX | flip | ΔOI CE ±2 % | ΔOI PE ±2 % |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 13:00 | 23,183 | 10.6 | −0.83 | 0.72 | 1.13 | 23,300 | 24,000 | 23,000 | +0.12 | 23,450 | +52.8 M | −2.3 M |
| 13:30 | 23,109 | 12.4 | −0.91 | 0.68 | 1.17 | 23,300 | 24,000 | 23,000 | +0.11 | 23,450 | +57.1 M | −7.9 M |
| 14:00 | 23,069 | 13.3 | −1.15 | 0.65 | 1.18 | 23,300 | 24,000 | 23,000 | +0.12 | 23,400 | +63.6 M | −10.1 M |

**SENSEX (24-Sep, expiry day)**

| time | spot | ATM IV | PCR OI | PCR vol | max pain | call wall | put wall | net GEX | flip | ΔOI CE ±2 % | ΔOI PE ±2 % |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 13:00 | 74,013 | 34.6 | 0.61 | 1.29 | 74,100 | 74,200 | 74,000 | +0.15 | 74,400 | +51.5 M | +14.9 M |
| 13:30 | 73,774 | 42.9 | 0.54 | 1.32 | 74,000 | 74,200 | 73,500 | +0.10 | 74,400 | +49.7 M | +10.2 M |
| 14:00 | 73,631 | 49.0 | 0.54 | 1.35 | 73,800 | 74,000 | 73,000 | +0.12 | 74,100 | +49.9 M | +8.3 M |

## 2. What a chart-reader would say

Both indices fell ~0.5 % after 13:05. The conventional read is **bearish-leaning**:
- **Call writing near spot, put unwinding:** NIFTY ±2 % ΔOI CE +63.6 M vs PE −10.1 M. SENSEX CE +49.9 M vs PE +8.3 M.
- PCR OI falling (NIFTY 0.72 → 0.65, SENSEX 0.61 → 0.54).
- NIFTY put skew steepening (25Δ RR −0.8 → −1.2) and IV rising as spot falls.
- Spot below the cumulative-gamma flip (NIFTY 23,400 vs 23,069).

Pointing the other way:
- Max pain is **above** spot in both (NIFTY 23,300, SENSEX 73,800).
- Net GEX is **positive** (+0.12), which reads as "dampened moves".
- NIFTY sits ~70 points above its 23,000 put wall.

The metrics disagree with each other, and the net-GEX-positive / spot-below-flip pair contradicts itself (the same
ambiguity flagged in the HedgeWall review).

Caveats:
- **Most of this follows price rather than leads it.** When the index falls, calls near spot become cheap to write and
  puts get unwound, skew steepens, and IV rises (spot–vol correlation).
- **SENSEX today is expiry day:** ATM IV 35 → 49 is the mechanical T → 0 effect, and 25Δ RR is noise. After 15:15
  the reference freezes (CAS), so late-session reads are unreliable.

## 3. Have these readings called direction before? — No

The 14:00 reading on each snapshot day 2026-09-04 → 09-23 was compared against the 14:00 → 15:14 index move
(NIFTY + SENSEX, n = 26, effectively ~13 independent days — the two indices move almost identically).

| 14:00 metric | Spearman ρ vs next ~75 min | p |
|---|--:|--:|
| PCR (OI) | +0.26 | 0.21 |
| put-writing tilt (ΔOI PE − CE, ±2 %) | −0.01 | 0.97 |
| net GEX | +0.07 | 0.75 |
| max-pain gap (max pain − spot) | −0.08 | 0.70 |

Sign hit-rate: writing tilt **42 %**, max-pain gap **42 %** — no better than a coin.

## 4. Conclusion

**The metrics do not define direction.** Today they lean bearish mostly because the market has already fallen, and
over the ~13 sessions of snapshot history none of them anticipated the late-session move. The only option-structure
result in this repo with statistical support is about **volatility, not direction**: Stage A found that high
end-of-day net GEX precedes a calmer-than-implied next day (`GEX_REGIME_STAGE_A_*`). The sample here is anecdote-grade
in both directions; a real directional test would need a pre-registered design and far more sessions.
