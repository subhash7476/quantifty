# CSMP Gate (b) — Implementation Record, Round 5

**Implementer:** Claude (operator-authorized exception to the charter role split — see caveat)
**Date:** 2026-07-10
**Baseline:** commit `91e7963`; findings from `CSMP_GATE_B_LEAD_REVIEW_R4.md`
**Deliverables:** `scripts/csmp/ingest_corporate_actions.py`, `scripts/csmp/audit_corporate_actions.py`,
`tests/csmp/test_ca_parsers.py`, regenerated `CSMP_GATE_B_CORPORATE_ACTIONS_AUDIT.md` + `CSMP_GATE_B_MOVES.csv`

---

## Caveat on independence

The charter (`CSMP_PHASE0_CHARTER.md`) locks DeepSeek V4 as implementer and Claude as Lead
Reviewer. The operator overrode that for this round. I wrote R4 and I implemented against it,
so **no independent party has checked this work.** The compensating control is that the
acceptance test is now code (§2 of the audit) rather than a reviewer's assertion: it is
adversarial to me, and it caught four of my own errors — including two findings in R4 that were
simply wrong. A genuine review of this commit is still owed.

---

## Verdict: **PASSED WITH DOCUMENTED EXCEPTIONS**

> **Addenda (same day), in order.**
> 1. The operator ruled the move screen inherits gate (a)'s H2 non-equity exclusion now rather
>    than at gate (c). Implemented by ISIN via a new `symbol_isin` table
>    (`scripts/csmp/build_symbol_isin.py`) — §10. **Dev-window residue 23 → 6**, no inferred factor.
> 2. The operator ruled (i) demergers are carried as a documented exclusion into gate (c), and
>    (ii) the gate records **PASS WITH DOCUMENTED EXCEPTIONS** once every residue row is either
>    resolved or named in `ca_scope_exclusions`. Implemented — §11. All 6 dev-window residue rows
>    are documented; **0 undocumented**; continuity 0. The audit prints the pass.

| | Before (`91e7963`) | After |
|---|---|---|
| Dev-window residue | 4,141 (opaque "genuine") | **6, all documented** (0 undocumented) |
| Adjusted ex-date continuity mismatches | 31 | **0** |
| Factors failing price evidence | not measured in code | **4 of 1,039** |
| Split factors with `factor = 1.0` (silent no-op) | 1 | **0** |
| Consolidations representable (`factor > 1`) | no | **yes** (VERTOZ = 10.0) |
| Parse rejects (refused, not guessed) | 0 | **19**, itemised |
| Parser unit tests | 0 | **37** |
| Sidecar CSV rows carrying a class | 0 of 5,609 | **all 5,609** |

Gate (b) does not pass. It is blocked on **two sourcing problems that no code change can honestly
close**, listed under "What I did not do".

---

## What changed

### 1. The acceptance test is now code (R4/N1)

`audit_corporate_actions.py` §2 defines and runs the price-evidence regression on every factor:

> For each ex-date, `F = Π factor` over all factors at that `(symbol, ex_date)`.
> `implied_open = open(ex)/close(ex−1)`, `implied_close = close(ex)/close(ex−1)`, taken over the
> **EQ+BE union**, and only where the two prints are **adjacent sessions** (gap ≤ 5d).
> The factor reconciles if **either** agrees within **25%**.

Three design points, each of which changed the answer materially:

- **EQ+BE union.** An EQ-only lookup compares prints across a symbol's suspension. `ATLASCYCLE`
  2017-10-30 appeared to be a 3.94× error; its EQ prints straddle **2,907 days**. In BE it traded
  every session and repriced 413.95 → 214.00 against a stored factor of 0.5. It is correct.
  **R4's finding on ATLASCYCLE was an artifact of my own query.**
- **Open *or* close.** The adjustment lands at the open, so the open is the sharper signal — but a
  thin open print is unreliable. `QGOLDHALF`'s open (0.01748) reconciles to nothing; its close
  (0.02024) confirms 1:50. Conversely `AXISGOLD`'s close (0.01199) is a `+20%` circuit day; its
  open is exactly 0.01000. **R4's claim that AXISGOLD "does not reconcile" was wrong** — it is a
  clean 1:100, and R3 and R4 both misread a circuit move as a factor error.
