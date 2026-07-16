# PSB-2 Protocol — Independent Review

**Document type:** Lead Review of a Phase 0 deliverable (pre-ratification)

**Subject:** `docs/reports/PSB2_PROTOCOL.md` — DRAFT Rev 1 (2026-07-14), authored by DeepSeek V4

**Reviewer:** Claude (Lead Reviewer). Roles per the standing split: DeepSeek V4 implements; Claude writes prompts and reviews; the operator decides. This review lists findings and recommends directions; it does not rewrite §5 formulas.

**Date:** 2026-07-16

**Verdict:** **DO NOT FREEZE — REVISE AND RE-REVIEW.**

> **Disposition (2026-07-16).** Operator ruled on all three BLOCK findings, as recommended: **F1 — C5 dropped**; **F2 — C1 dropped**; **F3 — §3 normative, C2/C3 fortnightly**. Recorded as **D11/D12** in `PSB2_PHASE0_RESEARCH_RECORD.md` (D9 superseded). Live slate: **C2, C3, C4 at m = 3**. **F11** was raised at disposition as a consequence of D12 and is included below. Rev 2 prompt issued to DeepSeek V4: `PSB2_IMPLEMENTATION_PROMPTS.md` §Prompt 0.

Two findings independently block ratification: **C5 cannot be run at all** (its only input does not exist in the repository and cannot be sourced without violating D4), and **C1 is predetermined to fail its own §8 eligibility gate** (its IC series is verbatim PSB-1's C5, whose power is already recorded at 0.54 against a 0.80 hurdle). A third — cadence is specified four mutually inconsistent ways — is not cosmetic: it selects n\* = 42 vs 84, which is itself the difference between pass and fail.

Because §9 immutability attaches on ratification, freezing this draft locks all three in. Fixing them afterward costs a whole new battery. Everything below is therefore raised now, pre-freeze, while revision is still free.

---

## Summary of findings

| # | Severity | Finding | Disposition |
|---|---|---|---|
| F1 | **BLOCK** | C5 (QARP) requires `roe_i(t)`; no fundamentals data exists anywhere in the repo. Sourcing it violates §1/D4 (no new ingestion). | Drop C5, or operator re-opens D4 |
| F2 | **BLOCK** | C1's IC series is definitionally identical to PSB-1 C5's → power = 0.541, fails §8(iii) ≥ 0.80 **by rule, before it runs**. | Re-specify cadence or drop C1 |
| F3 | **BLOCK** | Cadence stated four inconsistent ways (D10 / Phase-0 §6 / §3 / §5+§7). Determines n\* = 42 vs 84 → pass/fail. | Single normative cadence table |
| F4 | HIGH | C2/C3 declared delivery window (2020-04-01, ~34 formations) is structurally infeasible; earliest formation is **2020-09-04**, ceiling **28**. | Correct window and n |
| F5 | HIGH | Fortnightly grid's "the 15th" is not a full session in **18 of 42** sealed months; rule undefined there. Violates §9 "no free parameters remain". | Pin an exact rule |
| F6 | HIGH | Bonferroni m = 5 deflates the evidence floor for slots that cannot produce a result. | Re-pin m to the live slate (3 or 4) |
| F7 | MEDIUM | Exit bands drift from the D9-ratified slate (C1 0.35 vs slate 0.30); §5 preamble contradicts its own body. | Reconcile to D9 or record amendment |
| F8 | MEDIUM | D10's "0.54 → 0.80" projection plugs monthly δ/SD into n\* = 84 — not a valid fortnightly projection. **Touches a ratified decision.** | Operator awareness |
| F9 | MEDIUM | C4's `s = r_12 − r_1` is not the "12-month return skipping the most recent month" its prose claims. | Align formula and prose |
| F10 | LOW | §2 pins `open` (unused by any §5 candidate); drops PSB-1's `universe_eligibility` entity join. | Tidy |
| F11 | HIGH | *(raised at disposition, after D12)* §8's "common sealed n\*" ranking rationale is false under a mixed-cadence slate; power is invariant to dev-window length, not to cadence. | Correct the rationale; keep the rule |

Verification for every empirical claim below is script-reproducible against the pinned store; no number here is hand-estimated.

---

## F1 — BLOCK: C5 (QARP) has no data and cannot legally acquire it

§5 C5 requires:

```
roe_i(t) = trailing 4-quarter net income / average equity (or, if unavailable, trailing annual ROE)
```

**No fundamentals data exists in this repository.** Verified three ways:

- The pinned store `equity_bhavcopy.duckdb` holds 17 tables/views — `equity_bhavcopy`, `equity_bhavcopy_adjusted`, `adjustment_factors`, `corporate_actions`, `symbol_*`, `universe_*`, `trading_calendar`, `instrument_master`, `ingest_meta`, `ca_*`. **None is a fundamentals table.** The adjusted view's complete column list is `trade_date, symbol, series, open, high, low, close, prev_close, volume, turnover, deliv_qty, deliv_pct` — OHLCV + delivery only.
- Filename search for `*fundamental*` / `*financ*` across the repo: **no files**.
- Repo-wide grep for `roe|net_income|shareholders_equity|earnings_per_share|book_value|EPS` (case-insensitive): **2 hits, both inside the PSB-2 documents themselves.** No ingestion script, no loader, no column.
- The only other stores are `options_bhavcopy.duckdb` and 1,742 daily/1-min OHLCV candle files. A scan of `data/` for `.parquet`/`.csv`/`.json`/`.db`/`.sqlite` files named for fundamentals returns **none**.

**This finding does not depend on the file search.** §2 pins the substrate exhaustively, and every pinned source is OHLCV + delivery. Even if a fundamentals file existed somewhere unindexed, C5's input would not be *pinnable* without amending §2 — and an unpinned input is a §9/§10 violation on its own (no determinism, no audit trail, no certified provenance). C5 is unrunnable under this protocol either way.

So C5's primary input must be newly ingested — which §1 prohibits outright ("Any new data ingestion (operator decision D4, carried from PSB-1)"), and which Phase 0 §2 reasserts ("zero additional consumption", "Substrate inherited from PSB-1").

The fallback clause "*or, if unavailable, trailing annual ROE*" does not rescue this. It is a fallback between two unavailable sources, and it is itself an unpinned free parameter — §5's own heading promises "no free parameters remain", and §9 requires exhaustive pinning. A protocol cannot pre-register a choice it will make later based on what it finds.

This is not a fixable wording defect. **C5 as written is unrunnable.** Note also that ROE is a point-in-time-correct fundamentals problem (restatements, reporting lags, survivorship in vendor data) of roughly the magnitude the substrate certification effort just solved for prices — not a small ingestion.

**Recommended disposition:** drop C5 from the slate and reduce the ledger to four candidates (see F6), **or** the operator explicitly re-opens D4 and authorizes a fundamentals ingestion + certification program as a prerequisite — which is a much larger scope decision than a protocol freeze, and one PSB-2's own framing ("zero additional consumption") argues against.

---

## F2 — BLOCK: C1 fails its own eligibility gate before it runs

### C1's IC is not a new measurement

Compare, verbatim:

| | PSB-1 §5 C5 | PSB-2 §5 C1 |
|---|---|---|
| Score | `σ` over 252 td ending *t*, ≥ 200 obs; `s = −σ` | `σ` over 252 td ending *t*, ≥ 200 obs; `s = −σ` |
| Grid | monthly, last full session | monthly (§3) |
| Dev window | 2012-01-01 → 2022-12-31 | 2012-01-01 → 2022-12-31 |
| Banding | "IC uses no banding" | "IC uses no banding" |
| Exit band | 0.40 | 0.35 |

The **only** difference is the exit band — and both protocols state that **banding does not enter the IC**. The exit band changes portfolio construction, hence turnover, fees, and net spread. It cannot change the score, the grid, the window, or therefore the IC series.

So C1's IC series is **identical by construction** to PSB-1 C5's, which is already recorded in `CLAUDE.md`: mean IC = **+0.068**, t = 3.14, n = 131, **power = 0.54**.

### The power result is therefore already known

Recovering the IC SD from the recorded figures (`SD = δ√n/t = 0.068 × √131 / 3.14 = 0.2479`) and re-running §7's noncentral-t projection reproduces PSB-1's recorded number **exactly**, confirming the model:

| n\* | Cadence | Projected power |
|---|---|---|
| 42 | monthly | **0.541** ← matches PSB-1's recorded 0.54 |
| 84 | fortnightly | 0.802 |

§3 declares **C1 monthly**. §7 pins n\* = 42. Therefore C1's projected power is **0.541**, and §8's eligibility condition (iii) — power ≥ 0.80 — **drops it by rule**, whatever its net spread. To clear 0.80 at n\* = 42, C1 would need a dev mean IC of **0.0967**; the actual value is 0.068, and the tighter 0.35 band cannot move it, because banding does not touch IC.

**C1 is dead on arrival, and we know it before the run.**

### This defeats the exact purpose D10 was amended for

D10's ratified rationale is explicit: *"The fortnightly grid doubles n\* from ~42 → ~84, pushing C5's projected power from 0.54 → ~0.80 — the difference between eligibility and 'no winner.'"* The fortnightly grid exists **to rescue the low-volatility candidate's power**. Yet §3 assigns fortnightly to C2/C3 and leaves C1 — the low-vol successor, the very candidate the amendment names — on monthly, where it is guaranteed to fail.

The amendment's benefit was handed to the two candidates it was not written for, and withheld from the one it was.

**Recommended disposition:** the operator decides whether C1 runs fortnightly (where D10's arithmetic gives it a chance) or is dropped as a known-fail. What is not defensible is freezing a protocol that spends a candidate slot and a Bonferroni share on a predetermined negative.

---

## F3 — BLOCK: cadence is specified four mutually inconsistent ways

| Source | Says |
|---|---|
| **D10** (ratified, Phase 0 §3) | "fortnightly (15-day) or slower… **Each candidate declares its natural cadence.**" Both grids supported. |
| **Phase 0 §6** | "the §3 cadence rule is **monthly only** (D10)." |
| **Protocol §3** | C1 **monthly**; C2, C3 **fortnightly**; C4 monthly/6-mo hold; C5 monthly. |
| **Protocol §5 preamble** | "**All five constructs operate at monthly cadence (D10).**" C2 and C3 headings both read "**, monthly**". |
| **Protocol §7** | "`n*` = number of **monthly** grid dates… (≈ 42)." No fortnightly n\* defined. |

§3 and §5 contradict each other **about the same two candidates**, inside the same document. §5 and §7 assume monthly-only; §3 does not. Phase 0 §6 contradicts the ratified D10 it cites.

This is not editorial. §7's n\* is the sole input that turns a dev IC into the pass/fail power number, and per F2's table the choice is worth **0.541 vs 0.802** — pass or fail, on the same signal. A protocol whose §9 promises "no free parameters remain" cannot leave its most outcome-determining parameter stated four ways.

Downstream damage already visible in the draft, confirming §5 was written assuming monthly while §3 said fortnightly:

- §5's C2 claims "~34 **monthly** formations" for a candidate §3 declares fortnightly (see F4).
- §5's C3 defines `r_i(t)` as "the trailing **1-month** return (close at grid day *t* divided by close at **previous grid day**)". Under §3's fortnightly grid the previous grid day is ~15 days back, so the formula computes a **half-month** return while the prose says one month. The pinned formula and its stated meaning diverge — exactly the class of defect §9 exists to prevent.
- §3's C2/C3 note claims banding at 0.40 yields "turnover ~0.15 → fee drag ~78 bp/yr" — a fortnightly figure — while §5 calls the same candidates monthly.

**Recommended disposition:** one normative cadence table in §3, with §5, §7, and §9 written to reference it rather than restate it. Every per-candidate n\*, turnover, and fee-drag figure recomputed from it. Phase 0 §6's "monthly only" corrected to match ratified D10.

---

## F4 — HIGH: the C2/C3 delivery window is structurally infeasible

§3 and §5 declare C2/C3's delivery window as **2020-04-01 → 2022-12-31 (~34 monthly formations)**.

C2's baseline requires 252 trading days ending *t*−21 with **≥ 150 non-NULL** `deliv_pct`. Delivery data begins **2020-01-01** (verified: non-NULL span 2020-01-01 → 2026-07-09). So *t*−21 cannot precede the 150th full session on or after 2020-01-01:

- 150th full session on/after 2020-01-01: **2020-08-06**
- → earliest feasible formation *t* (+21 sessions): **2020-09-04**

**No formation is possible before September 2020.** The declared window's first five months are structurally empty. Counting monthly grid dates:

| | Count |
|---|---|
| Claimed in §5 | ~34 |
| Monthly grid dates in 2020-04-01 → 2022-12-31 | 33 |
| **Actually feasible** (from 2020-09-04) | **28** |

And 28 is a *ceiling*: it assumes every name has delivery on every session since 2020-01-01. The realized per-name n will be lower.

The error is a scaling artifact. PSB-1's C3 used a **60-day** baseline ending *t*−5, which is exactly why a 2020-04 start worked there. PSB-2 scaled the baseline to **252 days ending *t*−21** but carried the old window forward unchanged.

This matters beyond bookkeeping: n = 28 (not 34) is what feeds the SD estimate and the §8 Bonferroni-deflated p. PSB-1's C3 earned p = 0.002 at n = 143 (weekly); at n ≈ 28 the evidence bar is materially harder, and the operator should see the real number before freezing.

**Recommended disposition:** recompute both candidates' declared windows and expected n from the pinned baseline lengths, script-generated. Also note §3's "common robustness sub-window 2020-04-01 → 2022-12-31" is **degenerate for C2/C3** — it is their entire declared window, so it supplies no robustness information for them — and is itself infeasible before 2020-09-04.

---

## F5 — HIGH: the fortnightly grid is undefined for 43% of months

§3: *"for each calendar month, the **15th** and the **last** full-session trading day per `trading_calendar`."*

The second leg is exact. The first is not: **the 15th is frequently not a trading day.** In the sealed window alone, the literal 15th is not a full session in **18 of 42 months** — 43%. The rule specifies no resolution: nearest session? Last session on or before the 15th? First on or after? Skip the month?

Each choice yields a different grid, different formations, different IC, different n\*. §5's heading — "exact; no free parameters remain" — and §9's exhaustive pinning are both violated as written. PSB-1's §3 avoided this precisely by anchoring to a *rule over sessions* ("the last full-session trading day of that week"), never to a calendar number.

**Recommended disposition:** restate as a session-anchored rule (e.g. "the last full session on or before the 15th"), and verify the resulting grid count from `trading_calendar` before freeze. Note the count reconciles to the expected 84 under the on-or-before reading — but the reading must be *stated*, not inferred by the implementer.

---

## F6 — HIGH: m = 5 penalizes the live candidates for dead slots

§8's evidence floor deflates the winner's p-value by **m = 5**, and §9 pins m = 5 as the ledger size.

C5 cannot produce a promotable result under any branch (F1), and C1 cannot **as currently specified** (F2) — yet both still cost every surviving candidate a 5× p-value deflation. So **m = 5 is indefensible however the operator rules**; only the correct replacement value depends on the rulings.

This is the strongest argument for fixing pre-freeze rather than discovering it in Phase 2: catching it now **materially eases the evidence floor for the candidates that can actually win**. A candidate needing raw p < 0.01 at m = 5 needs only p < 0.0125 at m = 4, or p < 0.0167 at m = 3.

Deflation must be pinned before results exist, or it is unarguable-after-the-fact in name only. Post-freeze, §9 forbids the change — the battery would run with a floor everyone knows is wrong.

**Recommended disposition:** resolve the slate first (F1, F2), then pin m to the number of candidates that can actually produce a result. If the operator restores C1 at fortnightly cadence and drops only C5, m = 4.

---

## F7 — MEDIUM: exit bands drift from the ratified slate, and §5 contradicts itself

D9 ratified the slate in Phase 0 §5. The protocol does not match it:

| | Phase 0 §5 (ratified by D9) | Protocol §5 |
|---|---|---|
| C1 band | "exit only when the name falls out of the **top 30%** (0.30 band)" | **0.35** |
| C5 band | "banded exit" (unspecified) | 0.35 |

D9 ratified "5 candidates, fee-survivable by construction. Exact formulas pinned at protocol freeze" — so pinning C5's band at freeze is in scope, but **changing C1's ratified 0.30 to 0.35 is not**. The draft even describes 0.35 as "tighter than PSB-1 C5's 0.40" without noting it is *looser* than the slate the operator ratified.

§5's preamble also contradicts its own body: it asserts every candidate is "banded exit at ≤ **0.30** band", then defines C1 at 0.35 and C2/C3 at 0.40 — none of which satisfy it. And its "turnover ≤ 0.17" conflicts with Phase 0 §1's "turnover ≤ 0.06".

Per F2, C1's band is immaterial to its IC and power — but it drives the net spread that is eligibility condition (ii), and an undocumented drift from a ratified decision is exactly what the two-party discipline exists to catch.

**Recommended disposition:** reconcile to D9's 0.30, or record an explicit amendment for the operator to ratify. Rewrite the §5 preamble to describe the slate it actually contains.

---

## F8 — MEDIUM: D10's power rationale is not a valid fortnightly projection (ratified-decision awareness)

D10's ratified rationale states the fortnightly grid pushes low-vol power "from 0.54 → ~0.80". The arithmetic reproduces (F2's table: 0.802 at n\* = 84) — **but only by holding δ = 0.068 and SD = 0.2479 fixed while changing n\* from 42 to 84.**

Those δ and SD are properties of the **monthly IC series** — the Spearman correlation between σ-rank and the **~30-day** forward return. The fortnightly IC is a *different random variable*: the correlation between σ-rank and the **~15-day** forward return. Its mean and SD are unmeasured. Rank IC is scale-free, so the horizon change does not cancel; there is no general reason a 15-day IC equals its 30-day counterpart, and nothing in PSB-1 measured it.

So the projected 0.802 rests on an unpinned and unstated assumption. Practically: **even the fortnightly escape hatch has no validated basis for clearing 0.80.** The true fortnightly power is unknown until the fortnightly IC is measured — which Phase 2 does, after the hurdle is frozen.

There is a second reason the n\* = 84 gain is likely overstated, and the protocol already has the machinery to see it: **halving the horizon should raise the IC series' autocorrelation**, because adjacent fortnightly formations sit on overlapping information and a 252-day σ barely moves in 15 days. §6/§7's own AC₁ > 0.1 trigger and Newey–West (lag 4) columns exist for exactly this. But those are **report-only, never gating** — so a fortnightly candidate could clear the frozen 0.80 hurdle on a simple-t projection that its own reported AC₁ shows is inflated. Worth the operator's attention while the hurdle's basis is still amendable.

This touches a **ratified** decision (D10), so it is raised for operator awareness rather than proposed as a unilateral revision. The honest framing: fortnightly gives low-vol a *chance* at 0.80 that monthly provably denies it (F2) — it does not guarantee it. If the operator wants D10's rationale to hold as stated, the assumption "δ is horizon-invariant" should be recorded in §9 as pinned and acknowledged, not left implicit in a rationale cell.

---

## F9 — MEDIUM: C4's formula does not compute what its prose claims

§5 C4 pins:

```
s_i(t) = r_{12,i}(t) − r_{1,i}(t)
```

and describes it as "past 12-month winners (**excluding the most recent month**, to strip the short-term reversal effect)".

Standard 12-1 momentum is the **return from *t*−12 to *t*−1** — multiplicatively, `(1+r_12)/(1+r_1) − 1`. The pinned arithmetic difference `r_12 − r_1` is not that quantity; the two diverge as returns grow (the discrepancy is second-order in the returns and largest exactly for the high-|r| names that populate the top quintile the candidate trades).

The pinned formula is at least *exact and computable*, so this is not a free-parameter defect — but §9 immutability will freeze a formula whose stated hypothesis it does not implement, and any later reader reconciling the two will be unable to tell which was intended.

Related, minor: §5 C4's `r_{1,i}(t)` is defined as "trailing 1-month return (skip most recent month)", which is self-contradictory — a trailing 1-month return *is* the most recent month; it is the term being subtracted, not itself skipped.

**Recommended disposition:** state whether the intended construct is the ratio form or the difference form, and align the prose to the pinned formula.

---

## F10 — LOW: §2 pin tidy-ups

- §2's Prices row pins `open`, but **no §5 candidate uses `open`** — all five read `close`, `deliv_pct`, or (unavailably) ROE. Under §9's exhaustive-pinning discipline, an unused pin is noise; either a candidate was intended to use it (in which case §5 is incomplete) or it should be dropped.
- §2 pins Universe as `universe_membership` alone. PSB-1 §2 pinned `universe_membership` **joined to `universe_eligibility` for `entity`**. Given that the substrate's entity-grain resolution is the hard-won result of PSB-1 Prompts 2–5 (and the recorded pitfall "an entity is not one symbol for all time"), dropping the entity join from the pin is a regression in specificity, even if the harness happens to do it correctly. Confirm whether the omission is intentional.

---

## F11 — HIGH: the mixed-cadence slate breaks §8's ranking rationale

*Raised at disposition (2026-07-16), after D12 pinned C2/C3 to fortnightly and C4 to monthly. It is a consequence of the ruling, not a defect in Rev 1 as drafted, and is recorded here so the finding set stays complete.*

§8 ranks eligible candidates by projected sealed power, justified thus: *"size-invariant across unequal dev windows because it evaluates every candidate on the **common sealed n\***."*

Under D12 there is no common n\*: it is **84** for C2/C3 and **42** for C4. Since §7's noncentrality is `δ√n*/SD`, a fortnightly candidate gains **√2** over a monthly one at identical δ/SD. The quoted clause is now false.

**The rule is sound; only the justification is wrong.** Because each candidate's δ and SD are measured at its own cadence — the 15-day IC being a different random variable from the 30-day IC, per F8 — projected power still answers "how likely is this candidate to clear *its own* sealed gate," which is the program's stated objective. The fix is textual: power is invariant to **dev-window length** (the data accident PSB-1's F1 actually addressed), **not** to cadence — and cadence-dependence is legitimate, because cadence is a design choice with real consequences for sealed-gate success. Re-opening the ranking rule would be an overcorrection.

**Inherited, now load-bearing.** PSB-1 already had unequal n\* (182 weekly vs 42 monthly), so the "common n\*" phrasing was already loose — it simply never bit, because PSB-1 returned "no winner." PSB-2 is engineered to produce a winner *and* deliberately mixed-cadence, so this now helps decide the outcome.

**Concrete consequence to preserve:** power ranking favors C2/C3 (n\* = 84) while the evidence floor favors C4 (**132** monthly dev formations over 2012–2022, against C2/C3's delivery-limited **56** fortnightly) — so the two rankings will likely name **different winners**. §8's existing divergence rule ("if the winner differs, all are presented and the operator decides") is the right escape hatch and must survive Rev 2; the text should flag that it is now expected to trigger rather than treated as a remote contingency.

---

## What the draft gets right

Recorded so the revision does not lose it:

- **The substrate pin is correct and verified.** 7,030,920 rows and the `equity_bhavcopy_adjusted` view both confirm against the live store; `deliv_pct` non-NULL from 2020-01-01 as stated; `read_only=True`; the four-arm contract suite correctly promoted to a §11 structural gate ahead of Phase 1.
- **§7's n\* = 42 is exactly right** — verified against `trading_calendar` at the CSMP `n_symbols >= 200` full-session convention, not approximated.
- **The fee-first framing is the correct lesson from PSB-1** and is carried faithfully: every candidate is argued against the cost structure before the signal.
- **Directions are pre-registered** for C2, C3, C4, and the momentum-fence disclosure (D2/D8) is handled correctly — disclosed as prior exposure, no sealed read authorized, §12 reinforced.
- **§11's sequencing** (substrate gate → harness dev-proof + Lead Review → C1→C5 run order, committed as produced) preserves PSB-1's discipline, including the git-visible ordering that makes post-hoc tampering detectable.
- **C2's core thesis is well-founded** — PSB-1's C3 (+0.025 IC, +17.5% gross) was killed by weekly fees, not by the signal, and retesting it at a fee-survivable cadence is exactly the right use of this battery.

---

## Recommendation

**Do not freeze Rev 1.** Return to DeepSeek V4 for Rev 2 addressing F1–F10, then re-review. The three BLOCK findings each require an **operator decision**, not just an edit:

1. **F1 — C5:** drop it, or re-open D4 to authorize a fundamentals ingestion + certification program (a far larger scope decision than this freeze, and one Phase 0's "zero additional consumption" framing argues against).
2. **F2/F3 — C1 and cadence:** put C1 on the fortnightly grid D10 was amended to give it (a chance at 0.80, per F8 — not a guarantee), or drop it as a known-fail. Then state cadence **once**, normatively.
3. **F6 — m:** re-pin the Bonferroni ledger to the number of candidates that can actually produce a result, which eases the floor for the live contenders.

The two-party discipline worked here exactly as designed: the implementing party drafted, and independent review caught one unrunnable candidate, one predetermined to fail as specified, and a pass/fail ambiguity **before** §9 immutability made them permanent.

**What the live slate is depends on the operator's F1/F2 rulings, and this review does not presume them.** Two branches follow from the recommendations above:

| Branch | F1 — C5 | F2 — C1 | Live slate | m (F6) |
|---|---|---|---|---|
| **A** | dropped | dropped as known-fail | C2, C3, C4 | 3 |
| **B** | dropped | restored at fortnightly cadence | C1, C2, C3, C4 | 4 |

A third branch — the operator re-opens D4 to authorize a fundamentals ingestion and certification program — restores C5, but that is a scope decision far larger than this freeze, and Phase 0's own "zero additional consumption" framing argues against it.

Under either branch the battery is genuinely fee-survivable and worth running once the ledger reflects it honestly. Note that **m = 5 is wrong under every branch** (F6) — that much is settled regardless of how F1 and F2 land.

**One calibration, so "worth running" is not read as "likely to promote."** The live slate is small and thin on dev evidence. Per F4, C2 and C3 cannot form before **2020-09-04**, so their dev window is delivery-limited — **56 fortnightly formations** under D12 (28 had they stayed monthly), against the n = 143 that earned PSB-1's C3 its p = 0.002 at weekly cadence. That is roughly 40% of the observations, on a signal whose per-formation strength there was +0.025 mean IC. Even with F6's relief at m = 3, it is a steep evidence floor.

*(Figures updated 2026-07-16 after D12. This paragraph previously read "~28 monthly formations… roughly a fifth" — correct while F3 was open and monthly was one reading, stale once D12 pinned C2/C3 to fortnightly. The fortnightly grid halves the thinness; the concern stands at reduced magnitude. Counts are script-derived from `trading_calendar` at the `n_symbols >= 200` convention, not scaled by hand.)*

---

# Rev 2 Re-Review (2026-07-16)

**Subject:** `PSB2_PROTOCOL.md` DRAFT Rev 2, authored by DeepSeek V4 against `PSB2_IMPLEMENTATION_PROMPTS.md` §Prompt 0.

**Verdict:** **DO NOT FREEZE — one BLOCK, three failed acceptance criteria.** Substantially closer than Rev 1: the slate, cadence, grid rule, and C4 formula are all correctly resolved, and F11 is disposed properly despite the status line not claiming it. But the single most important item in Prompt 0 — the one guarding the program's chief audit exposure — is absent.

## Findings

| # | Severity | Finding | Criterion |
|---|---|---|---|
| R1 | **BLOCK** | The m = 3 **data-independence rationale is absent**. §8 justifies m = 3 only as "corresponds to the three live candidates" — circular, and precisely the reading that looks like rigging. | #2 FAIL |
| R2 | HIGH | F8's horizon-invariance assumption is **not** recorded in §9; §7 does not state the AC₁ exposure. | #8 FAIL |
| R3 | HIGH | §3's "Dev window: all candidates on 2012-01-01 → 2022-12-31" is **false for C2/C3**, whose entire feasible window is 2020-09-04 → 2022-12-31. Regression from PSB-1's per-candidate declared windows. | — |
| R4 | HIGH | §9 pins "252-day vol window with ≥ 200 obs" — an **orphan pin from the dropped C1**. No surviving candidate uses a volatility window. | #6 FAIL |
| R5 | MEDIUM | "~55 fortnightly formations ceiling" is a hand estimate, not script-derived, and is **wrong**: the true count is **56**. | #4 FAIL |
| R6 | LOW | Status line and §13 claim "F1–F10"; F11 *is* addressed in §7/§8 but uncredited, so the findings ledger does not reconcile. | #10 partial |

### R1 — BLOCK: the m = 3 rationale is missing, and this is the one that matters

§8 closes with: *"Bonferroni m = 3 corresponds to the three live candidates (C2, C3, C4). Deflation is pinned now, not after results."*

That is circular. It says m = 3 because there are three candidates — which a hostile reader already knows. It does not say **why dropping from five to three is legitimate rather than a loosened correction after the two weakest were removed.**

Prompt 0's criterion #2 was explicit: m = 3 **"with the data-independence rationale written into the protocol"**, and *"legible to a reader who was not in the room."* The reasoning exists in D11 but the protocol is the frozen artifact — a reader reconstructing the program's integrity years later reads §8, not the Phase 0 record's decision table.

The missing argument: both drops are **data-independent**. C5's follows from a schema fact (no ROE column) knowable without any run; C1's follows from PSB-1's already-published, already-banked results. Neither candidate is ever scored on PSB-2 data, so neither consumes a chance at a PSB-2 false positive, so neither may inflate the penalty. Deflating by candidates that cannot produce a result would be an arbitrary tax on the ones that can. **m = 3 is the honest ledger, not a relaxation** — but only if the protocol says so.

This blocks the freeze. §9 immutability makes the protocol's text the permanent record of its own defensibility.

### R3 — HIGH: C2/C3's declared dev window is stated two incompatible ways

§3 line 50: *"**Dev window:** all candidates on **2012-01-01 → 2022-12-31**."*
§3 line 51: *"**C2/C3 delivery-data sub-window:** 2020-09-04 → 2022-12-31."*

Calling the second a "sub-window" implies C2/C3 have formations across 2012–2022 with a delivery-limited subset. They do not: **no C2/C3 formation is possible before 2020-09-04** — that is their whole declared window, not a subset of a larger one.

This is load-bearing, not pedantic. §8's evidence floor is computed on *"the winner's **declared-window** one-sided p"*, and §7 takes δ and SD from *"each candidate's declared window."* An ambiguous "declared window" for two of three candidates leaves the two most outcome-determining inputs unpinned. PSB-1 §3 got this right with per-candidate declared windows ("C1, C2, C5: 2012→2022. C3, C4: 2020-04→2022"); Rev 2 regressed. State per-candidate declared windows and drop the "sub-window" framing for C2/C3.

### R4 — HIGH: an orphan pin from a dropped candidate

§9's exhaustive list still contains *"252-day vol window with ≥ 200 obs"*. That was **C1's σ_i(t)**, and C1 is gone. C2 uses a 252-day *delivery* baseline (separately and correctly pinned); C3 inherits C2's score plus a 21-trading-day return; C4 uses 12 grid dates of price history. **No surviving candidate computes a volatility window.** Criterion #6 named this exact class. Delete it — an exhaustive ledger containing a parameter no candidate uses is not exhaustive, it is stale.

### R5 — MEDIUM: the formation count is hand-estimated and wrong

§3 asserts *"~55 fortnightly formations ceiling."* Script-derived from `trading_calendar` at the pinned `n_symbols >= 200` convention over 2020-09-04 → 2022-12-31: **28 mid-month + 28 month-end = 56**. (September 2020's mid-month grid date is 2020-09-15, which is ≥ 2020-09-04 and therefore in range — the likely source of the off-by-one.)

The tilde is the tell: criterion #4 required every formation count to be script-derived and printed. The repo rule is no hand-edited numbers, and a protocol that hand-estimates its own n is the wrong artifact to relax it in.

## What Rev 2 gets right

Substantial and worth recording:

- **F9 resolved better than the finding asked.** C4 is now the ratio form `(1+r_12)/(1+r_1) − 1` with prose correctly describing "the 11-month return from *g*−12 to *g*−1." The self-contradictory "trailing 1-month return (skip most recent month)" is gone.
- **F11 is correctly disposed** — §7 and §8 both state the cadence-dependence plainly ("not invariant to cadence… the fortnightly noncentrality advantage is structural and disclosed") and preserve divergence reporting. The status line's "F1–F10" undersells the work (R6).
- **F5 exactly as recommended** — the grid is session-anchored ("last full session on or before the 15th"), unambiguous for every month.
- **F3's C3 sub-finding resolved elegantly** — `r_i(t)` is now pinned to *t*−21 **trading days**, decoupling the return horizon from the grid, so the formula and its "1-month" prose agree at any cadence.
- **F10 both items** — `open` dropped; the `universe_eligibility` entity join restored.
- **F4's date** — 2020-09-04 carried correctly into §3, §5, and the robustness sub-window.
- **F1/F2** — C1 and C5 fully removed from §1, §5, §9, and §11's run order, with no "deferred" residue.

## Recommendation

**Rev 3.** R1 alone blocks; R3/R4 fail named criteria and would freeze defects into an immutable document. All five are text fixes against work already done — no re-analysis, no re-derivation, no operator decision required. R1 is a paragraph that already exists in D11 and needs transcribing into §8 with its reasoning intact. This review deliberately puts **no projected t or p** on it: doing so would require assuming the IC is horizon- and cadence-invariant, which F8 rejects. The honest statement is qualitative — PSB-2 may well return "no winner recommended" again, and for a reason distinct from PSB-1's. PSB-1 died on fees; PSB-2's fee-survivable constructs buy cost survival by trading away the formation count that generates statistical evidence. **That tension is structural, not a defect in this draft**, and the operator should see it before committing Phase 2 rather than discovering it in the selection report.
