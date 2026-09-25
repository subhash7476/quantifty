# TS Basis Daily Combo — Paper Spec

**Branch:** `paper/ts-daily-combo` (from `main` @ `2f18388`)
**Status:** SPEC — build starts only on operator approval of this document.
**Sleeve status reminder:** TS Basis Daily is research-only by operator decision 2026-08-01.
This spec authorizes PAPER execution only. No LIVE, no capital, no sealed read.

---

## 1. Combo definition

On each formation date, from the Q1/Q5 legs in `ts_facts.duckdb:carry_facts`, keep:

| # | Filter | Rule | Source column | Threshold provenance |
|---|---|---|---|---|
| F1 | Recovery | drop leg if `basis_reverting = TRUE` | `carry_facts.basis_reverting` (written by `apply_recovery_filter.py`, \|z\|>0.7 + dislocation shrinking) | In-repo, PROMOTE verdict 2026-07-28 (`TS_BASIS_DAILY_RECOVERY_FILTER_VALIDATION.md`) |
| F2 | Conviction | keep leg only if `ABS(z) > 0.70` | `carry_facts.z_carry_neut` (clamped z_ts) | Sleeve's own TRAIN terciles (<0.30 weak / 0.30–0.70 mid / >0.70 strong); backtested as-investigated Jul–Sep 2026 (+24.57% vs +11.70% unfiltered) |

Both must pass (AND). Dropped names get **no replacement**. Empty leg contributes 0 that day
(backtest Jul–Sep: zero empty-leg days; live may differ — see §4).

**Book:** quintile legs as filtered (avg ~26L/29S in backtest), equal-weight per leg,
half-gross per side. **No TP exit, no sector cap** — faithful to the backtested evidence.
The existing forward runner's top-5 + TP@0.5% + sector-cap-2 config is NOT used here.

---

## 2. Data-flow map

**Read-only (never written by this work):**

- `data/signal_engine/ts_basis_daily/ts_signals.duckdb` — signal store (frozen builder)
- `data/signal_engine/ts_basis_daily/ts_facts.duckdb` — facts incl. `z_carry_neut`,
  `quintile`, `eligible`, `raw_z`, `basis_reverting`
- `data/market_data/futures_bhavcopy.duckdb` — execution prices / ADV
- `scripts/signal_engine/ts_basis_daily/build_ts_basis_daily.py`,
  `publish_facts.py`, `apply_recovery_filter.py` — frozen research pipeline,
  reused unmodified (forward runner already refreshes facts + recovery flag)

**Written:**

- `data/paper/ts_daily_combo/combo_paper.duckdb` — the combo's own state + P&L
  store (amendment A2). `production.duckdb` is **not** written.
- New branch files only (§3). No frozen file modified.

---

## 3. Paper wiring

1. **`core/execution/portfolio/carry_rebalancer.py`** — three optional hook params,
   defaults preserve current behavior exactly:
   - `min_abs_z: Optional[float] = None` — drop facts with `ABS(z) <= min_abs_z`
     (applied on the clamped `z_carry_neut`, same field as backtest).
   - `exclude_reverting: bool = False` — drop facts with `basis_reverting TRUE`.
   - `legs_by_quintile: bool = False` — pick legs from the stored Q5/Q1 and size
     each to half gross via `compute_quintile_combo_book` (equal-weight,
     ADV-capped, backtest-exact), instead of the rank-based 20% cut.
   - Applied post-`eligible`, pre-ADV/`_load_fwd_names`, inside `_execute`.
   - `compute_target_book` unchanged; generic pre-rank filtering via
     `apply_signal_filters` remains available when `legs_by_quintile=False`.
2. **New `scripts/ts_basis_daily_combo_forward.py`** — thin forward runner:
   `min_abs_z=0.7`, `exclude_reverting=True`, `legs_by_quintile=True`,
   `max_positions_per_leg=None`, no exit policy, no sector cap,
   `signals_db_path=None` (live-edge guard — see build report §2). *Superseded by
   A2:* identity and state live in `combo_paper.duckdb`, not a per-date
   `production.duckdb` run.