- **25% band.** A ±20% circuit move is legal in a single session. A 15% band flagged a dense
  cluster of correct factors sitting at exactly 1.20× their implied ratio.

The metric now lives in one place, so successive rounds measure the same quantity. R3 reported 42
violations; R4 reported 70. Both were reviewer scratch SQL; neither was reproducible from the repo.

### 2. Face values are parsed from the face-value clause (R4/D1)

`parse_split_clause()` locates the clause (`Face Value Split` / `Fv Spl` / `Sub-Division` /
`Consolidation`) and applies a decimal-aware, currency-anchored pattern **to that clause only**.
It never scans the whole string for integers. Consequences:

- `DPSCLTD` no longer takes 22 from its bonus ratio; `KCP` and `EMAMILTD` no longer take a
  dividend amount (`Rs.2.50` no longer yields `[2, 50]`).
- `VERTOZ` 2025-06-25 `Consolidation … Re 1 … To Rs 10` is now **10.0**, not 0.1. Its pre-2025
  history was wrong by 95×.
- `DWARKESH` 2017-08-10 is **0.1**, not the stored no-op 1.0.
- `STLTECH`'s compressed `Rs.5tors.2` parses to 5→2; `SHARONBIO`'s prefix-less
  `From 10/- To Face Value 2/-` parses to 10→2.
- **Reject, do not guess.** `capital_reduction_ambiguous` (6, incl. `MONNETISPA`'s
  reduction-then-consolidation, which has no single factor) and `non_equity_bonus` (13) go to
  `ca_parse_rejects` with the purpose text. The audit prints every row.

A bare `Spl` in this feed always abbreviates *Special Dividend* (`Agm/Spl Div- Rs.5/-`), never
*Split*, which is always written `Fv Spl`. Matching bare `Spl` produced 11 phantom rejects.

### 3. Both legs of a combined action (R4/D4)

The bonus leg is parsed from the same PURPOSE string and the same ex-date as the split. `DPSCLTD`
now carries `BONUS=0.043478 * SPLIT=0.1`; `STER`, `STLTECH`, `RESURGERE` likewise.

### 4. NSE CF-CA replaces the BSE feed for BONUS

BSE keys bonuses on `BCRD_FROM`, the **record date**, not the ex-date. Measured head-to-head on
open evidence: CF-CA 36 violations in 494 tested; BSE 82 in 504, with a further 230 events having
no price evidence at all because the date is wrong. Of 196 post-2010 BSE bonuses with no CF-CA
counterpart, only three corroborate — and two of those (`GUJNRECOKE`, `JISLJALEQS`) are DVR
bonuses whose stored factors (0.909, 0.952) are *wrong*: the implied ratio is ≈1.0, because a DVR
bonus does not dilute the equity line. BSE now supplies DIVIDEND only.

Bonus debentures, DVR, NCRPS and preference shares are excluded by name. `TVSMOTOR`'s
`Scheme Of Arrangement - Bonus Ncrps 4:1` was producing a 0.2 price factor against an implied 1.0.
NCRPS was the abbreviation my first pass missed.

### 5. Factors are mapped to the symbol in force at the ex-date

**The CF-CA feed files every historical event under the symbol's *current* name.** `BAJAJCON`
carries `BAJAJCORP`'s 2011-05-05 split; `METKORE` carries `CRONIMET`'s; `CCAVENUE` carries
`INFIBEAM`'s 2017 split; `SONAMLTD` carries `SONAMCLOCK`'s 2022 bonus. The ingest never consulted
gate (a)'s `symbol_changes`, so those factors landed on a symbol that did not yet exist, and the
real move went unexplained.

`resolve_symbol_at_ex_date()` walks the rename chain backwards and picks the first candidate that
actually traded within ±10 days of the ex-date. **170 records remapped.** Ex-dates lacking price
evidence fell from 99 to 22.

### 6. `prev_close` scaling, and duplicate rows in the adjusted view (R4/D2)

