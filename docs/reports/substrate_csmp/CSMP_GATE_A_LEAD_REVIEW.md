# CSMP Gate (a) — Lead-Reviewer Verdict

**Reviewer:** Claude (Lead Reviewer, per `CSMP_PHASE0_CHARTER.md` role split)
**Implementer:** DeepSeek V4
**Gate:** (a) — Equity daily bhavcopy ingestion + quality audit
**Date:** 2026-07-08
**Deliverables reviewed:**
`scripts/csmp/ingest_equity_bhavcopy.py`, `scripts/csmp/audit_equity_bhavcopy.py`,
`docs/reports/CSMP_GATE_A_EQUITY_BHAVCOPY_AUDIT.md`, `data/market_data/equity_bhavcopy.duckdb`.

---

## Verdict: **NOT PASSED — INCOMPLETE (code sound in exercised parts; gate evidence does not yet exist)**

This is **not** a rejection of the implementation. It is the only honest verdict available
because the gate's evidentiary deliverable — a **full-span 2010→present** audit — does not
yet exist. The store is a **7-trading-day proof-of-life slice** (2019-12-27 → 2020-01-06,
11,511 rows), explicitly and prudently deferred by the implementer to avoid hammering NSE
archives before code review. The scripts' plumbing is proven on that slice; the gate's
substantive claims (coverage-by-year across 2010–present, real era boundaries, non-zero
continuity breaks, full missing-day reconciliation) are all trivially empty on 7 days.

**A PASS cannot rest on a 7-day slice.** Path to PASS:
1. Fix **F1–F4** below (F1/F2 are latent defects that only bite at full scale — fixing them
   now avoids re-running a multi-thousand-request ingest twice).
2. Operator runs the full `ingest_equity_bhavcopy.py` (chunked; see §Operational).
3. Re-run the audit; Lead Reviewer issues the real PASS/NOT-PASSED on the full-span numbers.

The **prompt-4 discipline is respected** by the implementer's honesty here — the prior
program was returned for silently stopping at 43% coverage and calling it done. DeepSeek did
the opposite: it stopped explicitly, quantified the slice, and flagged the full run as an
operator action. That is the correct behavior and is noted favorably.

---

## Verification performed by the reviewer (evidence, not assertion)

| Check | Result |
|-------|--------|
| Store row count / days / span | 11,511 rows, 7 days, 2019-12-27 → 2020-01-06 — matches audit headline |
| Series retained | EQ (10,481) + BE (1,030) only — matches scope filter |
| `symbol_changes` populated | 1,050 rows — matches audit §5 |
| Audit determinism | Regenerated audit is **byte-identical** to committed report (fixed store) |
| Raw cache backing the audit | 7 entries (3 `legacy_*.zip`, 4 `secfull_*.csv`) — LEGACY+SECFULL only |

The 7-day slice straddles the LEGACY→SECFULL boundary (Dec 2019 legacy, Jan 2020 secfull),
so those two parsers and the source-preference order between them are lightly exercised.
**UDIFF is entirely unexercised** (see F4).

---

## Findings

### F1 — MAJOR — false-PASS in the gate's own pass criterion
`audit_equity_bhavcopy.py` computes coverage holes as:
```python
holes = [d for d in missing_idx if classify_missing(d) in ("not-fetched", "ingested-empty")]
```
`missing_idx` is, by construction, the set of dates the **index demonstrably traded** (drawn
from the known-good 1m index calendar, 2023+) yet are absent from the store. If all bhavcopy
sources returned 404 for such a date, `classify_missing` returns `"confirmed-absent"`, which
is **excluded** from `holes`. The fit-for-purpose section then reports "0 holes" and prints
the PASS language — even though a 404 on a date the index provably traded is, by definition,
a **source hole**, not a holiday.
**Impact:** a genuine post-2023 source hole passes the gate silently. This defeats the single
strongest check the gate possesses.
**Fix:** for any `d in idx_days`, `confirmed-absent` must be counted as a hole (holiday
ambiguity does not apply — we have positive evidence the day traded).

### F2 — MAJOR — sticky poisoned cache under NSE rate-limiting
`fetch()` writes `resp.content` to the `.csv`/`.zip` cache file for **any** non-404 2xx
response, *before* any zip/CSV validation:
```python
resp.raise_for_status()
data_path.write_bytes(resp.content)   # cached before validation
```
NSE archive endpoints, under bulk access, are known to return **HTTP 200 with an HTML
interstitial / blocked page** instead of the archive. That non-conforming body is cached
permanently. Downstream, `parse_*` raises `BadZipFile`/`KeyError` → the day falls through to
the next source or becomes a silent hole — and **every re-run re-reads the poisoned cache and
fails identically**. The "resumable cache" thus actively prevents recovery from exactly the
failure mode a 2010→present run will hit.
**Not exercised by the 7-day slice** (all 7 fetches returned clean bodies).
**Fix:** validate before caching — zip magic (`PK\x03\x04`) for `.zip`, expected header
tokens for `.csv`; on mismatch, treat as a **transient** failure (do not cache), so re-runs
retry rather than re-consuming poison.

### F3 — MAJOR — coverage-verification inversion (strong check covers the wrong window)
The only authoritative coverage check is index-calendar reconciliation, and the in-repo
index calendar spans **2023→present** — i.e. exactly the **sealed held-out window**
(D5: 2023-01 → 2026-06). The **dev window 2012-01 → 2022-12**, where all research actually
happens, has **no external calendar**: the audit falls back to the store as its own calendar
and states holiday-vs-source-hole is "indistinguishable." So the gate can strongly verify
coverage precisely where we are forbidden to look, and only weakly where we do the work.
The prompt explicitly requires every missing date classified as *holiday / source hole /
fetch failure* — unmet for 2010–2022 as written.
**Fix:** ingest an authoritative **NSE trading-holiday calendar for 2010–2022** (NSE
publishes annual holiday lists; also reconstructable) as the pre-2023 ground truth, so
dev-window weekday gaps resolve to holiday vs genuine source hole.

### F4 — MODERATE — UDIFF parser never exercised
The slice is Dec 2019 – Jan 2020, so only LEGACY + SECFULL ran. `parse_udiff`, the
`FinInstrmTp == "STK"` row filter, the `SctySrs` series field, and the UDIFF column names
have **never touched real data**, yet UDIFF governs **2024-06 → present** (part of the sealed
window and all forward accumulation). The `STK` filter value in particular is asserted, not
verified.
**Fix (before the full run is trusted):** spot-check one UDIFF day and the **2024-06 → 2024-07-05
era-overlap week**, where all three sources coexist and the SECFULL > UDIFF > LEGACY
preference order is the thing actually under test.

### F5 — MINOR — pre-2023 Saturday special sessions silently dropped
`date_range` yields weekdays only (`d.weekday() < 5`). NSE has held Saturday live sessions
(e.g. budget-day sessions, special trading sessions). Pre-2023 these are never fetched and
never flagged as missing (2023+ Saturdays would be caught by the index calendar). Over
2010–2022 this is a handful of days, but it is currently an **undisclosed** gap.
**Fix:** either attempt Saturdays too, or disclose the weekday-only assumption in the audit.

### F6 — MINOR — embedded store size is not rebuild-stable
The report embeds the `.duckdb` file size (`2.1 MB`). DuckDB file size can vary across a
**rebuild** (page allocation / checkpoint / free lists) even for identical data. The
byte-identical regeneration confirmed here is two audits over the *same* store file; it does
not guarantee identity across an ingest rebuild.
**Fix:** note the size as approximate, or exclude it from the byte-identity guarantee.

### F7 — MINOR — audit is not standalone against a bare store
Era map and missing-date classification read the `data/market_data/bhavcopy_raw/` cache. Run
against a `.duckdb` whose cache has been cleared, `source_for_date` returns `"unknown"` and
`classify_missing` returns `"not-fetched"` for every date — a wildly wrong report. Acceptable
for the ingest-then-audit-same-machine workflow, but the coupling should be documented (the
"runs clean on a fresh checkout" DoD holds only with the cache co-located).

---

## What is correct and should be preserved (positives)

- **Schema matches the prompt exactly**; `PRIMARY KEY (trade_date, symbol, series)` enforces
  the uniqueness constraint and makes duplicate screens structurally impossible.
- **Turnover normalized to rupees across all three eras** — verified column semantics:
  SECFULL `TURNOVER_LACS × 1e5`, LEGACY `TOTTRDVAL` (already rupees), UDIFF `TtlTrfVal`
  (rupees). Correct.
- **Idempotency is real**: skip-present loop + `ON CONFLICT DO UPDATE` upsert → re-runs
  reproduce the store; the reviewer confirmed byte-identical audit regeneration.
- **Transient-vs-404 discipline is correct**: 404 → `.404` marker (cached, confirmed-absent);
  timeout/5xx after retry exhaustion → uncached, counted as failed, retried next run. This is
  the right resumability contract (F2 is a gap in *what counts as* a cacheable success, not in
  this distinction).
- **EQ/BE-only scope filter** applied uniformly; all symbols retained (delisted-name
  retention for gate (c) preserved).
- **Scope fence honored**: work confined to new `scripts/csmp/` + new `data/market_data/`
  files; no frozen-component, `core/msi/`, DRA, or execution-stack diffs.
- **Honest framing**: NULL delivery for LEGACY/UDIFF disclosed; `-` → NULL disclosed;
  fit-for-purpose statement is scoped to what gate (a) can claim; the full run correctly
  deferred to the operator rather than faked.

---

## Operational note for the full run (operator action)

The default span (2010-01-01 → yesterday) is ~4,000 trading days; pre-2020 is legacy-only
(one request/day), 2020+ tries SECFULL first and stops on success. With the built-in
`time.sleep(0.4)` and retry/backoff, expect a long, throttle-sensitive run. Recommend
**chunking by year via `--start/--end`** (the script supports it) and running F1/F2 fixes
first so a transient NSE 200-with-HTML does not poison the cache mid-run. Re-audit after the
full ingest; the real coverage/era/continuity numbers are the basis for the gate PASS.

