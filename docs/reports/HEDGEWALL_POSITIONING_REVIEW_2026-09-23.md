# HedgeWall (@Hedgeewall) — Dealer-Positioning Review

**Date:** 2026-09-23 · **Branch:** `research/options-hedging-scenarios`
**Source:** ~30 public posts on x.com/Hedgeewall (Jul 24 → Sep 23, 2026) + @AshwinBadri2 post of Sep 22.
§1–4: desk review of third-party marketing content. §5: claim 1 tested on repo data (`scripts/research/hedgewall/claim1_hhi.py`).

## 1. What they compute

| Metric | Their definition (from posts) | Our equivalent |
|---|---|---|
| Net GEX | Σ γ·OI·lot·spot²·1%, in ₹ crore per 1% move | `OptionsAnalytics.calculate_gex` (`net_gex_cr`) |
| Gamma Flip | spot level where net GEX changes sign; moves minute-to-minute (23,314 → 23,234 in 30 min on Sep 22) | zero-gamma *strike* (cumulative signed gamma crossing) — coarser |
| Spot − Flip | cushion; above flip = moves absorbed, below = moves run | not built |
| Net DEX | Σ Δ·OI·lot — net dealer delta | not built |
| Call / Put wall | strike with largest call / put gamma | not built as named fields |
| Pin / "pin locked" | dominant gamma strike; "locked" when leader ≫ runner-up (e.g. 2.3×; "not locked" when runner-up ≥ ~40% of leader) | not built |
| HHI | Herfindahl index of gamma share across strikes — concentration, not size | not built |
| Dealer side | 4-quadrant ΔOI × Δprice per strike: OI↑ price↓ = seller arrived (dealer long γ); OI↑ price↑ = buyer (dealer short γ); OI↓ = covering/unwinding | `_infer_dealer_side` — **same method** |
| Two books | GEX on standing OI vs on *today's* ΔOI, labelled separately; "Closing Tape" compares them (e.g. book short ₹6.19L cr delta, today's flow long ₹3.55L cr) | `dealer_side="assumed"` vs `"inferred"` is related but not the same split |

Stated limitations (Sep 13): modal participant only; first 30 min is noise; only today's marginal flow is
classified (standing OI excluded — history unknown); gap days degrade inference.

## 2. Claims worth testing

1. **HHI rises into expiry.** "Pre-CAS, HHI ≈ 0.20–0.25 an hour before expiry"; post-CAS (since 2026-08-03) it
   stays dispersed until ~15:10–15:15. Hypothesis: CAS moves index settlement risk into the 15:15–15:30 window,
   so writers don't concentrate. Falsifiable from our chain snapshots.
2. **Pin strength predicts expiry close.** Leader/runner-up gamma ratio ≥ ~2× → spot settles near the pin.
   Their own Sep 8 case failed (pin 23,700, close 23,635).
3. **Spot-vs-flip regime predicts intraday realized vol / mean reversion.** Above flip → lower RV, fades work.
   This is the load-bearing claim behind the Sep 22 23300 CE trade.
4. **Standing-book vs today's-flow divergence** precedes reversals ("session traded against the position").

## 3. Red flags

- **Evidence is anecdotal and post-hoc.** Winning days are posted; the Sep 8 pin miss was deflected
  ("RSI showed oversold but market still closed lower. Why?"). No hit rate is published.
- **Sign ambiguity.** On Sep 22 at 10:29 they reported gamma *negative* with flip 23,459 *above* spot;
  the 13:47–14:17 table shows GEX *positive* with flip ~23,300 *below* spot. Either the flip moved ~150–225 pts
  in three hours or the two reads use different books — which proves their own point that an unlabelled
  GEX number is ambiguous, and shows how unstable the flip is.
- **Dealer = market maker is a US import.** In Indian index options the writer side is largely prop/FPI;
  the 4-quadrant inference mitigates this only for today's marginal flow.
- Commercial: invite-only, paid, targeted at "50L+ books".

## 4. Relevance to this repo

- We already hold the core (`calculate_gex`, inferred dealer side, 5-s chain snapshots via
  `options_provider.py`). Missing: repriced-spot flip, walls, pin ratio, HHI, DEX.
- Claims 1–3 are measurable on our own snapshot history **without** constructing a strategy — descriptive
  analytics, outside the RFA gate. Anything that becomes a trading rule must clear the RFA first; per the
  RS-MOM finding, a single-index `per_trade_pnl` construct faces the √T_sealed ≈ 1.89 wall.
- Claim 1 overlaps the ISD/CAS 15:29 auction-print issue (memory: ISD SEALED straddles CAS).

---

## 5. Claim 1 test — does expiry-day concentration stay dispersed post-CAS?

