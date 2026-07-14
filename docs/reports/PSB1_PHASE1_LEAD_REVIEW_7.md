# PSB-1 Phase 1 — Lead Review 7

**Subject:** Prompt 3-B — `prev_close` series-crossing fix (previous-session `cum`)
**Commit reviewed:** `af55c64` (branch `psb1/phase-0`)
**Date:** 2026-07-14
**Verdict:** **PASS.** Prompt 4 is **AUTHORIZED**.
**New item opened:** **F-7 (LITL)** — pre-existing, LOW severity, does not block Prompt 4.

---

## 1. Verdict

Prompt 3-B is correct, correctly scoped, and correctly applied. The 246 fabricated
`prev_close` cells are gone; nothing else moved. The substrate is fit for Prompt 4.

The review did **not** reuse the implementer's checks — reusing
`repair_prev_close.prev_close_col_violations()` would only re-run the predicate the fix
was written to satisfy. Every finding below is independently re-derived.

---

## 2. What was actually verified (independent)

| # | Check | Result |
|---|---|---|
| V0 | `equity_bhavcopy_adjusted` is a **VIEW**, not a materialised table | ✅ `VIEW` |
| V1 | Row conservation across the rewrite | ✅ `7,030,920 → 7,030,920` (delta 0) |
| V1 | `symbol_entity_intervals.entity` NULLs (would silently drop rows) | ✅ 0 |
| V1 | Fan-out: `(entity, trade_date)` keys with >1 distinct `cum_price` | ✅ 0 |
| V2 | Gap invariant, re-derived by **previous session** (EQ-preferred collapse) | ✅ 0 violations |
| V3 | Blind-spot probe: entity-first-session fallback | ⚠️ **1 entity** — see §4 |
| V4 | VERTOZ `2025-07-14` `prev_close` | ✅ `87.11` = `adj_close` 07-11 |

### 2.1 The rewrite introduced two structural hazards. Both are closed.

The fix replaced a window expression over `joined` with an **INNER JOIN** to a new
`prev_cum` CTE. That swap creates two failure modes the old form did not have:

1. **Silent row-drop.** `JOIN prev_cum p ON p.entity = j.entity` drops any row where
   `entity IS NULL` (`NULL = NULL` is false). Closed: `joined` reaches
   `symbol_entity_intervals` through an *inner* join, so `entity` is never NULL, and the
   interval table itself carries 0 NULL entities.
2. **Fan-out.** `SELECT DISTINCT entity, trade_date, cum_price` duplicates a print if any
   `(entity, trade_date)` carries more than one `cum_price`. Closed structurally —
   `events` is `GROUP BY entity, ex_date`, so the `LEFT JOIN cum` matches at most one row
   and `cum_price` is a true function of `(entity, trade_date)` — and empirically: 0 such keys.

Row conservation at exactly 7,030,920 is the single number that would have caught either.
It holds.

