# PSB-1 Phase 1 — Fourth Lead Review (Prompt 2)

**Reviewer:** Claude (Lead Reviewer). **Implementer:** DeepSeek V4.
**Under review:** commit `5f05b0d` (Prompt 2; entity-grain adjustment repair in `build_adjusted_view()`).
**Prior reviews:** `PSB1_PHASE1_LEAD_REVIEW.md`, `_2.md`, `_3.md`.
**Protocol:** `PSB1_PROTOCOL.md` (FROZEN Rev 2).

## Verdict

**CHANGES REQUESTED.** Do not accept `5f05b0d` as the certified substrate.

The approach is right and the headline result is real: entity-grain cumulative factors are the
correct fix for the rename discontinuity, and the 59 fabricated rename returns are genuinely
gone. Five of DeepSeek's six preconditions I re-verified independently and they hold.

But the change **rests on an assumption it never tested — that all symbols sharing an `entity`
are temporally disjoint — and that assumption is false.** The consequence is a *newly fabricated
overnight return*, which is precisely the class of defect PSB-1 exists to eliminate:

> **`equity_bhavcopy_adjusted` now reports `DVL` on 2021-08-05 with `adj_prev_close = 300.75`
> against `adj_close(2021-08-04) = 200.50` — a +50% phantom gap that did not exist before this
> commit.** It is the only symbol-grain continuity violation introduced across all 7,030,920 rows.
> The +50% is exactly **1.5× = 1 / 0.6667**, the reciprocal of the bonus factor: `prev_close` kept
> `cum = 1.0` where it should have carried `0.6667` (300.75 × 0.6667 = 200.50). The arithmetic ties
> the fabrication directly to the mechanism.

The investigation also found a **narrow, genuine gap in the NSE CF-CA feed** that Prompt 2
accidentally papered over (Finding 3) — though **not** the systematic defect I first claimed. See
the correction immediately below.

## Correction to this review (post-issue amendment)

**My first draft of Finding 3 was wrong and I withdraw it.** I wrote that "the BSE ingest path
types every corporate action as `DIVIDEND`" and called it a defect leaving "**251 real bonus/split
events across 215 trading symbols** with no adjustment factor — each a fabricated return sitting
in the substrate." I asserted that from a `COUNT(*)` without applying gate-(b)'s own evidence
screen. That is the same failure mode I corrected in my second review, and I repeated it.

