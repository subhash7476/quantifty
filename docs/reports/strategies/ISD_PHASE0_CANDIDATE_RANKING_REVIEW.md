# ISD Phase-0 Candidate Ranking — Lead Review

**Reviewed:** `ISD_PHASE0_CANDIDATE_RANKING.md` (v2, 2026-08-25, uncommitted working tree)
**Reviewer context:** independent re-derivation; no gated window touched, no signal-level read of the 1m store performed (review stayed inside the document's own discipline: calendar arithmetic, snapshot inspection, `scipy.stats.norm` re-computation).
**Date:** 2026-08-26

---

## Verdict

**ACCEPT WITH REQUIRED REVISIONS — nothing structural blocks the freeze.** This is the
best-grounded Phase-0 document this repository has produced: it answers all three
historical death modes *by construction*, its resolutions are mostly mathematically
correct, and every substrate claim I checked ties to the certified Phase-1 snapshot.
But the document contains **two hand-computed power figures that are wrong**, several
freeze-blocking specification gaps (label definitions, BH scope, paper-interval
contamination rule), and one asserted-but-unmeasured quantity (turnover) sitting at
the center of the cost argument. All are fixable before freeze; none requires new
data reads.

The operator should hear this plainly: *"I want this to work"* is precisely the
pressure this governance exists to resist. The review below is written adversarially
on purpose. The good news is that the design survives it better than any predecessor.

---

## 1. Independently verified (recomputed, not trusted)

| Claim in document | Recomputed | Verdict |
|---|---|---|
| z_α + z_β = 2.487 (α .05 one-sided, power .80) | 2.48647 | ✓ |
| Floor n = (2.487·0.20/0.028)² ≈ 315 | 315.57 | ✓ |
| Central power at floor (n=315): ncp 2.49 → 0.80 | ncp 2.485 → 0.7995 | ✓ |
| Pessimistic corner at floor: ncp 1.42 → 0.41 | ncp 1.420 → 0.411 | ✓ |
| HOLDOUT n=270 central power 0.74 | ncp 2.300 → 0.7440 | ✓ |
| TRAIN n=474 central power 0.92 | ncp 3.048 → 0.9197 | ✓ |
| SE(sd) = sd/√(2n) ≈ 0.7% at n=474 | 0.20/√948 = 0.65% | ✓ |
| Session fences sum: 474+270+159 = 903 | equals certified sessions exactly (snapshot: 903, 2023-01-02→2026-08-24) | ✓ |
| Slippage drift p90 ≈ 2.7–2.9 bp/side | G6 pooled deciles: 2.35–2.90 (deciles 2–9 match) | ✓ |
| Fees ~11 bp round trip | ₹5L ticket = 4.47 bp fees + ~2×2.8 bp drift ≈ 10.1 bp | ✓ (conservative) |
| Resolution 2: rank(x_i − x̄) ≡ rank(x_i) | Correct — and Pearson IC is affine-invariant too, so identical under either IC definition | ✓ |

**Two figures fail recomputation** (see R1).

---

## 2. Findings

### R1 · MINOR-BUT-MUST-FIX (numbers) — two power figures are wrong
- §4 "at n = 159 central power is **0.60**" → true value **0.55** (ncp 1.765,
  Φ(ncp−1.645)). The 0.60 figure back-solves to δ≈0.030, not the declared 0.028.
- §8/§4 optimistic corner "power **0.9999**" → true value **0.9937** (ncp 4.141).

Neither changes any decision (159 stays far below the floor; the optimistic corner
stays far above the hurdle). But this document is explicitly *the decision sheet the
freeze will be built from*, and the spec's guardrail 7 says script-generated numbers
only. These two were evidently hand-derived. Regenerate the entire power table from
`scripts/rfa/power.py` before freeze and embed the script output verbatim.

### R2 · BLOCKING-BEFORE-FREEZE (specification) — labels and execution points unpinned
Neither family pins the exact **measurement windows and execution prices**:
- Family 1: is the IC label the return **10:00→15:29 close** (post-entry leg, clean),
  or open→close (which includes the signal window itself and mechanically inflates
  continuation)? Entry at 10:00 bar open or 09:45 bar open for the 09:15–09:45 cell?
- Family 4: entry at the 09:15 opening print (auction print — not always reachable
  in size) vs first 1m bar close? Exit at 15:29 close?

If the label overlaps the signal window, the IC is inflated by construction — the
single easiest way for this battery to produce a false TRAIN pass. Pin, in the
pre-registration: feature window, entry price/bar, exit price/bar, and the exact
return algebra for the IC label and for the P&L ledger (they may legitimately differ;
say so explicitly if they do).

### R3 · BLOCKING-BEFORE-FREEZE (multiplicity) — BH scope and the TRAIN double-duty of Family 4
- "BH control across cells" — across all 16 cells (2 families × 8) or within family?
  With 16 cells, per-cell α = 0.003125; the TRAIN gate's stated α = 0.05 must be
  declared as *family-wise after BH* or the plateau rule does the work instead — pick
  one and write it down. Ambiguity here is a future dispute.
- Family 4 reads TRAIN twice (sign discovery + IC gate). The CARRY precedent accepted
  exactly this, but CARRY's record discloses it. Do the same: state Family 4's
  effective m > 1 and that its TRAIN IC gate is conditional on the TRAIN-discovered
  sign. Family 1's mechanism-pin avoids this — that asymmetry is a genuine advantage;
  keep it visible.

### R4 · MAJOR (cost argument) — turnover canvas is asserted, not measured
§3's canvas (τ 0.25→0.50 ⇒ 7→14%/yr) presumes banding holds one-way daily turnover at
or below 0.50. An unbanded daily-rebalanced 200-name rank book plausibly turns over
~1.0+/day ⇒ ~27%/yr drag — off the canvas entirely. The banded-exit cells exist, but
the pre-registration should commit: **turnover τ is measured empirically per cell on
TRAIN and the net-spread gate is applied at each cell's measured τ** — never at an
assumed τ. This is the PSB lesson restated at intraday cadence; do not let the
canvas table quietly become the assumed operating point.

### R5 · MAJOR (sealed-read calibration) — name the accepted risk
At the floor, pessimistic-corner power is 0.41: **if truth sits at the pessimistic
corner, a SEALED FAIL happens 59% of the time even though the effect is real.**
Raising the floor to cover that corner needs n≈966 sessions (~2029) — impractical,
so the compromise is right; but the document should say outright: *the read is
calibrated to detect the central effect; a FAIL retires the construct regardless and
cannot distinguish "weaker than central" from "unlucky."* Silent compromises become
post-hoc grievances; disclosed compromises become discipline.

### R6 · MAJOR (protocol) — paper-interval contamination rule missing
Q5 puts ≥3 months of forward PAPER inside what will later be spent as SEALED data
(the floor lands ≈2027-03; paper runs concurrently). Nothing currently forbids
adapting during that interval based on observed paper P&L — which would be
adaptation-on-sealed-data. Freeze the rule: **during the paper interval, only the
pre-registered mechanical criteria may act; no parameter edits, no early abort on
eyeballed P&L; any discretionary change restarts the paper clock and is logged in the
trial ledger.** This closes the TS Basis Daily failure mode (iterative promotion on
evaluation surfaces) at its last remaining entrance.

### R7 · MINOR (honesty of the anchor) — δ band is a plausibility envelope, not evidence
The δ band [0.020, 0.035] leans on CB-N50 HOLDOUT +0.029 — which came from EOD
close-to-close *reversal + basis* features on 50 names. Neither ISD family shares a
feature family with it. The shrinkage instinct (use the OOS number, not TRAIN +0.059)
is exactly right, and using the nearest in-house OOS read as a generic cross-sectional
prior is defensible — but label it as such: *no direct prior estimate exists for
opening-drive or gap cross-sectionals; the band asserts plausibility, not precedent.*
One sentence in §8 fixes this. (Directionally, intraday-derived features carry more
information than EOD features, so the band is more likely conservative than
generous — but that is an argument, not a measurement.)

### R8 · MINOR — "low ρ" between families is asserted, not known
Gap (prev_close→open) and drive (09:15→10:00) frequently co-move: big gap-up names
tend to open strongly. Whether the two *books* are weakly correlated is an empirical
property of the rank residuals. Pre-commit: book-level return correlation ρ₁₄ is
**reported at TRAIN, never optimized on**; composite talk waits until both families
have their own gate results. (The breadth thesis only earns its power claim if ρ is
genuinely low — measure it, don't assume it.)

### R9 · NOTE — conditioning covariates are tuning surfaces unless frozen
The spec lists VIX regime and prior-day delivery-% as available conditioners. The
§9 grid freezes only {window} × {band} × {exit}. Either the pre-registration states
*"no conditioning covariates in v1"* (recommended — smallest surface), or it freezes
each covariate with a pre-committed sign and mechanism (the delivery-% prior-exposure
rule in spec §4). An unfrozen covariate list is where freedom leaks back in.

### R10 · NOTE — slippage model boundary
G6's drift is bar-to-bar (next-bar-open vs signal-close) on 1m bars: it captures
latency/short-horizon drift, **not own-order impact, halts, or circuit limits**, and
its decile profile is suspiciously flat (2.35–2.90 bp everywhere — real impact rises
with illiquidity). Fine for a research hurdle at ₹5L tickets in F&O-eligible names;
not a claim about live fill quality. Keep the ADV cap in every cell's book
construction and treat live-paper divergence as information when it arrives.

### R11 · NOTE — small factual nits
- "Fees ~5–6 bp at ₹5L tickets": the G6 table says **4.47 bp** at ₹5L (5.88 bp at ₹2L).
  Conservative overstatement; cite the actual row.
- §2 "159 (today)" counts through **2026-08-24** (certified store's last session);
  pin the as-of date in the pre-registration.

---

## 3. Research grounding of the two families (the operator's second question)

### Family 1 — Opening-drive continuation: prior genuinely supportive, correctly fenced
- **Academic anchor is real and strong at the index level:** Gao, Han, Li & Zhou
  (2018, *JFE*) — first-half-hour market return predicts last-half-hour return
  (US, indexes and size-sorted portfolios; robust out-of-sample in their
  international checks). Mechanism chain (order-flow imbalance → partial adjustment
  → late-day continuation) is standard microstructure, not just a stylized fact.
- **NSE-specific support:** the 2010 pre-open call auction concentrates opening
  information into a single auction print, which sharpens exactly the signal this
  family uses. In-house: the Nifty/BankNifty pair work found intraday index moves
  *trend* (+1.10/+1.17 slopes) — the strongest empirical hint this repo owns that
  NSE intraday flow persists rather than mean-reverts.
- **Honest counterweights:** (a) the index-level anchor does not automatically
  transfer to a *cross-section* of stocks; single-stock intraday continuation is
  weaker in the literature than index intraday momentum; (b) CB-N50's negative
  daily close-to-close momentum is scoped out by horizon — the argument given is
  correct, but it means the sign pin rests on mechanism + index analogs, not on any
  stock-level in-house read. The §9 guard (negative TRAIN ⇒ family closed, no
  sign-flip fishing) is therefore the load-bearing element. It is the right guard.
- **Net prior:** modestly favorable — the best-evidenced of the two families, and
  the cheapest to kill cleanly.

### Family 4 — Overnight-gap cross-sectional: direction honestly unknowable ex-ante; TRAIN-burn is the right call
- The tug-of-war decomposition (Lou, Polk & Skouras, 2019, *JFE*) is monthly-horizon
  and says nothing decisive about the same-day intraday fade of a gap.
- Berkman, Koch, Tuttle & Zhang (2012, *JFE*) finds retail-sentiment-driven
  overnight moves reverse intraday (fade side); the information-runup literature
  supports continuation for news gaps (continue side). The document's
  "two mechanisms, opposite signs, not separable ex-ante without event
  classification" is an accurate reading — event classification would be a tuning
  surface, so refusing it is correct.
- Practitioner gap-fill statistics are time-series/single-instrument (the FTMO
  corpus tested that family and found a high-power null on indexes — another reason
  the cross-sectional version is the untested quadrant rather than a repeated one).
- **Net prior:** symmetric coin-flip on sign with whatever magnitude TRAIN reveals.
  Declaring the burn once, in advance, with one-sided tests afterward, is the
  CARRY precedent executed properly.

### Why this quadrant is the right place to spend the next window
The repo's own closed programs established: (i) delivery-equity fees kill sub-monthly
EOD turnover (PSB-1/2, three confirmations); (ii) `per_trade_pnl` on thin calendar
windows cannot reach power (FLOW, RS-MOM); (iii) `rank_ic` over a genuine daily
cross-section is the demonstrated √n escape (CB-N50); (iv) time-series intraday
price patterns on indexes were a high-power null in-house (FTMO corpus, 0/41).
ISD combines (iii)'s statistics with (iv)'s horizon while swapping in the intraday
fee structure that removes (i) — **that is the one quadrant none of the dead programs
occupied.** The design is not a reopen of anything retired; it inherits no burned
windows: TRAIN/HOLDOUT fences sit on native 1m equity history that no strategy
research has consumed (ops/paper infra usage disclosed and plausible), and SEALED
2026-01→spend-date is genuinely unread by this program.

---

## 4. Required revisions before freeze (checklist)

1. Regenerate every power figure from `scripts/rfa/power.py`; fix R1 (0.55, 0.9937).
   Embed script output; no hand-derived numbers anywhere in the pre-registration.
2. Pin labels + execution points per family/window cell (R2): feature window, entry
   bar/price, exit bar/price, IC-label return algebra, P&L return algebra.
3. Declare BH scope across all 16 cells (or hierarchical family→cell) and state the
   TRAIN gate α after BH (R3).
4. Commit to measured-per-cell turnover τ for the net-spread gate; retire the canvas
   as illustration only (R4).
5. Add the sealed-calibration disclosure sentence (R5).
6. Add the paper-interval contamination rule (R6).
7. Add the anchor-transferability sentence (R7) and the ρ-reporting commitment (R8).
8. Decide covariates: exclude from v1, or freeze with pre-committed signs (R9).
9. Fix the fee-table citation and pin the session-count as-of date (R11).

Then write the pre-registration document, freeze the RFA declarations with SHAs, and
run the battery. No further review round is needed on this ranking document if items
1–6 land; 7–9 are one-line edits.

---

## 5. What would kill this program (so nobody rediscovers it later)

- A TRAIN pass produced by a label overlapping the signal window (R2) — the false
  positive that reaches HOLDOUT looking brilliant and dies at SEALED.
- Post-HOLDOUT grid widening "because TRAIN looked flat" — the exact freedom §9
  already forbids; the trial ledger must show zero cells added after the first run.
- Tuning during the paper interval (R6) — contaminates the sealed spend silently.
- Treating the ~11 bp cost basis as fixed forever: it assumes ₹5L tickets in
  F&O-eligible names; if the book migrates down the liquidity curve, costs rise
  nonlinearly and the whole cost canvas shifts.
- Reading the vendor deep archive after first results "just to check" — Q1 froze
  native-only; the archive's option value is as an *unread reserve*, and it evaporates
  the moment it informs any choice.
