# TS Basis Daily Combo — Build Review

**Branch:** `paper/ts-daily-combo` @ `82432d0` (1 commit over `main` @ `2f18388`)
**Reviewed:** 2026-09-25 · **Scope:** `carry_rebalancer.py` diff, `ts_basis_daily_combo_forward.py`,
`test_combo_filter.py`, spec / build / mechanics reports.
**Verdict:** **NOT READY TO LAUNCH.** The hook changes and tests are sound, but the forward runner
cannot produce a continuous forward record. The combo's validate/kill criteria (mechanics report §5)
depend on that record, so they cannot be evaluated.

Tests: `tests/portfolio/` **56/56 green** (45 existing + 11 new).

---

## BLOCKING

### B1 — The running daemon never trades a formation date published after startup

`CarryRebalancerHook._load_calendar()` runs **only** in `__init__` (`carry_rebalancer.py:528`;
there is no other call site). The runner builds the hook *before* `_refresh_signals()` / `_refresh_facts()`.
When `refresh_if_exhausted()` loads new bhavcopy, the loop refreshes facts and `continue`s with the
**same hook**. `__call__` then returns `False` for the new date because it is not in `_formation_dates`.

**Proof** (scratchpad script, tmp facts DB): build the hook, insert a row for a new `formation_date`,
then call the hook on that date. Result: `new date in calendar: False`, `hook fires on new date: False`.

The dry-run could not catch this, because 2026-09-24 already existed in facts at startup. The defect is
inherited: `ts_basis_daily_forward_runner.py` has the same construct-then-refresh order (lines 188/196).
It still blocks this launch.

### B2 — No P&L is persisted, and state does not survive a restart

- The combo sink writes only `rebalance_summary` and `rebalance_positions`. **Nothing writes `equity_curve`**,
  in either this runner or the sibling runner.
- `signals_db_path=None` also means `_update_position_pnl` never runs. That is correct for the live edge,
  but it leaves no P&L path at all.
- `load_db_state=False`, so the PaperBroker state dies with the process.

Put B1 and B2 together: the only way to trade new dates is a daily restart. Each restart begins from
a flat broker and rebuilds the full book as fresh OPENs. The result is disconnected one-day books with
entry fees charged every day. That is not a forward record, and `production.duckdb` cannot answer
"forward net > 0 over an expiry cycle".

---

## MEDIUM

### M1 — Restarting on the same day overwrites the summary and duplicates positions

`run_id` is keyed on the UTC date. Here is what happens on a same-day restart:
- `run_metadata` and `rebalance_summary` use `INSERT OR REPLACE`, so the earlier row is silently overwritten.
- `rebalance_positions` has no primary key, so its rows are appended as duplicates. This is why the
  build report had to delete stale rows by hand.

The determinism hash then covers a mixed row set.

### M2 — The spec and the implementation disagree on the skip and hold rules (operator to decide)

- **`len(facts) < 5` skip:** spec §4 says the rule "stays". The `legs_by_quintile` branch bypasses it,
  so a book with one name will trade.
- **Both legs empty:** the hook `return`s before `rebalance_book`, so **yesterday's full book is held**.
  The backtest convention is flat (0 contribution). A single empty leg does close correctly, because
  `rebalance_book` closes held names that are missing from the target. The both-empty case is the odd one out.
- The same "hold on skip" behaviour applies to the pre-existing `< 5` path, the margin-check failure,
  and the ADV filter emptying the book.

### M3 — Governance: part of the evidence window lies inside the preserved SEALED window

The combo thresholds and the "+33.32%" evidence come from 59 formations dated 2026-07-01 → 09-22.
TS Basis Daily's SEALED window, declared "preserved unspent", ends at:
- **2026-07-20** in `run_sealed.py` (`SEALED_HI`): **14 of the 59 formations** fall inside it.
- **2026-07-24** in `run_sealed.py` prose and in CLAUDE.md: **18 of the 59** fall inside it.

July carries 25.5pp of the 33.3pp. One of the best days, **07-08 (+3.54% on 5 longs)**, is inside the
sealed window.

Spec §4's "Sealed window untouched" is true of **forward paper**. It is not true of the data the combo
was chosen on. The sleeve is research-only and nothing is being promoted, so this is a disclosure fix,
not a code fix. The `07-20` vs `07-24` inconsistency inside `run_sealed.py` should be resolved on its own.

### M4 — The quintile branch of `_execute` has no test

The new tests cover `apply_signal_filters`, `compute_quintile_combo_book`, and parameter storage. The
`legs_by_quintile` wiring in `_execute` has no test. That wiring is Q1/Q5 selection, `facts_full` sync
through the ADV filter, and the hold-on-empty behaviour. Its only coverage is one dry-run date.

---

## LOW

- **L1 — "Backtest-exact" holds for leg membership, not sizing.** `rebalance_book` applies `BAND_SIGMA`
  suppression to SCALE_UP/DOWN. When leg counts change day to day (e.g. 8 → 25 longs), held names keep
  stale caps inside the band. The daily equal-weight backtest had no band. The dry-run started from an
  empty book, so it never exercised this.
