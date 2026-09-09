# Review — RFA Gate Session, O1 Declaration, and PSB-O0 Option Backfill

**Date:** 2026-07-21
**Reviewer:** Claude (review-only role per standing implements/reviews split)
**Scope reviewed:** commits `9bcb838`, `35b3469`, `aba1bc2`, `a11ba32`, `6a433ac`
**Verdict:** **ACCEPT the substrate work. REJECT the O1 PROCEED verdict** — it is an artifact of
a precondition violation, not a finding. Two gate-hardening defects found (prior-session, not
introduced by this work).

---

## 0. Scope correction — who built what

The premise "GLM implemented RFA_gate" is not quite right, and it matters for apportioning the
findings. Git records every commit as `Codex`, so authorship is not distinguishable from the
log; the boundary is the session boundary.

| Work | Commits | Session |
|---|---|---|
| RFA gate itself (power core, declaration contract, verdict, report, retrospective, CLAUDE.md) | `c5d5908`..`b5deb33` (8) | **Prior session** — spec + plan + 6 tasks, 34 tests |
| O1 declaration + RFA report | `9bcb838`, `a11ba32` | GLM |
| PSB-O0 option bhavcopy extension + 5.49M-row backfill | `35b3469`, `aba1bc2` | GLM |
| Session report | `6a433ac` | GLM |

So the gate was already built and committed. **GLM's actual contribution is the first real
declaration, the option-data substrate, and the write-up.** The two gate-design defects in §3
below are inherited, not introduced.

**On the scope complaint — it is justified, but narrowly.** The RFA gate is *data-free by
design* ("It reads no market data, so it is free" — CLAUDE.md). GLM downloaded 5.49M rows of
NSE F&O bhavcopy in the course of filling out one integer field (`n_available`). That is scope
creep against the brief. The mitigation is real, though: the download **disproved** the number
GLM had already committed (`n=520`, assuming a Feb-2016 weekly launch), forcing the correction
to `n=380`. A declaration is only as good as its formation count, and that count was wrong
until the data was inspected. Undisciplined, but it caught a real error.

---

## 1. HEADLINE — the O1 PROCEED verdict does not survive its own declaration

### The defect

The declaration derives `delta` **from** `sd` via a Sharpe translation, stated explicitly in
`delta_provenance` (`governance/rfa/declarations/o1_vrp.py:17-18`):

> "The mean band [0.002, 0.005] per week on SPAN margin is the translation of Sharpe 0.5-1.0
> at the declared SD band: `weekly_mean = (S/sqrt(52)) * weekly_sd`."

This makes delta and SD **perfectly coupled**. But `gate.evaluate()` assumes they are
independent and forms its optimistic corner by **crossing** them — `(delta_hi, sd_lo)`
(`scripts/rfa/gate.py:34`). The generated report defends this as deliberate conservatism:

> "Because the bands are declared independently, (delta_hi, sd_lo) may describe a large edge
> with unusually stable outcomes — the least plausible combination in practice and the most
> generous to the construct."

The precondition in that sentence — *"because the bands are declared independently"* — is
false for this declaration. So the corner is not "generous but admissible." It is **outside
the declarant's own stated support.**

### What the numbers actually say

Reading the declared endpoints the way the declaration's own model requires (fixed Sharpe →
delta ∝ sd, so lo pairs with lo and hi with hi):

| Reading | delta | SD | Implied ann. Sharpe | Power at n=380 | Verdict |
|---|--:|--:|--:|--:|---|
| **Coherent lo/lo** | 0.002 | 0.025 | **0.577** | **0.4649** | **ABANDON** |
| **Coherent hi/hi** | 0.005 | 0.060 | **0.601** | **0.4907** | **ABANDON** |
| Declarant's stated ceiling * | — | — | 1.000 | 0.8540 | PROCEED (thin) |
| **Gate as run (crossed corner)** | 0.005 | 0.025 | **1.442** | **0.9877** | PROCEED |

\* This row is itself inconsistent with the declared numbers: Sharpe 1.0 at `sd_hi=0.060`
requires `delta = 0.00832`, not the `delta_hi = 0.005` declared. It is shown only as the most
generous reading the declaration's *prose* can bear.