**Determinism note (in the fix's favour):** the old `LAG` ordered by `trade_date, symbol`;
the new one orders by `trade_date` alone. That is *not* a new tie — the DISTINCT subquery
has exactly one row per `(entity, trade_date)`, so the ordering is total within the
partition. No nondeterminism was introduced.

### 2.2 An honest word about the invariant check

Both the implementer's P1 and my V2 are **satisfied by construction**, not by luck. Once
`adj_prev_close(t) = raw_prev_close(t) × cum(t-1)` and
`adj_close(t-1) = raw_close(t-1) × cum(t-1)`, the factor cancels and `adj_gap ≡ raw_gap`
identically. A passing gap check therefore cannot *fail* — it is a tautology given the fix.

That is the strongest possible outcome, not a weakness: the fix does not merely survive a
test, it makes the defect unrepresentable. But it means the gap check carries no evidential
weight on its own. The load-bearing evidence is elsewhere, and it is what I leaned on:
row conservation, key uniqueness, VIEW-derivation, and the concrete VERTOZ value —
a real BE→EQ series migration whose `prev_close` now reads 87.11, exactly the prior
session's adjusted close, where it previously read 871.10 (a factor-reciprocal fabrication).

---

## 3. Report-accuracy notes (non-blocking)

1. **Undisclosed artifact.** The commit adds `scripts/psb1/repair_prev_close.py` (144 lines),
   which the report never mentions while describing the scope as "`build_adjusted_view()`,
   `prev_close` expression only." On inspection it is a validate-on-copy-then-apply harness
   that re-executes the *fixed pipeline function* — legitimate, and **not** an ad-hoc data
   patch (the target is a VIEW; "apply" is a DDL replace). No harm done, but a new executable
   file in `scripts/` is a scope disclosure the report owed the reviewer.
2. **Wrong SHA on record.** The report cites commit `4ecf…`; HEAD is **`af55c64`**. Correct
   the record.

---

## 4. New finding **F-7** — `LITL` 2010-01-04, fabricated `prev_close` (PRE-EXISTING, LOW)

**The implementer's check cannot see this row.** `prev_close_col_violations()` filters on
`WHERE a.alag > 0` — it requires a previous row. An entity's **first** session has none, so
every first-session row is excluded from the predicate by construction. That is where the
last fabrication is hiding.

`build_adjusted_view()` line 582:

```sql
j.prev_close * COALESCE(p.prev_cum_price, j.cum_price) AS prev_close
```

On an entity's first in-panel session `prev_cum_price` is NULL, and the fallback uses the
**same-day** `cum_price` instead of the previous session's. That is wrong precisely when the
first session is itself an ex-date. Across 3,621 entities, exactly **one** qualifies:

| entity | first in-panel session | event | factor |
|---|---|---|---|
| `LITL` | 2010-01-04 (= panel start) | `SPLIT` | 0.1 (10:1) |

The resulting cell in the adjusted view:

```
2010-01-04  LITL  EQ   adj_prev_close = 576.70   adj_close = 58.10
```

`cum_price(t)` excludes an ex-date falling *on* `t` (the join takes `MIN(ex_date > trade_date)`),
so `cum(2010-01-04) = 1.0` and `prev_close` is left entirely unadjusted — a **9.93× ratio**,
i.e. a **fabricated −89.9% overnight return** for any consumer computing `close/prev_close − 1`.
The correct value is `576.70 × 0.1 = 57.67`, which sits sensibly beside the 58.10 close.

### 4.1 Provenance: pre-existing, **not** a 3-B regression

Verified, not assumed. The parent commit's (`07572e4`) `build_adjusted_view` was rebuilt on
a copy of the store and the same cell read back:

| view | LITL 2010-01-04 `adj_prev_close` / `adj_close` |
|---|---|
| parent `07572e4` (pre-3-B) | `576.70 / 58.10` |
| current `af55c64` (post-3-B) | `576.70 / 58.10` |

**Identical.** The old `COALESCE(LAG(…) OVER (PARTITION BY entity, series …), cum_price)`
falls back on a first-of-partition row exactly as the new one does. Prompt 3-B neither
introduced this defect nor was chartered to fix it. **3-B's pass is clean.**

### 4.2 Severity: LOW — and why it does not block Prompt 4

- **R1 does not read the `prev_close` column.** It derives returns from
  `LAG(close)` (`audit_corporate_actions.py:249`). This is the structural reason behind the
  implementer's P4 observation that R1 was unchanged while 246 `prev_close` cells moved.
- The only consumer of the adjusted `prev_close` **column** is gate-(b) §4 continuity
  (`audit_corporate_actions.py:414`), over `CONTINUITY_SYMBOLS`.
- It is the panel's **first day** (window opens 2010-01-04), so no in-panel previous session
  exists for any consumer to disagree with.
- `LITL` *is* present in `universe_eligibility` (1 row), so the cell is not strictly inert —
  which is why this is logged as an open item rather than closed as harmless.
- Prompt 4 targets `adj_close` (DVL/DTIL mis-key). Disjoint from `prev_close`. No interaction.

### 4.3 Recommended remedy (Prompt 3-C, or a rider on Prompt 4)

Change **only** the COALESCE fallback; leave the session `LAG` intact:

```sql
-- fallback for an entity's first in-panel session: cum(t-1) = cum(t) x factor(on t)
j.prev_close * COALESCE(p.prev_cum_price, j.cum_price * COALESCE(f.price_factor, 1.0))
```

joining `events` on `(entity, ex_date = trade_date)`.

**Do not** replace the `LAG` with the closed form `cum(t) × factor(t)` globally, tempting as
it is. The two are equivalent only when every ex-date falls on a trading day: the session
`LAG` yields `∏ factors of ex_dates > t-1`, which includes an ex-date landing on a holiday
or weekend, whereas the closed form yields `∏ factors of ex_dates ≥ t`, which drops it. The
`LAG` is the correct general form. The closed form is correct *only* for the first-session
fallback, where there is no `t-1` in panel and the ex-date in question is on `t` by
construction.

Deferring F-7 with a documented note is also defensible at this severity. It is the Lead's
call; it is not a gate.

---

## 5. Disposition

- **Prompt 3-B: PASS.** 246 → 0, rows conserved, no fan-out, no row-drop, no
  nondeterminism, R1/membership untouched, VERTOZ correct to the paisa.
- **Prompt 4: AUTHORIZED** (DVL/DTIL `adj_close` mis-key).
- **F-7 (LITL) opened:** pre-existing, LOW, one cell, remedy specified in §4.3.
- **Record corrections:** commit is `af55c64`, not `4ecf…`; `scripts/psb1/repair_prev_close.py`
  is part of the 3-B change set.

### Scope limit of this review (stated plainly)

The "246 before" figure was **not** independently re-derived — the store already carries the
fix, and the count is the implementer's. What I verified is the state that matters: the
post-fix substrate has **zero** gap-invariant violations under a check I wrote myself, with
rows conserved, plus one pre-existing first-session fabrication (F-7) that their check is
structurally incapable of seeing.