`prev_close(t)` is `close(t−1)`; its correct cumulative factor includes the event at `t`. The view
now scales it by `LAG(cum_price)`. Continuity: **31 → 0**.

Separately, factors sharing an ex-date (a combined bonus+split) produced **two output rows per
trade date** — the `MIN(ex_date)` join matched both. Factors are now compounded per
`(symbol, ex_date)` before the join. Row count unchanged at 7,030,920, verified.

### 7. The classifier requires magnitude, and a factor explains exactly one move (R4/D3)

A move is CA-explained only when the factor spanning its session matches it in **direction and
magnitude** (25%). The old 7-day proximity window let a stale factor claim an unrelated move —
`LANCER`'s −20% on 2022-12-23 was "explained" by an ex-date seven sessions earlier. The window is
gone: a factor explains the session `(prev_td, td]` that spans its ex-date, and nothing else.

New buckets: `CA-explained`, `genuine`, `magnitude-mismatch`, `direction-mismatch`,
`CA-shaped-orphan`. **Residue** = the last three. Per the operator's decision, a move with no
factor spanning it and no CA-shaped ratio is **classified** `genuine` — a classification, not a
residue, which is what the charter asks for.

`CA-shaped-orphan` (a move landing on a canonical CA ratio with no factor to explain it) is a
*missing-factor detector*. It is applied only where `prev_close ≥ Rs 5`: below that the Rs 0.01
tick grid forces canonical ratios — a stock at Rs 0.10 ticking to Rs 0.05 is exactly −50% and
means nothing. That guard removed 316 of 386 orphans; every survivor is real.

### 8. Report and hygiene (R4/H2, H3, M1, M2, N3, L1)

The `{match}` f-string bug is fixed by deleting the section: the twelve-event hand-verify is
superseded by the full-population evidence test. The sidecar CSV is written **after** classification
and carries `window`, `class`, `detail` on all 5,609 rows. Special-dividend rejections are counted
and printed (65 unparseable, 1,797 no prior close, 7,096 below threshold). The dead HTTP stack
(`requests`, `HTTPAdapter`, `Retry`, `get_session`, `SESSION`) and `dev_residue` are deleted. The
ambiguous `Adj before` label is gone with the section that used it.

### 9. Tests

`tests/csmp/test_ca_parsers.py` — 37 tests, all passing. Every PURPOSE string is verbatim from the
feed; the ones carrying a symbol name are cases the old parser got wrong.

---

## What I did not do, and why

Two blockers remain. Both require a **primary source I do not have**, and closing either by
inferring the factor from the price gap would reintroduce exactly the circularity that got Round 2
rejected (R2/C1). I did not do it.

### Blocker 1 — 18 index/sector ETF unit splits (dev window) — **CLOSED, see §10**

`KOTAKNIFTY` 2017-07-27 · `BANKBEES`, `NIFTYBEES`, `PSUBNKBEES` 2019-12-19 · `HDFCNIFETF`,
`HDFCSENETF` 2021-02-17 · `MON100` 2021-06-17 · `KOTAKGOLD` 2021-07-22 · `ICICI500` 2021-10-28 ·
`ABSLBANETF`, `ABSLNN50ET`, `BSLNIFTY`, `BSLSENETFG` 2021-11-25 · `MOLOWVOL`, `MOMOMENTUM`
2022-08-11 · `ICICIMOM30` 2022-08-12 · `ICICIBANKN`, `ICICITECH` 2022-09-01

(plus ~30 more in the sealed window and outside both). All are 1:10 or 1:5 unit sub-divisions. The
NSE CF-CA equity feed carries no ETF records; the nine gold ETFs already in the store come from AMC
notices. These need the same treatment: **an AMC notice per symbol, cited**.

**However** — gate (a) already recorded the relevant inheritance: *"H2 → gate (c): 200 ETF symbols
in series EQ must be excluded from the momentum universe."* The charter universe (D1) is NIFTY 200
equities. No ETF can ever enter it. If the operator rules that gate (b)'s move screen inherits that
exclusion now rather than at gate (c), this blocker disappears **without a single inferred factor**,
and the dev residue drops from 23 to 5. That is an operator call, not mine.

