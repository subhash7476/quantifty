# CSMP Gate (b) — Lead-Reviewer Verdict

**Reviewer:** Claude (Lead Reviewer, per `CSMP_PHASE0_CHARTER.md` role split)
**Implementer:** DeepSeek V4
**Gate:** (b) — Corporate-action adjustment + move-classification audit
**Date:** 2026-07-10
**Deliverables reviewed:**
`scripts/csmp/ingest_corporate_actions.py`, `scripts/csmp/audit_corporate_actions.py`,
`docs/reports/CSMP_GATE_B_CORPORATE_ACTIONS_AUDIT.md`, tables `corporate_actions` /
`adjustment_factors` and view `equity_bhavcopy_adjusted` in `equity_bhavcopy.duckdb`.

---

## Verdict: **NOT PASSED — REJECTED (structural, not residual)**

The audit self-reports NOT PASSED on "14 dev-window unexplained moves." That framing
drastically understates the failure. The 14 are the visible tip; the store itself is wrong:

1. **All 9,004 "SPLIT" events are dividends.** BSE's `CorporateAction/w` `Table` is the
   dividend table; the parser labeled it Split and turned rupee dividend amounts into
   multiplicative price factors (8,840 of the 9,732 factors).
2. **The adjusted view is unusable.** RELIANCE's adjusted close in Jan 2012 is **5,940×
   raw** (₹706.55 → ₹4,196,907). Every symbol with a dividend history is distorted by the
   product of its rupee dividend amounts.
3. **No stock split was ingested at all** — the endpoint has no split table — so every real
   sub-division gap in 16 years of data remains unadjusted in the "genuine" bucket.
4. **Half the move screen is artifact.** 3,314 of 6,486 screened "single-day" moves (51%)
   compare against a previous EQ close more than 7 days old (3,142 > 30 days old), because
   the `LAG` runs over EQ-series rows only and silently spans BE-series migrations and
   suspensions.

The one component that works: the **bonus pipeline** (900 events, `issue B:E` → factor
`E/(E+B)`), which correctly explains all 423 CA-explained moves (all matched factor < 1 with
negative return; only 2 spurious factor > 1 matches existed to contaminate it).

**Quarantine directive (immediate):** `equity_bhavcopy_adjusted` and the SPLIT rows of
`adjustment_factors` must not be used by any downstream work. The gate-(a) raw store is
unaffected and remains sound.

---

## Verification performed by the reviewer (evidence, not assertion)

All numbers below were re-derived read-only from `equity_bhavcopy.duckdb` this session.

| Check | Result |
|-------|--------|
| Raw JSON of newest RELIANCE/TCS/INFY "SPLIT" events | `purpose_name: 'Interim/Final Dividend'`, `Amount: 12.0 / 25.0 / 6.0 / 31.0 / 46.0` — dividends, not splits |
| 200-row sample of SPLIT factors vs actual ex-date price gap | 153 no price gap at all, **0** gaps matching the factor, 5 other (ETF/gap noise) |
| SPLIT rows exactly mirroring a DIVIDEND row (symbol+date+value) | 1,013 (remainder differ only via record-date vs ex-date field) |
| Split-like purpose strings anywhere in the store | 370, all inside DIVIDEND rows — no true split table exists in the source |
| RELIANCE adjusted vs raw, 2026-06-01→04 (before the ₹6 dividend) | adj = 6.0 × raw (7,920 vs 1,320) — a 6× discontinuity **created** where none existed |
| RELIANCE adjusted vs raw, Jan 2012 | adj = **5,940×** raw |
| CA-explained composition | 423 = bonus factor < 1 with ret < 0; factor > 1 matches: 2 |
| Screened moves with stale prev-close | 3,314 / 6,486 > 7 days; 3,142 > 30 days |
| Single-session drops −40%..−85% with ≤ 5-day gap | 880 — mostly real splits/bonuses sitting unadjusted in "genuine" |

---

## The 14 dev-window unexplained moves — all resolved, none a true anomaly

**Group 1 — real ETF unit splits missing from the source (7).** GOLDBEES 2019-12-19,
AXISGOLD 2020-07-23, HDFCMFGETF 2021-02-17, GOLDSHARE 2021-03-25, BSLGOLDETF 2021-11-25,
QGOLDHALF 2021-12-16, SETFGOLD 2022-01-06. Each shows a clean ~1:100 price step with volume
up 2–3 orders of magnitude (e.g. GOLDBEES 3,359.60 → 33.55, volume 4,386 → 1,664,422).
These are genuine gold-ETF unit sub-divisions; they are mutual-fund scheme actions and do
not appear in BSE's equity corporate-action feed. The sealed-window LICMFGOLD and IVZINGOLD
rows are the same family. Note: ETFs should not survive gate (c)'s universe definition
anyway — but gate (b) must still classify them, so the CA source needs an ETF-split patch
list (small, enumerable: ~10 events).