---

## Disposition

- **Prompt 1 (Gate a): NOT PASSED — INCOMPLETE.** Findings F1–F4 to be addressed by the
  implementer; F5–F7 at implementer discretion (disclose-or-fix). Then operator runs the full
  ingest and the Lead Reviewer re-audits the full-span report.
- **Prompts 2–5: remain HELD.** No next-gate work is authorized until gate (a) reaches PASS on
  full-span evidence.

---

# Round 2 — Re-review of revised submission (2026-07-09)

**Reviewer:** Claude (Lead Reviewer) · **Implementer:** DeepSeek V4
**Trigger:** revised `ingest_equity_bhavcopy.py` + `audit_equity_bhavcopy.py` + regenerated
`CSMP_GATE_A_EQUITY_BHAVCOPY_AUDIT.md` submitted in response to Round-1 findings F1–F7.

## Verdict: **STILL NOT PASSED — INCOMPLETE (code findings resolved; full-span gate evidence still absent)**

The Round-1 *code* defects are genuinely fixed and verified. The Round-1 *evidentiary* problem is
unchanged: the store is still the same **7-trading-day slice** (2019-12-27 → 2020-01-06, 11,511
rows). The gate cannot PASS on 7 days. The path to PASS is unchanged: run the full ingest, re-audit,
re-review on full-span numbers.

## Round-1 findings — disposition (all verified against code + store)

| # | Round-1 finding | Status | Evidence |
|---|-----------------|--------|----------|
| F1 | false-PASS (confirmed-absent excluded from holes) | **FIXED** | holes = `{cal day ∈ span} \ {store days}`; no `confirmed-absent` escape hatch (`audit…py:101`) |
| F2 | poisoned cache (200-with-HTML cached before validation) | **FIXED** | `_valid_body` checks `PK\x03\x04` (zip) / `SYMBOL…SERIES` (csv) before write; `NonConformingBody` raised as transient, uncached (`ingest…py:210,244,250`) |
| F3 | coverage inversion (strong check only on sealed window) | **PARTIAL** | F&O oracle (`fo_is_trading`) added as independent pre-2023 truth — good design — but **never fired on this slice** (see R1) |
| F4 | UDIFF parser unexercised | **PARTIAL** | 2024-06-28→07-05 era-overlap week was *fetched* (cache present), but those rows are **not in the audited store** — UDIFF has 0 rows in the gate evidence (see R5) |
| F5 | Saturday sessions dropped | **FIXED** | `date_range` now Mon–Sat (`weekday()<6`); Dec-28 & Jan-04 Saturdays probed and correctly 404'd |
| F6 | embedded size not rebuild-stable | **FIXED** | rendered "~2.9 MB — approximate; …not part of the byte-identity guarantee" |
| F7 | audit not standalone against bare store | **FIXED** | audit reads only store tables (`equity_bhavcopy, trading_calendar, ingest_meta, symbol_changes`); no cache dependency |

## New / carried-forward findings

### R1 — MAJOR — "0 coverage holes" is structurally untested on this slice
Verified from the store: **all 7 `trading_calendar` rows carry `source = equity_store`** — i.e. the
calendar is, for this slice, the equity store's own dates fed back to itself. The independent F&O
oracle ran only on the two spanning Saturdays (`focal_20191228.404`, `focal_20200104.404`), both
correctly non-trading. The oracle's *discriminating* case — **F&O present, equity absent = genuine
hole** — was never exercised, because a contiguous 7-day slice has no interior gap for it to catch.
So "Coverage holes: 0" is trivially true and demonstrates nothing about the coverage the gate exists
to prove. (This is the Round-1 "all substantive checks are empty on 7 days" point, surviving the
revision — the mechanism is now correct, it just has not been given a day it can fail on.)

### R2 — MODERATE — fit-for-purpose overclaims "(dev AND sealed windows)"
`audit…py:263` prints "no coverage hole against the authoritative trading calendar (**dev AND sealed
windows**)". The slice is entirely in the dev window (Dec 2019–Jan 2020) and touches **zero**
sealed-window (2023+) days. The parenthetical asserts a cross-window validation this run did not
perform. Scope the claim to what actually ran, or withhold it until the full ingest.

### R3 — MODERATE — audit does not disclose it is a proof-of-life slice
Read alone, `CSMP_GATE_A_EQUITY_BHAVCOPY_AUDIT.md` gives no signal that its 7 days are ~0.2% of the
~4,000-day gate target, nor that the full 2010→present ingest has not run. The "Gate (a) can honestly
claim: a complete… store" language reads as a PASS. The proof-of-life status and *full-run-pending*
must be stated **in the audit body itself** (today it lives only in this separate review), so the
document cannot be mistaken for the gate-passing evidence.

### R4 — MODERATE — sealed-window (2023+) calendar completeness is assumed, not verified
For 2023+, `build_trading_calendar` derives the calendar **solely** from `index_1m` filenames. A day
that genuinely traded but is missing from *both* `index_1m` and the equity store never enters the
calendar and is never counted as a hole — the exact F1 failure class, relocated to the sealed window.
The `index_1m` calendar's own completeness should be asserted (e.g. cross-checked against the F&O
oracle or an NSE holiday list) rather than trusted as ground truth.

### R5 — MINOR — raw cache is out of sync with the audited store; UDIFF unproven in evidence
The cache holds a 2024-06-28→07-05 secfull/udiff/legacy spot-check (good — UDIFF was at least
fetched), but those days are **not ingested** (store ends 2020-01-06), so §2's era map shows no UDIFF
row and the SECFULL > UDIFF > LEGACY preference order is not actually *audited*. For F4 to be met in
the gate evidence, the overlap week must be ingested into the store and appear in the era map.

## Path to PASS (unchanged from Round 1, refined)
1. R2/R3 are doc-only and should be corrected now (scope the claim; disclose proof-of-life status).
2. Operator runs the full chunked ingest 2010→present (F1/F2 fixes make this safe to run once).
3. Ensure the 2024-06→07-05 overlap week lands in the store (R5) so UDIFF and the era-preference order
   appear in the audited era map.
4. Address R4 (assert `index_1m` completeness for the sealed window).
5. Re-run the audit; Lead Reviewer issues the real PASS/NOT-PASSED on full-span numbers.

**Prompts 2–5 remain HELD.**

---

# Round 3 — Re-review of the full-span submission (2026-07-09)

**Reviewer:** Claude (Lead Reviewer) · **Implementer:** DeepSeek V4
**Trigger:** operator reports "Gate (a) audit is complete." Store is now full-span
(5,787,584 rows / 3,475 trade days / 4,020 symbols); audit regenerated.

## Verdict: **NOT PASSED — the audit's central claim is unsound**

The report states **"2 coverage holes."** The store is in fact missing **~617 trading days**
(2022-01-01 → 2024-06-30, a 913-calendar-day contiguous gap), and **both** of the 2 reported
holes are **false positives**. The audit did not under-report the gap by accident: its
`trading_calendar` is **derived from the equity store itself**, so the coverage check reduces
to `store − store = ∅` and is mathematically incapable of finding a real hole.

This is Round-1 **F3** and Round-2 **R1** surviving, unfixed, at full scale. The F&O oracle
built to fix F3 is **inert**: it returned `True` zero times in the entire run.

Round 2's disposition of F3 ("PARTIAL — good design, never fired") must be corrected to
**F3 — NOT FIXED**.

---

## Verification performed by the reviewer (evidence, not assertion)

All figures below are read directly from `equity_bhavcopy.duckdb` and the raw cache.

| # | Check | Result |
|---|-------|--------|
| V1 | `trading_calendar` source breakdown | **3,475 of 3,477 rows are `source='equity_store'`**; 2 are `index_1m`; **`fo_probe` = 0 rows** |
| V2 | Did the F&O oracle ever succeed? | `focal_*.zip` = **0**; `focal_*.404` = **782** (all 2010–2021). Never returned `True`, once. |
| V3 | Was 2022–2023 ever probed? | **No `focal_2022*`, no `focal_2023*`, no `legacy_2022*`/`legacy_2023*` markers exist.** Those years were never fetched. |
| V4 | Store rows in 2022–2023 | **0.** Calendar rows in 2022–2023: **0.** |
| V5 | `ingest_meta` vs store | `legacy` 2,475 dates + `secfull` 1,043 dates = **3,518 ≠ 3,475** distinct store dates. **43 `secfull` dates hold zero rows.** |
| V6 | The 43 orphan dates | All are NSE holidays (2020-12-25, 2021-01-26, 2024-08-15, 2024-12-25, 2026-03-03 …) |
| V7 | Holiday CSV provenance | `secfull_20241225.csv` → `DATE1 = 24-Dec-2024`; `secfull_20210126.csv` → `25-Jan-2021`; `secfull_20260303.csv` → `02-Mar-2026`. **NSE serves the previous trading day's file with HTTP 200.** |
| V8 | Hole #1 `2026-02-01` (Sun) | Index file holds **375 bars, one symbol (`NSE_INDEX\|Nifty Bank`)**, stamped Sunday 09:15–15:29. NSE has never traded a Sunday — backfill artifact. |
| V9 | Hole #2 `2026-03-03` | Index file `2026-03-03.duckdb` holds 197 bars whose timestamps are **all `2026-03-02`**. The secfull CSV for that date is also 02-Mar. Both sources agree: **2026-03-03 was a holiday (Holi).** |
| V10 | Index files are not date-partitioned | `2026-03-02.duckdb` spans 2026-02-27→03-02; `2026-03-04.duckdb` contains 2026-03-02 bars. Filenames ≠ contents. |
| V11 | Dev / sealed window occupancy | Dev (2012–2022) = 2,476 days — **2012–2021 only, 2022 contributes 0**. Sealed (2023–2026-06) = 494 days — **2024-07 onward only, 2023 contributes 0**. |
| V12 | Missing days **already provable from this repo** | `index_1m` filenames absent from the equity store: **246 (2023) + 123 (2024) = 369 days.** Plus all of 2022 (~248, no in-repo witness) ⇒ **~615–617 trading days**, consistent with 650 weekdays in the gap minus ~35 holidays. |

