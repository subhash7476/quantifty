# PSB-1 Phase 1 — Fifth Lead Review (Prompt 3)

**Reviewer:** Claude (Lead Reviewer). **Implementer:** DeepSeek V4.
**Under review:** Prompt 3 (time-aware entity resolution) — `scripts/psb1/repair_entity_intervals.py`,
`build_universe.py`, `build_adjusted_view()`. Implementer invoked the STOP rule; real store untouched.
**Prior reviews:** `PSB1_PHASE1_LEAD_REVIEW.md`, `_2.md`, `_3.md`, `_4.md`.
**Protocol:** `PSB1_PROTOCOL.md` (FROZEN Rev 2).

## Verdict

**The STOP was correct procedure but rests on a wrong diagnosis. The Prompt 3 repair is SOUND and
is APPROVED to apply.** Neither anomaly is a defect in the Prompt 3 work:

- **Finding A is REJECTED as diagnosed.** The backward-adjustment convention is not buggy. There is
  no "latent bug for every single-name bonus." The implementer proposed a root cause that, if acted
  on, would have corrupted 1,043 correctly-adjusted corporate actions.
- **Finding B is ACCEPTED as benign**, but the implementer under-diagnosed it: the invariant is
  mis-specified in **two** ways, not one. The production view is correct; only the *check* is wrong.

What the implementer actually surfaced — without recognising it — is a **confirmed error in the NSE
CF-CA source feed**, and it is the single root cause of *both* Finding A and Review 4's Finding 3.
That is a genuinely valuable result, and it is what Prompt 4 must address.

**Do not tune the adjustment convention. Do not drop DVL's factor. Re-key it.**

---

## Finding A — REJECTED as diagnosed; the real root cause is a mis-keyed corporate action

### The implementer's claim

> "DVL's only factor has `ex_date = 2021-08-05`, and backward adjustment scales prints with
> `ex_date > trade_date` — so 08-05 itself is unscaled while 08-04 is scaled ×0.6667. This is the
> **same latent bug for every single-name bonus**."

### Why the convention is correct (and why acting on this would have been destructive)

`ex_date > trade_date` (`ingest_corporate_actions.py:564`) is the **standard, correct** backward
adjustment. The ex-date print *already* reflects the corporate action; rescaling it would double-apply.
Three independent lines of evidence:

| Test | Result |
|---|---|
| All BONUS/SPLIT ex-dates with a computable adjusted return | **1,106** |
| …where the adjustment absorbs the CA (`\|adj_ret\| ≤ 15%`) | **1,043 (94.3%)**, median residual **3.17%** |
| For a real CA, does the **open** reprice by the factor? | COCHINSHIP `implied_open` 0.506 vs f 0.500; ADANIPOWER 0.209 vs 0.200; KRBL 0.103 vs 0.100 — **yes** |

If the convention were broken, **all 1,106** would show a fabricated jump. They do not. The identity
is `adj_ret(ex_date) = implied_close / f − 1`: when the market reprices by the factor,
`implied_close ≈ f` and the adjusted return goes to ≈ 0. The convention is doing exactly its job.

### The 63 "fabricated" jumps are mostly real market moves

The implementer's framing over-counts. Of 63 ex-dates with `|adj_ret| > 15%`, **51 have an open that
reconciles with the factor** — the CA is real, and the large close-to-close move is a genuine
**ex-date rally to the +20% upper circuit**, a well-documented Indian-market phenomenon on bonus and
split days. COCHINSHIP is the clean illustration:

```
2024-01-09  close 1338.00                       (cum)
2024-01-10  open   677.00   <- theoretical ex-price 1338 x 0.5 = 669.00  (CA is real)
            close  802.80   <- +20.0% off the adjusted base: upper circuit, a genuine rally
```

The adjusted view reports +20.0% here because the stock **actually rose 20%**. This is a correct
measurement, not a fabrication. Reporting it as one would have discarded 51 valid observations.

