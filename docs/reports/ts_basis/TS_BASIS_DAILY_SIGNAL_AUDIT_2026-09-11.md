# TS Basis Daily — Signal Audit (2026-09-11)

**Scope:** every row in `data/signal_engine/ts_basis_daily/ts_signals.duckdb` (485,520 rows, 2,610
formations, 2016-02-11 → 2026-09-09), the facts store built from it, and the top-5 LONG/SHORT books
that `ts_basis_daily_signals.py`, `ts_basis_daily_options.py` and `/ts-basis-daily/` publish.

**Method:** (1) a full from-scratch rebuild with the committed code into a scratch directory, diffed
row-by-row and book-by-book against the live incrementally built store; (2) mechanism attribution:
each diverging row is re-priced under the near and next contract from the futures store; (3) a
determinism test that re-publishes facts four times from identical signals; (4) direct checks of the
ADV join, the run path and the recency of what is published.

**Substrate held fixed:** `futures_bhavcopy.duckdb` (09:31:43) and `equity_bhavcopy.duckdb`
(09:32:40) mtimes and sizes were identical before and after the audit. During the audit, live
stores were opened read-only and never written. The fix phase did write them — see Remediation,
including the test-run incident.

**Governance:** signal-level comparisons only. No forward-return, spread or P&L figure was read for
any window, so the preserved SEALED window (2023-01-01 → 2026-07-24) got no performance read.
TS Basis Daily stays research-only; nothing here is a gate or a promotion argument.

---

## Verdict

**The published daily books are not what the committed code produces, and on many days they are
not reproducible at all.**

- On the 3 sessions before each monthly expiry, the live build priced basis off the **expiring
  contract**. Those books share 0–1 of 5 names with a correct build.
- Those outlier rows now sit in every name's 252-row window, so **every z-score since 2026-07-24
  is distorted**. September books overlap a correct build by 0–3 of 5 names on most days.
- Whenever more than 5 names sit at the ±3 clamp, **the top-5 is an arbitrary pick**. Four
  publishes from identical signals gave four different books.
- History before 2026-07-24 is **not reproducible from any committed code path tested**. Most
  likely it was written by the builder before its first commit.

Nothing flagged any of this, because the path producing the books has no run log, no alert and no
recency check.

**These defects are live, not historical.** As of this audit the store is one session stale (the
2026-09-10 formation is absent, F6). The next refresh will add 09-10 z-scored against the
contaminated history, and the next expiry defect lands on **2026-09-24, 09-25 and 09-28** (Sept
series expires 2026-09-29).

| # | Severity | Finding |
|---|---|---|
| F1 | CRITICAL | Roll rule cannot fire at the live edge: T-3..T-1 books are built on the expiring contract |
| F2 | HIGH | F1's outliers poison the 252-row windows; every z since 07-24 is distorted; the store never self-repairs |
| F3 | HIGH | Top-5 book is non-deterministic whenever the ±3 clamp ties more than 5 names |
| F4 | HIGH | z_ts for 2016-02-11 → 2026-07-23 is not reproducible from any committed code path tested |
| F5 | MEDIUM | `liquid` (eligibility) is arbitrary for 27,291 name-days (ADV join fan-out) and cycles with expiry |
| F6 | MEDIUM | Books come from an unlogged catch-up path with no freshness gate; the 09-10 formation silently did not build today |
| F7 | LOW | `fwd_ret_1m` is never filled for incrementally added dates, and is a 1-day return despite its name |
| F8 | LOW | Two divergent facts publishers exist |
| O1 | observation | Post-CAS basis level and z dispersion shifted; the clamp rate is 2.5–5× historical, which amplifies F3 |

What checked out clean: no duplicate `(formation_date, underlying)` keys. The row set is identical
between live and rebuild (0 rows only-live, 0 only-rebuild). Raw basis is identical on every date
except the F1 dates, plus one historical date (2017-08-24, 211 rows) that likely reflects a
source-side change since 07-23 and was not pursued.

---

## F1 — Roll rule cannot fire at the live edge (CRITICAL)

**Mechanism.** `contract_arms.build_basis_panel` counts trading days to expiry against `td_cal`,
which holds only trade dates that already exist in the futures store:

```sql
LEFT JOIN td_cal ec ON ec.trade_date = n.near_exp      -- future expiry → no row → NULL
...
CASE WHEN tdays <= 3 AND next_exp IS NOT NULL THEN next_exp ELSE near_exp END
```

While the near expiry is still in the future, `tdays` is NULL and `NULL <= 3` is not true, so the
build keeps the **expiring** contract. It then annualizes its basis with `×365/days_to_expiry`
where days_to_expiry is 1–5. A build run after expiry has the expiry date in `td_cal` and rolls
correctly. So the defect hits every live formation at T-3, T-2 and T-1. It hits any full build in
the same way for the last ≤3 sessions before a pending expiry.

**Attribution.** Every diverging row was re-priced under both contracts:

| Formation | Rows | Live = near contract | Rebuild = next contract | Near DTE | Median \|ann. basis\| live | rebuild |
|---|--:|--:|--:|--:|--:|--:|
| 2026-07-23 | 210 | 210 | 208 | 5 | 0.089 | 0.057 |
| 2026-07-24 | 210 | 210 | 208 | 4 | 0.119 | 0.067 |
| 2026-07-27 | 210 | 210 | 208 | 1 | **0.455** | 0.065 |
| 2026-08-20 | 208 | 208 | 207 | 5 | 0.209 | 0.052 |
| 2026-08-21 | 208 | 208 | 207 | 4 | 0.241 | 0.039 |
| 2026-08-24 | 208 | 208 | 207 | 1 | **0.941** | 0.038 |

Control dates (06-24, 06-25, 06-29, 08-19, 08-25) match in both stores. The June expiry was rolled
correctly because those dates were built in a batch after 06-30. For scale, the Jan–Sep 2026 median
\|basis\| is 0.064 and the p99 is 0.395.

**Book impact** (overlap with the correct build, of 5; names tied at the clamp, LONG/SHORT):

| Formation | LONG ∩ | SHORT ∩ | Clamp ties live | Clamp ties rebuild |
|---|--:|--:|--:|--:|
| 2026-07-23 | 0 | 0 | 8 / 28 | 0 / 2 |
| 2026-07-24 | 1 | 1 | 23 / 23 | 0 / 3 |
| 2026-07-27 | 0 | 0 | 42 / 42 | 1 / 2 |
| 2026-08-20 | 0 | 0 | 35 / 34 | 0 / 0 |
| 2026-08-21 | 1 | 0 | 22 / 39 | 1 / 0 |
| 2026-08-24 | 0 | 0 | 41 / 41 | 0 / 0 |

On these days the whole Q1/Q5 tail sat at ±3. The book was a basis-to-expiry artifact picked
arbitrarily from 23–42 tied names.

**Next occurrences:** 2026-09-24, 09-25, 09-28 (Sept series expires 2026-09-29), and then every
month.

## F2 — The contamination persists and never self-repairs (HIGH)

- F1's outliers stay in each name's `ROWS BETWEEN 252 PRECEDING AND 1 PRECEDING` window for about
  a year. Each monthly expiry adds 3 more per name. They inflate the trailing SD and compress every
  later z. On 2026-09-09 the live cross-sectional z SD is **0.66** against **1.07** in the correct
  build; the live max is +1.52 against a correct +3.00.