---

## Findings

### G1 — CRITICAL — the "authoritative calendar" is the store itself (F3/R1 unfixed)
`build_trading_calendar` seeds `entries = {d: "equity_store" for d in eq_days}` and only then
consults other sources. The audit computes `missing = cal_days ∩ span − store_days`. Since
99.94% of `cal_days` *is* `store_days`, `missing` is empty by construction. The gate's single
strongest check — independent coverage reconciliation — **has never once been performed**.
The "2 holes" are the only 2 days where a non-store source contributed, and both are bad data.
**Impact:** the report's headline number is meaningless. A store missing 2.5 interior years
reports 2 holes.

### G2 — CRITICAL — the F&O oracle is dead, and its failure reads as "market closed"
`legacy_fo_url()` targets `archives.nseindia.com/content/historical/DERIVATIVES/{yyyy}/{MON}/fo{dd}{MON}{yyyy}bhav.csv.zip`
— a **decommissioned** NSE path. Every probe 404s (782 markers, 0 successes). `fo_is_trading`
then maps *404-and-not-transient* → `False` → "market was closed", and writes a permanent
`.404` marker so **re-runs can never recover**.
This is Round-1 **F1** (404 on a provably-traded day treated as a holiday) and Round-1 **F2**
(poisoned permanent cache) reproduced *inside the very component built to fix F3*.
**Fix:** repoint to the live archive (`nsearchives.nseindia.com`, and the UDIFF F&O product
for 2024-06+), **assert the oracle is alive** before trusting a `False` (a run in which the
oracle returns `True` zero times must hard-fail, not silently pass), and purge the `.404`
markers. An oracle that cannot say "yes" is not an oracle.

### G3 — CRITICAL — 2022-01-01 → 2024-06-30 is absent and was never fetched
~617 trading days — including **all of 2022** (charter dev window) and **all of 2023**
(charter sealed window). No probe markers exist for those years, so the ingest was never run
over them. `build_trading_calendar` DELETEs/INSERTs only within `[start, end]`, so the
never-ingested range never entered the calendar and therefore never entered `missing`.
The audit's `is_slice` guard (`dmin <= 2010-12-31 and n_days > 1000`) keys on span endpoints
and row count, **not contiguity**, so the proof-of-life banner was suppressed and the report
rendered its full-gate language over a store with a 2.5-year interior void.

**Falsifiable prediction (no network required).** 369 of these missing days are *already
provable from data in this repo* (V12): `data/market_data/nse/candles/1m/` holds 246 index
files for 2023 and 249 for 2024, of which 123 fall outside the equity store. Re-run
`build_trading_calendar` over `2022-01-01 → 2024-06-30` and the calendar will gain **369
`index_1m` rows**, every one of which becomes a coverage hole. The audit reported 2 not
because the evidence was unavailable, but because **that range was never passed to the
calendar builder.** If a re-run does not produce ~369 holes, this finding is wrong.

**Fix:** ingest the missing range; make `is_slice` (or a new guard) fail on any interior gap.

### G4 — MAJOR — holiday requests silently ingest the previous day's file
`_valid_body` (the Round-1 F2 fix) validates the response's **shape** (`SYMBOL…SERIES` header),
never its **identity**. NSE answers a holiday request with HTTP 200 and the *previous trading
day's* CSV (V7). `parse_secfull` takes `trade_date` from the file's `DATE1` column, so those
rows upsert onto the previous day; `ingest_day` sees `n > 0` and writes an `ingest_meta` row
keyed to the **requested** date. Hence 43 `ingest_meta` dates with zero stored rows (V5/V6).
Outcome is benign *in this run* (the overwrite is idempotent), but the guard does not exist,
and the report is now self-contradictory: **§1 lists 2026-03-03 as a coverage hole while §2
counts it as a successful `secfull` trade day.**
**Fix:** assert `file_date == requested_date` before insert; treat a mismatch as
`confirmed-absent` (holiday), not a successful ingest. Write `ingest_meta` only for dates that
actually received rows.

### G5 — MAJOR — `index_1m` is trusted by filename; both "holes" are its artifacts (R4 unfixed)
`index_trading_days()` derives trading days from `*.duckdb` **stems** and never opens the file.
The two files it uniquely contributes are the two reported holes, and both are corrupt:
`2026-02-01` is a Sunday carrying 375 BankNifty bars (V8 — consistent with the
"BankNifty backfilled Feb 2026" note in `CLAUDE.md`); `2026-03-03` contains only 2026-03-02
timestamps (V9). More broadly the 1m files are **not cleanly date-partitioned** (V10), so the
filename is not a sound trading-day signal at all.
**Fix:** derive index trading days from `MIN/MAX(timestamp)` **inside** each file, require a
plausible bar count and a full symbol cross-section, and reconcile against a real holiday list.

### G6 — MODERATE — §4 continuity breaks are misattributed
The report says the 89 breaks are "almost all unadjusted corporate actions." With a 913-day
void in the series, `prev_close(2024-07-01)` (a real 2024-06-28 close) is compared against
`close(t−1)` = **2021-12-31** for every symbol — so **exactly one break per symbol is the gap
itself**, not a corporate action. 20 symbols, 89 breaks, 4–5 each: the gap is ~22% of the
total and is silently folded into the corporate-action bucket. The check also cannot tell the
two apart.
Related, undisclosed: `INFY` has 3,101 rows starting **2011-06-29** (pre-rename it is
`INFOSYSTCH`) and `TATAMOTORS` stops at **2025-10-23** (demerger). The continuity sample
silently analyzes truncated series and the report presents the row counts without comment.

### G7 — MODERATE — §6 window occupancy is stated in a way that conceals the void
"Dev-window (2012–2022) days: **2476** | Sealed-window (2023–2026) days: **494**" (V11).
Both numbers are true and both are misleading: 2022 and 2023 each contribute **zero**. An
operator reading §6 sees two populated windows. The STOP-CONDITION FLAG is the report's one
honest signal, but it is framed as *"charter D5 dev-start may need adjustment"* — i.e. it
invites **moving the research window to fit the defect** rather than filling the data. That
framing should be reversed: the gap is a data failure until proven otherwise.

---

## What is genuinely good (preserved from Round 2, re-verified)

- Round-1 **F1** (`confirmed-absent` escape hatch), **F5** (Saturday sessions — 11 surfaced,
  all in store), **F6** (size disclaimer), **F7** (audit standalone against store tables) are
  **fixed and hold at full scale**.
- **Integrity screens are clean on 5.79M rows**: 0 NULL OHLC, 0 non-positive close, 0
  `high < low`, 0 close outside `[low, high]`, 0 negative volume, 0 duplicates (PK-enforced).
  This is real evidence and it is good.
- **Era/row partition is exact**: legacy 3,751,283 + secfull 2,036,301 = 5,787,584 total. The
  `days` column is wrong (G4), the row split is right.
- Delivery present from SECFULL only (1,840,335 / 2,036,301); rename inventory 1,050 records,
  748 matching stored symbols. Both correctly scoped as inventory for gates (b)/(c).
- The **STOP-CONDITION FLAG fired**. The mechanism worked; only its framing is wrong (G7).

---

## Path to PASS

1. **G2 first** — repoint the F&O oracle at the live archive, purge `focal_*.404`, and add the
   liveness assertion (*zero `True` responses over a multi-year span ⇒ hard fail*). Without a
   working oracle nothing below can be verified, only asserted.
2. **G3** — ingest 2022-01-01 → 2024-06-30. Add an interior-gap guard so a discontiguous store
   can never render full-gate language.
3. **G4** — assert `file_date == requested_date`; write `ingest_meta` only for dates with rows.
   Re-derive §2 (`secfull` days should fall 1,043 → 1,000 and the era days should sum to 3,475).
4. **G5** — rebuild the index calendar from bar timestamps, not filenames. Quarantine
   `2026-02-01.duckdb` (Sunday) and `2026-03-03.duckdb` (mislabelled 03-02 bars); these are
   defects in the **1m index store**, outside gate (a)'s scope fence — raise separately.
5. **G1** — with 2–4 done, rebuild `trading_calendar` and **report the `equity_store` /
   `fo_probe` / `index_1m` source mix in the audit body**. A calendar whose rows are ≥99%
   `equity_store` must be labelled non-independent, on the face of the report.
6. **G6/G7** — separate the gap-induced continuity break from corporate actions; state 2022 and
   2023 occupancy explicitly in §6.
7. Re-run the audit; Lead Reviewer issues PASS/NOT-PASSED on the rebuilt numbers.

**Prompts 2–5 remain HELD.** No gate-(b) work is authorized.

## Note on the review process

Rounds 1 and 2 correctly identified the circular-calendar risk (F3, R1) but accepted the F&O
oracle as a fix on the strength of its **design**, having observed it fire only on two
Saturdays that both 404'd. A `False`-only oracle is indistinguishable from a dead one on a
7-day slice. The lesson for the remaining gates: **a validator that has never returned its
positive verdict has not been tested.** Require the positive case before crediting a fix.

---

# Round 4 — Re-review after the 2022→2024H1 backfill (2026-07-09)

**Reviewer:** Claude (Lead Reviewer) · **Trigger:** operator identified the Round-3 gap as an
ingest-range mistake (2022 → mid-2024 skipped), downloaded the missing data, re-ran the audit.
Store is now 7,017,254 rows / 4,090 trade days / 4,132 symbols, contiguous.

## Verdict: **NOT PASSED — but the audit is now sound, and it is failing itself correctly**

The audit reports **4 coverage holes** and declares itself NOT fit for purpose. That is the
right call, though not for the reasons it gives. On verification, **only 2 of its 4 are
genuine**; the other 2 are false positives from the index store. And it **misses 3 further
genuine holes** that no source it consults can see (see G8 amendment). **The true count is 5
missing trading days.** Gate (a) is nonetheless close: the blockers are specific and fixable,
not structural.

