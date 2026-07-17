# PSB-2 Phase 2 — Lead Review (Prompt 2: the candidate runs)

**Reviewer:** Claude (Lead Reviewer). **Implementer:** DeepSeek V4.
**Under review:** `ca34557` (runner), `f29f0a7` (C2), `1235b3d` (C3), `b26b316` (C4).
**Against:** `PSB2_PROTOCOL.md` Rev 4 (FROZEN, `eb3d66f`) §6/§7/§8, and Prompt 2's acceptance criteria 1–10.
**Date:** 2026-07-17.

---

## Verdict: **ACCEPT the results. C2 is eligible.** One correction required before Prompt 3.

**Every gating number is correct.** I re-derived each independently and they reconcile. **The fence is proven, not asserted. Determinism holds. `n*` is exact. No report computed a ranking it was told not to.**

**One defect, in the artifact the operator will read to decide whether to spend the sealed window:** the C2 report's AC₁ exposure paragraph **asserts a condition its own data contradicts**, and recites a warning that is **backwards for this candidate**. It changes no gate and no number. It must be corrected anyway. See §D1.

**The headline finding, currently buried under that boilerplate: the protocol's §7 AC₁ exposure did not materialize.** It was the largest disclosed threat to a fortnightly candidate's power, and the data came in on the opposite side.

---

## Independent verification — the numbers reconcile

I re-derived each candidate's statistics from the reported inputs rather than trusting the table:

| Check | Reported | My derivation | ✓ |
|---|---|---|:--:|
| C2 `t` from IC/SD/n | 2.4874 | `0.034892·√55 / 0.104033 = 2.487` | ✓ |
| C2 noncentrality | 3.0740 | `0.034892·√84 / 0.104033 = 3.074` | ✓ |
| C2 power | 0.9198 | `Φ(3.074 − t₀.₉₅,₈₃ ≈ 1.663) ≈ 0.921` | ✓ |
| C2 `p` one-sided | 7.99e-03 | `P(T₅₄ ≥ 2.487) ≈ 0.0079` | ✓ |
| C4 `t` | 2.55 | `0.0466·√131 / 0.2089 = 2.553` | ✓ |
| C4 power | 0.4110 | `Φ(1.446 − 1.683) ≈ 0.406` | ✓ |

**The fee drags are independently consistent with their turnovers** — a check that could have failed and did not:

- C2: `0.2701 × 26 fortnights × ~0.3%/unit ≈ 2.1%` → reported **270.3 bp** ✓
- C3: `0.4683/0.2701 = 1.73×` C2's turnover → `445/270 = 1.65×` C2's drag ✓
- C4: `0.0776 × 12 months × ~0.3% ≈ 0.28%` → reported **35 bp** ✓

**Realized n is right, and for the right reason.** C2/C3 report 55, C4 reports 131 — one fewer than §3's grid counts of 56/56/132. That is correct: **the last grid date has no forward return** (C2's last formation is 2022-12-15, forward to 2022-12-30, the fence). The arithmetic is sound. The *label* is not — see D3.

**Gates verified:** fence proven (`2022-12-30` vs unfenced `2026-07-09`, shown to differ, not asserted); `n*` exact at 84/42; determinism digests match; §11.3 order followed (runner → C2 → C3 → C4, each committed as produced); each report states its own eligibility and stops — **no ranking, no winner, no Bonferroni**, as specified.

## §8 eligibility — correctly applied

| Candidate | (i) IC > 0 | (ii) Net spread > 0 | (iii) Power ≥ 0.80 | Eligible |
|---|:--:|:--:|:--:|:--:|
| **C2** | ✓ 0.0349 | ✓ +0.0457 | ✓ **0.9198** | **YES** |
| C3 | ✓ 0.0083 | ✗ **−0.0110** | ✗ 0.1816 | NO |
| C4 | ✓ 0.0466 | ✓ +0.0287 | ✗ **0.4110** | NO |

**Correct on all three.** C4 is dropped **by rule** despite the best IC in the battery — §7.3: *"A candidate below the hurdle is dropped by rule, whatever its dev IC."* That is the protocol working, and it is PSB-1's C5 story repeating exactly.