The declared band is not a Sharpe 0.5–1.0 range at all. **Both endpoints sit on essentially the
same constant-Sharpe line, ≈ 0.59** — and the spread between them is only 0.024, which is the
tell. Two genuinely independent intervals would not land both natural pairings on the same
Sharpe line. Fixing S = 0.59 and translating across the declared SD band reproduces the declared
delta band almost exactly: `(0.59/√52)·0.025 = 0.00205` and `(0.59/√52)·0.060 = 0.00491` versus
the declared `[0.002, 0.005]`. By contrast, the stated translation of Sharpe 0.5–1.0 across that
SD band would have produced `delta ∈ [0.001733, 0.008321]`. The declaration's stated derivation
and its declared numbers disagree; the numbers encode a single Sharpe, not a range.

**The finding degrades gracefully — it holds under either reading:**

- **Accept the ≈0.59 reconstruction** (the only internally consistent reading): max power ~0.49
  → **ABANDON**.
- **Reject it and insist the bands are independent**: the crossed corner still demands Sharpe
  **1.44**, exceeding the declarant's own stated ceiling of 1.0. Clamp to that ceiling and power
  is **0.854** — a **thin** PROCEED with n_required 323 against 380 available (1.18× margin),
  not the reported 2.4×.

So: **at best a thin PROCEED, at worst ABANDON — never the comfortable PROCEED that was
reported.** No reading of the declaration supports "clears comfortably either way."

### The cleanest way to state O1's real position

The session report's own §6.1 finding (`ncp = S√T`, cadence cancels — see §5; it is correct and
valuable) collapses this to one number. Power depends only on annualized Sharpe and elapsed
years, so:

> **O1 is demonstrable at power 0.80 if and only if its true annualized Sharpe is ≥ 0.92**,
> given 7.4 years of weekly formations (n=380).

Against that threshold:

| Evidence source | Implied Sharpe | Demonstrable? |
|---|--:|---|
| In-repo prior-exposed evidence (MSRP Phase 7 straddle, ~Rs 158/day) | ~0.5 | No |
| The declaration's own endpoints | ~0.59 | No |
| Declarant's stated literature ceiling | 1.0 | Marginal (power 0.854) |
| Required by the gate's crossed corner | 1.44 | — beyond declared support |