## Retraction — Round-3 **G2 was wrong**

I claimed the F&O oracle was inert and that `legacy_fo_url()` pointed at a decommissioned NSE
path. **That is false, and I am withdrawing it.** I probed the URL directly against five known
trading days spanning every era:

| Probe date | Result |
|---|---|
| 2012-03-15 | HTTP 200, 327,087 B, valid zip → TRADING |
| 2015-06-10 | HTTP 200, 323,946 B, valid zip → TRADING |
| 2018-01-10 | HTTP 200, 478,866 B, valid zip → TRADING |
| 2021-07-14 | HTTP 200, 616,436 B, valid zip → TRADING |
| 2022-08-05 | HTTP 200, 753,776 B, valid zip → TRADING |

The oracle is **alive across the whole span**. My Round-3 inference — "782 × 404 and 0
successes ⇒ dead" — was a sampling error on my part: `build_trading_calendar` probes the
oracle *only for days absent from the store* (`if d in entries: continue`). In 2010–2021 the
store was complete, so every probed day was a genuine weekend/holiday and every `404 → False`
was the **correct** answer. A `False`-only record was evidence of a complete store, not a dead
oracle. This round the oracle produced its first `True` (`focal_20220808.zip`) and it caught a
real hole. **G2 is void.**

## Correction — Round-3 **G1 is substantially defused**

Given the above, the "circular calendar" objection is weaker than I framed it. `equity_store`
rows in `trading_calendar` are never used to *validate* themselves; they only exclude a day
from probing — and a day present in the store cannot be a coverage hole by definition. Every
day **not** in the store is put to the independent oracle. The design is therefore correct for
hole-detection, and the 4,090/4,094 `equity_store` share is an artifact of a near-complete
store, not of self-confirmation. **G1 downgraded CRITICAL → MINOR**, and the residual point is
narrow: the store's *own* days are never checked against the oracle, so a phantom date
inserted by G4 could never be challenged. Surfacing the source mix in the report body is still
worth doing, but as disclosure, not as a defect.

Round-3 **G3 is resolved** by the backfill: the store is contiguous (largest inter-day gap now
6 days), 2022 = 247 days, 2023 = 245, 2024 = 249. **G6 and G7 are resolved with it** — the
913-day continuity artefact is gone (breaks 89 → 106 over a longer series, ~5/symbol, the
corporate-action rate the report always claimed), and dev (2,723 days) / sealed (862 days) are
now genuinely populated.

## The 4 holes, adjudicated

| Date | Audit's source | Verdict | Evidence |
|---|---|---|---|
| **2022-08-08** (Mon) | `fo_probe` | **GENUINE HOLE** | `focal_20220808.zip` downloaded — F&O traded. Store jumps 08-05 → 08-10. **No `secfull_*`/`legacy_*` marker exists for the date at all** — the equity ingest never attempted it. (08-09 Muharram correctly 404s everywhere.) |
| **2023-11-12** (Sun) | `index_1m` | **GENUINE HOLE — Diwali Muhurat** | Index file holds **11,581 bars across 194 symbols, 18:15–19:14** — the signature of a Muhurat session. Control: 2024-11-01 Muhurat = 11,640 bars / 194 symbols / 18:00–18:59, and **is** in the store. No fetch marker exists for 2023-11-12. |
| **2026-02-01** (Sun) | `index_1m` | **FALSE POSITIVE** | 375 bars, **1 symbol** (`NSE_INDEX\|Nifty Bank`), 09:15–15:29. A real session carries ~200 symbols. Backfill artifact (cf. "BankNifty backfilled Feb 2026" in `CLAUDE.md`). |
| **2026-03-03** (Tue) | `index_1m` | **FALSE POSITIVE** | The file named `2026-03-03` contains **only `2026-03-02` timestamps** (15:29–15:59). Its `secfull` CSV also carries `02-Mar-2026`. Both sources agree it was a holiday (Holi). |

**Root cause of both genuine holes is the same class: the day was never fetched.**
`date_range()` yields **Mon–Sat** (`weekday() < 6`), so **Sunday sessions are structurally
invisible** to the ingest — and NSE's Muhurat session lands on a Sunday in some years
(2023-11-12). 2022-08-08 has no marker of any kind, so it was dropped by an ingest-range
boundary. Neither is a source failure; both are one-day re-runs.

## Findings carried forward / new

### G4 — MAJOR — **unchanged and now larger**: holiday requests ingest the previous day's file
`ingest_meta` now holds `legacy` 2,475 + `secfull` 1,694 = **4,169 dates against 4,090 stored
dates — 79 phantom entries** (was 43). Mechanism re-confirmed: `_valid_body` validates the
CSV's *shape*, not its *date*; NSE answers a holiday request with HTTP 200 and the prior
trading day's file (`secfull_20231114.csv`, a Diwali holiday, is cached); `parse_secfull` reads
`trade_date` from the file's `DATE1`, so rows upsert onto the previous day while `ingest_meta`
records the *requested* date. §2's "Trade days" column is therefore wrong, and the eras still
fail to sum to the store's date count.
**Fix (unchanged):** assert `file_date == requested_date` before insert; treat a mismatch as
`confirmed-absent`; write `ingest_meta` only for dates that received rows.

### G5 — MODERATE (revised) — `index_1m` is trusted by filename, and it is a mixed witness
`index_trading_days()` never opens the files. This produced 2 false holes (2026-02-01,
2026-03-03) — **and also caught the real Muhurat hole (2023-11-12) that nothing else would
have.** So the fix is not to distrust `index_1m`, but to *validate* it: derive the day from
`MIN/MAX(timestamp)` **inside** the file, require a plausible symbol cross-section (≥100
symbols, not 1), and reject files whose bars are stamped with a different date. All three
misclassifications above fall out of those two rules.
Separately: `2026-02-01.duckdb` (Sunday) and `2026-03-03.duckdb` (mislabelled 03-02 bars) are
defects **in the 1m index store**, outside gate (a)'s fence — raise as their own ticket.

### G8 — MAJOR (new) — Sunday sessions are structurally unreachable
`date_range()` is Mon–Sat. NSE holds Muhurat sessions on a Sunday in some years. The ingest can
never fetch them and the oracle is never asked about them; 2023-11-12 surfaced only by luck,
because the index store happened to hold the file. Round-1 **F5** was closed by extending
Saturday-only → this is its unclosed half.
**Fix:** extend `date_range()` to all 7 days and let the oracle adjudicate (it 404s cheaply on
true non-trading days, and those markers are already cached).

**Amendment — G8 is larger than the audit can see.** Muhurat also fell on a Sunday in 2013,
2016 and 2019. All three are absent from the store, absent from the calendar, and have **no
fetch marker of any kind**:

| Date | In store | In calendar | Fetch marker |
|---|---|---|---|
| 2013-11-03 | no | **no** | none |
| 2016-10-30 | no | **no** | none |
| 2019-10-27 | no | **no** | none |
| 2023-11-12 | no | yes (`index_1m`) | none |

Only the 2023 one is visible to the audit, because `index_1m` starts in 2023 — the pre-2023
Sunday sessions are invisible to *every* source the calendar consults, since the oracle is
never asked about a Sunday. **The true genuine-hole count is therefore 5, not 2**
(2022-08-08 + four Sunday Muhurat sessions), and the audit's "4 holes" is coincidentally close
to right for entirely wrong reasons: 2 of its 4 are false and 3 real ones are missing from it.
This does not change the verdict or the fix — it raises the stakes on G8 from "one lucky catch"
to "a systematic blind spot spanning the whole dev window."

---

## Path to PASS (short now)

1. **G8** — extend `date_range()` to Sunday.
2. Re-ingest **2022-08-08** and **2023-11-12**. Both are single days with live sources
   (`focal_20220808.zip` already proves 08-08 traded).
3. **G5** — validate `index_1m` by file contents (bar-date + symbol-count), which removes the
   two false holes; file the index-store corruption separately.
4. **G4** — assert `file_date == requested_date`; drop the 79 phantom `ingest_meta` rows;
   `secfull` days should fall 1,694 → 1,615 and the eras should sum to 4,090.
5. Re-run the audit. Expect **0 coverage holes** with a calendar whose non-store rows are all
   corroborated. Lead Reviewer issues PASS on those numbers.

**Prompts 2–5 remain HELD** — but on current evidence gate (a) is one short iteration from PASS.

## Note on the review process (Round 3 self-correction)

Round 3 called the oracle dead on the strength of an aggregate (`0 successes / 782 404s`)
without asking *which days it had been given*. It had only ever been handed non-trading days,
so it could not have answered `True`. I applied "a validator that has never returned its
positive verdict has not been tested" as a verdict about the validator, when it was only ever a
verdict about the **test**. The correct move — probing the URL directly — cost one command and
would have prevented a CRITICAL finding against working code. Verify the mechanism before
indicting it.

---

# Round 5 — Re-review after the Round-4 fixes (2026-07-09)

**Reviewer:** Claude (Lead Reviewer) · **Implementer:** DeepSeek V4
**Trigger:** operator reports the Round-4 recommended fixes (G4, G5, G8 + the two named
re-ingests) are implemented. Store is now 7,030,899 rows / 4,097 trade days / 4,132 symbols;
audit regenerated and reports **0 coverage holes**.

## Verdict: **NOT PASSED — three of four fixes verified; G8 is fixed in code but never exercised**

The code changes are real and, where the evidence can test them, they work. **G4 and G5 are
closed with positive proof.** The two named holes are filled, and three more I named in the
Round-4 amendment are filled too. But the audit's headline — *"0 coverage holes"* — still rests
on a span in which **830 of 861 Sundays were never fetched and never put to the oracle**.
`date_range()` was extended to seven days, and then the seven-day range was only ever *run* over
2026 and over the five Sundays I happened to name by hand. The class G8 identified is not
closed; its five known instances are.

This is one operator command from PASS, and I state below the falsifiable prediction that
command should produce.

## Retraction — Round-4's `2026-02-01` "FALSE POSITIVE" was wrong