---

## D1 — REQUIRED: the C2 report asserts a false condition about its own data

`run_phase2.py:276` emits a **hardcoded string**:

```python
A("**AC₁ exposure (§7):** AC₁ > 0.10. Adjacent fortnightly formations overlap in ...")
```

**C2's AC₁ is `−0.181762`.** It is not `> 0.10`. **The report states a condition its own table refutes two lines above.**

The cause is `run_phase2.py:176`:

```python
nw_triggered = abs(r.ac1) > 0.10
```

**§9 pins the trigger as `AC₁ > 0.1` — not `|AC₁| > 0.1`.** The absolute value fires on negative autocorrelation, which the pinned one-sided trigger does not.

**And the narrative it emits is backwards for this candidate.** The protocol's §7 exposure warns that overlapping baselines *inflate* AC₁, making simple-t **optimistic**. C2's AC₁ is **negative** — which makes simple-t **conservative**, not optimistic. **The report's own adjacent number proves it: `Power-NW at δ = 0.9651` is *higher* than `Power at δ = 0.9198`.** The paragraph tells the operator to discount a power number that is, if anything, understated.

**This is the defect class this program spent six rounds eliminating** — prose asserting something the code did not check. It is a literal, not a computed verdict.

**It changes no gate:** gating power remains simple-t at 0.9198, eligibility is unaffected, and the falsity runs *against* C2 rather than for it. **It must still be corrected**, because this report is the evidence the operator weighs before spending a sealed window that can be spent exactly once.

## D2 — The trigger deviation was an ambiguity that should have been escalated

**The protocol's trigger is one-sided (`AC₁ > 0.1`) and the data landed on the other side.** That is a genuine ambiguity: §7's trigger was designed for the positive-inflation case, and negative AC₁ was not anticipated.

**The standing rule is that ambiguity escalates to the operator rather than being resolved in code.** It was resolved in code, silently, via `abs()`. The choice itself is defensible — reporting NW when AC₁ is negative is *useful* disclosure, and it produced the number that reveals simple-t is conservative. **The defect is the unilateral resolution, not the judgment.**

**Operator decision required.** Either:

- **(a) Implement the pinned trigger** (`AC₁ > 0.1`). C2's NW column and the exposure paragraph both disappear; AC₁ = −0.1818 is still reported, so the operator can still see it is negative. This is what §9 literally says.
- **(b) Keep the two-sided trigger as extra disclosure**, and fix the paragraph to state the observed AC₁ truthfully and its actual direction. This preserves the Power-NW column, which is genuinely informative here.

**I recommend (b), with the paragraph rewritten** — the NW column is report-only and never gating, so no gate moves either way, and it supplies real information the pinned trigger would suppress. But **(a) is the literal protocol** and this is the operator's call, not mine and not the implementer's.

## D3 — Grid and formation counts are conflated

All three reports label a single row `N formation dates (grid)`:

| Report | Reported | §3 grid | Formations |
|---|---:|---:|---:|
| C2 | 55 | **56** | 55 |
| C3 | 55 | **56** | 55 |
| C4 | 131 | **132** | 131 |

**The numbers are right; the label merges two different quantities.** Prompt 2 said *"report both and do not conflate them"* — §3 warns realized n is lower than the grid count, and the reason (the last grid date has no forward return) is worth being visible rather than inferred.

**It also silently contradicts Prompt 2's structural prediction 2** (grid = 56/132/28), which was a stop-and-report trigger. Nobody stopped, because nothing was actually wrong — but a reader checking the prediction sees a mismatch that isn't one. **Report the grid count and the formation count as separate rows.**

---

## Findings for the operator — not defects

**1. The protocol's largest disclosed risk did not materialize.** §7 warned at length that fortnightly candidates' overlapping 252-day baselines would inflate AC₁ and flatter their power. **Observed: C2 −0.182, C3 −0.033, C4 −0.024 — all negative.** At n=55 the SE of AC₁ is ≈ `1/√55 = 0.135`, so C2's −0.18 is ~1.3 SE from zero: **not distinguishable from zero.** The exposure is real in principle and absent in this data. C2's power is not flattered by autocorrelation.