### 5.1 Data reality (found before any measurement)
- **No pre-CAS intraday chain exists.** `data/options/wall_chain_snapshots/` begins 2026-09-04 (all post-CAS).
  `options_poller.duckdb` does not exist. HedgeWall's pre-CAS "0.20–0.25 an hour before expiry" baseline
  **cannot be reproduced intraday** — so the pre/post contrast of claim 1 is untestable at their resolution.
- **Post-CAS intraday expiry days with the expiring series captured: 4** — NIFTY 2026-09-08 (capture ends 15:17),
  NIFTY 2026-09-15, SENSEX 2026-09-10, SENSEX 2026-09-17. **NIFTY 2026-09-22 was missed**: the poller captured
  the 2026-09-29 series on expiry day (capture defect in the Options-Wall writer — reported, not fixed here).
- SENSEX days are treated as post-CAS because the CAS register's A9 measures the SENSEX reference freezing at
  15:15 exactly as NIFTY's does.
- **EOD fallback:** `options_bhavcopy` is NIFTY-only, 2016-02-11 → 2026-09-11, so it has a post-CAS arm. It
  measures a *different quantity* (OI concentration at the expiry-day close) and is reported as such.
- **Late-session gamma is not trustworthy.** Vendor gamma evolves intraday (NIFTY 09-15, 23,200 strike: γ 0.0008 @09:30 when ~260 pts ITM →
  0.0035 @15:00 near ATM), but from ~15:10 CE and PE IV at the same strike diverge (99 vs 68 @15:10; 500 vs 961 @15:30),
  and the CAS register's A9 records the index reference freezing at 15:15. Gamma-HHI after 15:14 is shown but
  flagged.

### 5.2 Definitions (pinned before running)
- Expiring series only; strikes with OI > 0 (CE + PE combined per strike).
- **gamma-HHI** = Σ sᵢ², sᵢ = Σ_{CE,PE} |γ·OI| at strike i / total, vendor γ, rows with γ > 0.
- **OI-HHI** = same with OI in place of |γ·OI| — separates positioning from the mechanical effect that BS
  gamma collapses onto ATM as T → 0 (which raises gamma-HHI regardless of positioning).
- Per snapshot, then the median within each clock bucket. NIFTY and SENSEX reported separately (never pooled).

### 5.3 Prediction (stated before the run)
If HedgeWall is right, **gamma-HHI stays < 0.20 until ≥ 15:10 on every covered expiry day**. At n = 4
day-indices this is anecdote-grade in either direction — the same standard §3 applied to their posts.
EOD arm: if CAS dispersed positioning, the expiry-day close **OI-HHI** of post-CAS NIFTY expiries sits in the
lower part of the pre-CAS distribution.

### 5.4 Results (`python scripts/research/hedgewall/claim1_hhi.py`)

**Intraday, median per clock bucket (\* = after the 15:15 reference freeze; not trustworthy):**

| time | NIFTY 09-08 γ / OI | NIFTY 09-15 γ / OI | SENSEX 09-10 γ / OI | SENSEX 09-17 γ / OI |
|---|--:|--:|--:|--:|
| 10:00 | 0.159 / 0.041 | 0.114 / 0.036 | 0.088 / 0.026 | 0.077 / 0.025 |
| 12:00 | 0.175 / 0.043 | 0.127 / 0.039 | 0.099 / 0.028 | 0.083 / 0.025 |
| 14:00 | 0.195 / 0.045 | 0.138 / 0.039 | 0.110 / 0.029 | 0.092 / 0.026 |
| 14:45 | 0.198 / 0.045 | 0.132 / 0.036 | 0.100 / 0.027 | 0.089 / 0.026 |
| 15:00 | 0.195 / 0.044 | 0.128 / 0.034 | 0.097 / 0.027 | 0.085 / 0.026 |
| 15:10 | 0.189 / 0.042 | 0.128 / 0.034 | 0.096 / 0.025 | 0.086 / 0.025 |
| 15:14 | 0.184 / 0.040 | 0.128 / 0.034 | 0.093 / 0.025 | 0.087 / 0.025 |
| 15:20\* | — (capture ends 15:17) | 0.152 / 0.034 | 0.100 / 0.024 | 0.084 / 0.025 |
| 15:25\* | — | 0.327 / 0.032 | 0.213 / 0.023 | 0.200 / 0.027 |

**EOD, NIFTY expiry-day close OI-HHI** — pre-CAS 2024-01-01 → 2026-07-31: n = 135, median 0.037, p10 0.028, p90 0.048.
(Mixed-regime baseline shown for the record; the script now uses the single-regime 2025-09-01 baseline — §5.5 item 4.)

