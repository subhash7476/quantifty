# CSMP Phase 1 — Lead Review of the Research Dossier (pre-freeze)

**Date:** 2026-07-11
**Reviewer:** Claude (Lead Reviewer — prompts and reviews only; did not author the dossier)
**Under review:** `docs/reports/CSMP_PHASE1_RESEARCH_DOSSIER.md` (DRAFT, not yet frozen)
**Corroborating sources read:** `CSMP_PHASE0_CHARTER.md`, `CSMP_GATE_E_TRIAGE.md`, `CSMP_GATE_E_REVIEW_REQUEST.md`, `CSMP_GATE_E_LEAD_REVIEW.md`, `scripts/csmp/triage_momentum.py`

**Verdict: NOT PASSED FOR FREEZE.** The dossier is a strong pre-registration — the construct is charter-faithful, the decision table is pre-committed, the delisting convention is a real methodological improvement, and nothing in it reads the sealed window. But four findings are blocking, and two of them (B1, B2) go to whether the program's foundation and its gate are sound at all. B1 says the evidence that *unlocked* this phase is computed under a convention the dossier itself now disowns. B2 says the gate as pre-registered will most likely return "inconclusive" **even if the edge is exactly as strong as it was on dev** — and that fact is computable today, from dev data, and is not in the document.

Neither is fatal. Both are cheap to fix, and both must be fixed *before* the seal, because after the seal they are unfixable.

---

## Blocking findings

### B1 — Gate (e)'s CONTINUE rests on the survivorship-flattered convention §5.2 exists to abolish. Re-run dev before freezing.

The dossier's §3.1 calls the §5.2 delisting convention "the single most important methodology fix over the gate-(e) triage, which dropped such names." That claim is **correct**, and I confirmed it in the source. `scripts/csmp/triage_momentum.py:284-287`:

```python
pa = px.get((ent, t))
pb = px.get((ent, tp1))
if pa and pb and pa > 0:
    pairs.append((rank, sc, pb / pa - 1.0, sym))
```

If `pb` is missing — the name stopped trading in `(t, t+1]` — the name is silently dropped from `pairs`, and `pairs` feeds **both** the IC series and the portfolio (`per_month_rows.append((t, pairs, tp1))`, line 304). A name that gets crowded, collapses, and is suspended does not bear its terminal return; it vanishes. That is textbook survivorship bias, in the exact direction that flatters momentum.

**Magnitude, from the triage's own counters:** membership is exactly 200/month over 131 scored months (gate-(e) review, F5) → 26,200 member-months; minus 382 formation-incomplete exclusions → **25,818 scored**. The report states **25,797** forward returns computed. **21 member-months were silently dropped.**

So the hole is real but small — 21 of 25,818 (0.08%). It is *not* obviously fatal, and the sign is not even certain a priori (an M&A delisting has a *positive* terminal return; a bankruptcy suspension a catastrophic one). But note what follows:

1. **Gate (e)'s stop rule was cleared under this convention.** `mean_IC = 0.0458` (floor 0.02) and `net spread = 6.38%` (floor 0) are both computed on the dropped-delisting panel. The dossier now declares that panel methodologically wrong, and then cites those same two numbers in §2.1 as the evidence substantiating the claim. You cannot both disown the convention and lean on the numbers it produced.
2. **The gate-(e) independent review was explicitly asked to check this and did not.** `CSMP_GATE_E_REVIEW_REQUEST.md` §"What could make CONTINUE spurious", item 2, is a verbatim description of this bug — *"does the forward-return step silently drop names that delist mid-hold? … a dropped delisting is a survivorship bias that flatters momentum. Check how missing `px.get((ent, tp1))` is handled."* `CSMP_GATE_E_LEAD_REVIEW.md` returned PASS with findings F1–F5, none of which is this. The reviewer missed the one item the request singled out as the highest-value check. This is a process observation, not a re-litigation of the gate — but it means the PASS is weaker than it reads.

