# PTMS P3 — Family-by-family eligible research-window reconciliation

**Date:** 2026-09-13 · **Authority:** operator instruction — *"do P3 only … build a family-by-family
eligible research-window reconciliation for all seven PTMS families."*
**Access level:** meta only. No OHLC **value** was read; no feature was constructed, no candidate
run, no RFA declared, no market-data store modified. What was read: committed reports, the exposure
register, and artifact *metadata* (row counts, min/max timestamps, column names, symbol counts).

> **The answer, in one line: no family has both a certified surface and a fresh confirmatory window.
> Recommendation — none proceeds to P3 hypothesis definition today.**
>
> The useful output is not that verdict but the **ordering of blockers**. Certification is work you
> can buy; research budget is not — only calendar time makes more of it, and one family's budget is
> being **consumed right now** by a live scanner.

---

## 1. Method, and one interpretation that needs your ruling

### 1.1 Three axes, never collapsed

The instruction to treat physical availability as distinct from research availability needs a third
term, because today's certificate added one:

| Axis | Question | Who can fix a "no" |
|---|---|---|
| **Physical** | Do the bars exist, over what span? | Ingest — mostly already done |
| **Certification** | Is the surface certified for research use, over what window, on what clock? | **You can commission this work** |
| **Budget** | Has the window been read at signal level by a prior family? | **Nobody — only calendar time** |

A family needs all three. Five of seven fail on two.

### 1.2 Component-wise and transitive tracing

Path-literal grep is not admissible here — the register's own §2 records that it missed its single
largest index-1m consumer because the path was assembled from parts. Tracing was done on
**components** (surface × symbol class × date range) and followed **derivations**:

- **A derived timeframe is the same observation.** MRLC resampled the 1m store into 1h/4h/1d and
  traded those. Reading the 1h bar spends the sixty 1m bars under it.
- **A different file holding the same market is the same observation.** MRLC's archive test read a
  vendor 1m store (100 names, 2015-02 → 2025-08) that overlaps the canonical store on
  2023-01 → 2025-08 for the same names.
- **An estimation-level fit on a window constrains later signal use of that window**, which is why
  the register records level as a dimension rather than a gate.

> **⚠️ This second bullet is an interpretation, not a register rule.** The register's key is
> `surface × level × family`, and "surface" there is **file-shaped**. I applied an
> **observation-shaped** reading: the same (names, dates) read through a different file is the same
> exposure. It closes the "different file, therefore fresh window" move — but it is **not settled
> policy, and it needs an operator ruling** before a later reader treats it as one. Every row below
> marks where it was applied.

---

## 2. The finding that matters most: budget is being consumed while you read this

`data/mrlc_test/paper/paper.duckdb` is a **live forward-paper scanner on the certified surface.**
Measured today (meta only — table spans and a run log):

| Table | Span | Tickers |
|---|---|--:|
| `m1h` (resampled intraday) | 2026-04-27 09:15 → **2026-09-02 15:15** | 195 |
| `m4h` | 2026-04-27 → 2026-09-02 13:15 | 195 |
| `run_log` | scans on 2026-09-01, 09-02, **09-03** | 178–568 scanned |
| `trades` | signal dates 2026-06-11 → **2026-08-31**, 9 trades | — |

Its backtest store `data/mrlc_test/candles.duckdb` holds 1h/1d bars for **229 symbols,
2023-01-02 → 2026-08-28** — the whole certified window, resampled from the 1m store, with a trading
rule evaluated on it across four timeframes, two stretch thresholds, two stop multiples, a news
guard on/off, and a four-point slippage grid.

**Two consequences.**

1. **Family F's window is spent, not partly spent** — and spent *multiply selected*, which is worse
   than spent once.
2. **The remainder shrinks daily.** As of today, **2026-09-03 → 2026-09-11 (7 sessions)** shows no
   signal-level consumption. That is a measurement of the paper store's current state, **not a
   guarantee those dates are untouched** — the scanner runs daily and may simply not have re-run.
   No register row would have told you this: the register records reads that happened, and this one
   is happening.

**Action available today, and only to you: if Family F is ever to have a confirmatory window, the
scanner has to stop first.**

---

## 3. Reconciliation — all seven families

