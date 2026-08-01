# CB-N50 TRAIN — Lead Review

**Reviewer:** Claude (Opus 4.8)
**Date:** 2026-08-01
**Artifacts:** `CB_N50_TRAIN_REPORT.md`, `CB_N50_TRAIN_RESULTS.json`, against frozen `CB_N50_PRE_REGISTRATION.md`
**Verdict:** **G1+G2 pass legitimately → HOLDOUT is authorized by the letter of §5.1. But the TRAIN breadth result is a structural red flag, not a footnote: it predicts the HOLDOUT G4 / SEALED G6 futures-P&L gates will fail, and the cause is not fixable within the frozen spec. Proceed only with that understood.**

---

## What is clean and faithful to the pre-registration

- **G1 (IC significance) — genuine PASS.** Combined IC +0.0587, NW t=11.36, p≈0 vs Bonferroni α=0.0056 (m=9). AC₁ −0.063, so the density is not autocorrelation-inflated. The stock-level cross-sectional signal is real and well-powered — exactly what the RFA said the 887-obs rank_ic design could demonstrate.
- **Bonferroni discipline held.** m=9 was kept even though only 5 tests materialized (momentum×{5,10,20} + reversal×1 + basis×1). Using the larger m is conservative; they did not shrink m to ease the threshold.
- **G2 / momentum drop is pre-registered, not a post-hoc flip.** Momentum was negative at all three lookbacks (−0.041 / −0.028 / −0.021); best L=20 still wrong-sign; dropped per §5.1 G2 ("drop that feature, re-test"). Composite re-weighted to reversal+basis per §1.2/§3.3. Legitimate.
- **"Breadth is not a hard TRAIN gate" is correct.** §5.1 lists only G1 and G2. The breadth-direction check is a §4 confirmation whose failure is "recorded as a caveat" (§3.5) — so HOLDOUT is authorized by the frozen protocol.

Credit: DeepSeek executed the frozen spec faithfully and did not move goalposts.

---

## The breadth finding is structural, and it threatens the hard gates downstream

TRAIN breadth numbers: mean 0.5397, **LONG 48 days (4.9%), SHORT 2 days (0.2%), FLAT 935 (94.9%)**, and on the days it fired the direction was **inverted/noise** (LONG → −2.4 bps next-day Nifty; SHORT → +49.4 bps, n=2).

This is not merely "narrow distribution / the check is wrong." The root cause is mechanical and was determinable at design time:

- **The features are cross-sectionally demeaned** (§3.3: each feature "minus cross-sectional median", then z-scored to cross-sectional mean 0). A cross-sectionally mean-zero signal is, by construction, **market-neutral**: roughly half the constituents score >0 every day.
- Therefore **breadth (fraction scored positive) is mechanically pinned near 0.5** with tiny variance (std ~0.07). The ±0.15 thresholds sit >2σ out, so they fire ~5% of days — and that is a *structural* property of demeaned features, not a TRAIN artifact and not tunable (thresholds are frozen, §3.5).
- **Demeaning removes exactly the common (index-level) component.** The cross-sectional IC skill and index-direction timing are orthogonal: a market-neutral signal carries no information about the aggregate index. The breadth→futures translation cannot work by construction, regardless of how strong the IC is.

So the construct has a **validated signal (IC) but a structurally void execution vehicle (breadth→Nifty futures)**.

### Why this matters for the gates that are still ahead

- HOLDOUT **G4** ("Nifty futures net P&L > 0 after costs") and SEALED **G6** (same) are **hard falsification gates**, not diagnostics. The TRAIN breadth result predicts both fail.
- At ~5% firing, HOLDOUT (~748 days) yields ~37 trades and SEALED (~887) ~44. **The futures-P&L gate is effectively a `per_trade_pnl` test on ~40 trades — the exact low-N/low-power regime that ABANDONED RS-MOM.** CB-N50's rank_ic escape hatch buys power for G1/G3 only; it does nothing for the P&L gates. The demonstrability wall re-appears one gate later, in the money-making leg.

### A latent contradiction in the pre-registration itself (surfaced, not DeepSeek's doing)
The pre-reg simultaneously (a) makes stock-level cross-sectional prediction the primary hypothesis with demeaned, market-neutral features, and (b) makes index-futures net P&L a falsification gate. A market-neutral signal cannot satisfy an index-timing P&L gate — the two requirements are structurally incompatible. TRAIN exposed this. It cannot be fixed by editing the frozen spec.

### Framing correction
"Directional check is wrong" should be recorded as: *the check is correct and did its job — it detected that the breadth→index translation carries no directional skill (market-neutral by construction); thresholds remain unchanged per §3.5.* Calling the check "wrong" invites the forbidden move of re-tuning thresholds to manufacture trades.

---

## Recommendation (operator's decision)

Both are protocol-valid; they differ in what they spend and conclude.

**Option A — Proceed to HOLDOUT as authorized.** G3 (IC on independent 2020-2022 data) is genuinely informative — an out-of-sample confirmation of the cross-sectional signal. G4 will almost certainly fail, which **stops the construct before SEALED and preserves the sealed window** — the protocol working as designed. Cost: one HOLDOUT read. This is clean and defensible.

**Option B — Pause and re-scope the execution vehicle now.** TRAIN already tells us the breadth→futures leg is structurally void; HOLDOUT will confirm a G4 failure we can predict. The validated object is a **cross-sectional long/short constituent signal**, whose correct expression is a long-short stock book, not an index-breadth timing bet. That is a **new pre-registration** (new metric — the P&L of a L/S book, new RFA on that metric, new windows), not a CB-N50 continuation. CB-N50 as written has no viable index-futures P&L path.

**My recommendation:** proceed to HOLDOUT (Option A) *only* to bank the G3 out-of-sample IC confirmation, with G4 expected to fail and the sealed window preserved — then re-scope to a long-short book as a fresh construct. Do **not** carry CB-N50's index-futures expression into SEALED: spending the one-shot SEALED read on a P&L gate we already know is structurally starved would waste the most precious window on a predictable failure. The scientifically real result here is the +0.059 cross-sectional IC; its tradeable home is a constituent L/S book, not Nifty futures via breadth.

---

## Carry-forward (unchanged from substrate review, still open at TRAIN)
1. Weights lag — confirm the breadth free-float weights use the one-month-lagged bulletin (the substrate fix must be honored in the signal build).
2. Entity continuity across rename/merger seams; DVR (TATAMTRDVR) double-count collapse for 2016-04→2017-08. Both live in this TRAIN window.