**Required before freeze (dev-only, no sealed contamination, cheap):** re-run `triage_momentum.py` with the §5.2 convention applied, and confirm the stop rule still renders CONTINUE. Report the revised `mean_IC`, CI, and net spread, plus the count of rule-1 / rule-2 names by year. If CONTINUE survives — which I expect at 21/25,818 — the pre-registration stands on evidence it has not disowned, and §2.1 can cite numbers it believes. If it does not survive, you have learned that *before* spending the sealed window, which is precisely what gate (e) exists for.

### B2 — The §3.4 gate is underpowered. Its modal outcome is "inconclusive" even if the edge is real and undecayed. Compute this and put it in the document.

This is the most important finding and it requires no new data.

The sealed window carries **~41 monthly rebalances**. The dev-window IC series has `SD = 0.2078` (gate (e) §3). Under the pre-registered rule — 95% CI excluding zero — the implied requirement is:

```
SE(mean_IC) at n=41  = 0.2078 / √41 = 0.0325
implied threshold    = 1.96 × 0.0325 ≈ 0.064
```

**The gate, as written, requires a sealed-window mean IC of roughly 0.064 — about 40% higher than the 0.0458 the dev window actually produced.** The dossier's §3.4 note frames the sealed bar as *laxer* than gate (e)'s ("gate (e) used a higher `mean_IC > 0.02` floor … the sealed-window bar is the charter-D3 `mean_IC > 0`"). In effect it is **substantially stricter**, because the CI condition at n=41 does the work the floor did at n=131. The document currently obscures this.

Power, if the true out-of-sample edge equals the dev edge exactly (`mean_IC = 0.0458`, same SD):

| Test | Power | P(inconclusive) |
|---|---|---|
| Two-sided 95% CI excludes 0 (as pre-registered) | **~29%** | ~71% |
| One-sided 95% lower bound > 0 (matches the directional H₁) | ~41% | ~59% |

Months needed for 50% power: **~79**. For 80%: **~161** (13+ years).

So the program's modal outcome — by a wide margin, *conditional on the hypothesis being true* — is §10 row 3: "Inconclusive (underpowered) → Not Approved, do not tune, wait for more data." That is an honest and defensible thing to accept. It is **not** an honest thing to leave undisclosed in a pre-registration whose parent charter (D3) explicitly demands "the modal-outcome honesty the MSRP reviews demanded." §11 gestures at it in prose ("an 'inconclusive' verdict is an expected, non-failing outcome") but never computes it, and §3.4's framing points the reader the other way.

**Required before freeze — one of:**

- **(a) Accept and state it.** Add the power computation and the implied ~0.064 threshold to §11 and §3.4. Pre-commit to the extension schedule in §10 row 3 (how much additional forward data, and when, triggers a re-read under the *same* rule). This is the minimum.
- **(b) Take it to the operator as a re-opened D3 decision.** H₁ is directional (`mean_IC > 0`); the statistically correct test is one-sided, and it buys ~12 points of power for free. Charter D3 says "95% CI excluding zero," which a one-sided 95% lower bound satisfies on a plain reading. This is an operator call, it is charter-adjacent, and **it must be locked before the seal** — i.e. now, or never.

I recommend (a) unconditionally, and (b) presented to the operator as a decision with the power table above attached.

### B3 — The slippage impact is understated ~2×, because the dossier misreads gate (e)'s turnover metric.

§8.2 states: *"at the gate-(e) turnovers this trims the net spread by ~12 bp/yr."* That is wrong, and the error is in the definition of turnover.

`triage_momentum.py:408`: `two_way = (len(enters) + len(exits)) / (2 * N)`. Despite the name, this is the **average** of entries and exits as a fraction of the book — i.e. **half** the traded notional. At the reported 23.76%, the momentum arm trades **47.5% of capital per month**, not 23.76%.