Every independent line of evidence O1 cites points **below** the demonstrability threshold. GLM
had the tool to derive this (§6.1 is GLM's own finding) and did not apply it to O1.

### Assessment

This is not a rounding issue. The gate's single job is to answer "can this ever be
demonstrated," and on the declaration as written the honest answer is **no**. The report's
framing — "clears comfortably either way," "2.4× margin" — is wrong in the direction that
flatters the construct.

**Recommendation: withdraw the O1 PROCEED and re-declare.** Since delta and SD are coupled for
a `per_trade_pnl` metric, the re-declaration should declare a **Sharpe band directly** and let
the gate derive the rest — see §3.

---

## 2. Provenance — the binding input rests on citations that do not check out

The gate's entire value proposition is "independently defended bands, each with required
provenance." Four sources carry the two binding bands. All four have problems:

| Citation | Status |
|---|---|
| "Bakshi-Ju (2017)" | **Unlocatable.** No such paper found. Bakshi's known VRP work is Bakshi & Kapadia (2003, RFS). |
| "Cheng (2018, JFE)" | **Mis-cited and mis-applied.** It is Ing-Haw Cheng, *The VIX Premium*, **RFS 32(1), 2019** (WP May 2018). It concerns the **VIX-futures** premium and argues the premium *response* is puzzlingly low — it is not a source for "net-of-cost Sharpes of 0.4–1.0 for defined-risk short variance." |
| "Indian short-premium studies (Kumar-Iyer et al)" | **Not a citation.** No title, year, or venue. Unverifiable as written. |
| "Moreira-Muir (2017)" | **Real** (*Volatility-Managed Portfolios*, JF 2017) but **mis-applied** — it is about volatility *timing* of portfolio exposure, not an SD haircut for short-variance dispersion. |

**In fairness, the magnitude is not crazy.** The genuine literature does report Sharpe ratios of
roughly **0.85–0.98 for shorting variance swaps** on S&P 500 / S&P 100 / Dow (Carr–Wu 2009 and
successors). So a 0.5–1.0 band is in the right neighbourhood — **but not by the route claimed**,
and with two material transfers left undefended:

1. Those are **gross, pre-cost** figures. The declaration says "net-of-cost."
2. Those are **US index variance swaps at full notional**. O1 is an **Indian defined-risk iron
   condor on SPAN margin**. Wings cap the payoff and margin changes the denominator; neither
   transfer is argued.

Per the gate's own doctrine, provenance is the load-bearing input. Citations that cannot be
located, or that say something other than what they are cited for, mean the band is
**undefended** — which under the gate's rules should block approval regardless of the
arithmetic.

---

## 3. Two gate-design defects (inherited — prior session)

These would let the §1 failure recur on any future declaration.

**D1 — the gate never validates that its corner lies inside the declared support.**
`scripts/rfa/gate.py:34` forms `(delta_hi, sd_lo)` unconditionally. Nothing checks whether that
point is one the declarant defended. Suggested fix: require an explicit `sharpe_lo`/`sharpe_hi`
(or a `bands_independent: bool`) on `Declaration`, and reject or clamp any corner whose implied
Sharpe exceeds the declared ceiling.

**D2 — "independent bands" may not be well-defined for `metric="per_trade_pnl"`.**
For a PnL metric, mean and SD are linked through Sharpe almost by definition — a declarant
cannot honestly move one without the other. The independence assumption is defensible for
`rank_ic` (where IC dispersion is largely a sample-size artifact) but not here. The contract
should either forbid independent delta/SD declaration for `per_trade_pnl`, or accept a Sharpe
band directly and derive delta internally.

Everything else in the gate is sound. `scripts/rfa/power.py` is correct (noncentral-t,
one/two-sided, binary-search inversion), the whole-file SHA-256 digest is the right lesson from
PSB-2's MEDIUM-1 finding, and the methodology-version hard-fail is good discipline.

---

## 4. The option data — verified independently, and it is good

I checked the download rather than taking the audit report's word for it.

| Check | Result |
|---|---|
| Volume | 5,490,319 rows, 2,572 trade dates, 2016-02-11 → 2026-07-17, 304 MB |
| Scope | **NIFTY only** — no contamination (the NIFTYNXT50 purge works) |
| Schema | Sensible 5-part PK (symbol, expiry_dt, strike, option_type, trade_date) |
| Null/zero density | **Zero** nulls in settle/open; zero `close=0` across all 11 years |
| **2022→2023 ingest seam** | **Clean** — 1881 → 1710 → 1714 rows/day across the join. No structural discontinuity where old and new ingests meet. This was the main suspicion; it is not there. |
| Per-year coverage | 218–250 trade dates/year — normal NSE calendar, no gaps |

**The Feb-2019 weekly-launch correction is empirically confirmed.** Distinct expiries per year:
2016→11, 2017→12, 2018→13 (monthly only), then **2019→47**, 2020→53. First weekly expiry in the
data is `2019-02-14`. The claim is exactly right, and it is right *against* GLM's own earlier
committed assumption. That is the correction discipline working.

The ingestion script change (`35b3469`) is a **2-line diff** — extends the default start and
adds optional CLI args. No over-engineering, no abstraction added for one-time use. Correct.

**Still open (both flagged honestly in the session report):** the substrate has **not** been
through the PSB-1-style four-arm contract certification, and lot-size transitions (75→50→25→75),
strike-grid changes, and the Thursday→Tuesday expiry migration are exactly the class of silent
corrupters that certification exists to catch. India VIX history also only reaches back to 2023,
against options data to 2016.

---

## 5. What is genuinely good here — do not throw this away

1. **§6.1 — power is cadence-invariant.** `ncp = (S/√c)·√(cT) = S√T`; cadence cancels. This is
   correct, non-obvious, and it **falsifies a claim standing in CLAUDE.md** (the F1 closure's
   "higher cadence → more formations → escapes the sample wall"). Higher cadence buys nothing;
   only longer windows or higher Sharpe do. This is the most valuable thing in the session and
   should be propagated into CLAUDE.md regardless of what happens to O1.
2. **The self-caught n=520→380 error**, verified above and disclosed in-band in the commit
   message, the declaration `window` field, and the report — not silently patched.
3. **The digest was regenerated after the declaration edit** — verified that
   `25d4a723679ade9dedcabcf94d9968074e3e0e350f158630e301f697b64f2dad` matches the current file
   byte-for-byte. The seal was not left stale.
4. **The option substrate itself** is 10.5 years of clean NIFTY option data the repo did not
   have. It is a prerequisite for *any* options construct, independent of O1's fate. Given that
   F1 died precisely because NSE has locked down historical F&O data, having pulled this is a
   durable asset.
5. **34/34 tests pass** — run and confirmed.
6. **Honest disclosure throughout** — the `prior_exposure` field explicitly admits the delta
   band's centre is "consistent with prior-exposed evidence, not independent of it," and the
   report volunteers that the central case fails by 2.4×. The weakness was not hidden; it was
   just not followed to its conclusion.

---

## 6. On the legacy-cruft concern

Two separate things here, and the diagnosis differs.

**`OPTIONS_STRATEGY_RESEARCH.md` is NOT legacy.** It is dated 2026-07-17 and was committed
2026-07-18 in `8811767` — three days before this session, from this repo's own research line. It
explicitly states no candidate is authorized and that any pursuit requires a pre-registered
battery. **Following it to O1 was legitimate**, and O1 is the one candidate in that slate that
does not depend on phantom infrastructure.

**DayTypeEngine IS phantom, and that is a pre-existing documentation defect.** Searched:

- No `DayTypeEngine` class anywhere in the repo — zero `.py` hits.
- `scripts/build_intraday_features.py` — **missing**.
- `scripts/train_daytype_classifier.py` — **missing**.
- No `logistic_13pm_prod` model artifact.
- `v9_pm_runner` — only in `docs/archive/`.

Yet **CLAUDE.md carries an entire "DayTypeEngine — Feature Blocks" section** describing an
80%-validation-accuracy production model and giving retrain instructions for scripts that do not
exist. This directly contradicts CLAUDE.md's own "No production strategy currently exists"
section. It is pre-SALVAGE residue that survived the migration in docs but not in code.

**The consequence:** `OPTIONS_STRATEGY_RESEARCH.md`'s **O2 candidate** — starred as "the
differentiated edge" — is built entirely on this phantom, and its executive summary claims the
platform "already holds an unfair infrastructure position: ... a validated 80% day-type
classifier." That asset does not exist. The other two claimed assets **do** (`NseMarginEngine`,
`core/analytics/options_analytics.py` — both verified present).