| Family | Surface | Certified? | Consumed at signal | Genuinely fresh | Contiguous TRAIN/HOLDOUT possible? | Blocker class | Disposition |
|---|---|---|---|---|---|---|---|
| **A** Time-only | index 1m | **No** | 2012-01 → 2022-12 (I-4/5, I-7/8); 2023-01 → ~2026-05 (I-3) | ~2026-06 → 2026-09-11 (≈70 sessions) | **No** — one regime, no split | **Certification + budget** | **BLOCKED** (unchanged) |
| **B** Price × elapsed time | index 1m | **No** | as A | as A | **No** | **Certification + budget** | **BLOCKED** (unchanged) |
| **C** Gann geometry | index 1m + 1d | **No** | as A; 1d 2016 → 2022 (D-2), 2023 → 2025 estimation (D-1) | 1m as A; 1d 2012 → 2015 and 2026 | **No** on 1m; 1d fresh part is pre-2016 only | **Certification + budget** | **BLOCKED** (unchanged) |
| **D** Temporal symmetry / cycles | index 1m + 1d | **No** | as C | as C | **No** | **Certification + budget** | **BLOCKED** (unchanged) |
| **E** Nifty/Bank cross-market | index 1m pair | **No** | I-3 read the **ratio itself** 2023-01 → ~2026-05 at signal; both legs spent 2012 → 2022 | ~2026-06 → 2026-09-11 | **No** | **Certification + budget** | **BLOCKED** (unchanged) |
| **F** Stock-level cross-sectional price-time | equity breadth 1m | **YES** — N100, 2023-01-02 → 2026-09-11 | 2023-01-02 → 2024-11-30 (E-1/E-2, ISD, cross-sectional price-time — *the same hypothesis class*); 2023-01-02 → **2026-09-02** (E-3 MRLC, multiply selected, incl. forward paper) | **7 sessions**, 2026-09-03 → 2026-09-11, **and shrinking daily** | **No** — 7 sessions is not a fence | **Budget only** | **SUBSTRATE UNBLOCKED TODAY, BUDGET-BLOCKED** |
| **G** EOD derivatives / market state | index + stock options EOD, futures EOD | **No** | Index options: 2016-07 → 2020-12 (Skew TRAIN), **2023-01-02 → 2025-12-31** (MSRP D1 straddle triage). Stock options: **2016-02-26 → 2026-08-20** (seller-edge). Futures: F-1…F-6 across TRAIN/HOLDOUT/SEALED | **Index options only**: 2016-02-11 → 2016-06-30, **2021-01-01 → 2022-12-31**, 2026-01-01 → 2026-07-17 | **Yes, narrowly** — 2021–2022 as TRAIN (2 contiguous years) + 2026-H1 as a thin HOLDOUT (~130 sessions) | **Certification only** | **CONDITIONAL — the only purchasable blocker** |

### 3.1 Families A–E — one blocker, stated once

All five live on `NSE_INDEX` 1m. **Today's certificate covers `NSE_EQ|INE…` rows only**, so the
surface these families need is *not* certified — and C1-a, the vendor bundle's timestamp
specification, is still an open operator dependency. The store-wide census added a second
complication: the vendor-era seam is a **per-symbol** property (in 2022, `Nifty Bank` and
`India VIX` are start-labelled while only `Nifty 50` is end-labelled), so an index family spanning
the seam needs a per-series rule, not a per-date one.

Budget is independently fatal. I-4/I-5 and I-7/I-8 spent 2012 → 2022 at gated signal level, and I-3
spent 2023-01 → ~2026-05 on the same surface — the register's own §6 states it: *"No genuinely
unread index-1m window remains at signal level."* The residue, roughly 2026-06 onward, is one
regime and cannot carry a TRAIN/HOLDOUT split.

**Nothing in today's certification changes A–E.** They were budget-blocked on 2026-09-12 and they
are certification-and-budget-blocked now.

### 3.2 Family F — the certificate discharged its blocker, and the other one closed in

F was recorded **SUBSTRATE-BLOCKED (permanent)**, with an explicit rescue condition: *"not to be
rescued without an independently sourced and certified PIT universe."*

**That condition is now met.** `n100_membership` is built from NSE press releases gated monthly
against 198 MCWB archives — independent of the candle store it audits — and as of today it is
certified over 2023-01-02 → 2026-09-11. **F is no longer substrate-blocked.** That is a real change
and it should be recorded as one.

It does not help, because the budget is gone:

| Segment | Sessions | Status |
|---|--:|---|
| 2023-01-02 → 2024-11-30 | 474 | ISD F1 and F4 (E-1/E-2) — **cross-sectional price-time constructs, the same hypothesis class as F** — plus MRLC |
| 2024-12-01 → 2026-08-28 | 433 | MRLC backtest (E-3), 229 symbols, multi-parameter |
| 2026-08-31 → 2026-09-02 | 3 | MRLC forward paper |
| **2026-09-03 → 2026-09-11** | **7** | **no signal-level consumption measured today** |

E-1/E-2 matter more than their 474 sessions suggest. ISD's F1 (opening-drive continuation) and F4
(overnight gap) are *cross-sectional price-time constructs on the breadth panel* — Family F's own
hypothesis class, not a neighbouring one. A successor there inherits multiplicity, not just a
consumed window.

**Disposition: not eligible for a confirmatory read. Eligible for a *pre-registration* that spends
no window** — the RFA-style pre-check, a frozen specification, and forward paper as the
confirmatory mechanism. That path requires the scanner to stop.

### 3.3 Family G — and a stale verdict corrected

The P3 catalogue's G row says: *"index options 2023→2026-07-17 not signal-read by a market-state
family."* **That is no longer true, and the correction is material.**