- **From 07-24 on, 100% of live z_ts reproduce the committed formula applied to the live store's
  own raw basis** (e.g. 207/207 on each September date). So the incremental z arithmetic is
  correct; the input history is poisoned.
- Every z since 07-24 differs from the rebuild (e.g. 207/207 rows on 09-09, max |Δz| 1.3–2.2 on
  clean September dates). Book overlap on clean dates after 08-25 is mostly 0–3 of 5 names.
- **`basis_reverting` inherits it**, and `carry_rebalancer.py` reads that column. The flag is a
  one-row basis delta gated on `|z_ts| > 0.70`, so a near-contract basis followed by a
  next-contract basis reads as a reversion. Live vs rebuild disagree on **23–47 names on each F1
  date** and 11–20 on the session after (07-28, 08-25). In September the compressed z leaves fewer
  names over the gate: on 09-01, 19 flagged live against 46 in the rebuild. Store-wide the column
  disagrees on 12,562 rows; the pre-07-24 part comes from F4.
- **Nothing repairs it.** `build_ts_basis_daily.py --incremental` only computes new dates, and
  `refresh_all_strategies.py --force` still passes `--incremental` (line 268), so a forced refresh
  rebuilds nothing. The only full rebuild is deleting the store.

## F3 — The top-5 book is non-deterministic under clamp ties (HIGH)

`z_ts` is clamped to ±3, so many names share exactly −3.0 or +3.0. Every publisher orders by
`z_carry_neut` with no tiebreaker. That includes quintile assignment in
`_publish_daily_facts` (`ROW_NUMBER() OVER (… ORDER BY z_ts)`), `get_book` in
`ts_basis_daily_options.py`, `ts_basis_daily_signals.py` and the Flask panel. The facts table is
rebuilt from scratch on every refresh with `threads=4`, so tied rows come back in a different order.

**Test:** `_publish_daily_facts` run 4 times over the *same* rebuilt signals:

| Formation | Clamp ties L/S | Distinct books in 4 publishes |
|---|--:|--:|
| 2026-07-22 | 7 / 28 | 4 |
| 2026-08-03 | 3 / 40 | 4 (SHORT side: 19 distinct names across the 4 books) |
| 2026-08-17 | 32 / 7 | 4 (LONG side: 16 distinct names across the 4 books) |
| 2026-08-19 | 14 / 36 | 4 |
| 2026-08-31 | 22 / 41 | 4 |

The unclamped `raw_z` is already in the same table (added by `apply_recovery_filter.py`) and is
unused for ordering. Even in the correct build, clamp ties above 5 are routine: 08-03, 08-04,
08-12, 08-14, 08-17 to 08-19, 08-31. Every book on those days is one draw from many possible books.

## F4 — History before 2026-07-24 is not reproducible from committed code (HIGH)

What is proven is non-reproducibility. Provenance is inferred:

- **Likely explanation.** The builder has one commit, `d81859b` (2026-07-27 18:23), and the
  store's pre-07-24 rows were written in one batch whose live edge was 07-23 (which is why 07-23
  carries F1), so they likely predate that commit. A since-changed `build_basis_panel` or a
  different invocation path would leave the same signature, so this is not established.
- For 2016-02-11 → 2026-07-23, **~98% of z_ts rows match neither the committed formula nor any
  window variant tested store-wide**: ROWS 60/126/251/252/253/504 and including the current row,
  RANGE 252/365/504 days, and expanding. On sample names, a brute force over every contiguous
  window (sample and population SD) found no window of the stored basis that reproduces the stored
  z. Nor did settle-, trading-day- or adjusted-spot basis definitions.
- Live z starts at a name's **5th** observation rather than the 13th (`MIN_OBS = 12`): 8 extra
  z-scored rows per name, 2,294 in total. The first rows of ICICIBANK reproduce exactly if every
  date sits in the window three times (sample SD over triplicated rows). That matches a per-contract
  fan-out in the pre-commit version, but later rows do not fit, so the exact legacy formula stays
  unidentified.
- Consequence: the TS Basis Daily research reports that read this store's `z_ts` rest on z that
  committed code cannot regenerate. That covers net spread, HOLDOUT, the top-5 concentrated
  backtest, the ML filter and the recovery-filter validation. They were **not** re-run here, and
  re-running them is a separate decision.

## F5 — Eligibility (`liquid`) is arbitrary and cycles with expiry (MEDIUM)

- `adv_lookup` takes `MEDIAN(val_in_lakh)` over 30 **per-contract** rows. With three live contracts
  that is about 10 sessions of mixed near/next/far turnover, not a 30-session ADV.
- `adv_filled` keeps one row per distinct ADV value, so **370,231 of 485,730**
  `(trade_date, underlying)` keys carry more than one ADV. The LEFT JOIN fans out, and
  `DISTINCT ON (trade_date, underlying)` (no `ORDER BY`) keeps an arbitrary one.
- On **27,291** name-days the candidates straddle the 500-lakh threshold, so `liquid` is a coin
  flip. That is 9–18 names a day in September. It changes who can enter Q1/Q5.
  Live-vs-rebuild `liquid` disagrees on 484–3,814 rows every year.
- Because far-month rows dilute the median until the roll, the liquid count tracks the expiry
  calendar: **208 → 139 between 09-01 and 09-09**, and the same sawtooth appears in July and August.
  The count reflects the calendar, not the names' liquidity.

## F6 — Silent production path, no freshness gate (MEDIUM)

- The EOD worker (`schedule_worker.py` → `eod_job.py`) last recorded a run on **2026-08-06**.
  Since then signals have still advanced daily, but through the orchestrator's catch-up. That path
  is `orchestrator._dispatch_catchup` → detached `download_all_data.py` →
  `refresh_all_strategies.py`, launched with no stdout capture. It has no run log, no Telegram and
  no stale-feed suppression, which lives only in `eod_job.py`.
- **Today:** catch-up dispatched 09:29 and ingested the 09-10 bhavcopy (futures and equity written
  09:31–09:32). Both TS Basis Daily stores still carry 2026-09-10 09:20 mtimes. **The 09-10
  formation does not exist, and nothing records why**, because the catch-up's output was discarded.
  From mtimes only (carry monthly/weekly signals written 09:34, `carry/facts.duckdb` not), the
  refresh appears to have stopped before the carry facts publish. A file-handle check run hours
  later, after Flask had restarted, could not confirm a cause.
- Every consumer takes `MAX(formation_date)` with no recency assertion, so the 09-09 book is
  presented as current. This is the recorded pitfall again: a freshness value printed but never
  asserted.

## F7 — `fwd_ret_1m` (LOW)

The incremental forward-return step restricts equity to `[first new date, last new date]` and only
updates new dates. The last new date of every run therefore has no next close, and nothing
backfills it. **6,060** 2026 rows are NULL that the rebuild fills. At daily cadence the column holds
a next-formation (1-day) return, despite the `_1m` name. No current consumer reads it from this
store (the `fwd_ret_1m` readers use the carry store). Any future evaluation over this store would
silently drop most recent dates.

## F8 — Two facts publishers (LOW)

`refresh_all_strategies._publish_daily_facts` (used by the pipeline) rebuilds from scratch and
keeps `n_liq < 5` dates at quintile 3. `scripts/signal_engine/ts_basis_daily/publish_facts.py` is
insert-only on new dates and drops those dates. It is the same rule implemented twice, and one
implementation can never propagate a correction.

## O1 — CAS shift (observation, not a defect claim)