> **Amendment A1 (build-time, 2026-09-24):** spec v1 said "combo runner passes
> `nq=None` (quintile)". Measured on 5 dates, pre-rank filtering (20% cut on the
> filtered pool) reproduces only ~50% of the backtested legs and forces symmetric
> legs (e.g. 09-23: 24L/24S vs backtested 35L/38S; 07-30: 8L/8S vs 2L/32S) —
> because conviction drops the weak middle ~40% before the cut. `legs_by_quintile`
> + `compute_quintile_combo_book` implements the backtest-exact path (filter
> within stored Q1/Q5, variable leg sizes, equal-weight per leg). Dry-run legs
> match the backtest leg sets exactly (09-24: 8L/25S = 33 combo-pass legs).
3. **New `tests/portfolio/test_combo_filter.py`** — unit tests: threshold boundary
   (0.70 excluded, >0.70 kept), reverting exclusion, AND-combination, empty-leg
   passthrough, defaults-unchanged (existing 44 carry tests must stay green).

> **Amendment A2 (review fixes, 2026-09-25 — `TS_BASIS_DAILY_COMBO_BUILD_REVIEW.md`):**
> - **B1:** the hook re-reads its formation calendar (`reload_calendar()`) after
>   every signals/facts refresh; a refresh failure blocks trading for that cycle.
> - **B2:** state and P&L persist in `combo_paper.duckdb`
>   (`core/execution/portfolio/combo_paper_store.py`): held book, executed trades,
>   and per-formation P&L recorded twice — **futures** close-to-close (nearest
>   contract expiring after the mark date, priced at both ends: tradeable) and
>   **spot** `fwd_ret_1m` (research scoring: backtest-comparable). One stable
>   record: the runner resumes from the last persisted book (`hook.restore`), and
>   a restart after downtime catches up missed formations in order. Short-lived
>   connections: another process can read between writes with a **bounded retry**
>   (DuckDB file lock) — a prerequisite for any page panel. Futures marks use the
>   nearest contract expiring after the mark date (differs from the signal's T-3
>   roll in the last ~3 sessions; no roll cost charged).
> - Run identity moves from per-UTC-date `run_id` in `production.duckdb` to the
>   dedicated store (removes the same-day-restart overwrite/duplicate defect).

Validation before handover: `--dry-run --store <scratch>` pass against live
facts + store row check (A2). The supervised launch command is recorded in §5
of the build report; no daemon is left running by the builder.

---

## 4. Guardrails

- PAPER mode only (`ExecutionMode.PAPER`, `PaperBroker`). No LIVE path added.
- Sealed window untouched: no new reads of `run_sealed.py`-governed data; forward
  data only (formation dates > build date).
- Empty books go **flat** (operator decision 2026-09-25): if one filtered leg is
  empty that leg is closed and the other traded; if both are empty the whole held
  book is closed. The `len(facts) < 5` skip applies only to the rank-based path,
  not to `legs_by_quintile` (a 1–4-name combo book trades, as in the backtest).
- **Sealed-window disclosure:** the combo's 59-formation evidence window
  (2026-07-01 → 09-22) overlaps TS Basis Daily's preserved SEALED window —
  14 formations to `run_sealed.py`'s `SEALED_HI` 2026-07-20, 18 to the documented
  07-24 — including best day 07-08. "Sealed window untouched" holds for forward
  paper only, not for the data the thresholds were chosen on.
- Backtest caveat carried forward: combo evidence is 59 in-sample days, July-heavy
  (25.5pp of 33.3pp), with 2–7-name long legs on the best days. Paper is the
  confirmatory surface, not a promotion.
- Research-only status unchanged: paper P&L informs; it does not promote the sleeve.

---

## 5. Acceptance (first paper days)

- Hook + runner + tests merged on this branch, 44 existing tests green + new tests green.
- `--dry-run --store <scratch>` records one row per new formation with sane legs
  (non-empty, quintile-shaped, filtered counts ≈ backtest pass rates).
- Build report (`docs/reports/ts_basis/TS_BASIS_DAILY_COMBO_BUILD_REPORT.md`)
  records: diff summary, dry-run evidence, launch command, and the combo mechanics
  report (§6).
- **Report on how the combo works** (operator-requested): filter economics
  (why reverting + conviction combine), July–Sep evidence recap with concentration
  autopsy, live behavior to watch (pass rates, turnover, leg sizes). Written after
  build validation, before any supervised launch.

---

## 6. Out of scope

LIVE trading, capital sizing, sealed reads, changes to signal construction
(`build_ts_basis_daily.py`, `publish_facts.py`, `apply_recovery_filter.py`),
changes to `production.duckdb` schema, any other sleeve.