Two independent confirmations that 47.5% is the right reading:
- **Fee cross-check.** STT on delivery is 0.1% per side. `0.001 × 0.475 = 4.75 bp/mo`, plus stamp/txn/SEBI/GST ≈ **5.2 bp/mo** — matching gate (e)'s reported fee drag of **5.22 bp/mo** almost exactly. Under the 23.76%-notional reading the implied drag would be ~2.6 bp/mo, half the observed.
- **Arithmetic of the metric itself**, above.

Correct slippage impact at `κ = 5 bps/side`:

| Arm | Two-way (gate e) | Traded notional/mo | κ cost |
|---|---|---|---|
| Top-40 EW | 23.76% | 47.5% | 2.38 bp/mo → **28.5 bp/yr** |
| EW universe | 3.03% | 6.06% | 0.30 bp/mo → **3.6 bp/yr** |
| **Differential** | | | **≈ 25 bp/yr** (not 12) |

Immaterial against the 638 bp dev spread — but **not** immaterial against a sealed `Δ_net`, which is a bare point estimate over 41 months with no CI. If the sealed spread comes in at +30 bp, the difference between a 12 bp and a 25 bp slippage charge is the entire deployment verdict. A pre-registration must be arithmetically right about its own cost model.

**Required:** correct the figure, and **define turnover unambiguously in §8** as *traded notional as a fraction of capital, per month* — Phase 6 will re-implement this, and the current ambiguity is exactly how a 2× error propagates.

### B4 — §2.1 and §3.4 disagree about what falsifies the claim. (Downgraded to MEDIUM on re-check.)

**Correction to my own first pass:** I initially wrote that the decision table was *missing a row* for `mean_IC ≤ 0` **but** `Δ_net > 0`. That was wrong and I withdraw it. §10 row 4 (`mean_IC ≤ 0` → falsified) maps that case to Rejected regardless of `Δ_net`, so the table **is** exhaustive in the gating dimension. No outcome is left unhandled. What remains is real but smaller:

§2.1's scientific claim is a **conjunction**: momentum ranks with positive skill **and** the top quintile beats the EW universe net of costs. §3.4 gates Approval on the **IC alone**; `Δ_net` is only a deployment qualifier. So in §10 row 2 (IC clears, `Δ_net ≤ 0`) the artifact is *Approved* while the §2.1 claim as written is *false* — yet §2.1 asserts the claim "is adjudicated by the pre-registered metric of §3." The document never reconciles this.

Separately, the `mean_IC ≤ 0` with `Δ_net > 0` case deserves to be **named** in the table even though it is already handled. Rank IC is deliberately insensitive to the right tail, and an equal-weight top-bucket momentum book harvests much of its return *from* the right tail — so a sealed window in which a handful of large winners carry the top-40 while the rank ordering elsewhere is noise is a live possibility, not a curiosity. It is the row that will be argued about after the fact, and a pre-registration's job is to have already won that argument.

**Required:**
1. Restate §2.1 so the conjunction is explicit, and say which outcome falsifies which half.
2. Make row 4's treatment of `Δ_net` explicit rather than implicit:

| Sealed-window outcome | Verdict | Next action |
|---|---|---|
| `mean_IC ≤ 0` **but** `Δ_net > 0` | **Artifact Rejected** (row 4 applies; the economic outcome is recorded, not acted on) | The pre-registered gate is the IC (charter D3). A tail-driven portfolio win with no rank skill is *not* the hypothesis and does not rescue it. Do not deploy. "The payoff is in the tail, not the ranking" is a **new** increment-2 hypothesis with its own pre-registration. |

---

## Should-fix (non-blocking, but fix before freeze)