`scripts/msrp/triage_fee_impact.py` evaluates the **D1 next-day ATM straddle rule** — signal at
close *t* from forecast RV versus VIX-implied, enter at *t+1* open, exit at *t+1* close, gross and
net of the options fee model — over the dev window **2023-01-02 → 2025-12-31**. Its own docstring
calls it a triage rather than a backtest and flags the signal as in-sample, but a **trading rule
evaluated on a window is a signal-level read**, and a straddle rule conditioned on forecast-vol
versus implied-vol **is a market-state construct**. The register records this consumer under O-2
without pinning its window; the catalogue's verdict predates the pinning.

Pinned windows, measured from the artifacts today:

| Surface | Physical span | Signal-consumed | Fresh |
|---|---|---|---|
| Index options EOD | 2016-02-11 → 2026-07-17 | 2016-07 → 2020-12 (Skew TRAIN, FAILED at TRAIN so its 2021–22 HOLDOUT was **never read**); 2023-01-02 → 2025-12-31 (MSRP D1) | 2016-02-11 → 2016-06-30 · **2021-01-01 → 2022-12-31** · 2026-01-01 → 2026-07-17 |
| Stock options EOD | 2016-02-11 → 2026-09-11 | **2016-02-26 → 2026-08-20** — the seller-edge study's own artifact (`stock_straddles.parquet`, 134,515 rows) spans the whole store | effectively none |
| Futures EOD | 2016-02-11 → 2026-09-11 | F-1…F-6: Carry, TS Basis, IVOL, Trend, Skew, LAG, F1 — TRAIN/HOLDOUT/SEALED all spent except TS Basis Daily's preserved 876 formations | none usable |

So G's budget is **index options only**, and the one usable shape is **TRAIN 2021-01 → 2022-12
(two contiguous years) with a thin HOLDOUT in 2026-H1 (~130 sessions)**. Both are uncertified: the
09-12 matrix reads UNCERTIFIED for every EOD surface, and today's certificate explicitly does not
cover them.

**Disposition: CONDITIONAL, and the only family whose blocker is purchasable.** A P2-style
certification pass over the index options EOD surface — contiguity, expiry/strike integrity,
settlement-price semantics, PIT expiry mapping — would convert G from blocked to eligible without
spending a single session of budget.

---

## 4. Register corrections this reconciliation implies

**Not applied.** The register is append-only and its rule is *append a row before a read*; these are
rows for you to append, not for me to edit.

| Row | Recorded | Measured today | Why it matters |
|---|---|---|---|
| **E-3** | "2023-01-01 → present, signal, MRLC" | Backtest store 2023-01-02 → **2026-08-28**, 229 symbols; forward paper to **2026-09-02**, still running | Turns "→ present" into a moving boundary. The register cannot express a *live* consumer |
| **O-1** | "2023 → 2026" | Artifact entry dates **2016-02-26 → 2026-08-20** | The row understates the read by seven years |
| **O-2** | Window not pinned | Skew TRAIN 2016-07 → 2020-12; MSRP D1 triage **2023-01-02 → 2025-12-31** | The catalogue's G verdict rests on this gap |
| **E-1/E-2** | Recorded correctly | — | Worth re-reading before any F successor: same hypothesis class, so multiplicity carries |
| **New class** | — | A **live scanner** consuming a certified surface | The register has no row type for "consumption in progress" |

---

## 5. Recommendation

**No family proceeds to P3 hypothesis definition on the strength of a fresh confirmatory window.**
Ordered by what could change that:

1. **G — EOD derivatives / market state. The only one worth spending effort on now.** Its blocker is
   **certification**, which is work you can commission; it holds two contiguous unread years
   (2021–2022) plus a thin 2026-H1 tail on index options. Recommend: authorize a P2-style
   certification pass on the index options EOD surface, then re-run this reconciliation. **Do not
   pre-register a G construct before that pass** — the catalogue's stale verdict is exactly what
   happens when a family is specified against an unpinned window.
2. **F — stock-level cross-sectional price-time. Newly substrate-clear, budget-dead.** Recommend two
   decisions, both yours and both available today: **(a) stop the MRLC paper scanner** if F is to
   have any future window, and **(b)** if F is wanted, pre-register it now with **forward paper as
   the confirmatory mechanism**, which spends no historical budget and accrues ~21 sessions a month.
3. **A–E.** Recommend recording them as **closed for this cycle** — certification *and* budget, on a
   surface whose seam is per-series. Re-opening any of them means certifying the index 1m surface
   (needs C1-a from you) *and* manufacturing budget through forward time. That is not a P3 decision;
   it is a programme decision.

**What would create budget, in order of cost:** forward paper (calendar time, no risk) · certifying
a surface nobody has read — the VIX assets remain the largest genuinely unread surface in the repo
at exposure level NONE, though a volatility-state hypothesis is a different hypothesis from any of
A–G · nothing else. There is no third mechanism.

---

## 6. What this report is not

It defines no hypothesis, declares no RFA, proposes no construct, and authorizes no read. It read no
OHLC value and modified no market-data store. The seven dispositions above are inputs to your
decision about which, if any, family gets a P3 specification — and on the evidence, the honest
recommendation is **one certification pass (G), one operational decision (stop the scanner), and no
new hypothesis work until one of them lands.**
