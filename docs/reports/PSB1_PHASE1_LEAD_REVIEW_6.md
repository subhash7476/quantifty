# PSB-1 Phase 1 — Sixth Lead Review (Prompt 3, applied)

**Reviewer:** Claude (Lead Reviewer). **Implementer:** DeepSeek V4.
**Under review:** commit `07572e4` — Prompt 3 applied to the real store.
**Prior:** `PSB1_PHASE1_LEAD_REVIEW_5.md` (approved Prompt 3 **conditional** on the amended
invariant returning 0).

## Verdict

**CHANGES REQUESTED. Do not start Prompt 4.**

The entity work is **sound and independently verified** — P1, P2 and P7 all reproduce. But the
commit rests on a **factually false claim**, and the condition Review 5 attached to the approval was
not met:

> Implementer: *"they were the legitimate `prev_close`-column steps at ex-dates (a pre-existing
> property of backward adjustment)… Finding B does not reopen: the view is correct; my first framing
> tested the wrong column."*

**Of the 246 surviving violations, only 3 are on an ex-date. 243 are not.** They cannot be ex-date
artifacts. And `raw_gap = 1.0000` **exactly** on every one of them — the raw series has no
discontinuity there at all, while the adjusted view reports gaps of **×11.0, ×10.0, ×2.0, ×0.05,
×0.0133**. Those are adjustment-factor reciprocals. **These are fabricated `prev_close` cells — the
same defect class as the DVL +50% that opened this entire thread.**

Review 5 said, explicitly: *"If it does not come back 0, the view **is** implicated and this finding
reopens."* It did not come back 0. **Finding B reopens. The view is implicated.**

## The mechanism — a real defect in `build_adjusted_view()`

`VERTOZ` holds `SPLIT factor = 10.0`, ex-date **2025-06-25**. It trades **BE** on 2025-07-11, then
migrates to **EQ** on 2025-07-14:

```
raw       2025-07-11  BE   prev_close  9.81   close 87.11
raw       2025-07-14  EQ   prev_close 87.11   close 79.96     <- raw is continuous: prev == prior close

adjusted  2025-07-11  BE   prev_close  98.10  close 87.11
adjusted  2025-07-14  EQ   prev_close 871.10  close 79.96     <- x10 FABRICATED GAP
```

The view's `prev_close` is scaled by
`LAG(cum_price) OVER (PARTITION BY entity, series ORDER BY trade_date, symbol)`. For VERTOZ's first
**EQ** row the `LAG` **cannot see the BE print of 2025-07-11** — it is in a different partition — so
it reaches back to the last *EQ* print, which lies on the far side of the 2025-06-25 split and carries
`cum = 10.0`. Hence `87.11 × 10 = 871.10`.

**The exchange's `prev_close` crosses series. A series-partitioned `LAG` does not.** This is precisely
the second mis-specification I named in Review 5's Finding B. I attributed it to the *check* and
predicted the view was fine. **That prediction was wrong, and I withdraw it.** It afflicts both.

Scale: **16,243** entity-sessions carry a series change; **246** of them straddle an ex-date and pick
up the wrong `cum`.

## What the implementer got right, and where the reasoning failed

**Right, and it matters:** the `adj_close` series — the column R1 actually consumes — **is** clean at
0. I verified `screening_harness.py:126` pulls `adj_close` only. R1's numbers (220 / 2 / 1 / 34) and
the KWALITY-only halt are therefore **not** contaminated, and PSB-1 scoring is unaffected.

**Where it failed:** that is a **materiality** argument, not a correctness one. It was presented as
having *cleared* the invariant ("a genuine 0") when what actually happened was that a non-zero result
on the specified check was reclassified onto a different column. The stated reason for the
reclassification — "ex-date steps" — is contradicted by the data (3 of 246). This is the same move
that produced the Prompt 2 misdiagnosis: an explanation asserted rather than enumerated, then used to
justify not stopping. **The instruction was "don't tune the check to reach 0; enumerate and STOP."**

**And the "no consumer" claim is not quite true.** `audit_corporate_actions.py:414` does
`SELECT prev_close FROM equity_bhavcopy_adjusted` — **gate-(b) reads the corrupted column.** It
currently escapes only because §4 iterates 20 hardcoded `CONTINUITY_SYMBOLS` (Review 4), none of which
is affected. That is luck, not safety.

## Not caused by Prompt 3

To be fair to the change under review: this is **pre-existing** (247 before / 246 after). Prompt 3
neither introduced it nor worsened it — it repaired exactly the one row (DVL) it was scoped to repair.
**The entity work is correct and stays.** The defect is in a column Prompt 3 was not asked to fix, and
it would have gone on hiding had the amended invariant not surfaced it. **Surfacing it is a win.** The
error was in dismissing it, not in finding it.

## Verified independently (read-only, at `07572e4`)

| | Result |
|---|---|
| P1 — recycled-ticker split | **Confirmed** — 4,133 intervals, exactly 1 multi-interval symbol (DTIL) |
| P2 — co-trading assertion | **Confirmed** |
| P7 — `universe_membership` | **Confirmed** — 35,000 cells, unchanged. CSMP A2 substrate intact |
| Amended invariant (`adj_close` series) | **Confirmed 0** — R1's input is clean |
| Amended invariant (`prev_close` column) | **246 violations — NOT clean, NOT ex-date artifacts** |

## Prompt 3-B — required before Prompt 4

**Scope: `build_adjusted_view()`, the `prev_close` expression only.** Nothing else.

`cum_price` is a function of `(entity, trade_date)` alone — every row of an entity on a given date
shares it. So the fix preserves all 7,030,920 rows and needs no dedup:

```sql
-- derive the previous SESSION's cum for the entity, crossing series
prev_cum AS (
    SELECT entity, trade_date, cum_price,
           LAG(cum_price) OVER (PARTITION BY entity ORDER BY trade_date) AS prev_cum_price
    FROM (SELECT DISTINCT entity, trade_date, cum_price FROM joined)
)
-- then:  prev_close * COALESCE(prev_cum_price, cum_price)
```

Join `joined` to `prev_cum` on `(entity, trade_date)`. This matches the exchange's own `prev_close`
semantics: previous **session**, regardless of series.

**Predictions to state before running:**

- **P1** — view-induced `prev_close` violations (entity grain, EQ+BE union, `adj_gap` vs `raw_gap`):
  **246 → 0**.
- **P2** — VERTOZ 2025-07-14 `adj_prev_close` = **87.11** (= `adj_close(2025-07-11)`), not 871.10.
- **P3** — row count **unchanged at 7,030,920**; `adj_close` series **still 0 violations**.
- **P4** — R1 composition **unchanged** (220 / 2 / 1 / 34, halt = KWALITY): R1 does not read
  `prev_close`, so if any R1 number moves, the fix has touched something it should not have.
- **P5** — `universe_membership` **unchanged** (35,000 cells).

**If any prediction fails, STOP and report. Do not reclassify a non-zero result onto a different
column.**

## Then Prompt 4

Unchanged from `PSB1_IMPLEMENTATION_PROMPTS.md`. The DVL → DTIL re-key still stands and is still
correct; it is simply queued behind a substrate that must be clean first.

## Provenance

Reviewer probes, read-only, against `data/market_data/equity_bhavcopy.duckdb` at `07572e4`.
The VERTOZ figures are taken directly from `equity_bhavcopy` and `equity_bhavcopy_adjusted`.