### Blocker 2 — 4 demergers (dev window) and 1 disputed bonus — **DOCUMENTED, see §11**

`ORIENTPPR` 2013-03-07 (−80.4%) · `FOURSOFT` 2013-10-17 (−67.3%) · `SINTEX` 2017-05-25 (−75.2%) ·
`DCM` 2019-05-30 (−49.0%). Also outside the dev window: `QUESS` 2025-04-15, `ABFRL` 2025-05-22,
`TRIVENI` 2011-05-03, `SURANAT&P`, `WEIZMANIND`, `TEXMACOLTD`, `ORIENTABRA`.

The charter scopes gate (b) as *"splits/bonuses (and rights, where material)"*. Demergers are not
named, and their factor is not derivable from the CF-CA purpose text — it needs the resulting
entities' relative values on the ex-date. They corrupt momentum exactly as splits do. This is a
**scope question for the operator**: extend gate (b) to demergers with a real source, or record
them as a documented exclusion carried into gate (c).

`AHLEAST` 2022-10-06: NSE says `Bonus 1:2` (factor 0.667); the market repriced by 0.502, i.e. a 1:1
bonus. Exchange text and market disagree. One row; it needs adjudication against the company filing,
not a code change.

### The 4 evidence-test failures

| Symbol | Ex-date | Legs | Stored | implied_open | implied_close | Deviation |
|--------|---------|------|-------:|-------------:|--------------:|----------:|
| SAHPETRO | 2013-07-09 | `BONUS=0.452381` | 0.452381 | 0.821348 | 0.821348 | 44.9% |
| KWALITY | 2010-06-15 | `BONUS=0.583333` | 0.583333 | 0.850920 | 0.850920 | 31.4% |
| DVL | 2021-08-05 | `BONUS=0.666667` | 0.666667 | 1.008479 | 0.934497 | 28.7% |
| AHLEAST | 2022-10-06 | `BONUS=0.666667` | 0.666667 | 0.528042 | 0.501642 | 26.3% |

All four are bonus ratios the exchange published and the market did not honour. They are stored
(the document is the authority) and flagged in `ca_evidence_exceptions` (the price is the screen),
per the operator's decision. Downstream can filter these four symbols. They are **not** silently
adjusted, and they are **not** silently dropped.

---

## New tables

| Table | Purpose |
|-------|---------|
| `ca_parse_rejects` | Every record refused rather than guessed at, with reason and purpose text |
| `ca_evidence_exceptions` | Every factor whose stored value cannot be reconciled against the ex-date repricing |

---

## Reproduction

```
python scripts/csmp/ingest_corporate_actions.py    # rebuilds CA tables + adjusted view
python scripts/csmp/audit_corporate_actions.py     # regenerates the audit + sidecar
python -m pytest tests/csmp/test_ca_parsers.py -q  # 37 passed
```

The ingest purges and rebuilds only the corporate-action tables. The gate-(a) store
(`equity_bhavcopy`, 7,030,920 rows) is never written and remains sound.

---

## 10. Non-equity exclusion — Blocker 1, closed (operator decision)

The operator ruled that gate (b)'s move screen inherits gate (a)'s H2 constraint immediately.

H2 identified ETFs by the symbol-name pattern `%BEES%`/`%ETF%`/`%GOLD%`. **Names are not
identifiers.** That pattern misses `KOTAKNIFTY`, `MON100`, `ICICI500`, `ICICIBANKN`, `MOLOWVOL` and
93 others, and would match a substring in an operating company's ticker.

The bhavcopy carries the real answer: NSE issues `INE*` ISINs to companies and `INF*` ISINs to
mutual-fund schemes, which is what an ETF is. `scripts/csmp/build_symbol_isin.py` unions the ISIN
column of every raw payload that has one — 2,481 legacy `cm*bhav.csv` and the UDiFF
`BhavCopy_NSE_CM_*.csv` — into a new `symbol_isin` table (3,628 symbols; 3,165 of the store's 4,132
EQ+BE symbols mapped). Gate (c) needs this map anyway.