`BSE = DIVIDEND only` is a **documented, deliberate design decision**
(`ingest_corporate_actions.py` lines 3-6: BSE "keys bonuses on the record date, which is not the
ex-date, and it mislabels bonus debentures as equity bonuses"). Running the module's own screen
(`EVIDENCE_TOLERANCE = 0.25`, `EVIDENCE_MAX_GAP_DAYS = 5`) across all 251 candidates **largely
vindicates that decision**:

| Outcome of the evidence screen | Count |
|---|---:|
| **CONFIRMED** — price actually repriced by the stated ratio (real + unadjusted) | **2** — and only 1 survives scrutiny |
| **CONTRADICTED** — price did *not* reprice; BSE date/ratio unreliable | 4 |
| **No NSE price at the BSE ex-date** — BSE-only listing or symbol collision | 202 |
| **Unparseable** — almost all `"Split of Mutual Fund Units"` (ETF, outside equity scope) | 43 |

`GUJNRECOKE` (2010-05-06, `BONUS 1:10`) passes only because a 0.25 tolerance is far too loose for
a small ratio: expected 0.9091, observed **1.0038** — the price did not move at all. At any sane
tolerance it is CONTRADICTED. **The real confirmed population is one row: `DTIL`.**

The true finding is therefore much narrower, and is restated as Finding 3 below.

## What I verified and confirmed (credit where due)

Reproduced from my own read-only probes against `data/market_data/equity_bhavcopy.duckdb`,
not from the implementer's report.

| Claim | How I checked | Result |
|---|---|---|
| One edit, scoped to `build_adjusted_view()`; `audit_corporate_actions.py` untouched | `git show 5f05b0d` | **Confirmed** |
| No row fan-out from the new `LEFT JOIN universe_eligibility` | `COUNT(*)` vs `COUNT(DISTINCT symbol)` = 4132/4132 | **Confirmed** — unique by symbol |
| View preserves the panel | raw 7,030,920 vs adjusted 7,030,920 | **Confirmed** — delta 0 |
| The new `INNER JOIN` in `events` drops no factors | `adjustment_factors` symbols absent from `equity_bhavcopy` | **Confirmed** — 0 |
| `COALESCE` fallback (`entity := symbol`) never exercised | bhavcopy symbols with no `universe_eligibility` row | **Confirmed** — 0 |
| Rename discontinuities repaired | entity-grain continuity, raw vs adjusted | **Confirmed** — 0 view-induced |

The mechanism is sound *for genuine rename chains*. My objection is not to entity-grain
adjustment. It is to the unguarded assumption underneath it.

## Finding 1 — CRITICAL: `entity` is not temporally disjoint; the view fabricates a return

### Root cause

`symbol_changes` holds a real chain, all rows labelled *Dhunseri Ventures Limited*:

```
DTIL -> DPTL  (2010-07-26)
DPTL -> DPL   (2014-11-12)
DPL  -> DVL   (2019-01-02)
```

`build_universe.py` resolves this with a union-find (`uf.find`, line 274) that **has no time
dimension**. It therefore collapses all four symbols into a single entity, `DPL`:

```
DPL -> DPL     DPTL -> DPL     DTIL -> DPL     DVL -> DPL
```

But **`DTIL` never stopped trading.** It prints continuously from 2010-01-04 to 2026-07-09
(2,980 rows), overlapping `DPL` (2014-11-12 → 2019-01-01) and `DVL` (2019-01-02 → 2026-07-09)
for sixteen years. NSE **recycled the ticker**: the 2010 rename vacated `DTIL`, and the demerged
tea business later relisted under it. The `corporate_actions` rows prove they are different
companies — **`DTIL` is BSE scrip `538902` ("Dhunseri Tea & Industries Ltd")** while
**`DVL` is BSE scrip `523736` ("Dhunseri Ventures Ltd")**.

A symbol is therefore **not** a single entity for all time. `DTIL` is two entities, sliced at
2010-07-26. The entity map cannot express this, and Prompt 2 has now imported that limitation
into the price substrate.

**2,695** `(entity, series, trade_date)` groups draw from more than one symbol. All belong to
this one entity — **1 overlapping entity repo-wide**, so today's blast radius is 4 symbols.

### Corruption A — a corporate action applied across two different companies

`DVL`'s 2021-08-05 `BONUS` (factor 0.6667) is the entity's only adjustment factor. At entity
grain it is now compounded into `DTIL`'s cumulative factor, rescaling **all of `DTIL`'s
pre-2021-08-05 history by ×0.6667** — a different, concurrently-listed company. Under the old
symbol-grain code `DTIL` had `cum = 1.0`.

**This happens to produce the numerically correct `DTIL` series** — because `DTIL` *itself* had
an identical 1:2 bonus on the identical ex-date, and its factor is missing (Finding 3). Its raw
close falls 521.15 → 346.65 on 2021-08-05, which is ×0.665: an ex-bonus drop, not a crash.

**That is luck, not correctness.** The mechanism applied one company's corporate action to
another and landed on the right answer only because the two events coincided in both ratio and
date. There is no guard. A co-trading pair with divergent CAs would be silently corrupted, and
the entity map will keep minting these unions every time NSE recycles a ticker.

### Corruption B — the fabricated `prev_close` (demonstrated)

```sql
prev_close * COALESCE(
    LAG(cum_price) OVER (PARTITION BY entity, series ORDER BY trade_date, symbol),
    cum_price) AS prev_close
```

For `DVL`'s 2021-08-05 row, the preceding row **in the entity partition** is not `DVL`'s
2021-08-04 row — it is **`DTIL`'s 2021-08-05 row** (same date; `'DTIL' < 'DVL'` under the
`ORDER BY trade_date, symbol` tiebreak). It carries `cum_price = 1.0` (post-ex), not `DVL`'s
pre-ex `0.6667`. The result:

| trade_date | symbol | `adj_prev_close` | `adj_close(t-1)` |
|---|---|---:|---:|
| 2021-08-04 | DVL | 205.90 | 205.90 |
| **2021-08-05** | **DVL** | **300.75** | **200.50** |
| 2021-08-06 | DVL | 281.05 | 281.05 |

A **+50% fabricated overnight gap** — precisely `1 / 0.6667`, the reciprocal of the bonus factor
(300.75 × 0.6667 = 200.50). Symbol-grain view-induced continuity violations across the whole
substrate: **exactly 1** — this row. It did not exist before `5f05b0d`.

Reaching across to a different symbol's row is *the point* at a genuine rename (it is how
`prev_close` survives the handoff). It is simply wrong when two symbols co-trade.

## Finding 2 — HIGH: every guard in the harness is structurally blind to this

This is a **coverage gap**, not evasion. But all four guards miss it, and they miss it for
reasons worth stating precisely, because the same blind spots will pass Prompt 3 too.