I adjudicated 2026-02-01 (Sunday) a backfill artifact on the grounds that its 1m index file
holds 375 bars for a single symbol, and "a real session carries ~200 symbols." The equity
ingest has now fetched the day directly:

- `secfull_20260201.csv` exists, and its `DATE1` column reads **`01-Feb-2026`**.
- **2,507 EQ/BE rows** are in the store for that date, and they passed DeepSeek's new G4
  identity guard (`file_dates == {d}`) — the guard that *exists precisely to reject* NSE's
  habit of serving the previous trading day's file.

NSE published a bhavcopy stamped 2026-02-01. **The market traded**: it is the Union Budget
session, which NSE has run on a non-business day before (2015-02-28 Sat, 2020-02-01 Sat,
2025-02-01 Sat — all in this store). The single-symbol index file was an unrelated BankNifty
backfill artifact that coincidentally named a real trading day. **My Round-4 verdict is
withdrawn: 2026-02-01 was a genuine hole, and the G8 fix caught it.** That makes the Round-4
true-hole count **6, not 5** — and it means the index store's evidence and the day's reality
were two different questions that I collapsed into one.

## Verification performed by the reviewer (evidence, not assertion)

All figures read directly from `equity_bhavcopy.duckdb` and the raw cache.

| # | Check | Result |
|---|-------|--------|
| V1 | Audit determinism | Re-ran `audit_equity_bhavcopy.py` — **byte-identical** to the committed report |
| V2 | G4: `ingest_meta` vs store | **4,097 meta rows vs 4,097 store dates; 0 phantoms, 0 orphans, in both directions.** Was 4,169 vs 4,090. |
| V3 | G4: era days sum | legacy 2,479 + secfull 1,618 = **4,097 = store dates.** They now reconcile. |
| V4 | G5: index witness, positive case | `index_trading_days()` returns 843 days and **accepts 2023-11-12** (11,581 bars / 194 symbols) and 2024-11-01 |
| V5 | G5: index witness, negative cases | **rejects** `2026-02-01` (375 bars, **1** symbol) and `2026-03-03` (197 bars all stamped 2026-03-02) |
| V6 | Oracle liveness, both branches | `focal_20220808.zip` **and** `foudiff_20250305.zip` present — the oracle has now returned `True` on the legacy **and** the UDIFF F&O product |
| V7 | The 6 genuine holes | all in store: 2022-08-08 (1,944 legacy) · 2013-11-03 (1,279) · 2016-10-30 (1,553) · 2019-10-27 (1,613) · 2023-11-12 (2,070 secfull) · 2026-02-01 (2,507 secfull) |
| V8 | `2026-03-03` | **absent from the calendar entirely** — index file rejected, `foudiff_20260303.404`. Correctly a holiday (Holi). The §1/§2 self-contradiction of Round 4 is gone. |
| V9 | Coverage holes, recomputed independently | `trading_calendar ∩ span − store` = **∅**. The report's 0 is arithmetically right. |
| V10 | Mon–Fri non-store days never fo-probed | **0.** Every weekday absence in the span was independently adjudicated. |
| V11 | Saturdays | 861 in span, **861 carry an equity fetch marker**, 847 fo-probed, 14 in store |
| V12 | **Sundays** | 861 in span, **31 carry an equity fetch marker, 26 fo-probed, 5 in store.** **830 Sundays were never fetched and never probed by anything.** |
| V13 | Which Sundays *were* reached | the 5 in the store, plus every Sunday from **2026-01-04 onward**. Nothing between 2010-01-04 and 2025-12-28. |

## Findings

### G8 — MAJOR — carried forward: Sunday reachability is fixed in code, unexercised in evidence
`date_range()` now yields all seven days (`ingest…py:146`) and the docstring names the four
Muhurat Sundays. But `build_trading_calendar` DELETEs/INSERTs only within `[start, end]`, and
`main()` skips any date already holding rows. The seven-day range has therefore only ever *run*
over 2026 plus five hand-picked days (V13). Across **2010-01-04 → 2025-12-28 there are 830
Sundays with no equity fetch marker, no F&O marker, and no calendar row** (V12). A Sunday
session in that window cannot enter the calendar, so it cannot be counted as a hole, so the
audit cannot report it. The report's `0` is silent about them, and §1's Saturday list has no
Sunday counterpart to reveal the asymmetry.

The five Sundays that *are* in the store are there because **I named them in Round 4** and the
operator ingested them by date. That is fixing the instances, not the class — and it is the same
shape as every prior round: a mechanism is built, its positive verdict is never demanded, and
the "0" it produces is read as evidence.

**Fix (one run, mostly cached):** re-run the ingest over the full span. Mon–Sat costs no network
(every day is either in the store or has a cached `.404`); only the 830 Sundays hit NSE — one
equity 404 and one oracle probe each, ~20 minutes at the built-in 0.4 s sleep. The same
invocation rebuilds `trading_calendar` with those Sundays probed.

**Falsifiable prediction.** Muhurat is the only recurring Sunday session NSE holds, and in this
span it fell on a Sunday exactly in 2013, 2016, 2019 and 2023 — all four now in the store — with
2026-02-01 the one budget-session Sunday. **The re-run should therefore surface 0 new holes and
write ~830 `focal_*.404` / `foudiff_*.404` markers.** If it surfaces even one Sunday where the
oracle answers `True` and the equity store is empty, that is a genuine hole and this prediction
is wrong. Either way the claim stops resting on my recall of the NSE calendar and starts resting
on the oracle — which is the entire point of having built one.

### N1 — MODERATE — new: unresolved oracle probes are dropped silently and never persisted
In `build_trading_calendar` (`ingest…py:531-535`), `fo_is_trading` returns `None` on a transient
probe failure; the day is counted into a local `unresolved` and then **simply not added to
`entries`**. A day the oracle could not adjudicate is therefore indistinguishable, in the store,
from a day the oracle confirmed closed: neither appears in `trading_calendar`, so neither can
ever be a coverage hole. `cal_unresolved` is printed to stdout and **written nowhere**; the
audit reads only store tables (correctly, per F7) and so has no way to know it. A run with NSE
throttling would under-report holes and still render the fit-for-purpose language.

This is the F1 failure class — *absence treated as confirmation* — relocated into the oracle's
error path. It is latent today (this store shows 0 Mon–Fri unprobed days, V10) and will bite on
the very re-run G8 requires.

**Fix:** persist unresolved days (a `trading_calendar` row with `source='unresolved'`, or an
`ingest_runs` table); have the audit count them, print them, and **withhold the fit-for-purpose
claim while any exist**. An oracle that shrugged is not an oracle that said no.

### G3-b — MINOR — carried forward: no interior-gap guard
Round 3's fix list included "make `is_slice` (or a new guard) fail on any interior gap."
`is_slice` still keys only on span endpoints and row count (`audit…py:83`), and `_flag_long_gaps`
only escalates at ≥ 90 days. The 913-day void of Round 3 would have tripped it; a 60-day void
would not, and the report would render full-gate language over it. Harmless in the present store
(largest inter-day gap 6 days, V9) — but the guard that would have caught Round 3's defect still
does not exist.

### R5 — MINOR — carried forward: UDIFF remains unexercised in the gate evidence
The era map shows **0 UDIFF rows** — correct behaviour, since SECFULL outranks it and SECFULL is
complete. §2 handles this honestly, but the sentence *"The parser and the SECFULL>UDIFF>LEGACY
order are verified directly"* asserts something the store cannot show and the audit does not
test. Either cite the spot-check artifact, or drop the claim to "unexercised — UDIFF is a
fallback that no day in this store required."

### G5-b — MINOR — the ≥100-symbol rule trades a false positive for a false negative
The new content validation is right, and V5 proves it rejects both Round-4 false holes. Note the
cost: it also rejects `2026-02-01`, which we now know **was a real trading day** (V7). The index
witness would no longer flag that day if the equity store lacked it. The F&O oracle is the
backstop and would have caught it — so the design holds — but the index store is now, by
construction, a witness that can only say "yes" about days with a full cross-section. Worth one
sentence in §1 rather than a code change.

## What is genuinely fixed (verified, preserve)

- **G4 — CLOSED.** The identity guard (`file_dates != {d}` → discard, no rows, no meta) plus the
  phantom purge reconciles `ingest_meta` to the store **exactly** (V2), and the eras now sum to
  the store's date count (V3). The 79 phantom entries are gone. §2's "Trade days" column is
  trustworthy for the first time.
- **G5 — CLOSED.** `index_trading_days()` opens every file, filters bars by `CAST(timestamp AS
  DATE) = filename date`, and requires ≥ 100 distinct symbols. It **accepts the real Muhurat
  session and rejects both artifacts** (V4/V5) — the positive verdict is demanded and produced.
- **The oracle now has a `True` on both of its branches** (V6). Round 3's indictment is not only
  retracted, it is now empirically foreclosed for the UDIFF F&O product too.
- **Round-4's two named re-ingests are done**, plus the three amendment Sundays and 2026-02-01.
- **F1, F5, F6, F7 hold at full scale**; integrity screens remain clean on 7.03 M rows (0 NULL
  OHLC, 0 non-positive close, 0 `high < low`, 0 close outside `[low, high]`, 0 negative volume,
  0 duplicates); **0 prev_close glitches across all 20 continuity symbols**; the audit
  regenerates **byte-identically** (V1).
- The store is contiguous, dev = 2,727 days and sealed = 864 days are both genuinely populated,
  and §4's 35 CA candidates are now a clean corporate-action preview with no gap artefact.

## Path to PASS (one run + two small edits)

1. **N1 first** — persist unresolved probes and make the audit withhold the fit-for-purpose
   claim while any exist. Do this *before* step 3, because step 3 is the run that will generate
   them if NSE throttles.
2. **G8 / R5 / G5-b — doc + guard edits:** add a Sunday-sessions line to §1 alongside the
   Saturday list; soften the UDIFF "verified directly" sentence; optionally add the interior-gap
   guard (G3-b).