**S1 — The F1 baseline switch is presented as "conservative." It is the opposite.**
§3.2 moves the gating baseline to the all-200 book "resolving gate-(e) finding F1 … (dev-window impact was 9 bp and conservative)." Gate (e)'s F1 used "conservative" to describe the *formation-complete* baseline (net 9.16%) — the **harder** bar. The all-200 book nets **9.07%**, so the switch **lowers** the bar by 9 bp and widens the reported spread. Charter D3-1 does call for "just buy everything," so the choice is defensible — but the justification must own its direction. Cleanest fix, and it costs nothing: pre-register **both** baselines and gate on the **stronger** of the two on the sealed window. That is unimpeachable and removes the appearance of having picked the easier bar.

**S2 — The stated rationale for `L = 12` is wrong, and `L = 12` is poorly behaved at n = 41.**
§1.1 says L was fixed a priori from the formation overlap and *"**Not** derived from the IC autocorrelation (circular)."* Deriving L from the **dev-window** IC autocorrelation is **not circular** — dev-window decisions are exactly what this dossier is permitted to make. Circularity would require choosing L against the *sealed* window. The stated reasoning is confused, and it matters, because:

Gate (e)'s own numbers show `L = 12` is doing almost nothing. Naive i.i.d. 95% CI at n=131: `0.0458 ± 1.96 × 0.2078/√131 = [0.0102, 0.0814]`. Reported block-bootstrap CI: `[0.0093, 0.0812]`. **The blocked CI is 1% wider than the i.i.d. CI** — i.e. the IC series has negligible serial dependence (unsurprising: the *scores* overlap by 11 months, but the *forward returns* are disjoint, and IC is a correlation against the latter). So blocking cost nothing on dev — but at n=41 with L=12 you have **3.4 effective blocks**, where the moving-block percentile CI is genuinely unreliable, not merely "intentionally wide" as §11 claims.

**Fix:** either (i) keep L=12 for charter continuity but disclose the above honestly (drop the "conservative CI" framing — it is a *degenerate* CI, not a conservative one), or (ii) pre-register a dev-derived L via a standard automatic rule (Politis–White), pinned to an integer now, with L=12 reported as a robustness arm. Do not leave the current rationale in a frozen document.

**S3 — "An order of magnitude more effective observations" is a conceptual error, and it recurs in the charter.**
§3.4 justifies the IC as primary metric on the grounds that it is "a panel of ~200 names × ~41 months — an order of magnitude more effective observations than a single-series construct." The cross-section width reduces the **measurement error of each monthly `IC_t`**; it does **not** reduce the **month-to-month dispersion of the true IC**, which is what governs the power of `mean_IC`. And the dispersion dominates: sampling error of a 200-name Spearman under the null is ≈ `1/√200 ≈ 0.07`, against an observed `SD = 0.208` — so `√(0.208² − 0.07²) ≈ 0.196` of the SD is *genuine* month-to-month variation in momentum's efficacy. **The effective n for the gate is 41, not 8,200.** This is the same claim the charter makes in §1 ("Statistical power"), and it is the root cause of B2 going unnoticed. Correct it here.

**S4 — The Calibration domain (§9) is not executable as written.**
"Empirical relationship between reported uncertainty and realized **momentum-estimate error**" — but §7 correctly states the score is a *parameter-free deterministic transform*. It has no estimation error. There is no such quantity to measure, so the domain cannot be run. Also, §7 defines *two* things (formation-window sub-return dispersion, and a completeness fraction) but the MSI `Estimate` carries **one** scalar `uncertainty` — the combining formula is unspecified.

**Fix:** pin the scalar (e.g. `uncertainty = SD of the 11 monthly formation sub-returns`, with completeness carried as separate metadata, not folded in), and define the calibration test as something runnable: *sort names into uncertainty terciles at each `t`; compute `mean_IC` within each tercile; a calibrated uncertainty implies monotonically higher IC in the low-uncertainty tercile.* Measured on dev, reported once on held-out, never tuned. Alternatively — see R4 — drop the uncertainty machinery entirely, which the charter explicitly permits.