### What DVL actually is

DVL is the opposite case, and it is not a convention problem at all:

| | 2021-08-04 close | 08-05 open | 08-05 close | implied_open | verdict |
|---|---:|---:|---:|---:|---|
| **DVL** (Dhunseri Ventures, BSE 523736) | 300.75 | 303.30 | 281.05 | **1.0085** | **never repriced** |
| **DTIL** (Dhunseri Tea, BSE 538902) | 521.15 | **330.00** | 346.65 | **0.6332** | **repriced ×⅔** |

DTIL's theoretical 1:2 ex-price is `521.15 × ⅔ = 347.4`. **Its open (330.0) and close (346.65) both
land on it.** DVL has **zero** sessions with a >20% drop anywhere in 2021.

The company that repriced holds **no factor**. The company that holds the factor **never repriced**.
Same date, same ratio. These are not two defects — they are one:

> ### The NSE CF-CA feed mis-keyed DTIL's bonus to DVL.

Source evidence, `data/market_data/corporate_actions_raw/CF-CA-equities-01-01-2021-to-31-12-2021.csv`:

```
"DVL","Dhunseri Ventures Limited","EQ"," Bonus 1:2","10","05-Aug-2021","06-Aug-2021","-","-"
```

NSE assigned both the symbol **and** the company name to the wrong Dhunseri entity. DTIL does not
appear in the file at all. But **BSE carries the correct record** — scrip `538902`, ex-date
2021-08-05, *"Bonus issue 1:2"* — which the BSE dividend-only path (a deliberate, sound design
decision) types as `DIVIDEND`, so no factor was ever built from it. The price panel corroborates BSE,
not NSE.

The ingest did not cause this: `resolve_symbol_at_ex_date` only walks renames **new → old**, and the
`DPL → DVL` rename (2019-01-02) precedes the ex-date, so no remap occurs. The stored raw payload
matches the CSV byte for byte. **This is a source-feed error, confirmed against two independent
corroborating sources (BSE register + price panel).**

### This unifies Finding A with Review 4's Finding 3 — and vindicates Prompt 3

Review 4 (Finding 3) recorded DTIL's bonus as *"absent from the NSE feed entirely"* and treated it as
a **coverage gap**. It is not a gap. It is a **mis-key**, and that reframing is what makes everything
consistent:

- **Prompt 2 was right by accident.** Its time-agnostic union merged DVL and DTIL into one entity,
  which routed the mis-keyed factor back to the company it actually belonged to. Review 4 called this
  *"luck, not correctness"* — correct, and now we know precisely why it landed.