3. **Operator: re-run the full-span ingest** (`--start 2010-01-01`). Mon–Sat is served from
   cache; the 830 Sundays are the only network cost.
4. **Re-run the audit.** Expect: 0 coverage holes, ~830 new `.404` markers, `unresolved = 0`,
   and a §1 that says so. On those numbers the Lead Reviewer issues **PASS**.

**Prompts 2–5 remain HELD.** Gate (a) is one run from PASS, and this time the run is what
*produces* the evidence rather than what confirms it.

## Note on the review process (Round 4 self-correction)

Round 4 read a corrupt 1m index file and concluded the *day* was fake. The index store's defect
and the market's calendar are independent facts; I let the first stand in for the second because
the artifact was vivid and the day was a Sunday. The check that settled it — fetch the equity
bhavcopy and read its `DATE1` — was available then and cost one request. Twice now (Round 3's
oracle, Round 4's Sunday) I have inferred a fact about the *world* from a defect in a *witness*.
The general form: **when a witness is broken, that tells you about the witness. Go ask the
world.** DeepSeek's G8 fix asked, and the world answered 2,507 rows.

---

# Round 6 — Re-review after the N1 fix and the full-span Sunday run (2026-07-09)

**Reviewer:** Claude (Lead Reviewer) · **Implementer:** DeepSeek V4
**Trigger:** operator reports the Round-5 fixes (N1 + the full-span re-run that G8 required) are
done. Store is now 7,030,920 rows / 4,099 trade days / 4,132 symbols; audit regenerated and
reports **0 coverage holes, 0 unresolved oracle probes**.

## Verdict: **NOT PASSED — narrowly. Coverage is now genuinely proven; the store contains two trading days on which no equity cross-section exists, and the calendar cannot tell them apart from the other 4,097.**

Round 5's PASS conditions are, on the evidence, **met**: the Sunday class is closed (not just its
instances), the oracle is live on both branches, `unresolved` is persisted and gates the
fit-for-purpose claim, and the audit regenerates byte-identically. **G4, G5, G8 and N1 are all
CLOSED with positive proof.** No further ingest is required — no network.

Two things block PASS, and neither is a coverage defect:

1. **H1 (new, MAJOR)** — the full-span Sunday run correctly discovered two *real* NSE sessions
   (2010-05-16 Akshaya Tritiya, 2012-11-11 Dhanteras) in which **only gold ETFs traded — 7 and 14
   symbols**. They enter `trading_calendar` as ordinary trading days. For a cross-sectional
   momentum program, a day with a 7-symbol cross-section is not a day on which a cross-section can
   be ranked.
2. **R5 (carried forward, MODERATE)** — Round 5 asked that §2's UDIFF sentence be softened or
   evidenced. It was **neither**: it was restated more assertively and tagged `(R5)`, and it now
   contains a claim about the full-span run that the run did not perform.

Both are fixed by a schema column, an audit paragraph, and a deleted sentence.

## Retraction — my own working hypothesis this round was wrong, and I caught it one command short of writing it down

The store gained **+2 trade days but only +21 rows** over Round 5 (7,030,899 → 7,030,920). I
recorded, as a pre-registered doubt before touching the database, that two Muhurat sessions should
add ~1,300–2,600 rows *each*, and that 7- and 14-row days were therefore **phantoms** — that G4's
identity guard had failed and manufactured fake trading days.

That was wrong. I opened the archives instead of reasoning from the aggregate:

```
legacy_20100516.zip -> cm16MAY2010bhav.csv (7 data rows)
    GOLDBEES,EQ,1800,1829.5,1785,1800.6,...,482410,873916640.35,16-MAY-2010
    GOLDSHARE,EQ,...  KOTAKGOLD,EQ,...  QGOLDHALF,EQ,...  RELGOLD,EQ,...
legacy_20121111.zip -> cm11NOV2012bhav.csv (14 data rows)
    AXISGOLD,EQ,...  BSLGOLDETF,EQ,...  CRMFGETF,EQ,...  GOLDBEES,EQ,...
```

Every symbol is a gold ETF. Real OHLC, real volume (GOLDBEES: 482,410 units, ₹87.4 cr turnover),
real ISINs, `TIMESTAMP` equal to the requested date. **2010-05-16 was Akshaya Tritiya; 2012-11-11
was Dhanteras** — NSE runs a special Sunday gold-ETF session on those festivals. The days are
genuine, the payloads are genuine, and **G4's identity guard behaved exactly as designed.**
DeepSeek's G8 fix found two real sessions that this program did not know existed.

The `+21 rows` I flagged as evidence of fraud is `7 + 14` — the exact arithmetic of the discovery.

## Verification performed by the reviewer (evidence, not assertion)

All figures read directly from `equity_bhavcopy.duckdb` and the raw cache.

| # | Check | Result |
|---|-------|--------|
| V1 | Audit determinism | Regenerated audit is **byte-identical** (`md5 75e5ccb25111363dc97907df22898a87`) |
| V2 | Headline | 7,030,920 rows · 4,099 days · 4,132 symbols · 2010-01-04 → 2026-07-09 — matches report |
| V3 | **G8: Sunday reachability** | **861 Sundays in span; 861 carry an equity fetch marker; 0 unreached.** 854 fo-probed (the 7 skipped are the in-store Sundays). Was 31/830-unreached. **Class closed.** |
| V4 | Oracle liveness, both branches | `focal_*.zip` = 1 (2022-08-08) · `foudiff_*.zip` = 1 (2025-03-05); 1,698 + 423 `.404`. Alive, and its `True` is demanded |
| V5 | **N1: unresolved persisted + gates the claim** | `entries[d]="unresolved"` written to `trading_calendar` (`ingest…py:539`); audit excludes them from trading-day counts, prints them, and the fit-for-purpose branch is `elif missing==0 and unresolved==0` with a withholding `else` (`audit…py:353,369`). **0 unresolved in store.** **CLOSED** |
| V6 | G4: `ingest_meta` ↔ store | 4,099 meta dates vs 4,099 store dates; **0 phantoms, 0 orphans, both directions**. Eras sum: legacy 2,481 + secfull 1,618 = **4,099** ✓ |
| V7 | Coverage holes, recomputed independently | `trading_calendar ∩ span − store` = **∅**. The report's 0 is arithmetically right |
| V8 | **Thin-cross-section days** | Exactly **2**: `2010-05-16` (**7** symbols), `2012-11-11` (**14** symbols). The next-smallest day in the entire store is `2013-05-11` at **1,249**. A ~90× cliff |
| V9 | The two days are real | Payloads are gold-ETF-only bhavcopies, correctly dated, with volume and turnover (see Retraction) |
| V10 | Per-symbol day counts diverge | `GOLDBEES` = **4,099** days · `NIFTYBEES` / `BANKBEES` / `LIQUIDBEES` = **4,097** |
| V11 | **The report contradicts itself** | §1 claims **4,099** trade days; §4 lists **4,097** rows for RELIANCE, TCS, HDFCBANK, ICICIBANK, SBIN, ITC, LT and every other full-history symbol. The 2-day discrepancy is visible on the face of the report and is unremarked |
| V12 | `trading_calendar` source mix | **4,099 of 4,099 rows are `equity_store`.** `fo_probe` = 0, `index_1m` = 0, `unresolved` = 0 |
| V13 | Equity UDIFF payloads in cache | **1** (`udiff_20240703.zip`). All other `udiff_*` entries are `.404` markers |
| V14 | UDIFF rows in store | **0** — §2's era map has no UDIFF row |
| V15 | ETF symbols carried in series `EQ` | **200** symbols match `%BEES%` / `%ETF%` / `%GOLD%` |

## Findings

### H1 — MAJOR — new — `trading_calendar` does not model session breadth; a 7-symbol day is indistinguishable from a 1,500-symbol day

The store now contains two days — `2010-05-16` and `2012-11-11` — on which NSE traded **only gold
ETFs** (7 and 14 symbols, V8). They are real sessions and the rows belong in a raw store. But they
are written into `trading_calendar` as bare `(trade_date, source)` rows, identical in kind to the
4,097 full-cross-section days.

`trading_calendar` is the **spine of the whole program**: gates (b)–(e) will key corporate-action
alignment, point-in-time universe membership, lookback windows and rebalance dates off it. A
cross-sectional momentum strategy that lands a rebalance on 2012-11-11 ranks **14 gold ETFs** and
trades them. A "252-trading-day" momentum lookback counted off the calendar spans a different real
window than one counted off the equity cross-section. Neither failure raises an error; both produce
numbers.

The defect is already legible **inside the audit itself** (V11): §1 says 4,099 trade days, §4 says
4,097 rows for every symbol with a full history. Nothing in the report reconciles the two, and §6's
dev (2,728) / sealed (864) day counts silently include both gold days. §1 lists them under
"**Sunday special sessions in calendar (7)**" beside five full sessions, implying a parity that
does not exist — 5 of those 7 carry 1,279–2,507 symbols; 2 carry 7 and 14.

**This is not a coverage defect and does not impugn the ingest.** It is a data-model gap that the
Sunday run *exposed* rather than caused, and it will propagate silently into every downstream gate.

**Fix (no network, no re-ingest):**
- Add session breadth to `trading_calendar` — an `n_symbols` column, or `session_type ∈ {full,
  restricted}` derived from the EQ/BE symbol count.
- Have the audit surface every day below a breadth threshold (~200 symbols) in §1, by name, with
  its symbol count, and reconcile §1's day count against §4's per-symbol row counts.
- Restate the fit-for-purpose claim as what is actually true: **4,097 full-cross-section trading
  days plus 2 restricted gold-ETF sessions**, over 2010-01-04 → 2026-07-09, with zero coverage
  holes.

### R5 — MODERATE — carried forward, and **regressed**: the UDIFF sentence now asserts an event that did not occur

Round 5 wrote: *"Either cite the spot-check artifact, or drop the claim to 'unexercised.'"*
§2 of the regenerated audit reads:

> "The parser and the SECFULL>UDIFF>LEGACY order are verified directly, and UDIFF fills any SECFULL
> gap in the full-span run (R5)."