**S5 — Pin the degrees of freedom that are still open.**
- **Seed:** §1.1 says *"e.g. the gate-(e) value 20260711."* An "e.g." in a pre-registration is a hole. Write the integer.
- **The sealed rebalance grid and the exact month count.** "~41 months" is not pinned. The grid is a *calendar* fact, derivable without reading a single price or return — pin the explicit list of sealed rebalance dates now. It removes a degree of freedom at zero cost.
- **Is it 41 or 42?** The last **dev** formation month is 2022-12-30, whose forward return lands in **2023-01** — a legitimate sealed-window observation, computed entirely from dev-window formation prices. Gate (e) correctly excluded it (it would have read sealed data). Phase 6 should *include* it: it is the natural first out-of-sample month, it is free, and in a power-starved test one extra observation is not nothing. **Decide and pin it.** Silence here is exactly the kind of latitude pre-registration exists to kill.
- **`K` shortfall:** state what happens if fewer than 40 names are formation-complete in a sealed month (hold all of them). Structurally impossible on dev, but unpinned is unpinned.

**S6 — §11 promises drawdown honesty; §9 and §10 never commit to reporting it.**
§11: *"the drawdown expectation is disclosed, not hedged."* Nothing in the validation plan or the decision table requires reporting a drawdown. Separately: a top-quintile momentum book carries materially **more beta and vol** than the EW universe. A positive raw `Δ_net` can therefore be compensation for risk rather than skill — and `Δ_net` as pre-registered is a **raw return difference** with no risk adjustment (charter D3 locks this, so it must stay the gate). **Add to §9 Robustness, non-gating:** annualized vol, Sharpe, and max drawdown for both arms on the sealed window, with the dev values alongside for context. Without these the reader cannot tell whether `Δ_net > 0` means anything.

**S7 — §5.2 rule 2 (a 0% step) is generous in exactly momentum's left tail.**
A name in the universe at `t` with **no** session in `(t, t+1]` gets a 0% return and exits. The realistic generator of that state is a suspension ahead of a bankruptcy delisting, whose true return is nearer −100% than 0%. Rule 1 handles the common case well; rule 2 is the one that bites, and it bites in the direction that flatters the arm holding the name. Keep 0% as the pre-registered gate (it is mechanical and defensible), but **add a pre-registered sensitivity**: report the result with rule-2 names marked at −100%, non-gating. Cheap, and it closes the criticism permanently.

**S8 — Add the falsifiable "we did not select K" statement, because it is *true* and it is free.**
The dossier justifies `K = 40` partly by "consistency with the gate-(e) transmission evidence." That reads defensively. Two much stronger facts are available and unstated:
- **No top-30 portfolio was ever computed on the dev window.** Gate (e) computed the quintile (40) and decile (20) *gross* spreads and a *net* portfolio for the quintile only. There was no search over `K`, so no selection could have occurred.
- **The dev top-decile gross spread was *higher* than the quintile's** (1.22%/mo vs 1.07%/mo). K=40 is therefore demonstrably **not** the dev-window-maximizing choice.

Say both. A pre-registration that can prove it did not select its own parameter is worth far more than one that asserts it.