On the correct build, comparing 2026-06-01 → 08-02 with 08-03 → 09-10: median annualized basis fell
**5.3% → 3.8%**, cross-sectional z SD rose **1.09 → 1.37**, and the clamp rate rose **3.2% → 8.6%**.
The 2016–2025 clamp rate was 1.6–3.4%. The universe is CAS Category I throughout (every row that
`cas_category` covered, which stops at 2026-08-28), so this is a level shift, not a split between
categories. It fits spot close becoming the 15:30–15:35 auction print while futures trade to 15:40,
but regime and roll effects are not isolated here. It matters for two reasons: the 252-row window
straddles the break until about Aug 2027, and a higher clamp rate directly worsens F3.

---

## Per-date book diff (2026-07-01 → 2026-09-09)

Top-5 as `get_book` emits it (eligible names, Q5 highest-z first / Q1 lowest-z first). *Live* is
the live facts store at audit time; *rebuild* is the then-committed code on the same substrate.
**Neither column is what is published now:** the remediation's eligibility, quintile-universe and
tie-order changes move the books further. Rebuild books on
tie-heavy days are themselves one arbitrary draw (F3). F1 dates are **bold**.

| Formation | L∩ | S∩ | Ties L/S live | Ties L/S rebuild | Live LONG | Live SHORT | Rebuild LONG | Rebuild SHORT |
|---|--:|--:|--:|--:|---|---|---|---|
| 2026-07-01 | 4 | 2 | 0/2 | 0/1 | FORCEMOT, 360ONE, AMBUJACEM, OBEROIRLTY, VOLTAS | UPL, DABUR, M&M, HEROMOTOCO, NESTLEIND | FORCEMOT, 360ONE, VOLTAS, ASHOKLEY, AMBUJACEM | M&M, NESTLEIND, SHRIRAMFIN, MCX, JSWSTEEL |
| 2026-07-02 | 3 | 1 | 0/2 | 0/0 | APOLLOHOSP, VOLTAS, BAJFINANCE, DIXON, TORNTPHARM | DABUR, UPL, M&M, CROMPTON, HEROMOTOCO | APOLLOHOSP, VOLTAS, FORCEMOT, ANGELONE, BAJFINANCE | M&M, NHPC, MCX, KPITTECH, SHRIRAMFIN |
| 2026-07-03 | 2 | 3 | 0/4 | 0/1 | VOLTAS, CIPLA, BANKBARODA, INDUSINDBK, HINDUNILVR | DABUR, UPL, CROMPTON, MCX, HEROMOTOCO | VOLTAS, HINDUNILVR, HYUNDAI, GVT&D, ADANIENSOL | MCX, UPL, WAAREEENER, CROMPTON, ABB |
| 2026-07-06 | 5 | 3 | 0/6 | 0/2 | ITC, PATANJALI, EXIDEIND, VOLTAS, IOC | DABUR, UPL, JSWSTEEL, HEROMOTOCO, DLF | ITC, VOLTAS, IOC, EXIDEIND, PATANJALI | LODHA, JSWSTEEL, DABUR, GODREJPROP, UPL |
| 2026-07-07 | 3 | 3 | 0/5 | 0/1 | SBILIFE, VOLTAS, POLICYBZR, COLPAL, OFSS | CROMPTON, UPL, DABUR, LODHA, CUMMINSIND | SBILIFE, VOLTAS, COLPAL, RVNL, INDIANB | LODHA, DABUR, GODREJPROP, ABB, UPL |
| 2026-07-08 | 2 | 3 | 0/5 | 0/4 | VOLTAS, JSWENERGY, MAXHEALTH, POLICYBZR, OFSS | HEROMOTOCO, LODHA, UPL, CROMPTON, DABUR | VOLTAS, BAJAJHLDNG, JSWENERGY, INDIANB, KALYANKJIL | DABUR, NESTLEIND, GODREJPROP, LODHA, UPL |
| 2026-07-09 | 3 | 4 | 0/6 | 0/3 | VOLTAS, AMBUJACEM, JSWENERGY, INDHOTEL, BAJFINANCE | CROMPTON, LODHA, DRREDDY, DABUR, BHARTIARTL | VOLTAS, AMBUJACEM, COCHINSHIP, JSWENERGY, CGPOWER | BHARTIARTL, DRREDDY, LODHA, DABUR, BDL |
| 2026-07-10 | 4 | 3 | 0/7 | 0/2 | CAMS, MARUTI, CONCOR, PAYTM, OFSS | DLF, DABUR, CROMPTON, UPL, LODHA | CAMS, PAYTM, FORCEMOT, CONCOR, MARUTI | BHARTIARTL, LODHA, DABUR, GODREJPROP, DLF |
| 2026-07-13 | 3 | 2 | 1/9 | 1/9 | CONCOR, BIOCON, NESTLEIND, ITC, BANKBARODA | BDL, CROMPTON, MAXHEALTH, DLF, CUMMINSIND | CONCOR, BIOCON, NESTLEIND, PAYTM, CIPLA | DLF, DABUR, UPL, LODHA, BDL |
| 2026-07-14 | 4 | 2 | 0/10 | 0/10 | NESTLEIND, HDFCLIFE, EXIDEIND, PAYTM, GVT&D | DABUR, MAZDOCK, BDL, CROMPTON, TORNTPHARM | HDFCLIFE, GVT&D, PAYTM, NESTLEIND, FEDERALBNK | DABUR, MAZDOCK, LICI, DLF, BHARTIARTL |
| 2026-07-15 | 4 | 2 | 1/6 | 1/8 | PAYTM, EXIDEIND, FORCEMOT, BIOCON, OFSS | DLF, GODREJPROP, HEROMOTOCO, BHARTIARTL, UPL | PAYTM, EXIDEIND, FORCEMOT, BIOCON, UNIONBANK | LUPIN, BHARTIARTL, DABUR, CROMPTON, GODREJPROP |
| 2026-07-16 | 4 | 3 | 0/8 | 0/10 | FEDERALBNK, NMDC, RBLBANK, BIOCON, MANAPPURAM | MAZDOCK, HEROMOTOCO, UPL, TORNTPHARM, BHARTIARTL | FEDERALBNK, MANAPPURAM, BIOCON, NMDC, MCX | BHARTIARTL, TORNTPHARM, MAZDOCK, DABUR, DIXON |
| 2026-07-17 | 5 | 4 | 0/5 | 0/6 | OFSS, POLICYBZR, ABB, EXIDEIND, MCX | DLF, BHARTIARTL, GODREJPROP, CROMPTON, HEROMOTOCO | OFSS, POLICYBZR, ABB, MCX, EXIDEIND | BHARTIARTL, CROMPTON, HEROMOTOCO, DIXON, DLF |
| 2026-07-20 | 3 | 2 | 7/8 | 6/8 | MANAPPURAM, RBLBANK, BPCL, CANBK, NESTLEIND | PIDILITIND, CROMPTON, DIVISLAB, BHARTIARTL, HEROMOTOCO | GVT&D, CANBK, POWERINDIA, MANAPPURAM, NESTLEIND | CROMPTON, OBEROIRLTY, GODREJPROP, DIVISLAB, TORNTPHARM |
| 2026-07-21 | 4 | 1 | 3/14 | 5/13 | RBLBANK, POLICYBZR, GVT&D, POWERINDIA, SRF | DLF, CROMPTON, GODREJPROP, HEROMOTOCO, NAUKRI | KALYANKJIL, POLICYBZR, SRF, GVT&D, POWERINDIA | BANDHANBNK, DIVISLAB, WAAREEENER, DLF, MAZDOCK |
| 2026-07-22 | 3 | 2 | 4/25 | 7/28 | VBL, NESTLEIND, INDUSTOWER, COLPAL, POLICYBZR | SRF, DELHIVERY, GODREJPROP, PHOENIXLTD, AMBUJACEM | POLICYBZR, POLYCAB, VBL, NESTLEIND, POWERINDIA | BHARTIARTL, CROMPTON, NAUKRI, GODREJPROP, PHOENIXLTD |
| **2026-07-23** | 0 | 0 | 8/28 | 0/2 | MANAPPURAM, COLPAL, IDEA, JSWENERGY, PHOENIXLTD | NAUKRI, CGPOWER, SUNPHARMA, ADANIGREEN, M&M | VOLTAS, ASHOKLEY, ANGELONE, HDFCLIFE, ASIANPAINT | LODHA, BRITANNIA, NHPC, MAZDOCK, SONACOMS |
| **2026-07-24** | 1 | 1 | 23/23 | 0/3 | CUMMINSIND, DRREDDY, MAZDOCK, CANBK, AUBANK | INDUSTOWER, DELHIVERY, EICHERMOT, CIPLA, DLF | NUVAMA, CGPOWER, VOLTAS, ASHOKLEY, CANBK | LODHA, BRITANNIA, EXIDEIND, EICHERMOT, MAZDOCK |
| **2026-07-27** | 0 | 0 | 42/42 | 1/2 | AMBER, DRREDDY, PETRONET, TORNTPHARM, SONACOMS | RELIANCE, RBLBANK, HINDZINC, ETERNAL, BAJAJFINSV | NUVAMA, PAYTM, KOTAKBANK, VOLTAS, ASHOKLEY | BRITANNIA, LODHA, ICICIBANK, MAZDOCK, MARUTI |
| 2026-07-28 | 4 | 4 | 0/6 | 0/6 | NUVAMA, VOLTAS, BAJFINANCE, ASHOKLEY, ASIANPAINT | SIEMENS, BDL, BRITANNIA, EXIDEIND, LODHA | NUVAMA, TATAELXSI, VOLTAS, BAJFINANCE, ASHOKLEY | SIEMENS, BRITANNIA, BDL, EICHERMOT, EXIDEIND |
| 2026-07-29 | 4 | 4 | 0/3 | 0/3 | VOLTAS, HINDZINC, TATAELXSI, HINDUNILVR, NATIONALUM | LODHA, BRITANNIA, PNBHOUSING, MARUTI, BDL | VOLTAS, TATAELXSI, HINDZINC, AMBUJACEM, NATIONALUM | BRITANNIA, LODHA, PNBHOUSING, MARUTI, ICICIBANK |
| 2026-07-30 | 4 | 4 | 0/2 | 0/4 | ASHOKLEY, VOLTAS, TATAELXSI, NATIONALUM, RVNL | BRITANNIA, LODHA, MARUTI, EICHERMOT, PNBHOUSING | ASHOKLEY, TATAELXSI, FORCEMOT, VOLTAS, NATIONALUM | WAAREEENER, LODHA, MARUTI, BRITANNIA, EICHERMOT |
| 2026-07-31 | 3 | 4 | 0/0 | 0/0 | FORCEMOT, PATANJALI, LTM, RVNL, MUTHOOTFIN | DIXON, MARUTI, SHREECEM, ICICIBANK, LICHSGFIN | PATANJALI, FORCEMOT, TATAELXSI, ICICIGI, LTM | MARUTI, SHREECEM, DIXON, LAURUSLABS, ICICIBANK |
| 2026-08-03 | 5 | 1 | 2/31 | 3/40 | SAIL, CGPOWER, JINDALSTEL, INOXWIND, OFSS | GRASIM, PHOENIXLTD, TATACONSUM, SHRIRAMFIN, JSWSTEEL | CGPOWER, JINDALSTEL, SAIL, OFSS, INOXWIND | BAJAJFINSV, NTPC, SHRIRAMFIN, MARUTI, BAJAJ-AUTO |
| 2026-08-04 | 3 | 0 | 0/23 | 0/32 | ALKEM, AMBUJACEM, BIOCON, POLICYBZR, POWERINDIA | BRITANNIA, BAJAJFINSV, MARUTI, IDFCFIRSTB, LAURUSLABS | AMBUJACEM, BIOCON, ALKEM, CROMPTON, PAYTM | NYKAA, ICICIPRULI, IREDA, ZYDUSLIFE, MFSL |
| 2026-08-05 | 3 | 3 | 1/6 | 1/15 | BANDHANBNK, JINDALSTEL, PNBHOUSING, UNITDSPR, MUTHOOTFIN | MARUTI, CUMMINSIND, ADANIENSOL, PIDILITIND, GVT&D | BANDHANBNK, JINDALSTEL, GODREJPROP, PNBHOUSING, VBL | PIDILITIND, JUBLFOOD, MARUTI, CGPOWER, GVT&D |
| 2026-08-06 | 3 | 3 | 2/5 | 2/7 | APLAPOLLO, SOLARINDS, BAJFINANCE, BIOCON, JINDALSTEL | IDFCFIRSTB, MARUTI, NESTLEIND, UNOMINDA, MOTILALOFS | APLAPOLLO, SOLARINDS, BIOCON, INDUSTOWER, PAYTM | RBLBANK, GMRAIRPORT, MOTILALOFS, MARUTI, NESTLEIND |
| 2026-08-07 | 4 | 1 | 0/5 | 1/11 | MPHASIS, AXISBANK, FORTIS, INDIGO, BAJFINANCE | BANDHANBNK, HAVELLS, BHEL, IOC, INOXWIND | MPHASIS, FORTIS, AXISBANK, BAJFINANCE, NTPC | HINDALCO, ULTRACEMCO, HAVELLS, GAIL, LICHSGFIN |
| 2026-08-10 | 4 | 3 | 0/10 | 2/11 | VBL, ABCAPITAL, GLENMARK, POWERINDIA, JIOFIN | NAUKRI, LUPIN, LAURUSLABS, SAIL, FEDERALBNK | VBL, ABCAPITAL, GLENMARK, CANBK, JIOFIN | FEDERALBNK, LAURUSLABS, MARICO, JUBLFOOD, NAUKRI |
| 2026-08-11 | 4 | 2 | 1/12 | 2/14 | PNBHOUSING, APOLLOHOSP, ZYDUSLIFE, SIEMENS, AXISBANK | YESBANK, BAJAJFINSV, SAIL, CGPOWER, BEL | ZYDUSLIFE, PNBHOUSING, APOLLOHOSP, AXISBANK, PAYTM | INOXWIND, BEL, YESBANK, BANDHANBNK, SHRIRAMFIN |
| 2026-08-12 | 4 | 1 | 2/19 | 4/25 | ADANIENSOL, AMBUJACEM, MARUTI, M&M, KALYANKJIL | PATANJALI, RELIANCE, TITAN, LAURUSLABS, SAIL | AMBUJACEM, ADANIENSOL, KOTAKBANK, M&M, MARUTI | FORTIS, MPHASIS, DABUR, PATANJALI, GAIL |
| 2026-08-13 | 4 | 3 | 2/6 | 3/7 | CONCOR, PNB, DELHIVERY, ICICIBANK, KALYANKJIL | IOC, LICHSGFIN, PATANJALI, LAURUSLABS, JINDALSTEL | CONCOR, DELHIVERY, PNB, ICICIBANK, CIPLA | AUBANK, LAURUSLABS, LICHSGFIN, PATANJALI, PAYTM |
| 2026-08-14 | 1 | 4 | 5/5 | 13/10 | HDFCLIFE, TATAPOWER, MCX, APLAPOLLO, EICHERMOT | NMDC, BIOCON, FORTIS, LICHSGFIN, ADANIGREEN | BHEL, KOTAKBANK, APLAPOLLO, NAUKRI, GMRAIRPORT | HINDPETRO, BIOCON, ADANIGREEN, NMDC, LICHSGFIN |
| 2026-08-17 | 0 | 3 | 32/3 | 32/7 | SHRIRAMFIN, FORTIS, BAJFINANCE, JSWSTEEL, DIVISLAB | GLENMARK, LICHSGFIN, BHEL, JUBLFOOD, PATANJALI | BOSCHLTD, AXISBANK, KOTAKBANK, KALYANKJIL, INDUSINDBK | ULTRACEMCO, GLENMARK, BHEL, JUBLFOOD, DRREDDY |
| 2026-08-18 | 1 | 3 | 15/11 | 23/14 | GMRAIRPORT, SAIL, MARICO, UNIONBANK, DALBHARAT | JIOFIN, AUROPHARMA, CAMS, CGPOWER, LICHSGFIN | BIOCON, UNIONBANK, EICHERMOT, GLENMARK, ULTRACEMCO | AUROPHARMA, CAMS, JIOFIN, PIDILITIND, GAIL |
| 2026-08-19 | 1 | 1 | 10/37 | 14/36 | VBL, ZYDUSLIFE, MANAPPURAM, TMPV, GLENMARK | AMBUJACEM, TITAN, ADANIGREEN, RELIANCE, BAJAJFINSV | MANAPPURAM, ABCAPITAL, PAGEIND, ADANIENSOL, COFORGE | TATAPOWER, MAZDOCK, LICHSGFIN, ITC, AMBUJACEM |
| **2026-08-20** | 0 | 0 | 35/34 | 0/0 | TECHM, INDUSTOWER, LUPIN, INDIANB, JIOFIN | HINDALCO, CGPOWER, TVSMOTOR, UNITDSPR, BOSCHLTD | DALBHARAT, VOLTAS, TATACONSUM, PAGEIND, HINDUNILVR | JSWSTEEL, SHRIRAMFIN, HDFCAMC, NMDC, LAURUSLABS |
| **2026-08-21** | 1 | 0 | 22/39 | 1/0 | MARUTI, SONACOMS, ICICIPRULI, BSE, M&M | IDFCFIRSTB, SBIN, ASIANPAINT, FORCEMOT, PRESTIGE | DALBHARAT, MARUTI, TATAPOWER, MUTHOOTFIN, ICICIGI | BANKBARODA, NBCC, ZYDUSLIFE, CIPLA, NTPC |
| **2026-08-24** | 0 | 0 | 41/41 | 0/0 | ZYDUSLIFE, SBICARD, SBILIFE, IDEA, CDSL | OFSS, JINDALSTEL, HAVELLS, VBL, HAL | DALBHARAT, INDUSTOWER, LICI, MOTILALOFS, BAJFINANCE | DIXON, SUZLON, NTPC, ITC, VMM |
| 2026-08-25 | 2 | 3 | 0/1 | 0/2 | SBILIFE, INDIANB, SHRIRAMFIN, ULTRACEMCO, RVNL | DALBHARAT, IREDA, DIXON, LODHA, JUBLFOOD | ULTRACEMCO, SBILIFE, HINDPETRO, RADICO, COFORGE | DIXON, DALBHARAT, IREDA, NTPC, ETERNAL |
| 2026-08-26 | 2 | 4 | 0/0 | 0/1 | CAMS, MAXHEALTH, COLPAL, ALKEM, DABUR | LODHA, IREDA, LAURUSLABS, DIXON, MFSL | MAXHEALTH, AMBUJACEM, HINDALCO, ADANIPORTS, CAMS | DIXON, LODHA, LAURUSLABS, IREDA, ETERNAL |
| 2026-08-27 | 3 | 3 | 1/1 | 1/1 | CONCOR, SAIL, ICICIGI, PAYTM, ABB | LAURUSLABS, IREDA, JUBLFOOD, NHPC, NBCC | CONCOR, PAYTM, SAIL, RELIANCE, SBILIFE | LAURUSLABS, IREDA, JUBLFOOD, ADANIENSOL, DIXON |
| 2026-08-28 | 3 | 4 | 0/1 | 0/1 | PHOENIXLTD, LICHSGFIN, TATAELXSI, KPITTECH, ASHOKLEY | LAURUSLABS, IREDA, LODHA, NTPC, KEI | PHOENIXLTD, SUNPHARMA, LICHSGFIN, TATAELXSI, JSWENERGY | LAURUSLABS, IREDA, LODHA, NTPC, BANKINDIA |
| 2026-08-31 | 0 | 0 | 8/22 | 22/41 | ADANIPORTS, M&M, KALYANKJIL, TMPV, BHARTIARTL | NESTLEIND, BIOCON, LAURUSLABS, COLPAL, INDIANB | VBL, HINDUNILVR, RELIANCE, IDEA, ADANIENT | PAYTM, BAJAJFINSV, HDFCAMC, HAVELLS, ETERNAL |
| 2026-09-01 | 2 | 2 | 0/0 | 0/2 | HCLTECH, SBICARD, RVNL, TECHM, ASTRAL | INDIANB, NTPC, IREDA, COALINDIA, KALYANKJIL | BANKBARODA, TRENT, SWIGGY, HCLTECH, SBICARD | NTPC, ADANIGREEN, SONACOMS, INDIANB, HAVELLS |
| 2026-09-02 | 2 | 2 | 0/0 | 0/0 | CONCOR, VOLTAS, SBICARD, BANDHANBNK, RVNL | KALYANKJIL, 360ONE, COALINDIA, ONGC, BAJAJFINSV | HDFCLIFE, CONCOR, VOLTAS, TRENT, SONACOMS | KALYANKJIL, ABCAPITAL, ETERNAL, BANKINDIA, ONGC |
| 2026-09-03 | 2 | 2 | 0/0 | 0/1 | NMDC, MCX, AXISBANK, TATAELXSI, CUMMINSIND | COALINDIA, GMRAIRPORT, TVSMOTOR, BAJAJFINSV, KEI | RELIANCE, ULTRACEMCO, CUMMINSIND, MCX, INOXWIND | VMM, DIXON, GMRAIRPORT, ADANIPORTS, COALINDIA |
| 2026-09-04 | 2 | 4 | 0/0 | 0/0 | SAIL, COLPAL, LICHSGFIN, BPCL, BHEL | KAYNES, HAVELLS, KALYANKJIL, DIXON, PIIND | SAIL, RELIANCE, CANBK, BHEL, SWIGGY | HAVELLS, DIXON, KAYNES, SBILIFE, KALYANKJIL |
| 2026-09-07 | 2 | 3 | 0/0 | 0/1 | NMDC, BAJAJHLDNG, VOLTAS, APOLLOHOSP, DRREDDY | HAVELLS, APLAPOLLO, HINDPETRO, KALYANKJIL, KAYNES | HDFCLIFE, APOLLOHOSP, BOSCHLTD, ICICIGI, NMDC | HAVELLS, HINDPETRO, APLAPOLLO, ADANIGREEN, INOXWIND |
| 2026-09-08 | 0 | 2 | 0/0 | 0/0 | DMART, TCS, ABB, ASHOKLEY, ICICIBANK | HAVELLS, AUROPHARMA, BDL, JIOFIN, RBLBANK | PAYTM, SBILIFE, IDFCFIRSTB, ULTRACEMCO, BEL | HAVELLS, INDUSTOWER, AUROPHARMA, UNIONBANK, AMBUJACEM |
| 2026-09-09 | 3 | 5 | 0/0 | 1/3 | AXISBANK, ONGC, TVSMOTOR, MANAPPURAM, BAJFINANCE | AUROPHARMA, RBLBANK, BOSCHLTD, HDFCAMC, UNIONBANK | MANAPPURAM, RELIANCE, ICICIBANK, ONGC, BAJFINANCE | BOSCHLTD, AUROPHARMA, HDFCAMC, UNIONBANK, RBLBANK |