**Group 2 — real special dividend (1).** MAJESCO 2020-12-23: ₹974/share special dividend on
a ~₹985 stock (985.65 → 12.20; 985.65 − 974 = 11.65 ≈ 12.20 ✓). The move is real economics.
Ironically the event **is** in the store — it is the "max split factor 974.0000" in the
audit's §2 table, and the direction check (factor > 1 requires positive return) blocked the
misparsed event from explaining its own move. Requires a charter decision: special dividends
above some threshold (e.g. > 20% of price) either get an adjustment factor or the
symbol-date is excluded; ordinary-dividend non-adjustment stands.

**Group 3 — artifacts of the audit's own screen (6).** Not single-day moves at all; the
prior EQ close is stale because the symbol traded in BE series or was suspended in between:

| Symbol | "Move" date | Prev EQ close used | Actual staleness | Reality on the day |
|--------|------------|--------------------|-----------------|--------------------|
| SBC | 2022-03-29 | 179.35 (2022-01-12) | 76 days | BE 6.35 → EQ 6.05, continuous |
| UVSL | 2020-08-18 | 0.05 (2020-03-12) | 159 days | BE 0.50 → EQ 0.55, continuous |
| LCCINFOTEC | 2021-04-07 | 0.40 (2017-11-21) | 1,233 days | BE 4.75 → EQ 4.55, continuous |
| KOVAI | 2021-08-05 | 139.35 (2010-11-22) | 3,909 days | resumed trading at 1,592.55 |
| RUCHI | 2020-06-16 | 68.35 (2020-03-03) | 105 days | BE 979.75 → EQ 1,028.70, continuous |
| VISESHINFO | 2022-03-29 | 0.05 (2019-08-28) | 944 days | BE 1.10 → EQ 1.05, continuous |

So the honest tally for the 14: **7 unsourced real CAs + 1 unsourced real special dividend +
6 screen artifacts + 0 true data anomalies.** The sealed-window residue decomposes the same
way (gold ETFs + penny relistings). Nothing here impeaches gate (a)'s raw store.

---

## Findings

### F1 — CRITICAL — BSE response tables misidentified; dividends ingested as splits
`parse_bse_to_events()` maps `Table`→Split, `Table1`→Bonus, `Table2`→Dividend. Empirically:
`Table` = dividends keyed by record date (`BCRD_FROM`/`Amount`), `Table1` = bonuses
(`XTYPE: 'Bonus'`, `VALUE: 'issue B:E'`), `Table2` = dividends keyed by ex-date
(`Ex_date`/`Details`). The plain-float fallback in `derive_factor()` then converted every
dividend amount into a price factor (₹12 dividend → factor 12.0). **Impact:** 8,840 bogus
factors; adjusted view distorted by orders of magnitude on virtually every dividend-paying
symbol. **Fix:** map `Table` as DIVIDEND (record-date variant) or drop it in favour of
`Table2`; delete the plain-float branch entirely — a bare number can never define a
split ratio safely.

### F2 — CRITICAL — no split source; real split gaps remain in the data unadjusted
The endpoint carries no sub-division table, so 16 years of real splits (FV 10→1, 10→2, …)
are absent. ~880 tight-gap −40%..−85% single-session drops sit in the "genuine" bucket —
for a cross-sectional momentum program these fake negative returns are signal-destroying.
**Fix:** source splits separately. Candidates, in order of structure: (i) BSE's
corporate-actions listing API used by bseindia.com/corporates/corporates_act.html (accepts
`Purpose` subdivision filters and date ranges), (ii) NSE's CF-CA archive CSV
(nsearchives), (iii) reconstruct from the bhavcopy itself: a symbol-day where
`prev_close/close` clusters at 2, 5, 10, 25 with volume scaling. Whatever the source, the
§3 screen (fixed per F3) is the acceptance test: every real split gap must become
CA-explained.

### F3 — CRITICAL — move screen spans suspension/series gaps; 51% of screened moves are not moves
`LAG(close) OVER (PARTITION BY symbol ORDER BY trade_date)` is computed after filtering to
EQ series and full sessions, so a symbol returning from BE series (trade-to-trade) or a
multi-year suspension is compared against its last EQ close — months or a decade old.
**Impact:** 3,314 of 6,486 screened rows are artifacts; headline counts ("6,032 genuine")
are meaningless; 6 of the 14 gate-failing rows are this bug. **Fix:** include BE rows in
the return computation (or partition-agnostic prev close), and require the lagged
`trade_date` to be the immediately preceding full session (or gap ≤ 5 calendar days);
report symbol-days that fail the gap requirement separately as "resumption/migration"
events, which are not rankable returns.