| post-CAS expiry | OI-HHI | percentile in pre-CAS |
|---|--:|--:|
| 2026-08-04 | 0.031 | 0.21 |
| 2026-08-11 | 0.045 | 0.88 |
| 2026-08-18 | 0.047 | 0.89 |
| 2026-08-25 | 0.035 | 0.37 |
| 2026-09-01 | 0.040 | 0.66 |
| 2026-09-08 | 0.034 | 0.34 |

### 5.4b Decomposition from the 14:00 snapshot (positioning path / gamma path)
Positioning path: γ frozen per contract at its 14:00 value, OI(t) varies. Gamma path: OI frozen at 14:00, γ(t)
varies. Median gamma-HHI per bucket.

| time | NIFTY 09-08 | NIFTY 09-15 | SENSEX 09-10 | SENSEX 09-17 |
|---|--:|--:|--:|--:|
| 14:00 | 0.195 / 0.195 | 0.138 / 0.138 | 0.110 / 0.110 | 0.091 / 0.092 |
| 14:45 | 0.200 / 0.194 | 0.131 / 0.134 | 0.106 / 0.103 | 0.090 / 0.091 |
| 15:10 | 0.194 / 0.190 | 0.122 / 0.126 | 0.101 / 0.100 | 0.087 / 0.090 |
| 15:14 | 0.190 / 0.193 | 0.120 / 0.127 | 0.100 / 0.098 | 0.086 / 0.092 |
| 15:20\* | — | 0.119 / 0.127 | 0.099 / 0.133 | 0.082 / 0.092 |
| 15:25\* | — | 0.120 / 0.171 | 0.094 / 0.198 | 0.091 / 0.202 |

Positioning path: flat to slightly falling through 15:25 on every day. Gamma path: flat to 15:14, then carries
the whole post-freeze spike.

### 5.5 Reading

1. **The prediction "holds" — and that is uninformative.** gamma-HHI stays < 0.20 until ≥ 15:10 on all four
   days, but it stays < 0.20 *all day*: the absolute level is set by the strike universe (every OI > 0 strike,
   ~100+ on NIFTY) and the weighting, not by positioning. HedgeWall's 0.20–0.25 is on an undisclosed definition
   (likely a spot band), so **their thresholds cannot be compared to ours**; only the shape can.
2. **Shape: concentration plateaus or falls after ~14:00–14:45 through 15:14**, on all four days, both indices.
   That matches the qualitative claim ("stays dispersed until ~15:10–15:15"). With no pre-CAS intraday series it
   cannot be said whether this is *new* since CAS.
3. **The post-15:15 spike is an artifact, not "concentration finally arriving".** gamma-HHI jumps to 0.20–0.33
   by 15:25 while OI-HHI does not move (0.023–0.034); §5.4b attributes it entirely to the gamma path. Our jump
   lands at 15:20–15:25, later than HedgeWall's cited 15:10–15:15, so it does not by itself explain their read.
4. **EOD: no CAS dispersion in close OI concentration.** Against the mixed 2024-01 → 2026-07 baseline the six
   post-CAS NIFTY expiries span the 21st–89th percentiles. Restricted to a single regime — after SEBI's
   2024-11-20 expiry measures (n = 89: 27th–92nd) or after the 2025-09 Tuesday switch (n = 48: 23rd–96th) — two
   of six (08-11, 08-18) sit **above** p90. If anything post-CAS closes are *more* concentrated, not less.

**Verdict: not demonstrated; the pre/post contrast is untestable at intraday resolution.** Post-CAS, positioning
does drift slightly *less* concentrated from 14:00 to 15:14 (§5.4b positioning path, −0.005 to −0.018) — the
direction HedgeWall describes — but with no pre-CAS intraday series it cannot be called a CAS effect. The only
large late move in HHI is mechanical (gamma path, after the 15:15 freeze). The EOD arm finds no CAS dispersion at
the close and, on a single-regime baseline, leans the other way. n = 4 intraday day-indices, 6 EOD expiries —
descriptive, anecdote-grade.

### 5.6 Follow-ups (not done)
- **Capture defect:** the Options-Wall poller captured the next series on the NIFTY 2026-09-22 expiry day.
  Every missed expiry day is permanently lost for this question. **Root cause found and fixed — merged to main as PR #7 (`492809b`) from
  `fix/options-expiry-lock-poisoning`:** a transient lock on the instrument master at poller start made
  `get_weekly_expiry` fall back to `as_of + 1 day` (skipping today) and memoise it for the session; the same lock
  pinned NIFTY `lot_size` at 75 (true 65) all day. HHI is scale-free, so §5 results are unaffected.
- Recompute gamma from LTP with minute-precise time to expiry and a non-frozen reference (synthetic forward,
  per A9's fix direction) before reading any post-15:15 gamma measure.
- A pre-CAS intraday baseline cannot be recovered from the repo; claim 1's pre/post contrast is untestable here.