- **Prompt 3 correctly split the entities, and in doing so correctly exposed the mis-key.** DVL keeps
  the factor it should never have had (→ the +40.2%); DTIL loses the factor it always deserved
  (→ P5's −0.3348, the raw unadjusted bonus drop).
- **Review 4 predicted exactly this** (lines 208–211): *"Fix the entity bug without fixing this and
  DTIL silently becomes unadjusted again — a real +50% fabricated return, this time in the `close`
  series."* P5 is that prediction coming true. It is a **pass**, not a failure.

**Prompt 3 introduced no defect. It removed the mask.** That is what it was asked to do.

### Disposition: re-key, do not drop

Moving `(DVL, 2021-08-05, BONUS, 0.6667)` → `(DTIL, 2021-08-05, BONUS, 0.6667)` is a **one-row fix**
that simultaneously:

1. removes DVL's fabricated **+40.2%** adjusted return, and
2. restores DTIL's correct adjustment, removing the **−33.48%** fabricated close return.

Dropping the factor would fix (1) and leave (2) permanently broken. **Review 4's sequencing was right
and must hold:** the re-key can only land *after* the entity split, or `events` would compound DVL's
0.6667 with DTIL's 0.6667 to 0.4444 and halt the build.

---

## Finding A′ — NEW, HIGH: the evidence screen has a structural blind spot

`record_evidence_exceptions` compares the stored factor against the market's own repricing and flags
deviations beyond `EVIDENCE_TOLERANCE = 0.25`, using `min(dev_open, dev_close)`. The tolerance is
**relative to `f`**, so a CA that fails to reprice **at all** produces `dev = |f − 1.0| / 1.0`. That is
detectable only when:

```
|f − 1| > 0.25   <=>   f < 0.75
```

**Every corporate action with factor ≥ 0.75 is invisible to the screen when it does not reprice.**
Measured against the register: **28 no-reprice CAs sit at `f ≥ 0.75`, and the screen caught 0 of them.**

The screen's 4 exceptions are all real (SAHPETRO, KWALITY, DVL, AHLEAST). But it misses at least a
fifth:

| symbol | ex_date | factor | expected drop | observed | screen |
|---|---|---:|---:|---:|---|
| **STAMPEDE** | 2017-01-10 | 0.8000 | −20% | **−2.2%** | **MISSED** — `dev = 0.18 < 0.25` |

Two caveats I will not paper over:

- **The tail is genuinely ambiguous.** At `f ≈ 0.909` (a 1:10 bonus) the expected drop is only ~9%,
  which is inside the noise of a stock that rallied into its ex-date. Of the 28, only those with a
  large expected drop and a near-zero observed one are unambiguous. **I am not asserting all 28 are
  bad**, and the implementer must not either. They need a better discriminator than open-vs-factor.
- **AHLEAST is a different failure class again.** It *did* reprice — but by **×0.528**, not the
  registered 0.6667. The market says 1:1; the register says 1:2. That is a **wrong ratio**, not a
  spurious event, and dropping the factor would leave a real bonus unadjusted. Per-name adjudication,
  not a blanket rule.

### Materiality — this does not block Prompt 3

**The symbol that matters here is DTIL, not DVL.** Prompt 3 *moves* the artifact: DVL's +40.2%
persists until Prompt 4 re-keys it, but the new one Prompt 3 creates is DTIL's **−33.5%** unadjusted
bonus drop. If DTIL were a scored member, the panel would be contaminated in the Prompt-3 → Prompt-4
interval. It is not:

> **DTIL holds ZERO universe memberships, ever** (`universe_membership`, all rebalances).

This is also the independent explanation for the implementer's P6 result. Prompt 3 predicted that *if*
DTIL were a member it would surface as a `CA-shaped-orphan` and take halt 1 → 2. The copy rebuild
returned **halt = 1 (KWALITY only)**. `load_panel` is member-scoped, so it never sees DTIL. The
prediction and the observation agree: **the −33.5% does not enter the scored panel.**

The other four confirmed-bad CAs (SAHPETRO, KWALITY, DVL, AHLEAST, STAMPEDE) likewise hold no
membership within ±400 days of their bad ex-date. R1 is already halting on KWALITY independently.

But the blind-spot tail **does** contain members. Joining all 32 suspects against membership windows
that bracket their own bad ex-date returns **exactly one** hit:

> **OMAXE, ex 2013-11-11, f = 0.7959, `implied_open` = 0.9153** (expected −20%, observed −8.5%) —
> held across its own suspect ex-date at **3 rebalances**. It is the **only** suspect that can reach
> the scored panel, and it must be adjudicated before the A2 substrate is certified.

---

## Finding B — ACCEPTED as benign; the *check* is wrong, not the view

The implementer is right that DTIL 2015-02-04 is not a fabrication, and right that an
entity-interval-aware invariant yields 0. But the diagnosis is incomplete. The check is mis-specified
in **two** independent ways, and only one was identified.

DTIL's prints around the seam:

```
2010-07-20 .. 2010-07-23   EQ   ~165     <- entity DPL (Dhunseri Petrochem, pre-rename)
        [ 4.5-year gap ]
2015-01-20 .. 2015-02-03   BE   213-259  <- entity DTIL (Dhunseri Tea, relisted)
2015-02-04 ..              EQ   221.90   <- entity DTIL, migrated BE -> EQ
```

`prev_close(2015-02-04) = 232.95` — the **BE** close of 2015-02-03. The check's
`LAG(...) OVER (PARTITION BY symbol, series)` cannot see it, because:

1. **It crosses the entity seam** (the recycled-ticker defect the implementer found), and
2. **it crosses a series migration** — the exchange's `prev_close` spans `BE → EQ`, but a
   series-partitioned `LAG` does not. It reaches back to the last **EQ** print, which here is
   4.5 years and one company away.

**The production view is expected to be correct here — stated as a prediction, not a verified fact.**
Its `prev_close` uses `LAG(cum_price) OVER (PARTITION BY entity, series ...)` with a `COALESCE`
fallback; for DTIL's first EQ row the `LAG` is NULL, so the fallback applies and it should return the
correct **232.95**. I hand-traced this rather than executing it: the Prompt 3 view is not applied to
the real store, so I cannot run it read-only. **The implementer must confirm it** when re-running the
corrected invariant — which is exactly what the amended P3 (0 violations) tests. If it does not come
back 0, the view *is* implicated and this finding reopens.

**Fix the test, not the view.** Any symbol that migrates EQ ↔ BE will trip this check; DTIL is simply
where the stale print happened to be a different company. This is lighter than the STOP report implies.

---

## What I verified independently

All figures reproduced by the reviewer from **read-only** probes against
`data/market_data/equity_bhavcopy.duckdb` and the raw CF-CA CSV. No repo file was modified by this
review. The implementer's P1, P2, P5 and P7 results were re-derived and **hold**; P4 as written
**passed** (`adj_prev_close == adj_close(t−1)`) — the +40.2% is a *different* metric the prompt never
asserted, which is why the STOP fired on an untested quantity.

**Correction to my own first hypothesis, recorded for the same reason Review 4 recorded its
withdrawal:** I initially concluded "4 bad CAs, 59 genuine" from three spot-checks. That was wrong —
`min(dev_open, dev_close)` means a non-flagged name proves nothing about its open, and the full sweep
found the `f ≥ 0.75` blind spot. Stated so the count is not cited downstream from the wrong draft.

## Required before the substrate can be certified

**Prompt 3 — APPROVED, apply to the real store**, with one change:

1. **Fix the P3 invariant**, do not touch the view. Partition the `LAG` by **entity** (not symbol) and
   over the **EQ+BE union** (not per-series), matching the exchange's own `prev_close` semantics.
   Expected result: **0** violations.

**Prompt 4 — CA register evidence audit** (issued separately; must run **after** Prompt 3):

2. **Re-key** `(DVL, 2021-08-05, BONUS, 0.6667)` → `DTIL`. Evidence: BSE 538902 + price panel.
3. **Tighten the evidence screen** so a no-reprice is detectable at any factor — test `implied_open`
   against **1.0** (did the CA happen?) as well as against `f` (is the ratio right?). The current
   relative tolerance cannot do this for `f ≥ 0.75`.
4. **Add a re-key search:** when a factor fails the screen, look for a symbol that *did* reprice by
   that factor on that date. DVL → DTIL would have been caught automatically. This is the general
   mechanism; the Dhunseri case is one instance of it.
5. **Adjudicate OMAXE 2013-11-11** — the one suspect CA inside a live membership window.

## Provenance

Reviewer probes, read-only, at working-tree state (Prompt 3 uncommitted, real store untouched).
The NSE mis-key is confirmed against three independent sources: the raw CF-CA CSV (says DVL), the BSE
corporate-actions register (says DTIL, scrip 538902), and the price panel (says DTIL). Two of three
agree, and the price is dispositive.