---

## Remediation (proposed — nothing changed in this audit)

Order matters: fix the construction, then rebuild. A rebuild on the current code would reintroduce
F1 for any pending expiry, and it would not fix F3/F5. **Deadline: before the 2026-09-24
formation.**

1. **F1: compute days-to-expiry without needing the future to exist.** Count sessions from
   `trade_date` to `expiry_dt` against a forward NSE trading calendar
   (`core/market/session_schedule.py` / the holiday list), not against dates already in the futures
   store. Add a regression test: an as-of-T-2 panel must select the next contract.
2. **F5: build ADV per day, not per contract.** Use `SUM(val_in_lakh)` per `(trade_date, underlying)`
   first, then the 30-session median, so the join is 1:1. Give every `DISTINCT ON` an explicit
   `ORDER BY`.
3. **F3: deterministic ordering everywhere.** Order by `raw_z` then `underlying` (or rank on unclamped
   z) in the facts `ROW_NUMBER`, `get_book`, `ts_basis_daily_signals.py` and the Flask panel. Add a
   test that repeated publishes yield identical books.
4. **F2/F4: full rebuild of the live store after 1–3**, copy-first (snapshot the current store
   before replacing it), and make `refresh_all_strategies.py --force` do a real rebuild. Treat the
   TS Basis Daily research reports as resting on non-reproducible z until anyone chooses to
   re-derive them. That is a separate decision, and HOLDOUT/TRAIN are already burned as selection
   surfaces.