**S9 — Forward-return horizon heterogeneity in the IC set.** *(Adopted from DeepSeek's F2 — a genuine catch I did not make.)* A §5.2 rule-1 name contributes a **partial-month** return (liquidated at its last session in `(t, t+1]`) while every continuing name contributes a full month. The Spearman IC treats them as homogeneous, and the block bootstrap inherits that assumption. The effect is small — delistings are rare in the NIFTY-200 — but it is real and belongs in §11 alongside the per-month rule-1/rule-2 counts that §5.2 already requires.

---

## Reconciliation with `CSMP_PHASE1_LEAD_REVIEW.md` (DeepSeek self-review)

A second review of the same dossier exists, by its own author, reaching **PASS WITH REVISIONS** on four documentation-level findings. The divergence from this review's NOT PASSED is not a matter of judgement, and should not be split down the middle. It has a single mechanical cause, which that review states plainly in its own scope section:

> *"Did not re-run any computation (Phase 1 is a research document, not a script; the gate-(e) triage already proved the dev-window numbers)."*

**B2 and B3 are pure arithmetic on numbers already printed in the gate-(e) report.** No store access, no re-run, no new data is needed to find either — only the willingness to divide 0.2078 by √41, and to check what `two_way` actually computes. A review that declines to compute cannot find them, and did not. That review is also, by its own admission, a **self-review** (author reviewing their own dossier); under the locked role split the sanctioned Lead Review is this one.

Where the two agree, and what this review adopts:

| DeepSeek finding | Status here |
|---|---|
| F1 — §5.2 rule 2's 0% step needs an economic interpretation | **Agreed** — overlaps S7. DeepSeek's "liquidated at the entry close" framing is the better wording and should be used. S7 goes further and asks for a **−100% sensitivity**, non-gating, because the 0% step is generous in exactly momentum's left tail. |
| F2 — partial-month horizon heterogeneity in the IC set | **Adopted as S9.** A genuine catch this review missed. |
| F3 — the K=40 quintile assumes N ≥ 80 in the sealed window | **Agreed** — overlaps S5's `K`-shortfall item. |
| F4 — pin the scored-month count in §1.1 | **Agreed** — overlaps S5. Note this review goes further: pin the **explicit rebalance-date grid**, and **decide 41 vs 42** (the 2022-12 formation's forward return lands in 2023-01 and is a free, legitimate sealed observation). |

Two places where the self-review actively reinforces an error rather than catching it:

- Its gate-evidence table asserts the dossier *"does not rest the sealed-window bar on"* the gate-(e) numbers. The **sealed bar** doesn't, correctly — but the **decision to spend the sealed window at all** does, entirely, and §2.1 cites those numbers as its supporting evidence. The same review then acknowledges (in its structural checks) that gate (e) *"silently dropped names with missing `px(t+1)`."* Both statements are true; put together they are **B1**, and the review does not draw the consequence.
- It certifies that *"the 9 bp dev-window quantification is accurate."* The magnitude is accurate. The **direction** is backwards — the all-200 baseline is the *weaker* bar, not the conservative one (**S1**). The self-review repeats the dossier's own framing error without testing it.

**Answer to the pending question ("fold F1–F4 in now, or hold them for the operator?"):** fold the documentation-level findings from **both** reviews — but **F1–F4 alone do not clear the dossier for freeze.** B1 and B2 are not edits; they are computations, and per the locked role split they are DeepSeek's to run. Freezing on F1–F4 would freeze a pre-registration whose primary gate is ~29% powered against its own dev-window point estimate, with that fact undisclosed and framed as a *laxer* bar than gate (e)'s. That is precisely the outcome the charter's "modal-outcome honesty" clause exists to prevent.

---

## Additions

**A1 — A pre-registered data-integrity precondition on the sealed run. (The biggest missing safeguard.)**
§12.1 names the scariest assumption in the document — *"gate-(b) CA adjustment is correct over the sealed window (dev residue was 0; **sealed residue was counted-not-examined**)"* — and then does nothing about it. A single wrong split factor on one NIFTY-200 name manufactures a ±50% phantom "momentum," which in a 40-name equal-weight book is a 1.25% portfolio move, and can put that name straight into the top quintile. The charter's own threat list says data integrity is "where equity cross-section research quietly dies."

**Add to §8/§9:** step 0 of the Phase-6 harness run re-executes gate (b)'s `>|20%|` single-day-move classification screen over 2023-01 → 2026-06, and **the run is VOID if unexplained residue > 0** — the verdict is not read, the window is re-sealed pending a gate-(b) fix. This preserves the seal (nothing is scored, no metric is computed, the residue count is a data-quality fact, not a result) while making it impossible to score a corrupted panel and then argue about it afterwards. Pre-register the VOID rule now, or you will be negotiating with yourself later.

**A2 — A block-bootstrap CI on `Δ_net`, reported and explicitly non-gating.**
`Δ_net` currently gates deployment as a bare point estimate over ~41 monthly returns — statistically, close to a coin flip. Report its CI so the reader knows how much to believe it, and **pre-register that it does not gate** so it cannot be retrofitted as one after the fact.

**A3 — Report the dev-window results under the frozen §5.2 convention** (the B1 re-run) inside the dossier, replacing the current citations to 0.0458 / 6.38%. §2.1 should cite numbers the document endorses.

---

## Removals

**R1 — The reference-arm probe inside the Phase-6 run.**
§3.2/§8 defer the NIFTY200 Momentum 30 TRI obtainability question ("Phase 6 will additionally probe the niftyindices TR index-value series") into the single sealed run. This is public index data from an external site — it has **nothing to do with the seal** and can be settled today. Carrying an unresolved data probe into the one irreversible run adds a failure mode for no benefit, and creates a temptation if the primary result lands weak. **Resolve it now: probe it, and either pre-register exactly how the arm is scored, or delete the arm from the dossier.** It is non-gating either way; an unresolved non-gating arm is pure liability.

**R2 — The `(pin at build)` placeholders that are already known.** Seed, `L`, `B`, `κ`, `K` are all decided. Write them. Only the library versions, store hash, and commit hash genuinely require build time. A pre-registration's authority comes from having nothing left to choose.

**R3 — The D1-lesson restatement.** It appears in the header prior-art block, §2.1, §3.4's note, §4, §10 row 2, and §11. Once, canonically, is enough; the repetition dilutes it and inflates a document whose most important content (B2's power table) is missing.

**R4 — Either fully specify the §7 uncertainty machinery, or remove it.**
It is defined loosely, explicitly not acted on, has no defined combining formula (S4), and its calibration test cannot be run (S4). The charter §4 *explicitly permits* the simpler path: *"or explicitly pre-registers that increment 1 consumes ranks only and uncertainty is reported-not-acted-on."* The current middle — an under-specified uncertainty with an unrunnable calibration gate — is the worst of both. Pick one. If you keep it, S4 tells you exactly what to write.

---

## What is right, and worth saying

- The construct is **charter-faithful** — 12-1, monthly, EW, long-only, PIT universe, CA-adjusted, entity-continuous. No drift, no tuning, no construct search.
- **§5.2 is a genuine methodological improvement** over gate (e), correctly diagnosed and correctly motivated. It is the best thing in the document. (Its own predicate is what B1 asks you to act on.)
- The **rejected-features table (§6)** and the scope fence are exactly the pre-commitment discipline MSRP's D1 failure demanded.
- **Nothing in the dossier reads the sealed window.** The fence discipline is intact and the document is honest about what it does and does not know.
- The decision table's **row 2** (signal real, does not transmit → *not deployed, do not tune*) is the D1 lesson correctly institutionalized. It is the row most research programs never write.

The dossier's failure mode is not dishonesty. It is that it has not yet done the one arithmetic that would tell it whether its own gate can answer its own question (B2), and it has not yet re-derived its foundation under the standard it just raised (B1). Both are an afternoon's work, both are dev-only, and both are irreversible once the window is opened.

---

## Recommended sequence before freeze

1. **B1** — re-run `triage_momentum.py` under §5.2; confirm CONTINUE; publish revised dev numbers.
2. **B2** — compute and publish the power table + implied `mean_IC ≳ 0.064` threshold; take the one-sided-test question to the operator as a re-opened D3 decision.
3. **B3, B4, S1–S8** — document edits; no new computation except S6/A2 (dev-window risk metrics).
4. **A1** — pre-register the sealed-run VOID rule.
5. **R1** — settle the reference arm now; keep or delete.
6. Re-issue the dossier; **then** Phase 2 independent review; **then** freeze.

*Nothing in this review reads, or is informed by, the sealed held-out window (2023-01 → 2026-06).*