This is not GLM's doing, and **O1 does not depend on it** except as an optional regime filter.
But the stale CLAUDE.md section should be deleted before it seeds another candidate.

---

## 7. Recommendations

| # | Action | Priority |
|---|---|---|
| 1 | **Withdraw the O1 PROCEED.** Mark `O1_RFA.md` superseded — the corner violates the declaration's own Sharpe support; coherent readings give power ~0.49 → ABANDON. | **HIGH** |
| 2 | **Fix D1** — gate must reject a corner outside declared support (add a Sharpe band to `Declaration`). | **HIGH** |
| 3 | **Fix D2** — forbid independent delta/SD for `metric="per_trade_pnl"`, or accept a Sharpe band and derive delta. | **HIGH** |
| 4 | **Re-source the provenance** or drop the band. Cite Carr–Wu-lineage figures accurately, and defend the gross→net and US-variance-swap→Indian-defined-risk-on-SPAN transfers explicitly. | **HIGH** |
| 5 | **Delete the stale DayTypeEngine section from CLAUDE.md**; add a caveat to `OPTIONS_STRATEGY_RESEARCH.md` §O2 that its core asset does not exist. | MEDIUM |
| 6 | **Keep the option substrate.** Run four-arm contract certification before any construct trusts it. | MEDIUM |
| 7 | **Propagate §6.1 (cadence invariance) into CLAUDE.md** and correct the F1 closure's "higher cadence" prescription. | MEDIUM |
| 8 | Backfill India VIX to 2019 to match the options window. | LOW |

**The uncomfortable bottom line — and a distinction worth keeping crisp.** The gate *as coded*
outputs PROCEED (0.9877); that was run and confirmed. This is **not a code bug producing a wrong
number.** The finding is that a correctly *specified* declaration — one declaring a Sharpe band,
with D1/D2 fixed — would yield **ABANDON** on O1's own evidence, which puts it at Sharpe ~0.5–0.6
against a 0.92 demonstrability threshold. The declaration was written in a form the gate does not
police, and it routed around the check.

That makes this the fourth time demonstrability has bound (C5, C4, C2-extended, F1 — now O1). The
gate's premise is sound; its contract needs to stop accepting inputs that can encode a Sharpe
claim it never inspects.

---

*All numbers in this review are script-generated or read directly from the committed artifacts
and the DuckDB store. Power figures computed with the repo's own `scripts/rfa/power.py`
semantics (noncentral-t, α=0.05, one-sided, n=380).*