5. **F6: make the path observable.** Capture the catch-up's stdout/stderr to a dated log. Record
   catch-up refreshes in the EOD run log, or restart the EOD worker, which has not recorded a run
   since 08-06. Make the book consumers assert `formation_date == latest futures trade_date` and
   refuse (or visibly mark STALE) otherwise.
6. **F7/F8:** recompute forward returns over a trailing window each run (or drop the column from
   this store), and delete the unused `publish_facts.py` in favour of the one publisher.

## Reproduction

Scripts ran from the session scratchpad; the key queries are below.

- **Rebuild:** import `build_ts_basis_daily`, point `OUT_DB` at a scratch path, run `main()`
  without `--incremental` (60 s). Then `refresh_all_strategies._publish_daily_facts` and
  `apply_recovery_filter.main` with their DB globals redirected to scratch. Result: 485,730 signals /
  2,611 formations (includes 09-10), 481,338 z-scored.
- **Self-consistency:** rebuild `z_ts == clamp(raw_z, ±3)` on 481,338/481,338 rows; live on
  16,917/483,632.
- **F1 attribution:** join each signal row to FUTSTK rows ranked by `expiry_dt` (rn=1 near, rn=2
  next) and equity `EQ` close on the same date. Recompute
  `(fut_close − spot)/spot × 365 / GREATEST(date_diff('day', trade_date, expiry_dt), 1)` and
  compare with `raw_ann_basis` at 1e-9.