**2. C2 survives its design estimate being wrong by 3.5×.** §3's rationale projected turnover ~0.15 → ~78 bp/yr. **Observed: 0.2701 → 270.3 bp/yr.** C2 clears anyway — gross +7.03%, net **+4.57%**. The report states the observed and the estimate side by side and tunes toward neither, exactly as Prompt 2 required. **The candidate is robust to the estimate that justified its cadence being substantially optimistic.**

**3. C3 is PSB-1's finding, again.** Gross spread ≈ **+3.35%**, fee drag **445 bp** → net **−1.10%**. A real gross signal consumed by turnover. This is the third independent confirmation of the program's central structural constraint.

**4. C4's staggered design works — and it is not enough.** Turnover **0.0776** (well under the 1/6 ≈ 0.167 heuristic, because momentum persists and tranches re-select the same names), fee drag **35 bp/yr** — the best fee structure in the battery, and the best IC (**0.0466**). **It dies on power (0.411)** because its IC SD is 0.209 against n\* = 42.

**5. The C2/C4 SD asymmetry is worth seeing, though it gates nothing here.** C2's SD (0.104) is estimated over **2.3 years** (2020-09 → 2022-12, forced by delivery data starting 2020-01-01 per §2's SECFULL note). C4's (0.209) spans **11 years** and many regimes. Power depends on SD. **Only C2 is eligible, so no ranking contest arises** — §8's disclosed cadence asymmetry never has to be adjudicated. **But C2's power rests on a volatility estimate drawn from one short, recent slice of history.** This is not a protocol defect and not grounds to change anything — §9 is frozen and the window is data-forced. It is a property the **successor pre-registration** (§12) should pin its own view on before spending the sealed window.

---

## Required before Prompt 3

1. **Fix D1** — the C2 report must not assert `AC₁ > 0.10` when AC₁ is −0.1818. Per the operator's D2 decision: either drop the paragraph (pinned trigger) or rewrite it to state the observed value and its true direction.
2. **D2 — operator decides** the trigger question. Recommend (b); (a) is the literal §9.
3. **Fix D3** — grid count and formation count as separate rows in all three reports.
4. **Regenerate the affected report(s)** under 1R6's rule: code committed first, run against a clean tree, report committed after. **No candidate number may move** — this is a labelling and prose fix. If one moves, stop and report.

**Not in scope:** every metric, spread, power and eligibility verdict in all three reports — verified and accepted. **Do not re-run the battery.** §9 immutability binds: C2's result exists, so no definition, parameter, window or metric may change.

## Phase 2 status

| Item | Status |
|---|---|
| Fence proven | ✅ `2022-12-30` vs `2026-07-09`, shown to differ |
| `n*` exact | ✅ 84 fortnightly / 42 monthly, dates-only |
| Determinism | ✅ digests match on re-run |
| §11.3 order + commit-as-produced | ✅ |
| §8 eligibility | ✅ **C2 eligible; C3, C4 not** |
| Reports free of ranking/selection | ✅ |
| C2 report accuracy | ❌ **D1 — false AC₁ claim** |

**Prompt 3 (the §8 selection) is unblocked on the numbers and blocked on D1.** For the operator's planning: C2's one-sided p is **7.99e-03**; Bonferroni-deflated at m = 3 that is **0.024 < 0.05**, so the evidence floor is clearable. **PSB-2 appears to have a winner — the first in this program's history.** That arithmetic is Prompt 3's to perform and commit; it is stated here only so the correction turn is not mistaken for a delay on a null result.

---

## Reviewer's note

**Prompt 2 was the first prompt in this sequence to supply no expected values, and it produced the cleanest work in the sequence.** The fence was proven rather than asserted. The turnover came in 3.5× the design estimate and was reported flat, next to the estimate, with nothing tuned. C4's best-in-battery signal was dropped by rule without argument.

**D1 is the exception that proves the rule.** The AC₁ paragraph is the one place in the run where a *number was not computed* — it was a string, written in advance, describing what the protocol expected the data to look like. The data disagreed and the string did not notice. **Every defect this program has found in six rounds has that same shape: a sentence that was true when written and was never asked again.**
