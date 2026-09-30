# Second-Opinion Audit — RFA Framework (Muse hostile audit) + M1c RFA chain

**Date:** 2026-09-30 · **Status:** independent second review, read-only. No market data read, no backtest, no
strategy design, no framework redesign, no next-idea selection.
**Audited:** `RFA_FRAMEWORK_HOSTILE_AUDIT_2026-09-29.md` ("Muse"); M1c protocol **v1.3** (`a69f23a`) — **no
v1.4 exists** in any branch or commit, the chain ends at frozen v1.3, which is what was audited; M1c RFA
declarations v1–v4 (`a9399c3`, `66bcc42`, `f4b7e44`, `d86f0b3`); `M1C_RFA_V3_REVIEW`, `M1C_RFA_V4_REVIEW`;
`scripts/rfa/{power,gate}.py`; `governance/rfa/declaration.py`; RFA design spec §2.2; closure ledger §4;
coverage map v1.1; `CB_N50_HOLDOUT_REPORT.md` (for the anchor's published statistics); `n50_ls.py` provenance.
All figures below recomputed with `scipy` (noncentral t / normal) from the documents' own inputs.

---

## A. RFA framework

**A1. Optimistic-corner power math — CORRECT.** `power_at` computes noncentral-t power with ncp = δ√n/σ at
the Student-t critical value; `per_trade_pnl` passes δ = S/√c, σ = 1, n = c·T so ncp = S√T. Recomputed:
FLOW 0.6053 (exact), N50-LS ≈0.75, RS-MOM ≈0.34, A-INDEX ≈0.872, CB-N50 ≈1.00. Muse's reconstruction is right.
One unflagged detail: for `two_sided` the code evaluates only the upper rejection tail — conservative by a
negligible amount (NON-MATERIAL).

**A2. Monotonicity — CORRECT.** Power is increasing in δ, S, n, α and decreasing in σ, so the optimistic corner
(δ_hi, σ_lo, or S_hi) maximises power over the band; ABANDON at the corner implies ABANDON everywhere in the
band. `n_required`'s bisection relies on the same monotonicity in n and is valid.

**A3. What RFA tests — CORRECT, with a narrowing CAVEAT.** It tests only whether a *stylised* version of the
declared test (iid/normal noncentral t; overlap/HAC and non-normality handled, if at all, by hand) reaches
0.80 power at the declared best-case magnitude and the fixed n. It is narrower than Muse states: it is power of
an idealised test, not of the pinned statistic's exact finite-sample behaviour (HAC size, skew, selection).

**A4. Bands are the critical human input — CORRECT.** With n, α, sidedness and hurdle fixed by calendar and
convention, the band ceiling is the only input carrying world-content. The design spec concedes this itself
(§2.2: "Ordering does not confer independence… The control is the written, defended, frozen argument plus
explicit disclosure. Nothing else."). Muse documents the consequences; the limitation was declared.

**A5. Optimistic-corner-only adjudication and false negatives — mixed.**
- §10(a) false-positive risk from reading only the optimistic corner: **CORRECT** (STOCK-STRADDLE central
  implies ≈0.59 vs verdict 0.82).
- §9(a)–(c) false negatives from a mis-set ceiling, SD, or breadth: **CORRECT** — these are band errors, not
  rule errors.
- §9(f) "the verdict reads the least-plausible corner, so a construct whose truth sits at central-but-not-
  ceiling … is abandoned despite realistic feasibility": **ERROR.** The optimistic corner is the most
  PROCEED-lenient reading of the band; if it is underpowered the central corner is strictly worse. The rule
  cannot generate a false negative relative to the band — only a mis-specified band can.
- §9(d) "frozen-n shortfall conflated with no-edge": correct as a description of *interpretation* risk, not
  of the math.

**A6. Meaning of ABANDON — CORRECT.** Logically, ABANDON = "the frozen experiment cannot demonstrate the
declared effect at 0.80 power under its declared band and test form." It carries no information on whether the
mechanism has an edge; no data is read and no belief is updated. The design's "ABANDON is dispositive… do not
build it" is a governance disposition built on that narrow proposition, not an epistemic claim of absence.

**Other Muse items**
- "Firewall drafted by name and routed around" (§6): **CORRECT and the most substantive framework-level
  finding.** Design §2.2 bars PSB/SFB results from *defining* bands; M1c v1 §6 cites PSB-1 C1 to
  "corroborate" the IC scale (a letter breach, low weight) and anchors on CB-N50 HOLDOUT (a spirit breach).
- "Grinold coupling reintroduces the O1 defect through the back door" (§7): **CAVEAT** — correct that
  measured IC × chosen breadth is a coupled construction the v2 contract does not police; overstated as
  "the same defect" (O1 crossed two independently-declared corners; here one measured input is paired with
  one chosen input).
- "Nine of seventeen declarations anchor on in-repo figures" (§6): **not independently verified** here.
- NON-MATERIAL slips: FLOW δ 0.030→0.038 gives **0.781**, not a flip (≈0.039 needed, +30%); M1c "robust to 2×
  band error" should read ≈ +38% (1.8 → 2.49); STOCK-STRADDLE's Φ-vs-exact-t gap is not a verdict risk because
  the gate used exact nct — its real distributional risk is skew (−1.19), which Muse also names.
- §12/closing governance recommendation (B/C status, appealable ABANDON): out-of-scope preference; neither
  endorsed nor countered here.

## B. M1c

**B1. HOLDOUT power — arithmetic CORRECT (v4).** Under Assumption W and v4's strategy-level mapping,
ncp = S√T for every H. VAL (α=0.025, T=4.96): MDE 1.26; at S=1.8 power 0.980. HOLDOUT (α=0.05, T=1.0): MDE
(1.6449+0.8416) = **2.49**; at S=1.8 power **0.562** (exact t, n=250: 0.560); sessions needed at 1.8: 477.
The HOLDOUT-binding rule ("both stages ≥ 0.80") originates in **declaration v1 §10**, not in the protocol
(§15.2 requires only that both sizes be *covered*). It is nonetheless consistent with protocol §9, which states
VAL is prior-exposed and "confirmatory weight is carried by the forward, never-before-read HOLDOUT." Legitimate.
Stale figures: Muse §13 and ledger §4 quote "0.61 / 0.26 … best cell 0.26" — those are v1–v3 values at S=1.0;
v4 at S=1.8 is 0.98 / 0.56 (NON-MATERIAL; verdict unchanged).

**B2. Breadth / N_eff.**
- *Measured for M1c?* No. No M1c data was read. b ∈ [5, 15] daily bets is chosen, disclosed only as
  "favorable breadth"; V4-2 already flagged it as an undeclared cap.
- *Empirically established?* No for M1c. **But breadth *is* observable for the anchor, and v4's cap is
  inconsistent with it.** CB-N50 HOLDOUT reports mean IC 0.029355, IC sd 0.182629, n = 746, NW t 4.35. The
  anchor's own dispersion implies b_eff ≈ 1/0.1826² ≈ **30** (pure-noise rank-IC sd at N=50 is 0.143, so ≈30
  of 50 names are effectively independent), and its realised annualised IC-IR is **2.52–2.54** (NW / naive).
  The anchor-consistent Grinold translation therefore lands at the HOLDOUT break-even (b* ≈ 28.6; S 2.49), where
  HOLDOUT power ≈ **0.81**. v4's "optimistic 1.8 = favorable breadth, full capture" uses half the breadth its
  own anchor exhibits.
- *Does breadth change the conclusion?* Yes — the verdict is knife-edge on it. It does **not** follow that M1c
  would PROCEED: IC-IR is not strategy Sharpe; it presumes transfer coefficient 1 on a market-neutral,
  whole-cross-section, next-day book. M1c is absolute (no netting), tail-only (~10% of name-sessions), gapped
  (t+2), H-day, on a panel including illiquid names. An unhedged tail book with unbalanced legs loads on the
  market factor in exactly the sessions where tails cluster, which can cut N_eff well below 30. Tail
  conditioning can raise or lower per-bet IC. **The breadth direction is genuinely two-sided.**
- *Muse's break-even argument:* b* ≈ 28.7 is arithmetically correct. The supporting reason — "not obviously out
  of reach on a 2,300-name panel" — is weak: universe size does not imply effective breadth. Right conclusion
  (verdict is breadth-fragile), wrong argument. **CAVEAT.**
- *Conditional or unconditional?* **Conditional** — on breadth ≲ 29 effective daily bets and on the
  cross-sectional-IC → absolute-tail-Sharpe translation, neither of which is established.

**B3. Sharpe ceiling 1.8.**
- *Reasonable prior?* Yes — a documented translation of an adjacent OOS number with stated idealisations.
- *Adversarial ceiling?* **No.** It is assembled from a different estimand (cross-sectional, market-neutral,
  50 large caps, full cross-section, next-day open-to-open) with a breadth below the anchor's own measured
  breadth; the anchor applied consistently gives ≈2.5, not 1.8. No argument in v1–v4 bounds the gross Sharpe of
  the *M1c* estimand from above.
- *Empirically impossible above 2.49?* **Not shown.** Nothing in the chain establishes it; nothing establishes
  the opposite either.

**B4. Frozen window.** "250 sessions cannot resolve Sharpe below ≈2.5 at 80% power (one-sided α=0.05)" is
**correct** — it is a property of T=1 year alone (MDE = 2.49/√T). Translating it into "M1c is not worth
researching" is **not valid**: it is a statement about the frozen v1.3 design, not the mechanism. The protocol's
own §12 sends RFA-ABANDON to "the protocol returns to draft"; *retirement* is reserved for a HOLDOUT failure.
**Strongest supported conclusion:** *the frozen v1.3 experiment cannot demonstrate M1c at the repo's power
standard for any strategy Sharpe below 2.49; the declared ceiling (1.8) is below that; whether the true M1c
Sharpe lies above or below it is unknown.*

**B5. Data firewall.**
- M1c market data: none read — the "no M1c data" statements are true.
- Market-result contamination: **yes, pre-M1c-data but not pre-market-data.** CB-N50 HOLDOUT (2020–22) is a
  realised read of a reversal-containing signal on Nifty-50 names that sit inside M1c's panel, overlapping
  M1c's VAL window (2018–22) in calendar time and mechanism family. PSB-1 C1 (weekly reversal, 2012–22) is
  cited as corroboration — a letter breach of design §2.2. PSB-1 C2 and MRLC (ext t 8.62, same panel/period)
  were consulted to be *excluded*; the authors therefore knew of stronger positive reads.
- N50-LS is not cited by M1c, but shares the pattern: same CB-N50 anchor, N_eff capped at 8 on the same 50
  names whose IC dispersion implies ≈30.
- Direction: every contaminated choice (b ≤ 15, MRLC excluded, C2 excluded) pushed the ceiling **down**. The
  contamination cannot have manufactured a false PROCEED; it weakens the claim that the ceiling is
  "independently defended" and makes the ABANDON more fragile, not less.

## C. Direct answers

**Did Muse uncover a material flaw in the RFA framework?** Mainly no. The mathematics is sound, and the
central limitation (verdict = band-conditional, bands are human judgments) is written into the design spec
itself. Muse's material framework-level contribution is a **governance/practice gap**: the prior-exposure
firewall is drafted by name (PSB/SFB) and routinely routed around through adjacent in-repo reads, and there is
no rule governing breadth in Grinold translations. One Muse claim (§9(f)) is an error; several numbers are stale
or slightly off without affecting conclusions.

**Did Muse materially weaken the specific M1c ABANDON?** It showed the ABANDON must be read conditionally —
which the repo's own V4-2 review had already said (b* ≈ 28.7, "label ABANDON conditional"). This audit finds
the conditionality is sharper than either Muse or V4-2 stated: under the anchor's own measured breadth the
translated ceiling sits at the HOLDOUT break-even. The ABANDON remains mathematically valid under its frozen
assumptions; its *legitimacy as a robust verdict* is weaker than "optimistic 1.8, needs 2.49" suggests.

## D. Final classification

| Question | Claude verdict | Confidence | Reason |
|---|---|---|---|
| RFA mathematics | CORRECT | High | Noncentral-t power, ncp = δ√n/σ = S√T, monotone; recomputed FLOW/N50-LS/RS-MOM/A-INDEX/CB-N50 match; two-sided upper-tail-only is negligible |
| RFA logical interpretation | CORRECT | High | ABANDON = frozen experiment cannot demonstrate declared effect under its assumptions; no data read, no belief updated |
| RFA optimistic-corner rule | CAVEAT | High | Creates false-positive risk (Muse §10a right); Muse §9(f) false-negative claim is an ERROR — the corner is the lenient reading; false negatives come only from a mis-set band |
| RFA band assumptions | CORRECT (with governance CAVEAT) | High | Band is the sole world-content input, as the design admits; firewall is name-scoped and routed around via CB-N50/PSB-1 |
| M1c power calculation | CORRECT | High | v4 mapping S√T for all H; VAL 0.98, HOLDOUT 0.56 at 1.8; MDE 2.49; 477 sessions; rescue threshold Σρ ≤ −0.42 |
| M1c breadth assumption | CAVEAT | Medium-High | b ≤ 15 chosen, not measured; the anchor's own IC sd implies b_eff ≈ 30 ≈ b*; but absolute tail-book market loading could cut N_eff — direction two-sided |
| M1c Sharpe ceiling | CAVEAT | Medium-High | 1.8 is a reasonable prior, not an adversarial ceiling; anchor-consistent translation ≈ 2.5; >2.49 neither shown impossible nor supported |
| M1c HOLDOUT conclusion | CORRECT (narrowly) | High | "250 sessions cannot resolve S < 2.49" is exact; it is a property of the frozen design, not of the mechanism |
| M1c ABANDON legitimacy | CAVEAT | Medium-High | Valid under frozen assumptions; conditional on breadth ≲ 29 and an unestablished IC→absolute-tail translation; knife-edge under the anchor's own breadth |
| Muse audit overall | CORRECT (with CAVEATs) | Medium-High | Core characterization right; one logical error (§9f), stale/slipped numbers, weak universe-size argument; framework findings are governance, not math |

## Final judgment

1. **Is Muse's RFA critique materially correct?** Yes in substance. RFA is a band-conditional pre-data power
   screen that cannot establish absence of edge. The flaws Muse identifies are in governance and practice
   (firewall scope, unregulated breadth), not in the mathematics. §9(f) is wrong, and several figures are stale.
2. **Is M1c's ABANDON mathematically correct under its frozen assumptions?** Yes. At S = 1.8 HOLDOUT power is
   0.56 < 0.80, and any ceiling below 2.49 fails.
3. **Empirically closed, or only RFA-infeasible/empirically unknown?** Only RFA-infeasible, i.e. empirically
   unknown. No data was read. The protocol's own §12 returns it to draft rather than retiring it. The ledger
   already records it as EMPIRICALLY UNKNOWN, and the verdict is conditional on a breadth and translation
   premise that the anchor's own statistics do not support at the declared cap.
