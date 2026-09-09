# CSMP Phase 1 — Operator Decisions Before Freeze (Lead Reviewer recommendation)

**Date:** 2026-07-11
**Author:** Claude (Lead Reviewer — recommendation only; the decisions are the operator's)
**Context:** Dossier Rev 2 closed B1–B4 and S1–S9. Two decisions remain open in §3.4: **(D-i)** the CI method, **(D-ii)** one-sided vs two-sided. Rev 2's power simulation produced a finding that changes their order and their weight.

---

## The finding that reorders the decisions

Rev 2 simulated the **pre-registered procedure itself** (moving-block percentile CI, `L = 12`, `n = 42`) and found it **under-covers ~4×**: Type-I ≈ 10% per tail against a nominal 2.5%.

This is not a "wide CI" problem. It is a **validity** problem, and it points the opposite way from how B2 was framed:

- **Under the null, the pre-registered gate approves the artifact roughly 10% of the time per tail** — four times the rate it advertises. A "95% CI excluding zero" that is really an ~80% CI is not a conservative gate. It is an anti-conservative one.
- Its *apparent* decisiveness is therefore borrowed. The realized power of the current procedure is **higher** than the analytic 30% precisely **because** it is invalid — it clears more often than it should, under the null and under the alternative alike.
- **Fixing coverage does not cost power; it reveals the honest power.** A correctly-calibrated test lands back on the analytic figures: **~30% two-sided, ~41% one-sided**, at the dev-window effect size.

So the two decisions are **not independent, and not equal**. (D-i) is a correctness question and must be settled first; (D-ii) is a power question that only becomes meaningful once the test is valid. Deciding (D-ii) on top of an under-covering CI would compound a liberal test with a liberal tail.

**Ordering: settle (D-i) first. Then (D-ii) on the corrected test.**

---

## D-i — CI method (correctness; settle first)

**Recommendation: replace the `L = 12` moving-block percentile interval, and pre-register the replacement by a stated selection rule rather than by its number.**

The evidence that `L = 12` was never earning its keep is already in hand, from gate (e):

- Naive i.i.d. 95% CI at n=131: `[0.0102, 0.0814]`. Reported block CI: `[0.0093, 0.0812]` — **1% wider**. The IC series carries negligible serial dependence, which is what theory predicts: the *scores* overlap by 11 months, but the *forward returns* are disjoint, and the IC is a correlation against the latter.
- So `L = 12` bought nothing at n=131 and, at n=42 (3.5 blocks), it breaks — exactly as Rev 2's simulation now shows.

The original rationale (§1.1: L fixed from the formation overlap, *"not derived from the IC autocorrelation (circular)"*) was the error underneath this. Choosing `L` from the **dev-window** IC autocorrelation was never circular — dev-window decisions are what this dossier exists to make. Circularity requires reading the *sealed* window.

**Pre-register the selection rule, not the outcome:**

> The CI method is the one whose **empirical coverage at n = 42, simulated on the dev-window IC series, is closest to nominal**. Candidates: i.i.d. percentile bootstrap; stationary bootstrap (Politis–Romano) at the automatically-selected mean block length; studentized/BCa block bootstrap; Student-t interval. The winner is pinned to a single method and its parameters at A2 build, recorded in §1.1, and never re-selected.

**Guardrail — the trap to avoid:** do **not** select the method that yields the *narrowest* interval. Select the one with **coverage closest to nominal**, even where that is a wider interval than L=12's. The selection criterion is calibration, not decisiveness. Write that sentence into §3.4 so it cannot be relitigated after the seal.

Given the near-zero serial dependence, I expect a short-block stationary bootstrap or a studentized interval to win, and the resulting CI to be **wider and honest** rather than narrower.

---

## D-ii — One-sided vs two-sided (power; settle second, on the corrected test)

**Recommendation: adopt the one-sided 95% lower bound.**

- **H₁ is directional.** §3.3 states `mean_IC > 0`. Nobody will deploy on a significantly *negative* IC. The two-sided test spends half its α guarding an outcome that has no decision attached to it.
- **Charter-compatible.** D3 says "block-bootstrap 95% CI excluding zero." A one-sided 95% lower bound excluding zero satisfies that language on a plain reading. This is a clarification of a locked decision, not a reopening — but it is the operator's call to say so, and it must be said **before** the seal.
- **It is the difference between a test that can answer and one that mostly cannot:** ~41% power vs ~30%, at a correctly-calibrated 5% Type-I.

**What it does not fix.** Even one-sided and correctly covered, **"inconclusive" remains the modal outcome (~59%)** if the true edge equals the dev edge. That is the honest state of the program and it must be stated in §11 in exactly those terms. 41% is not a good test. It is the best *valid* test available on 42 months, and the alternative — a liberal CI that clears more often — is not power, it is a false-positive rate wearing power's clothes.

---

## The package, stated honestly

| | Type-I (per tail) | Power at dev effect | Verdict quality |
|---|---|---|---|
| **Pre-registered today** (L=12 block percentile, two-sided) | **~10%** | inflated | **Invalid** — approves ~1-in-10 under the null |
| Corrected CI, two-sided | 2.5% | ~30% | Valid; mostly inconclusive |
| **Corrected CI, one-sided** *(recommended)* | 5% | **~41%** | **Valid; the best available; still modally inconclusive** |

---

## D-iii — The extension rule reintroduces the Type-I problem D-i just fixed. (NEW — raised against Rev 3.)

**This is my own addition coming back to bite, and it must be closed before freeze.**

Rev 3's §10 row 3 pre-commits to re-reading at month **#56**, then **annually to #128** or until the gate clears. With the Phase-6 primary read at #42, that is a schedule of **~8 looks** (42, 56, 68, 80, 92, 104, 116, 128), each at a one-sided α = 0.05, each on **nested accumulating data**, with a stopping rule of *"or the gate clears."*

That is a group-sequential design. Testing repeatedly at full α and stopping on success is the textbook mechanism for Type-I inflation. Rev 3 says multiplicity is **disclosed** — but disclosure is not control. Under the standard Brownian approximation for equally-spaced nested looks, ~8 looks at a naive one-sided 5% gives a family-wise Type-I of roughly:

```
FWER(8 nested looks, naive α = 0.05, one-sided)  ≈  0.15 – 0.17
```

**Compare that to the incumbent we just removed for being invalid: `mb_L12`, one-sided Type-I 0.129.**

So as it stands, Rev 3 has replaced a single invalid test (12.9%) with a schedule of valid tests whose *family-wise* error is **worse** (~16%). The validity win from D-i is not merely eroded — it is spent, and then overdrawn. "Re-read annually until it clears" is, stated plainly, *keep looking until significant* — the precise behaviour pre-registration exists to prevent, and it is more dangerous in a formalized schedule than in an informal one, because it now looks rigorous.

### The design choice, with the boundary math done (Rev 4)

**Correction to my own recommendation.** I said: *"take the group-sequential, eat the hit at #42, power drops below 40%."* That was wrong by an order of magnitude. Rev 4's boundary computation shows O'Brien–Fleming at information fraction 0.33 spends so little α that **#42 power collapses to 4%** — the primary read becomes decorative, the mirror image of the failure I was trying to prevent. Within group-sequential, **Pocock dominates OBF on this schedule**, and OBF should be discarded.

| Design (overall one-sided α = 0.05) | #42 power | #128 (2033) power |
|---|---:|---:|
| **Single-shot** (extensions non-Approval-bearing) | **0.41** | — |
| **Pocock GS** | 0.24 | 0.73 |
| ~~OBF GS~~ (discarded — primary read decorative) | 0.04 | 0.78 |

### Recommendation: **single-shot**, not Pocock. The 0.73 is not what it looks like.

Pocock's terminal power is quoted as 0.73. It is not 73%. It is:

```
0.73  ×  P(the edge still exists at dev strength in 2033)
```

The charter names **crowding/decay** as the program's central threat, and notes the NIFTY200 Momentum 30 ETF went live in **2020** — before the sealed window even opens. Pocock's headline number is therefore **conditional on the falsity of the program's own primary risk**. You cannot bank power obtained by assuming the good case.

Rev 5 settles this by computing the scenario that matters — an edge alive across the sealed window that then decays:

| Post-2026 edge | Single-shot #42 | Pocock #128 |
|---|---:|---:|
| Persists at dev strength | 0.41 | 0.73 |
| Decays to half | 0.41 | 0.50 |
| **Dead after 2026** | **0.41** | **0.34** |

That table is the whole argument. **Single-shot's 0.41 is invariant to post-2026 decay** — it conditions on 2023–2026, data that already exists. **Pocock's terminal power is `0.73 × P(edge survives to 2033)`**, and under the charter's own central threat it falls *below* single-shot — having already halved the primary read to 0.24 to get there.

*(Correction for the record: I previously wrote that a decayed edge leaves the 2033 look "powered at roughly α." That was rhetoric, not arithmetic. The true figure is **0.34** — the 2023–2026 signal persists in the cumulative statistic. It does not change the conclusion (0.34 < 0.41, and Pocock still paid 0.41 → 0.24 up front); it makes the point exactly rather than rhetorically.)*

Single-shot's **0.41 carries no such condition.** It is a statement about 2023–2026, on an edge that either survived to those years or did not. That is a *real* 41%, and it is the honest maximum available from the window the program actually sealed.

Three further reasons single-shot is the better trade:

1. **Pocock buys the 2033 option by halving the primary read** (0.41 → 0.24). It pays a certain cost now for a contingent payoff later, and the contingency is precisely the thing the program doubts.
2. **"Wait seven years for the edge to appear" is not a research plan; it is an abdication.** A pre-registration whose recovery path for a null is a 2033 re-read has removed the possibility of being wrong on any humanly useful timescale. MSRP's STOP was valuable *because it arrived*.
3. **The re-read is the wrong forward path anyway** — see below.

### The bind, and the way out of it

Single-shot appears to strand the program: if #42 reads Inconclusive (~59% likely *even if H₁ is true*), the artifact is Not Approved, and charter §6 makes Approval a precondition for the Phase-7 PAPER consumer. "No extension path" looks like "no path."

It isn't, and the charter already supplies the exit. **D5 provides for forward accumulation after pre-registration.** The clean way to gain power is **not** to re-read the same sealed window eight times — that is nested data, and it costs α at every look. It is to accumulate **genuinely new forward months**, which are fresh data and cost nothing against the sealed test.

**Recommended §10 row 3, replacing the re-read calendar:**

> **Inconclusive** (`mean_IC > 0`, CI includes 0) → the artifact is **Not Approved**. The sealed window is **spent, and never re-read**. The Phase-7 PAPER consumer may still be built and run as an explicitly **exploratory, non-Approved** deployment (PaperBroker only, zero capital at risk — the engineering deliverable the charter actually wants), and its **forward** performance from 2026-07 onward accumulates as genuinely out-of-sample data for a **new pre-registration with its own α**. No parameter of the frozen construct may change.

This keeps the artifact honest (Not Approved stays Not Approved), gets the first production Knowledge consumer built regardless of the verdict — which §2.2 already states is the point — and buys further power from **new data rather than from repeated looks at old data**. It requires the operator to permit an exploratory PAPER run on a Not-Approved artifact, which is a deviation from charter §6's completion criterion and must be **ratified explicitly, not assumed**.

**§11 must carry the tension in plain words** (Rev 4 has this): the road to 80% lands ≈2033 and assumes the edge holds at dev strength for seven more years, against crowding/decay — the charter's central named threat. A program whose recovery plan for a null is "wait seven years for the edge to appear" is betting against its own primary risk. **That is the strongest argument for single-shot, and it is why I now recommend it over the group-sequential design I proposed one round ago.**

---

## Recommended operator actions

1. **Ratify D-i:** Student-t, selected by the pre-registered *coverage-closest-to-nominal* rule. ~~Note for the record that the rule selected **against power** (0.398 vs stationary's 0.453) — that is the evidence the rule is genuine and was not reverse-engineered.~~ **[CORRECTED 2026-07-12 — Phase-2 finding F1.** That claim is **withdrawn as inaccurate.** The stationary bootstrap was never the rule's winner under either reading, and the relevant foil — **`iid_perc`, power 0.418, the winner under a literal *two-sided* reading of the rule as written here** — was omitted from the comparison entirely. The rule stated in this memo was **underspecified**: it never named *which* calibration metric "closest to nominal" referred to. Accurate statement: Student-t is the **lowest-power valid candidate** (0.398, vs `iid_perc` 0.418 and stationary 0.453), selected on **one-sided Type-I closeness for a one-sided gate** — a disambiguation ratified **pre-seal** on 2026-07-12 and applied mechanically to a §5.2-corrected table. See `CSMP_PHASE2_INDEPENDENT_REVIEW.md` F1 and `CSMP_PHASE2_LEAD_DISPOSITION.md` §1.**]**
2. **Ratify D-ii:** one-sided 95% lower bound, on the corrected method.
3. **Decide D-iii (new, blocking) — and it is the substantive one.** *Recommended:* **single-shot** (Phase-6 is the only Approval-bearing test; the sealed window is spent and never re-read), with §10 row 3 rewritten to permit an **exploratory, non-Approved PAPER** consumer whose **forward** months from 2026-07 feed a *new* pre-registration. *Alternative:* **Pocock** group-sequential (OBF is discarded — it collapses the primary read to 4% power). **Do not freeze with "multiplicity disclosed" as the control**, and do not adopt the naive re-read calendar: its family-wise Type-I is 0.130, the exact level of the `mb_L12` bug that D-i removed.
4. **Ratify the charter deviation** that single-shot implies: an exploratory PAPER run on a Not-Approved artifact departs from charter §6's completion criterion. It must be granted explicitly.
5. **§11:** state the ~60% modal-inconclusive figure plainly, and the crowding/decay tension in the extension path.
6. Then Phase-2 independent review — by a party that is neither Claude nor DeepSeek, both of whom have now spent their independence on this document.

---

## What the operator is actually being asked (the three decisions, stated together)

D-i and D-ii are statistics. **D-iii is not.** Stripped of the machinery, the choice is:

> **Do we believe this edge survives to 2033?**
>
> - **Yes** → Pocock. Halve the primary read (0.41 → 0.24) to buy a 0.73 shot in seven years.
> - **No, or unknown** → **single-shot.** Take the honest 0.41 on data that already exists, accept that "inconclusive" is the likely answer, build the PAPER consumer anyway, and let *new* months — not repeated looks at old ones — decide the next pre-registration.

The program's own charter answers this question. It names crowding/decay as the central threat and notes the momentum ETF has been live since 2020. **A program should not stake its recovery plan on the failure of its own primary risk.** That is the whole of the recommendation.

*Nothing in this memo reads, or is informed by, the sealed held-out window (2023-01 → 2026-06).*