The clause **"UDIFF fills any SECFULL gap in the full-span run"** describes something the full-span
run did not do. SECFULL has **no gap** in this store, so UDIFF filled **nothing**: it contributed
**0 rows and 0 days** (V14). The sentence asserts a counterfactual as an observed result, and the
trailing `(R5)` reads as a citation *discharging* the finding when the finding is what the sentence
violates. "Verified directly" is likewise unevidenced in the deliverable: exactly **one** equity
UDIFF payload was ever fetched (`udiff_20240703.zip`, V13), and neither the store nor the audit
shows it parsed. The source-preference order *is* correct — it is `ingest_day`'s first-success-wins
loop, verifiable by reading the code — but that is a **structural** guarantee, not a *direct
verification*, and the report should not call it one.

This is the third round in which a mechanism's *design* has been offered where its *positive
verdict* was asked for. The rule this program adopted in Round 3 — **a validator that has never
returned its positive verdict has not been tested** — applies to the sentence describing the
validator too.

**Fix (delete and replace):**
> "UDIFF is a fallback that no day in this store required: SECFULL outranks it and SECFULL is
> complete, so the era map shows 0 UDIFF rows. The parser was exercised once against a live payload
> (`udiff_20240703.zip`) and is otherwise unexercised. The SECFULL > UDIFF > LEGACY order is
> structural (first-success-wins in `ingest_day`), not empirically tested by this store."

### G3-b — MINOR — carried forward (third round): still no interior-gap guard

`is_slice` still keys only on span endpoints and row count (`audit…py:83`), and `_flag_long_gaps`
escalates only at `>= 90` days (`audit…py:391`). Harmless in the present store (largest inter-day
gap 6 days, §1) — but the guard that would have caught Round 3's 913-day void still does not exist,
and a 60-day void would today render full-gate language.

Related and still latent: the STOP-CONDITION text reads *"Operator decision required (charter D5
dev-start may need adjustment)"* (`audit…py:394`). Round 3's **G7** objected to exactly this framing
— it invites moving the research window to fit the defect. G7 was marked resolved in Round 4 because
the *gap* vanished, but the *framing* is unchanged in code and will reappear verbatim the next time
the flag fires. Reverse it: a gap is a data failure until proven otherwise.

### H2 — for gate (c), not a gate (a) defect — 200 ETF symbols live in series `EQ`

`GOLDBEES`, `NIFTYBEES`, `BANKBEES`, `LIQUIDBEES` and **200 symbols** matching `%BEES%`/`%ETF%`/
`%GOLD%` carry `series = EQ` and are present on essentially every trading day (V10, V15). The EQ/BE
scope filter — correct for gate (a), which must retain everything NSE published — does **not**
exclude ETFs. A cross-sectional *equity* momentum universe must exclude them at gate (c), and
`LIQUIDBEES` in particular (a cash-proxy fund with near-constant NAV) would rank pathologically in
any momentum sort. Recording it here so gate (c) inherits the constraint rather than rediscovering
it. Not a blocker.

### G1 — residual, MINOR — the store's own days are never challenged

`trading_calendar` is **100% `equity_store`** (V12): `fo_probe` = 0, `index_1m` = 0. This is the
correct *arithmetic* consequence of a complete store — a day present in the store cannot be a
coverage hole, so it is excluded from probing — and §1 now discloses the mix, which is what Round 4
asked for. The disclosure is done.

The residual is unchanged and worth one line: because store days are never put to the oracle, the
gate's independent witness has **no opportunity to contradict the store**, only to fill its
absences. Had 2010-05-16 been oracle-probed, F&O would almost certainly have 404'd (no derivatives
trade in a gold-ETF session) — and the disagreement *"equity present, F&O absent"* is precisely the
signal that would have surfaced H1 automatically. A cheap future hardening: probe a random sample of
store days and flag disagreement. Not a blocker for gate (a).

## What is genuinely fixed (verified — preserve)

- **G8 — CLOSED, class not instance.** 861/861 Sundays carry an equity fetch marker; 0 unreached
  (V3). Round 5's falsifiable prediction — *"the re-run should surface 0 new holes and write ~830
  `.404` markers"* — **held**, and the run additionally surfaced two genuine sessions nobody had
  named. This is the first round in which a mechanism was run over its whole domain rather than over
  the days a reviewer happened to list.
- **N1 — CLOSED.** Unresolved probes are persisted to `trading_calendar`, excluded from trading-day
  counts, printed, and the fit-for-purpose claim is *withheld* while any exist (V5). Absence no
  longer reads as confirmation.
- **G4 — CLOSED and re-confirmed at the new scale.** `ingest_meta` reconciles exactly to the store
  in both directions, 0 phantoms / 0 orphans, eras sum to 4,099 (V6). The identity guard correctly
  *admitted* two unusual-but-valid payloads while still rejecting misdated ones — the harder half of
  the test.
- **G5 — CLOSED.** Index witness validates by file contents; accepts the real Muhurat session,
  rejects both artifacts.
- **Oracle has a `True` on both branches** (V4) and is demanded, not assumed.
- **F1, F5, F6, F7 hold at full scale.** Integrity screens clean on 7.03 M rows; 0 `prev_close`
  glitches across all 20 continuity symbols; store contiguous (largest gap 6 days); audit
  regenerates byte-identically (V1).
- §4's note that NSE publishes `prev_close` as the **raw** prior close — so the chain survives splits
  and bonuses, and a non-zero glitch count means a genuine data error rather than a corporate action
  — is a correct and genuinely useful piece of analysis that was not in any prior round.

## Path to PASS (no network, no re-ingest — two edits and a schema column)

1. **H1** — add session breadth to `trading_calendar` (`n_symbols` or `session_type`); have the
   audit name every sub-threshold day with its symbol count in §1; reconcile §1's day count with
   §4's per-symbol row counts; restate the fit-for-purpose claim as **4,097 full-cross-section days
   + 2 restricted gold-ETF sessions**.
2. **R5** — delete the UDIFF sentence; replace with the honest version above.
3. **G3-b** — add the interior-gap guard; reverse the STOP-CONDITION framing (data failure, not
   window adjustment).
4. Re-run the audit. Expect 0 coverage holes, 0 unresolved, 4,099 calendar days of which **4,097 are
   full sessions**. On those numbers the Lead Reviewer issues **PASS**.
5. Carry **H2** (ETF exclusion) into the gate (c) prompt as an inherited constraint.

**Prompts 2–5 remain HELD.** Gate (a)'s *data* is, on this evidence, fit for purpose; what remains
is making the calendar and the report say what the data actually shows.

## Note on the review process (Round 6 self-correction)

I opened this round by pre-registering, as fact, that the two new days were phantoms manufactured by
a failed identity guard. The arithmetic that convinced me (`+2 days, +21 rows`) was real; the
inference was not. **One command — `unzip` — refuted it.** Rounds 3 and 4 ended with the same
lesson stated two ways: *verify the mechanism before indicting it*, and *when a witness is broken,
go ask the world*. Round 6 adds the third face of the same coin: **when an aggregate looks wrong,
open the payload.** A row count is a summary of evidence, not the evidence.

Three rounds running, a reviewer inference from an aggregate has been wrong — and each time the
refuting check cost one command. The difference this round is only that the check came *before* the
finding was written. That ordering is the whole discipline, and it is worth more to this program
than any individual finding: **the two "phantom" days were the most valuable thing the full-span run
produced.** Had I filed the phantom finding, DeepSeek would have deleted two real NSE sessions and
"fixed" a guard that was working, and H1 — the defect that would actually have corrupted gate (e) —
would have shipped inside the correction.

---

# Round 7 — Re-review after the H1 / R5 / G3-b fixes, with reviewer remediation (2026-07-09)

**Reviewer:** Claude (Lead Reviewer) · **Implementer:** DeepSeek V4
**Trigger:** operator reports another round of fixes and — departing from the standing charter role
split — **explicitly authorized the reviewer to apply remedial steps**: *"if you think theres still
errors, then you are free to the remedial steps."*

## Verdict: **PASS — conditional on independent confirmation of the three edits the reviewer made himself (§Reviewer remediation).**

DeepSeek's Round-6 fixes are real and verified against the store, not against the report that
describes them. **H1's core, R5 and G3-b are CLOSED.** I found two further defects plus one latent
one, and — under the operator's explicit authorization — fixed them in the **generator script**,
never by hand-editing the generated Markdown, so the artifact remains reproducible. The audit
regenerates byte-identically across two consecutive runs after the change.

Gate (a)'s data was already fit for purpose at Round 6. What remained was making the calendar and
the report say what the data shows. They now do.

## Verification of DeepSeek's Round-6 fixes (evidence, not assertion)

| # | Check | Result |
|---|-------|--------|
| W1 | **H1: `n_symbols` column exists and is trustworthy** | `trading_calendar(trade_date, source, n_symbols)`. **4,099 rows, 0 NULL, 0 mismatched** against the actual store cross-section (`tc.n_symbols <> count(eb.symbol)` returns no rows). Not merely present — *correct* |
| W2 | H1: restricted days identified | Exactly 2: `2010-05-16` (7), `2012-11-11` (14). Matches V8 of Round 6 |
| W3 | **G3-b: interior-gap guard exists and can fail** | `INTERIOR_GAP_DAYS = 14` (`audit…py:42`); `if worst_gap > INTERIOR_GAP_DAYS: fail.append(...)` (`:412`) — it **withholds the fit-for-purpose claim**, it does not merely print. Round 3's 913-day void would now hard-fail |
| W4 | G7 framing | The *"charter D5 dev-start may need adjustment"* STOP-CONDITION text is **gone from the code entirely**. The framing objection is resolved by deletion |
| W5 | **R5: the false UDIFF sentence** | Replaced, near-verbatim with the Round-6 prescription: *"UDIFF is a fallback that no day in this store required… exercised once against a live payload (`udiff_20240703.zip`)… The SECFULL > UDIFF > LEGACY order is structural…, not empirically tested by this store."* **CLOSED** |
| W6 | §4 reconciliation | The 4,097-vs-4,099 discrepancy I flagged (Round-6 V11) is now stated and explained in §4 |
| W7 | Determinism | Audit regenerates **byte-identical** before and after my edits (two consecutive runs) |