- **L2 — Cap-then-rescale defeats the ADV cap on thin legs.** On a 2–3-name leg, rescaling to half gross
  lifts names above `ADV_CAP_FRAC × ADV`. This is documented in the test and shared with `compute_target_book`,
  but it matters most exactly on the skeletal-leg days the mechanics report highlights.
- **L3 — Refresh failures are ignored.** The return values of `_refresh_signals()` and `_refresh_facts()`
  are discarded, so a failed build trades stale facts silently. This is the CLAUDE.md pitfall
  "freshness printed, never asserted".
- **L4 — Stale documentation.**
  - The build report §1 heading says "uncommitted", and §5 says "No commit made". Both are false after `82432d0`.
  - The runner docstring still says "quintile book (nq=20%)", which A1 superseded.
  - The spec §3 test list still describes the pre-A1 design.
- **L5 — `compute_quintile_combo_book` stamps `formation_date=date.today()`** instead of the actual
  formation date. This matches the existing `compute_target_book`. It is cosmetic today, because `_execute`
  re-wraps the book with `fdate` before calling the sink (`carry_rebalancer.py:671`). Any future direct
  reader of `.formation_date` would get the wrong date.

## Confirmed correct

- The filter semantics: `|z| > 0.7` is strict, `reverting=None` is treated as not reverting, filters combine
  with AND, and the defaults are identity. Every existing call site is unchanged when the new parameters are left at their defaults.
- `facts_full` stays in sync with `facts` through the ADV and forward-name filters.
- Finding F-live about the sibling runner is **correct**. `_load_fwd_names` documents itself as
  historical-replay-only, and `ts_basis_daily_forward_runner.py:188` passes `signals_db_path`.
  The plain forward runner therefore drops every name at the live edge.
- Frozen research files are untouched, and the `production.duckdb` schema is unchanged.

## Required before launch

1. **B1:** reload the calendar on refresh. Either expose `hook.reload_calendar()` and call it after
   `_refresh_facts()`, or read `formation_date` membership lazily in `__call__`. Add a test that inserts a
   date after construction.
2. **B2:** persist equity and P&L, either through the `equity_curve` writer from the broker's mark-to-market
   or from forward returns joined after the fact. Also decide how state resumes across restarts, or make
   the runner a single long-lived process with an explicit resume path.
3. **M2:** the operator picks flat or hold for empty and sub-5 books, and the spec §4 wording is updated
   to match the code.
4. **M3:** add the sealed-overlap disclosure to the spec §4 and mechanics §2 caveats.
5. **M1 and L3–L4:** these can travel with the fixes above.

---

## Outcome — fixes applied 2026-09-25 (spec amendment A2)

| Item | Status |
|---|---|
| B1 calendar | **Fixed.** `hook.reload_calendar()` after every refresh; a failed refresh blocks that cycle (also closes L3). Test: `TestCalendarReload`. |
| B2 P&L + resume | **Fixed.** `combo_paper_store.py` holds book/trades/daily P&L (futures + spot); runner resumes via `hook.restore`, catches up missed formations, `__call__` skips dates ≤ last processed. Tests: `TestResume`, `TestBookReturns`, `TestComboPaperStore`. |
| M1 restart duplicates | **Fixed** by B2 — date-keyed DELETE+INSERT in one transaction; `production.duckdb` no longer written. |
| M2 empty books | **Operator: go flat.** Both-legs-empty now closes the held book (`TestFlatOnEmpty`); sub-5 skip stays rank-path only (spec §4). |
| M3 sealed overlap | **Disclosed** in spec §4. `SEALED_HI` 07-20 vs 07-24 inconsistency left for the operator. |
| L4 stale docs | Fixed (build report §1/§5, runner docstring, mechanics). |
| M4, L1, L2, L5 | Open. |

**New findings while fixing:**
- **2026-09-24 was not an expiry day.** The near expiry is 2026-09-29, the last Tuesday. The build report's expiry-compression explanation is withdrawn.
- **The backtest headline appears to be a leg spread.** The "+33.32%" compounds the long-minus-short leg spread, which is about 2× the return on gross (mechanics §2 caveat).

**End-to-end check (scratch store, real data, `--no-refresh`).** The store was seeded as flat after 09-21. The runner resumed, then traded and marked each date:

| Formation | Book | Trades | Futures P&L (Rs) | Spot P&L (Rs) | Costs (Rs) |
|---|---|--:|--:|--:|--:|
| 09-22 | 40L/29S | 69 | 0 | 0 | 7,963 |
| 09-23 | 35L/38S | 122 | +10,852 | +19,937 | 14,143 |
| 09-24 | 8L/25S | 96 | +72 | +18,416 | 14,981 |

- Every name was priced in both series.
- Cumulative net on the futures series was −26,163.
- A second run processed 0 formations and wrote no duplicates.

Tests: 66/66 in `tests/portfolio/`.