**1. The invariant runner never measures `prev_close`.** `repair_adjusted_view.py:33-82`
(`invariant_violations`) compares the *adjusted* close-to-close return against the *raw*
close-to-close return divided by the spanning factor. The `prev_close` column **does not appear
anywhere in the query.** The 322 → 307 numbers therefore cannot detect a `prev_close` defect of
any size — this is not a matter of grain or threshold; the column under test is absent. The
fabricated `DVL` row is not hiding inside the 307; it is in a population the runner never looks at.

**2. That same runner collapses the overlap it would need to see.** It dedups to one print per
`(entity, trade_date)` — `ROW_NUMBER() … ORDER BY turnover DESC, symbol`, `rn = 1` (line 45). For
entity `DPL` that keeps whichever of `DTIL`/`DVL` traded heavier that day, splicing two different
companies into a single "entity" close series. The co-trading condition is erased before the
invariant is evaluated.

**3. The STOP assertion passes vacuously.** `assert_no_double_apply` (line 85) checks that no
`(entity, ex_date)` draws factors from **more than one symbol**. `DTIL` has **zero** rows in
`adjustment_factors` (Finding 3), so the pair contributes one symbol and the assertion is
satisfied. The hazard is not "two symbols contribute a factor at the same ex-date" — it is **"two
symbols of one entity trade at the same time."** That precondition is never asserted.

**4. `audit_corporate_actions.py` §4** (the ex-date continuity check — the one guard that *does*
test `adj_prev_close(t)` vs `adj_close(t-1)`) iterates `CONTINUITY_SYMBOLS`: 20 hardcoded
mega-caps (line 58). Neither `DVL` nor `DTIL` is in it.

**5. Prediction P2** ("no new move appears at a rename date") is scoped to *rename dates*. The
fabrication sits at a **bonus ex-date**. Out of scope by construction.

The defect is visible only under a symbol-grain `prev_close` check — which nothing in the harness
performs. My own measurement: **0** view-induced violations at entity grain, **1** at symbol grain
(`DVL`, 2021-08-05). Separately, **the 307 residue was dismissed, not enumerated** — "sub-threshold
and/or at documented ex-dates" is an assertion, and that invariant is exact, not thresholded.

## Finding 3 — MEDIUM (gate-(b)): the NSE feed has a real coverage gap, and nothing detects it

Not a classification bug (see the correction above). The defect is narrower and different:

**The NSE CF-CA feed is the sole source for `BONUS`/`SPLIT`, and it silently missed a real
event.** `DTIL`'s 1:2 bonus of 2021-08-05 is **absent from
`CF-CA-equities-01-01-2021-to-31-12-2021.csv` entirely** — it is not in the file, and it is not in
`ca_parse_rejects` (which holds only 19 rows: 13 `non_equity_bonus`, 6
`capital_reduction_ambiguous`). The parser did not reject it; the feed never carried it. `DTIL`
therefore has **0** rows in `adjustment_factors`, while the price panel shows an unmistakable
ex-bonus reprice at that date: observed **0.6652** against an expected **0.6667**.

The evidence for the event exists in the store — in the discarded BSE record, whose
`"Ex_date": "05 Aug 2021"` is *correct* and corroborated by the price. It was thrown away because
the BSE path is dividend-only.

So the design decision is right in general (BSE bonus/split records are mostly unreliable) but it
is applied as a blanket discard, and **there is no cross-check anywhere that would notice the NSE
feed dropping an event.** A single-source feed with no corroboration screen is the actual defect.

Consequences:

1. **Prompt 2 masked this instance.** `DTIL` looks correctly adjusted only because a *different
   company's* factor stood in for its missing one. Fix the entity bug without fixing this and
   `DTIL` silently becomes unadjusted again — a real +50% fabricated return, this time in the
   `close` series.
2. **R1's `genuine` bucket is very nearly sound.** My earlier claim that it was invalidated by 251
   missing events was wrong. The confirmed miss is **one** row. The 34 large-genuine rows stand,
   pending the `DTIL` disposition.

The remedy is **not** "trust BSE bonuses." It is a **corroboration screen**: for any BSE
bonus/split-shaped record on an NSE-traded symbol that has no NSE factor, run the existing
evidence screen against the price panel; anything CONFIRMED is a genuine NSE-feed gap and must be
either admitted as a factor *with its price evidence recorded*, or registered as a documented
exception. Today that screen yields exactly one row.

**Related hazard, flagged not sized:** BSE records are matched to NSE symbols by `short_name`, and
the names collide across exchanges — BSE `DPL` is *Dipna Pharmachem* (scrip 543594), NSE `DPL` is
*Dhunseri Petrochem*. The 202 "no NSE price at the BSE ex-date" rows are the visible symptom. Since
BSE `DIVIDEND` rows **do** feed `SPECIAL_DIVIDEND` factors, a mis-attributed dividend could place a
factor on the wrong company. This needs an ISIN/scripcode-validated join, not a name match. I have
not sized it; it belongs to gate-(b).