## Findings — three defects remaining after DeepSeek's round

### H1-b — MODERATE — the fix reached §1 and §4 but not §6, the one place a downstream gate reads window sizes

§6 rendered `Dev-window (2012–2022) days: **2728**` — the raw calendar count, computed from
`equity_bhavcopy` and therefore **including the restricted `2012-11-11`**. Verified directly:

```
dev     total=2728  full-session=2727  restricted=1
sealed  total=864   full-session=864   restricted=0
```

The fit-for-purpose sentence then claimed no coverage hole *"across the dev (2728 days) and sealed
(864 days) windows."* H1's entire premise is that a restricted day is not a rankable day; §6 was
still counting one. A gate-(e) author sizing a walk-forward off `2728` would be off by exactly the
day H1 exists to exclude. **Fixed** — §6 now reports full-session counts with the calendar total in
parentheses: `Dev-window (2012–2022) full-session days: 2727 (of 2728 calendar days)`.

### H3 — MAJOR (latent) — a genuine coverage hole would render as a benign "restricted session"

`build_trading_calendar` writes `n_symbols = 0` for a calendar day **absent from the store** —
i.e. for a genuine coverage hole (`ingest…py:551-556`, *"0 for non-store trading days (coverage
holes)"*). The audit's restricted filter was:

```python
restricted = [... if r[1] != "unresolved" and r[2] is not None and r[2] < RESTRICTED_THRESHOLD]
```

A hole (`n_symbols = 0`) satisfies `is not None and < 200`. It would therefore have been printed in
§1's **"Restricted sessions"** table — described to the reader as *"real NSE trading days, correctly
ingested raw"* — rather than as the hole it is.

This is the **F1 failure class**, fourth appearance: *absence rendered as confirmation*. It is
dormant today only because the store has zero holes, which is precisely the condition under which
nobody would notice. It would have fired on the first genuine hole the gate ever caught.

**Fixed** — the predicate is now `0 < r[2] < RESTRICTED_THRESHOLD`, and `n_symbols == 0` is
documented at the constant as *"a coverage hole, not a restricted session."*

**Falsifiable prediction, stated before the check and confirmed:** on synthetic rows including a
`fo_probe` day with `n_symbols = 0`, the old predicate lists it as restricted and the new one does
not, while neither counts it as a full session.

```
OLD predicate -> restricted: [('2012-11-11', 14), ('2022-08-08', 0)]   # hole misclassified
NEW predicate -> restricted: [('2012-11-11', 14)]                      # hole excluded
hole counted as full session? False                                    # remains a hole
```

### H4 — MODERATE — the audit fabricated a calendar fact from a row count

§1's restricted table rendered its `Session` column as:

```python
w(f"| {d} | {n} | " + ("Gold-ETF Muhurat" if n < 20 else "Restricted"))
```

**The festival label was a function of the symbol count.** `n < 20` → *"Gold-ETF Muhurat"*. The
store has no knowledge of the Hindu calendar, and the label is wrong for both days: `2010-05-16` was
**Akshaya Tritiya** and `2012-11-11` was **Dhanteras**. Neither is Muhurat — and the genuine Muhurat
Sundays (`2013-11-03`, `2016-10-30`, `2019-10-27`, `2023-11-12`) sit unlabelled twelve lines below
in the same section. A gate artifact was inventing calendar facts, and would have kept inventing
them for any future day that happened to trade fewer than 20 symbols.

**Fixed** — the column is replaced with the weekday and the instruments the store actually recorded,
so the gold-ETF claim is *shown* rather than asserted:

| Date | Weekday | Symbols | Instruments traded (from the store) |
|------|---------|--------:|-------------------------------------|
| 2010-05-16 | Sun | 7 | GOLDBEES, GOLDSHARE, KOTAKGOLD, QGOLDHALF, RELGOLD, RELIGAREGO, … (+1) |
| 2012-11-11 | Sun | 14 | AXISGOLD, BSLGOLDETF, CRMFGETF, GOLDBEES, GOLDSHARE, HDFCMFGETF, … (+8) |

No festival is named anywhere in the deliverable. The word "Muhurat" no longer appears in the audit
body or the script.

## Reviewer remediation — disclosure and the conflict it creates

Under the operator's explicit authorization I made three edits, **all in
`scripts/csmp/audit_equity_bhavcopy.py`**, none in the generated report:

1. Hoisted `RESTRICTED_THRESHOLD = 200` to a module constant, documenting that `n_symbols == 0` is a
   hole, not a session.
2. `0 < n < RESTRICTED_THRESHOLD` in the restricted filter (**H3**); added `dev_full` / `sealed_full`
   and rendered them in §6 (**H1-b**).
3. Replaced the count-derived festival label with store-derived instrument names (**H4**).

The generated Markdown was **never hand-edited** — that would sever the artifact from its generator
and destroy the reproducibility the gate rests on. `python -m py_compile` is clean; the audit
regenerates byte-identically across two consecutive runs.

**This is a conflict of interest and I am flagging it rather than burying it.** The charter's role
split (DeepSeek implements, Claude reviews) exists so that no one both writes and blesses the same
code. The operator suspended it for this round, which is their call — but the consequence is that
**three edits in the gate's evidentiary tooling have had no independent reader.** They are small,
covered by a stated-in-advance falsifiable prediction (H3) and by a determinism check, but "small and
tested by its author" is the exact epistemic position this program has correctly refused to accept
five rounds running. **The PASS is conditional on DeepSeek or the operator reading those three
edits.** If that is not going to happen, the honest verdict reverts to NOT PASSED.

## Carried forward — not blockers

- **H2 — gate (c) inherits it.** 200 symbols matching `%BEES%`/`%ETF%`/`%GOLD%` carry `series = EQ`.
  A cross-sectional *equity* universe must exclude them; `LIQUIDBEES` (a cash proxy with near-constant
  NAV) would rank pathologically in any momentum sort. This must appear in the gate (c) prompt.
- **G1 residual — MINOR.** `trading_calendar` remains 100% `equity_store`; store days are never put to
  the oracle, so the independent witness can fill the store's absences but never contradict its
  presences. Cheap future hardening: probe a random sample of store days and flag disagreement. Note
  that this is exactly the check that would have surfaced H1 automatically.
- **Stale cross-reference.** `docs/reports/CSMP_IMPLEMENTATION_PROMPTS.md:103` still reads *"Gate (a)
  is NOT PASSED (Round 4…)"*. It should be refreshed before the next prompt is issued.

## Disposition

- **Prompt 1 (Gate a): PASS**, conditional on an independent read of the three reviewer edits above.
  Final numbers: 7,030,920 rows · 4,099 calendar days · **4,097 full-session trading days** + 2
  restricted gold-ETF sessions · 0 coverage holes · 0 unresolved oracle probes · largest interior gap
  6 days · integrity screens clean on 7.03 M rows · audit byte-identically reproducible.
- **Prompts 2–5: RELEASED** once that independent read is done. Gate (b) must inherit **H2**.

## Note on the review process (Round 7)

Rounds 3–6 each ended with a reviewer error traced to trusting a summary over the thing summarized:
an aggregate of oracle responses, a corrupt witness file, a row count. Round 7's two substantive
findings are the same error committed by the *implementer* and caught in the artifact: §6 trusted a
`COUNT(DISTINCT trade_date)` over the session-breadth column that had just been added to correct it,
and §1 derived a festival name from a row count because the number was small.

The pattern across seven rounds is now unmistakable and worth stating plainly for gates (b)–(e):
**every defect this program has produced has been a number standing in for the evidence it
summarized.** The fix has never once required more data — only opening the payload the number came
from. H3, the one defect here that could still have corrupted a future gate, was invisible in every
number the audit printed and visible immediately in the predicate that produced them.

---

# Round 8 — Closure: the Round-7 condition is discharged; PASS is final (2026-07-10)

**Reviewer:** Claude (Lead Reviewer) · **Trigger:** operator reports the independent read that
Round 7's conditional PASS required — a review of the three reviewer-made edits in
`scripts/csmp/audit_equity_bhavcopy.py` (H1-b, H3, H4) — was performed by a separate reviewer
(Claude Opus) in a prior session. The edits were not authored by that reviewer, so the
independence the condition demanded is satisfied.

## Disposition: **Gate (a) — PASS (final, unconditional)**

Final gate-(a) evidence, unchanged from Round 7: 7,030,920 rows · 4,099 calendar days ·
**4,097 full-session trading days** + 2 restricted gold-ETF sessions · 0 coverage holes ·
0 unresolved oracle probes · largest interior gap 6 days · integrity screens clean on 7.03 M
rows · audit byte-identically reproducible (`md5 75e5ccb25111363dc97907df22898a87` lineage,
re-verified at Round 7 W7).

- **Prompt 2 (gate b) is RELEASED and ISSUED** as of this date
  (`CSMP_IMPLEMENTATION_PROMPTS.md` — the stale Round-4 cross-reference there is fixed in the
  same edit). Prompts 3–5 remain held pending sequential reviews, per the charter.
- **Inheritances, recorded for the downstream gates:**
  - **H2 → gate (c):** 200 ETF symbols carry `series = EQ`; the equity momentum universe must
    exclude them (`LIQUIDBEES` would rank pathologically).
  - **Restricted sessions → gates (b)–(e):** `trading_calendar.n_symbols` exists and is
    verified; any day-pair or window logic must key on **full sessions** (n_symbols ≥ 200), not
    bare calendar rows.
  - **G1 residual (optional hardening):** store days are never put to the F&O oracle; a random
    sample probe would let the independent witness contradict the store, not just fill it.
  - **Process rule for every remaining gate:** a validator that has never returned its positive
    verdict has not been tested, and a number may not stand in for the evidence it summarizes.