- **F2 identity:** on live rows from 07-24 on, the committed window
  `ROWS BETWEEN 252 PRECEDING AND 1 PRECEDING` over the live store's own `raw_ann_basis` reproduces
  `z_ts` on 100% of rows.
- **F3 determinism:** `_publish_daily_facts` ×4 into separate scratch files over identical signals;
  `get_book` logic per file.
- **F5 fan-out:** `SELECT trade_date, underlying, COUNT(*), MIN(adv_lakh), MAX(adv_lakh) FROM adv_filled
  GROUP BY 1,2` — `n > 1`: 370,231 keys; `MIN < 500 <= MAX`: 27,291.
- **Substrate stamp:** futures 2026-09-11 09:31:43 / 130,560,000 B; equity 09:32:40 / 737,423,360 B;
  unchanged before vs after.

---

## Remediation — implemented 2026-09-11 (branch `fix/ts-basis-daily-signal-defects`)

| Finding | Fix | Commit | Verification |
|---|---|---|---|
| F1 | `build_basis_panel` counts sessions past the store's last date from `core/market/nse_holidays.py` (moved out of `MarketHours`, which re-exports it). A near expiry close enough for an unlisted year's holidays to flip the roll hard-fails | `e54a4a7` | Full-history panel identical in contract, basis, prices and entity on all 485,730 cells; only `trading_days_to_exp` fills for 2,520 post-store cells (no consumers). Real futures store truncated at each F1 date now reproduces the full-history selection 100%. 6 unit tests |
| F2 / F4 | Full rebuild mode builds beside the store, copies it to `data/_baselines`, then replaces it; `refresh_all_strategies.py --force` runs it; incremental runs are one transaction and hard-fail on an old-schema store | `d34c014` | Live store rebuilt (below) |
| F3 | `raw_z` stored in signals and carried into facts; quintiles and every book consumer order by `(z_ts, raw_z, underlying)` | `d34c014` | 3 publishes from the live signals give identical quintiles, equal to the live facts |
| F5 | ADV = 30-session median of **daily total** futures turnover (contracts summed); 1:1 join; duplicate keys raise | `d34c014` | Unit test; see construct change below |
| F6 | Latest-book CLIs exit 2 with a STALE message, and the Flask panel shows a banner, when the futures store is ahead of the newest formation; the catch-up's output goes to `logs/catchup_*.log`. **EOD behaviour change:** on a day futures publish but the TS Basis Daily formation is not built (e.g. equity stale), the chain now aborts at `ts_basis_daily_signals.py` with a `chain_failed` alert instead of completing with a suppressed book | `d34c014`, `d63120b` | Unit tests; `ts_basis_daily_signals.py` prints 2026-09-10 as current |
| F7 | Forward returns fill for the new dates **and** the formation just before them | `d34c014` | Incremental run equals a full build in a unit test |
| F8 | `publish_facts.py` is the only publisher; the pipeline, the Flask refresh button and the forward runner all use it, followed by the recovery filter, and a failed step fails the refresh | `d34c014` | Unit tests |

**Live store rebuilt 2026-09-11 15:58** via `refresh_all_strategies.py --force --skip-carry --skip-ts-basis`: 485,730 signals, 2,611 formations (2016-02-11 → 2026-09-10), 481,338 facts across 2,599 formations. Checks:
- Symmetric difference against an independent scratch build of the same code is 0 rows.
- No duplicate keys.
- `z_ts` is NULL exactly when `raw_z` is NULL.
- A second `--incremental` run is a no-op.

On basis, `z_ts` and forward returns, the new code matches the previous code's full rebuild on every row. Only `liquid` changes.

### Construct changes (on the record)

TS Basis Daily is research-only, and these change what it publishes. Research numbers computed under the old definitions are **not comparable**.