The screen excludes **355 non-equity symbols: 309 by `INF*` ISIN, 46 by H2's name pattern** where no
raw payload carries an ISIN for them. ISIN is authoritative; the name pattern is the fallback, not
the rule.

**One symbol escapes both**: `ICICIMOM30` (−89.9%, 2022-08-12) has no ISIN in either payload era and
does not match the name pattern. The audit **prints it by name** rather than let it pass as an
equity. Closing it needs an NSE instrument master, which gate (c) will require regardless.

A NULL-handling bug was caught and fixed during this change: an unmatched `LEFT JOIN` makes
`si.isin LIKE 'INF%'` evaluate to `NULL`, and `NOT NULL` is `NULL`, so the first version silently
dropped **all 967 unmapped symbols** from the screen — 414 real moves. `COALESCE(si.isin, '')` is
load-bearing and commented as such.

Effect: dev-window residue **23 → 6**. The 18 ETF unit splits are gone from the screen without a
single factor being inferred from a price gap. What remains is Blocker 2 in full: four demergers,
`AHLEAST`'s disputed bonus, and `ICICIMOM30`.

The audit regenerates byte-identically on re-run.

---

## 11. Documented exceptions and the PASS criterion (operator decision)

The operator ruled: demergers are carried as a documented exclusion into gate (c), and the gate
records **PASS WITH DOCUMENTED EXCEPTIONS** once every residue row is either resolved by a factor or
named, with a reason, in a register that gate (c) inherits.

`ca_scope_exclusions` (written by the ingest) holds 13 moves in three reasons:

- **`out_of_scope_corporate_action`** (11 rows; 4 in the dev window: `ORIENTPPR`, `FOURSOFT`,
  `SINTEX`, `DCM`). A CA-shaped move with **no split, bonus or special dividend in the NSE CF-CA
  feed**. The charter scopes gate (b) to splits/bonuses/rights. Each has the shape of a demerger,
  but that is recorded as a **suspicion, not a finding** — nothing in this repository corroborates
  it, and a factor would need the resulting entities' relative values on the ex-date. Carried to
  gate (c).
- **`disputed_ratio`** (1 row: `AHLEAST`). NSE publishes `Bonus 1:2`; the market repriced 1:1.
  Factor stored as published; flagged in `ca_evidence_exceptions`; needs the company filing.
- **`unidentified_instrument`** (1 row: `ICICIMOM30`). No ISIN in any payload and no name match, so
  the non-equity screen cannot reach it. Needs an NSE instrument master — a gate (c) prerequisite.

**The gate criterion is now precise and mechanical:** an *undocumented* dev-window residue row fails
the gate; a documented one does not. The audit computes `undocumented = residue − ca_scope_exclusions`
and the register is keyed `(symbol, move_date)` so a symbol excluded for one event is not excluded
for another. Today: **6 dev-window residue rows, 6 documented, 0 undocumented.** The four
evidence-test failures are documented by construction in `ca_evidence_exceptions` (factor stored as
the exchange published it); per the operator's earlier decision they report, they do not block.

Guardrail against silent scope creep: `tests/csmp/test_scope_exclusions.py` (6 tests) asserts every
listed move carries a reason, every reason has detail text, there are no orphan detail entries or
duplicate keys, and the four named dev-window demergers plus the two distinct non-demerger reasons
are present. If a future run drops a factor for one of these symbols, the move leaves the residue and
the exclusion simply goes unused — it can never mask a *new* undocumented move, because the audit
subtracts the register from the residue rather than the reverse.

---

## Quarantine status

`equity_bhavcopy_adjusted` is the authoritative research source for downstream CSMP work, **excluding
the symbols named in the two exception tables** — `ca_scope_exclusions` (13 moves) and
`ca_evidence_exceptions` (4 factors). For every other symbol the view is continuous at every ex-date,
every factor traces to an exchange document, and every factor with adjacent-session evidence
reconciles against the market's own repricing within 25%. Gate (b) is **PASSED WITH DOCUMENTED
EXCEPTIONS**; the gate-(a) store is unaffected throughout.