## Required before the substrate can be certified

**Prompt 3 (this repair):**

1. **Time-aware entity resolution.** Entity must be a function of `(symbol, trade_date)`, not
   `(symbol)`. A rename edge `old → new` at date `D` means `old`'s prints **before** `D` belong
   to the chain; prints of `old` **on/after** `D` are a recycled ticker and a different entity.
   *Do not* "fall back to symbol grain for overlapping members" — that under-adjusts: `DTIL`'s
   pre-2010-07-26 rows genuinely belong to the Petrochem chain and genuinely need `DVL`'s 2021
   bonus.
2. **Replace the vacuous STOP assertion.** `assert_no_double_apply` tests the wrong precondition.
   The one that matters: **no entity may contain two symbols with overlapping `[min, max]`
   trade-date spans.** That is what Prompt 2 silently assumed. With it, the `LAG` tiebreak can
   never reach a same-date row of a different symbol.
3. **Add a `prev_close` invariant and run it at symbol grain.** The current runner does not test
   `prev_close` at all. Required check: `adj_prev_close(t) == adj_close(t-1)` with
   `LAG(...) OVER (PARTITION BY symbol, series ORDER BY trade_date)`, across the **whole panel** —
   not a 20-symbol sample. **Enumerate** every surviving violation. No dismissals, and no dedup
   that collapses co-trading symbols before the check runs.

**Scoping decision for the operator (§4.1):** the union-find entity map lives in
`build_universe.py`, which is **frozen**. The correct fix belongs there, not in a workaround
inside `ingest_corporate_actions.py`. This needs an authorization call before Prompt 3 is
written. Reassurance for that decision: **time-aware resolution changes no `DTIL` close
numbers** — both segments still land at ×0.6667 pre-ex. It removes the `DVL` `prev_close`
fabrication and unmasks the CA bug. It is not a re-pricing.

**Separate gate-(b) prompt (Finding 3) — and it must run SECOND, after the entity repair.** Add a
**corroboration screen** over the discarded BSE bonus/split records: evidence-screen each against
the price panel and admit or document the CONFIRMED ones. Do **not** re-type the BSE feed
wholesale; the dividend-only decision is sound. Today the screen yields one row (`DTIL`).

**The order is forced, and it is the opposite of what I first recommended.** If the BSE screen
runs first, `DTIL` gains its own `BONUS` factor *while the bad `DPL` union still exists*. The
`events` CTE groups by `(entity, ex_date)` and compounds with `EXP(SUM(LN(factor)))`, so `DTIL`'s
0.6667 and `DVL`'s 0.6667 would multiply to **0.4444** — a double application — and
`assert_no_double_apply` would then see two symbols contributing a factor at one `(entity, ex_date)`
and **halt the build**. The BSE screen cannot land until the entity is split.

Between the two prompts `DTIL` is genuinely unadjusted (a real +50% gap in `close`). That transient
is acceptable on a dev branch and is in fact honest: it exposes the true feed gap instead of
hiding it behind another company's factor. It must not be certified in that state.

## What is *not* in dispute

- The 59 rename discontinuities are genuinely fixed. Entity-grain `cum` is the right idea.
- No fan-out, no dropped factors, no row loss, fallback never exercised — all verified.
- The **220-move count is not affected by the fabricated `prev_close`** — but not for the reason I
  first gave. (I wrote that R1 "reads raw prices," citing `audit_corporate_actions.py:249`. That is
  gate-(b)'s audit, not R1, and it cannot be right: Prompt 2 changed *only* the adjusted view and
  R1 moved 235 -> 220.) The correct statement, from `screening_harness.py:103-131`: **R1 loads
  `adj_close` from `equity_bhavcopy_adjusted`** (entity-deduped `rn=1` by turnover, scoped to
  universe-member entities) and derives returns from **consecutive adjusted closes**. It never
  selects the `prev_close` column. That is what makes the `DVL` fabrication invisible to the move
  screen — while leaving it live for any other consumer that does read `prev_close`.
- Nor, contrary to my withdrawn claim, is the 220 count materially affected by Finding 3 — that is
  one row, not 251.
- 30/30 tests pass. The tests do not cover this; that is the gap, not a failure.

## Provenance

All figures above reproduced by the reviewer from read-only probes against
`data/market_data/equity_bhavcopy.duckdb` at commit `5f05b0d`. No repo file was modified by this
review.