1. **Eligibility.** Measured as daily total turnover, ~100% of F&O names clear the 500-lakh bar in every year from 2016 on. Under the old per-contract median artifact the pass rate was 47% (2016) to 96% (2024). The old filter's exclusions were mostly the measurement artifact, not illiquidity; the threshold constant is unchanged.
2. **Quintile universe (new finding, F9).** The research (`run_net_spread.py`) ranks quintiles among liquid names only. The pipeline's inline publisher ranked among all names and then neutralized the illiquid ones, so Q1/Q5 held fewer liquid names than the research construct. The single publisher now uses the research rule.
3. **Tie order.** Names tied at the ±3 clamp are ordered by unclamped z. Before, their order was arbitrary.

### Other defects found while fixing

- `ts_basis_daily_forward_runner.py` ran the build **without** `--incremental`. Under the old code that re-inserts every date into an existing store, duplicating it. It now builds incrementally and runs the recovery filter.
- The Flask refresh button ran the insert-only publisher, never ran the recovery filter, and reported "Refresh complete" even when publishing failed.
- The new build's first draft clamped with DuckDB `GREATEST/LEAST`, which **skip NULLs**. A NULL `raw_z` would have become `z_ts = +3.0`, sending every new listing to Q5. The real-data comparison caught it before any live write (4,392 rows), and a regression test now covers it.

### Incident during the fix — live facts overwritten by a test run

At **15:47:48** the RED run of `test_ts_basis_daily_pipeline.py` ran against the not-yet-changed `refresh_all_strategies.py`. That old code called its inline `_publish_daily_facts()` directly rather than through the `_run` the test stubbed. It deleted and republished the **live** `ts_facts.duckdb` from the live signals, and the stubbed recovery filter left it without `raw_z` / `basis_reverting`.

- The signals store was untouched (mtime still 2026-09-10 09:20).
- The pre-fix facts were regenerated with `main`'s code from the untouched signals baseline. The regeneration matches this audit's recorded counts exactly: 481,131 joined rows, 12,562 `basis_reverting` disagreements, 38,131 flags. Quintiles on clamp-tie days can differ from the original, since that is F3 itself.
- The live store was then rebuilt as above.
- The same test file also let the existing catch-up test write two empty `logs/catchup_*.log` files. The test now uses `tmp_path` (`d63120b`) and the files were removed. A full re-run of the suites left the live stores' mtimes unchanged.

### Incident — branch switch removed the NiftyShield fee fix from the live tree

`F:\Nifty` is the tree the orchestrator runs from. This branch was cut from `main` at 15:17:56. `main` lacked `0f46f9b` (option legs charged the options fee schedule), so from then until the merge of `fix/nifty-shield-option-fees` at **16:02:43** (`9efb5b3`) the files on disk were the pre-fix versions.

- **No impact found.** The NiftyShield session child had loaded the fixed code at 14:27, placed its last order at 13:29, and did not restart inside the window.
- The orchestrator, Flask and the ingestor restarted at 16:01:47–48, 55 s before the merge. Neither Flask nor the ingestor places NiftyShield orders.
- `core/execution` on this branch is now identical to the fee-fix branch.

### Baselines (`data/_baselines/`)

| File | What it is |
|---|---|
| `ts_basis_daily_ts_signals_pre_audit_fix_20260911_155230.duckdb` | Original live signals (2026-09-10 09:20), byte copy |
| `ts_basis_daily_ts_facts_pre_audit_fix_regenerated_from_main.duckdb` | Original facts regenerated with `main`'s pipeline from the signals above |
| `ts_basis_daily_ts_facts_overwritten_by_test_20260911_1547.duckdb` | The facts as the test run left them (no `raw_z` / `basis_reverting`) |
| `ts_basis_daily_signals_20260911_155814.duckdb` | Automatic baseline taken by the forced rebuild (same content as the first row) |

### Not changed — decisions left open

- **`carry_rebalancer.compute_target_book` tie order.** TS Basis Daily replay/forward books remain tie-nondeterministic, because the facts query has no `ORDER BY` and the sort key is the clamped z. Carry's z is winsorized too, so fixing this shared production path needs Carry parity re-verification. The forward runner's store has not been written since 2026-08-07.
- **`fwd_ret_1m` name.** It holds a next-formation (1-day) return. It was kept because frozen research scripts read it by name.
- **EOD worker.** It is alive (heartbeat 2026-09-11 15:51) but `enabled = 0` since 2026-08-03, which is why the scheduled chain stopped. Enabling it sends Telegram messages, so that is an operator decision.
- **Research reports** computed on the old store (F4 plus the construct changes) were not re-derived.
- **2027 NSE holidays** must be added to `core/market/nse_holidays.py` before about **2027-01-18**. From then on the January expiry is within the hard-fail margin, and builds that use `build_basis_panel` (TS Basis Daily, Carry, trend continuous) will stop with a message naming the file.
- **O1 (CAS)** is unchanged; it is an observation, not a defect.

---

## Addendum — the 2026-08-31 book is a closing-auction artifact (F10), and exiting names blow up at expiry (F11)

Raised from the `/ts-basis-daily/` panel for 2026-08-31, which showed 10+ names at exactly ±3.0000 on each side. Both findings are present in the rebuilt store.

### F10 — spot and futures closes are not synchronous after CAS; auction-imbalance days fabricate basis (HIGH)

- **2026-08-31 stands alone.** The cross-sectional raw_z SD is 3.46 (the surrounding sessions run 0.7–1.1), with 22 names at +3 and 62 at −3. The extremes reverse the next session: ITC's annualized basis goes 6% → **48%** → 2%, and ICICIPRULI's 9% → **−40%** → 1%.
- **The prices are genuine; the basis is not.** The bhavcopy close is the official CAS auction print. ITC traded around ₹264.40 up to 15:14, then the 15:29 auction printed ₹255.50 on 5.46M shares (−3.4%). RELIANCE traded around ₹1,294.90 and printed ₹1,277.00 on 26.6M shares. The futures close (₹265.30 for ITC) comes from the derivatives market, which trades to 15:40 and does not take part in the equity auction.
- **Scale on 08-31.** On the 148 names matched to the 1m store, the median auction-vs-continuous gap is 1.88%, and 83 names are more than 1% apart. With the auction close as spot, 36 names show an annualized basis above 30%; with the last continuous-session price as spot, 1 does.
- **Not only 08-31.** Across 210 names, the spot close falls outside the same-day futures high–low range on 0 names on 07-27/28 (pre-CAS), 1–11 names on most post-CAS days, **56** on 08-26, **25** on 08-27 and **87** on 08-31.
- **Consequences.** These cells are real rows in each name's 252-row window, so, as with F1, they compress later z for about a year. The 08-31 books were auction-imbalance picks, not basis dislocations. This escalates observation O1 to a defect.
- **Side finding.** The 1m store's 08-31 carry-forward bars (15:15–15:28, `volume = 0`) are **not** flagged `is_synthetic`, so the CAS marker has not covered that session. The cause is under *Remediation — F10 and F11* below.

### F11 — names leaving F&O are annualized over 0–3 days at their last expiry (MEDIUM)