### F4 — MAJOR — §4 adjusted-continuity check is vacuous; its PASS verified nothing
The loop skips any row whose `trade_date` is an ex-date (`rows[i][0] in ca_events:
continue`) — the only rows where adjustment has any effect. Between ex-dates, adjusted
close and adjusted prev_close are scaled by the same cumulative factor, so mismatches are
impossible by construction: the check passes on **any** factor values, including the
current garbage. The report's "0 residual — PASS" is therefore not evidence. **Fix:** at
each ex-date row, assert `adj_prev_close(t) ≈ adj_close(t-1)` — i.e., the adjustment must
*close* the raw gap; off-ex-date rows are the trivial case, ex-date rows are the test.

### F5 — MAJOR — §2 "hand-verified" table is self-refuting and was not read
RELIANCE 2026-06-05 "SPLIT ratio 6.0": raw close before 1,303.70, raw close after 1,291.00 —
no price gap, so no split happened (it was a ₹6 final dividend) — yet "adjusted before" is
printed as 7,822.20, a fabricated 6× discontinuity, in a table titled *hand-verified*.
Verification that doesn't compare `adjusted_before` to `raw_after` verifies nothing.
**Fix:** the hand-verify section must assert `adj_before ≈ raw_after` per event and fail
loudly otherwise.

### F6 — MAJOR — ex_date is actually the record date for Table/Table1
`BCRD_FROM` is the book-closure/record date, not the ex-date (India moved to T+1 ex/record
alignment only in 2023; before that the ex-date precedes the record date by ≥ 1 session).
Bonus factors are therefore anchored to the wrong day; the ±7-day classification window
masked this in §3, but the adjusted view shifts prices on the wrong session. **Fix:**
prefer `Table2`-style `Ex_date` where available; for bonuses, derive the ex-date by
locating the raw price gap within [record_date − 5, record_date] in the bhavcopy —
deterministic and self-auditing.

### F7 — MEDIUM — dividend inventory double-counted
`Table` and `Table2` carry the same dividend events (1,013 exact same-date mirrors; the
rest offset by record-vs-ex date). Any future dividend-based logic (special-dividend
threshold per Group 2) must first dedupe on (symbol, amount, ±7 days). The `INSERT OR
IGNORE` on `adjustment_factors` PK `(symbol, ex_date, action_type)` also silently drops
same-day double bonuses (rare but real).

### F8 — MEDIUM — split factor convention inverted even as designed
`derive_factor()` returns `old/new` for splits ("split from 10 to 5 → 2.0") and the view
multiplies **pre-event** prices by it. Backward adjustment must scale pre-event prices
*down* by `new/old` (FV 10→5 halves the price; pre-event prices × 0.5). The §2 prose
contradicts itself in one sentence ("2:1 split → factor 2.0" vs "1:10 split → factor 0.1").
Moot today (no real splits ingested) but must be fixed before re-ingest. The bonus branch
and the volume treatment (`volume / cum_factor`) are correct as written.

### F9 — MINOR — report hygiene
(a) 560 KB / 6,689 lines is not a reviewable document — emit the full move table to a
sidecar CSV/parquet and keep only residue + samples in the MD; (b) the per-row cap
`len([l for l in L if str(td) in l]) < 200` is O(n²) and caps on substring-matching the
date anywhere in any line — replace with a plain counter; (c) text says "within 5 calendar
days", code uses 7; (d) scope note hardcodes "~967 unmapped" vs the computed 1,472; (e)
§3 preamble renders "they have < -20% symbols" — wrong variable (`MOVE_LO` where
`RESTRICTED_THRESHOLD` was meant); (f) `full_set`, `timedelta`, `start`/`end` args are
dead code.

---

## Path to PASS

1. **Purge and re-derive** (no re-download needed — raw JSON cache is intact):
   drop all SPLIT rows from `corporate_actions`/`adjustment_factors`, re-parse the cached
   `bse_ca_*.json` with corrected table mapping (F1), corrected factor convention (F8),
   and ex-date derivation (F6). Bonus rows may be re-derived under the same run.
2. **Add a split source** (F2) and the ~10-event ETF unit-split patch list (Group 1);
   ingest with the same raw-cache discipline.
3. **Charter decision (operator):** special-dividend treatment (Group 2 — MAJESCO-class
   events). **LOCKED 2026-07-10: adjust above a 20% threshold** — dividend amount ≥ 20% of
   the prior full-session close gets a backward factor `(P − D)/P`; below, no factor
   (Prompt 2R §R6).
4. **Fix the screen** (F3) and the continuity check (F4); re-run the audit. Acceptance:
   every real split/bonus gap CA-explained, resumption/migration rows reported in their own
   section (not as returns), dev-window unexplained residue = 0 **with the residue defined
   on true consecutive-session returns only**.
5. Lead Reviewer re-verifies §2 arithmetic (F5 assertion in place) and issues the verdict.

Per the role split, the remediation brief was issued as **Prompt 2R** in
`docs/reports/CSMP_IMPLEMENTATION_PROMPTS.md` (2026-07-10), covering F1–F9 plus the locked
special-dividend rule; this document is the review of record for the current deliverable.