- A name with no next contract cannot roll, so its last ≤3 sessions price the expiring contract. `×365 / GREATEST(days, 1)` then blows the basis up. Example: DALBHARAT on 2026-08-25 (expiry day, no September contract) had basis −186% and raw_z **−29.1**, and it sat in that day's SHORT book.
- **History:** 625 cells, 145 names, 217 dates. Median \|annualized basis\| is 31.8% against 7.1% for all cells, with a maximum of 2,670%.
- The fix belongs in the TS Basis Daily build (drop cells whose selected contract is inside the roll window), not in `build_basis_panel`, so Carry's frozen panel is untouched.

### Remediation — F10 and F11 (implemented 2026-09-11)

Operator decisions:
- **F10:** after CAS, spot is the continuous-session close. The 1m gap is closed by a backfill, the daily 1m universe is widened, and a name without a bar fails the build.
- **F11:** drop the cells in the TS Basis Daily build.

| Finding | Fix | Commit | Verification |
|---|---|---|---|
| F11 | The build deletes panel cells whose **selected** contract is ≤ `ROLL_TRADING_DAYS` trading days from expiry. Such a cell only exists when there is no next contract. `build_basis_panel` is unchanged | `4cdb0f6` | Exactly the audited 625 cells / 145 names / 217 dates are dropped; no other key changes. `raw_z` moves materially (> 1e-9) on 6,859 cells, all in names that lost a cell; elsewhere the differences are float noise (≤ 7e-15). DALBHARAT's last cell is now 08-19. Unit test |
| F10 | From `CAS_EFFECTIVE` (2026-08-03), spot = the last 1m bar with `volume > 0` before the `cash_cat1` window ends (15:15). A post-CAS cell without one raises, naming each date and name. The name → `NSE_EQ\|<isin>` map comes from `instrument_master` (current ISIN); `symbol_isin` still carries pre-split ISINs (HDFCBANK `…01026` has no bars, `…01034` has 375) | `0ea73cb` | 3 unit tests (continuous close used; missing bar fails; missing file fails) |
| F10 coverage | `scripts/cas/backfill_fo_1m.py` fetches only runs of sessions on which a name has **no row at all**, so no existing bar is re-upserted. It takes copy-first baselines, then runs the CAS marker, then re-checks coverage (exit 1 on any gap). `download_all_data.py` now adds every FUTSTK underlying to the daily 1m universe | `0ea73cb`, `ad8b703` | See below |

**The gap was not a narrow download list.** Every symbol in every post-CAS file maps through `instrument_master`. Each file simply holds whatever universe its writer used: 200 to 231 symbols, changing in blocks that line up with ingest runs.
- KOTAKBANK, DLF and BAJAJFINSV were absent on 08-10..08-20.
- ANGELONE, FORCEMOT and NAM-INDIA were absent on all 29 sessions.
- In all, 570 (session, name) cells were absent; 194 of them sat in Q1/Q5 and 23 in a top-5 book.

**Backfill, 2026-09-11 17:07.** 5 fetch runs, 0 fetch errors. Against the 29 baselines in `data/_baselines/1m_pre_fo_backfill/`:
- **213,750 rows added** (570 × 375 bars), 0 existing rows changed in OHLCV, 0 rows lost.
- **The marker touched existing bars.** 14,843 existing bars went `is_synthetic` FALSE → TRUE, all in the 08-21..08-28 files. The daily download had re-fetched those files on 09-01 20:56, and its upsert resets the flag. The re-check then reported 0 absent, 0 without a continuous close, 0 unmapped.

**Live store rebuilt 2026-09-11 17:13** (baseline `ts_basis_daily_signals_20260911_171316.duckdb`, the F11-only store): 485,105 signals, 2,611 formations; 480,713 facts across 2,599 formations. 6,052 post-CAS cells were priced at the continuous close. Predictions stated before the rebuild, then checked:

| Check | Predicted | Result |
|---|---|---|
| Pre-CAS cells vs the F11 store | identical | 0 differing rows (every column) |
| 08-31 names with \|annualized basis\| > 30% (all 210 names) | falls to ~1 | 46 → **2** |
| 08-31 cross-sectional raw_z SD | well below 3.46 | 3.47 → **1.11** (neighbours 0.73–1.04) |
| 08-31 names at the ±3 clamp | far fewer than 84 | 85 → **3** |
| ITC / ICICIPRULI on 08-31 | back in line with 08-28 / 09-01 | 48% → **4.3%** / −40% → **−3.3%** |
| Keys, duplicates, NULL-z clamp | unchanged / 0 / 0 | identical key set / 0 / 0 |

**Consequence for the pipeline.** Refreshing a post-CAS formation now needs 1m bars for every F&O name on that date. `download_all_data.py` fetches them (step 6) before it refreshes (step 9). Two entry points skip that download and can hit the hard-fail when the latest date's 1m file is incomplete: a refresh started on its own (the Flask button, or `refresh_all_strategies.py` run by hand) and the orchestrator catch-up. The error names the backfill command.

### Found while fixing F10 / F11 — recorded, not changed here

- **The CAS category table ends 2026-08-28.** `data/cas/cas_category.duckdb` has no rows effective after 08-28, so `cat1_isin_symbols()` returns an empty set for 08-31 onward, and `mark_file()` then silently returns 0. The carry-forward bars on **08-31..09-10** (2,730 per session in 15:15–15:28, both existing and backfilled) are still unmarked; that is the side finding above. The backfill printed "flagged on 29 files" when only 20 were marked, and `ad8b703` makes it refuse such sessions up front. **Operator:** extend the table with `scripts/cas/build_cas_category.py`, then re-mark 08-31 onward.
- **`mark_synthetic_bars.py --apply` overwrites its own snapshots.** It re-copies every post-CAS file over `<date>.duckdb.pre_cas_mark`, so a re-run destroys the baseline of the first marking, which is the pitfall CLAUDE.md records. The F10 backfill called `mark_file` directly behind its own baselines and did not use `run()`.
- **The daily download un-marks a week of bars every run.** It re-fetches a 7-day trailing window, and the fetcher's `ON CONFLICT` sets `is_synthetic = FALSE`. The 08-21..08-28 flags restored above are one instance of that. It does not affect F10: the continuous close reads `volume > 0`, not the flag.
- **June 2023 never rolled.** The bhavcopy lists the June 2023 contracts with `expiry_dt` 2023-06-29, a holiday that is not a session, so `trading_days_to_exp` is NULL. For 5,049 cells (2023-05-22..06-27) the T-3 rule could never fire, and the last days priced the expiring contract, down to 2 calendar days. That is F11's blow-up on every name at once. It is a defect in Carry's frozen panel and falls inside the TS Basis Daily SEALED window; it was not fixed.
- **`fwd_ret_1m` still uses the auction close.** After CAS it runs from the formation's auction close to the next day's. Only the basis spot changed.
- **Test isolation.** In a full-suite run, `tests/psb1` caches `scripts/psb1/contract_arms.py` under the module name the carry panel uses, so 11 of this branch's tests loaded the wrong module and failed. `34f58c3` swaps the cache around the import; `tests/psb1` + `tests/signal_engine` pass in either order.
- **Full-suite failures that do not come from this branch.** The g1 closure guard (2 tests) fails identically on `main`. `tests/reliance_regime/test_intraday.py` (3 tests) failed only in the full-suite order and passes when run alone.

| Baseline | What it is |
|---|---|
| `ts_basis_daily_signals_20260911_164726.duckdb` | Store before F11 (the 15:58 rebuild) |
| `ts_basis_daily_signals_20260911_171316.duckdb` | Store after F11, before F10 |
| `1m_pre_fo_backfill/<date>.duckdb` (29) | Post-CAS 1m files before the F&O backfill and marker pass |
