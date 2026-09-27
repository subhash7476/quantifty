# STOCK-STRADDLE-M10 — Forward Pre-Registration

**Status: DRAFT, awaiting operator approval of D1–D14 (§11).** It freezes at the commit that
records the approval. From then on it is immutable: SHA-256 over the file's LF bytes, recorded
in the freeze commit message and the CLAUDE.md RFA table.

**Deadline.** The freeze commit must exist **and be pushed to origin before 2026-10-12 15:15 IST**,
when the first entry capture runs. If it misses, cycle 1 becomes the **2026-11-23** expiry, not
11-24, which is a holiday (entry 2026-11-06, exit 2026-11-20). The count of 36 cycles is
unchanged; the window just ends one month later.

| Item | Reference |
|---|---|
| RFA declaration (FROZEN 2026-09-27) | `governance/rfa/declarations/stock_straddle_m10.py`, whole-file SHA-256 `a2015e0f135f470a13c2ad388d7bb4bc6c9b00328897c46f2f42adb2c4a891c5`, body `9ecb9116…` |
| RFA report | `docs/reports/STOCK-STRADDLE-M10_RFA.md`: **PROCEED**, max power 0.8211, n_required 34 / 65 / 177 |
| Evidence | `OPTIONS_SELLER_EDGE_STUDY_2026-09-11.md` · `STOCK_STRADDLE_SELLING_EVIDENCE_AUDIT_2026-09-24.md` · `STRADDLE_CA_FILTER_SPLIT_2026-09-27.md` (W6) |
| Quote capture | `scripts/research/options_seller_edge/straddle_cycle_capture.py` (§5) |

This document sets the rules only. It authorizes paper tracking and nothing else: no live
orders and no capital.

---

## 1. Hypothesis and test

- **H1 (one-sided):** the mean per-cycle net seller return on premium is > 0.
- **H0:** the mean is ≤ 0.
- **Statistic:** one-sample t on the **36 counted cycle means** (§8), against t(0.95, 35) = **1.690**, at α = 0.05.
- **Confirmation is read once, after cycle 36.** There is no interim confirmation look (§9).
- **What the RFA says about this test:** PROCEED means "not provably infeasible" and is a floor.
  - At the declared central Sharpe of 1.08, 36 cycles give power well below 0.80. The central corner needs 65.
  - A non-rejection at cycle 36 is therefore the expected outcome unless the edge is near the optimistic corner.
  - A non-rejection is reported as **NOT CONFIRMED**, never as falsified. Only §9 falsifies.

## 2. Instrument and cycle calendar

- **Instrument:** NSE single-stock options, monthly expiry.
  - Short one ATM call and one ATM put, **one lot per name**.
  - The strike is taken off the same-expiry future (§4).
- **Monthly expiry E:** a futures expiry date that lists ≥ 100 stock underlyings in the instrument master (weeklies and odd dates list fewer than 20).
- **Entry:** the **T-10** session, i.e. the 10th regular session strictly before E.
- **Exit:** the **T-1** session, the last session before E, so physical settlement is never reached.
- **Session counting (D10):**
  - Sessions are regular trading sessions per `core/market/trading_calendar.is_session`.
  - A special session is not counted. For example, the Diwali Muhurat that falls on Sunday 2026-11-08, inside the Nov-23 hold, does not count.
  - The study counted every futures-bhavcopy date. Under that rule the Nov cycle's T-10 would land on the Muhurat hour itself.

| Cycle | Expiry E | Entry (T-10) | Exit (T-1) |
|--:|---|---|---|
| 1 | 2026-10-27 | 2026-10-12 | 2026-10-26 |
| 2 | 2026-11-23 (11-24 is a holiday) | 2026-11-06 | 2026-11-20 |
| 3 | 2026-12-29 | 2026-12-14 | 2026-12-28 |

- **The calendar ends at 2026-12-31.**
  - `run_if_session.py` exits 2 and alerts from 2027-01-01.
  - The 2027 holidays must therefore be in `nse_holidays.py` / `trading_calendar.py` before then, or cycle 4 (Jan 2027) is not captured.
  - The same obligation recurs every year of the window.

## 3. Universe and eligibility at entry

Every rule below is evaluated from data that exists at the entry pass. No input depends on
anything after entry.

A name is **eligible** for cycle E if all of the following hold.

| # | Rule | Source |
|---|---|---|
| U1 | Stock (not index) future listed for E in the instrument master snapshot used at entry | master; `INDEX_NAMES` excluded |
| U2 | An ATM strike exists under §4, with both legs two-sided and traded that day | entry capture |
| U3 | History filters from `cycle_study.load()`: `n20 ≥ 15`, `n60 ≥ 40`, `rv20 > 0` | front-future daily log returns in `futures_bhavcopy` (same contract, consecutive sessions, days with \|ln r\| ≥ 0.25 excluded, as in `build_stock_straddles.py`), **through T-11**, the previous session (D4) |
| U4 | Not in the F&O ban period on the entry date | captured `fo_secban.csv` (D6) |
| U5 | No known corporate action with ex-date in (entry, exit] | captured NSE corporate-action list (D5) |

**Two filters from the study are removed, not replaced:**
- `ca_in_hold`, which dropped cycles on the hold-period outcome (audit §7.1; W6 showed the dropped rows were genuine crashes);
- the exit-existence conditions `ce_exit / pe_exit / fut_exit notna()`.

A missing exit is priced by the §6 fallback. It is never dropped.

## 4. ATM selection (D3)

The selection uses the **primary pass** (c-5, §5).

1. **Reference price** = the pass's last traded price of the same-expiry future.
2. **Candidate strikes** are those where both the CE and the PE have a best bid > 0, a best ask > 0 and volume > 0 for the day. This is the live equivalent of the study's "both legs traded at entry".
3. **ATM** = the candidate nearest the reference price. A tie goes to the lower strike, as in the study.
4. The ATM must lie within **5 %** of the reference price. Otherwise the name fails U2.

**If a name's primary pass is unusable**, the whole name is taken from the next pass in the order
**c-2, c-10, c-20**. Unusable means `api_fail`, no future quote, or no candidate strike. Legs are
never mixed across passes. If no pass qualifies, the name fails U2. That is an ex-ante exclusion:
nothing about the outcome is known at 15:35 on T-10.

## 5. Quote capture (the Sep-29 failure mode)

The Sep-29 paper cycle was lost because no stock-option quote was captured at entry (audit §5).
Capture is now a scheduled, alerting job:

- **Trigger:** Windows task `\Nifty\StraddleCapture`, daily at 15:15, through `scripts/ops/run_if_session.py straddle_capture`.
  - It is a no-op unless today is T-10 or T-1 of the next monthly expiry.
  - A non-zero exit sends a Telegram alert. That happens if futures coverage < 90 % on any pass, if any quote chunk fails after 3 retries, or if the job starts after the derivatives close.
  - Success sends a one-line Telegram summary.
- **Passes (D2):** at 20, 10, 5 and 2 minutes before the derivatives close, from `session_schedule`. Post-CAS that is 15:20, 15:30, **15:35 (primary)** and 15:38.
- **What each pass quotes:**
  - every stock future for E;
  - at entry, every CE/PE within 10 % of that pass's future LTP;
  - at exit, **exactly the option keys captured at entry**, with ATM never recomputed.
- **Method (D1):** batched Upstox `market-quote/quotes`, 450 keys per call, about 15 calls per pass.
  - A chunk that still fails after retries is stored as `api_fail`, distinct from `missing`.
  - Zero prices are stored as NULL.
  - The card named the option-chain API. It quotes spot, not the future the ATM rule needs, and would take more than 200 calls per pass.
- **Entry artifacts:** the day's `fo_secban.csv` and NSE's corporate-action list for (entry, exit], stored as raw bytes.
- **Store:** `data/research/straddle_m10/capture.duckdb`, with tables `capture_runs`, `quotes` and `artifacts`.
- **Changes after the freeze:** the tool may be changed only to fix mechanical defects. Every change is logged in §12, and none may alter a rule in this document.

**Dry-run evidence before the freeze** is in §10.

## 6. Fills, costs, and the missing-quote rule (D7)

- **Entry (sell):** each leg fills at the **best bid** of the pass that selected the name (§4).
- **Exit (buy):** each leg fills at the **best ask** from the first pass that has one, in the order **c-5, c-2, c-10, c-20**.
- **Exit fallback,** used when there is no ask in any pass, or the exit capture failed:
  - fill = **1.10 × max(** highest captured LTP that day, the T-1 bhavcopy close (settle if untraded) **)**;
  - it is applied per leg, the leg is flagged, and it is never dropped;
  - it is seller-hostile on purpose, and it is fixed now, before any forward quote exists.
- **Fees:** `core/execution/options/fees.py` at the trade date's schedule, which includes the **0.15 % sell-side options STT from 2026-04-01**.
  - Four orders per name (2 SELL at entry, 2 BUY at exit), quantity = lot size.
  - ₹20 brokerage per order, plus exchange, SEBI, GST and stamp charges.
  - The file is imported read-only. It is on NiftyShield's hash list and is not edited.
- **Per-name net return on premium:**
  `r = (bid_CE + bid_PE − ask_CE,exit − ask_PE,exit − fees / lot_size) / (bid_CE + bid_PE)`
- **The spread assumption is replaced.**
  - The RFA band was built on a 2 % round-trip spread (audit §7.2, a single mid-cycle day).
  - The forward test pays the live spread at T-10 and T-1, which is unmeasured and likely wider on T-1's shrunken premiums.
  - This threat to the band is disclosed here. The band is not touched.

## 7. Unit of observation and weighting (D12)

- **One trade = one cycle.**
  - Its value is the **equal-weight mean of r across the cycle's eligible names**.
  - It is not lot-weighted or notional-weighted.
  - Names within a cycle are never counted as separate trades.
- **Reported per cycle:**
  - names eligible and traded;
  - gross return (before fees and spread) and net return;
  - the spread paid;
  - the share of legs filled by the §6 fallback;
  - exclusions by rule (U1–U5).

## 8. Counted cycles, void cycles, and the window (D8)

- **Void cycle:** the **entry** capture has no pass with futures coverage ≥ 90 %, or it produced no eligible name.
  - A void cycle is not traded and is not counted.
  - The window extends by one cycle.
  - This is legitimate because a void is decided at 15:38 on T-10, before any of the hold is known.
- **Exit gaps never void a cycle.** They take the §6 fallback.
- **More than 3 voids in the window** is escalated to the operator. The rules do not change.
- **Window:** 36 counted cycles from cycle 1 (§2), nominally through the Sep-2029 expiry.

## 9. Interim looks and falsification (D9)

- **No interim confirmation look.** Confirmation is read once, at cycle 36.
- **Falsification (the only early stop).** From counted cycle 6 onward, after each cycle:
  - **F1:** the one-sided t for "mean < 0" on the cycles so far is ≥ **2.33** (p < 0.01). Or,
  - **F2:** the cumulative sum of cycle net returns is ≤ **−100 % of premium**, i.e. the book has given back more than a full cycle's premium in aggregate.
  - Either one ends the test as **FALSIFIED**.
- **Why this does not inflate the confirmation error rate:** stopping early can only prevent a rejection of H0, never cause one. It costs power, not size.
- **For scale:** the confirmation window's per-cycle SD was about 18.6 % of premium (mean +8.07 % at t 2.85 over 43 cycles, W6). F2 is about 5 average cycle SDs.

## 10. Dry-run evidence (filled before freeze)

**Pending.** Monday 2026-09-28 is the first live close. Each dry run records:
- futures coverage;
- names with a two-sided, traded ATM pair within 5 %;
- the share of option rows with both bid and ask;
- the counts of `api_fail` / `missing` / one-sided rows per pass.

Command:

```
python scripts/research/options_seller_edge/straddle_cycle_capture.py --dry-run --role entry \
    --expiry 2026-10-27 --db data/research/straddle_m10/dryrun.duckdb
```

Run it from `F:\Nifty` once it is on main, before 15:20. A worktree needs
`--credentials F:/Nifty/config/credentials.json --master F:/Nifty/data/instruments/nse_fo_instruments.duckdb`.

The 2026-09-27 (Sunday) smoke run confirmed the plumbing:
- 213 stock futures and 11,995 listed options for 10-27;
- both artifacts fetched, including a ban file stamped "Trade Date 28-SEP-2026";
- every quote chunk recorded as `api_fail` (HTTP 401, expired token) rather than as absent.

It is **not** live evidence.

## 11. Operator decisions

| # | Decision | Recommendation |
|---|---|---|
| D1 | Quote source | Batched `market-quote` (future + options in about 15 calls), not per-name option-chain (spot only, 200+ calls) |
| D2 | Pass times; which is primary | c-20 / c-10 / **c-5** / c-2 off the derivatives close, primary c-5 (15:35 post-CAS). The cash auction has ended and 5 minutes of F&O trading remain |
| D3 | Live ATM definition | Nearest strike to the c-5 future LTP among strikes with both legs two-sided **and** volume > 0, within 5 %. Whole-name fallback to c-2, c-10, c-20 |
| D4 | History window for U3 | Through **T-11**. At 15:35 there is no T-10 bhavcopy yet; the study's window included the entry day |
| D5 | Corporate-action rule | Exclude when the NSE list captured at entry shows an ex-date in (entry, exit] for any purpose **other than a dividend**, or a dividend ≥ **2 %** of the c-5 future LTP. If the capture failed, the operator runs `download_corporate_actions.fetch(entry+1, exit)` before the T-9 open. If that also fails, the cycle carries no CA exclusion, and this is disclosed. `equity_bhavcopy.duckdb:corporate_actions` is used **only afterwards**, to report CAs in the hold that were unknown at entry. Those names stay in the book |
| D6 | Ban rule | Exclude names on the captured `fo_secban.csv` **whose header trade date equals the entry date**. Otherwise use NSE's dated archive file for the entry date. If neither exists, apply no ban exclusion and disclose it |
| D7 | Missing-quote rule | §6: entry is whole-name pass fallback, else ineligible. Exit is ask pass fallback, else 1.10 × max(LTP, bhavcopy close or settle). Never drop |
| D8 | Void cycles | §8: void only on an entry-capture failure, and the window extends by one. Escalate at more than 3 voids |
| D9 | Interim looks | None for confirmation. Falsify on F1 (t ≥ 2.33 for mean < 0) or F2 (cumulative ≤ −100 % of premium), from cycle 6 |
| D10 | Session counting | Regular sessions per `trading_calendar.is_session`. Muhurat and other special sessions are not counted |
| D11 | Sizing and margin | **Paper only.** Margin comes from the broker basket (`POST /v2/charges/margin`) per **ADR-025**, recorded descriptively at entry when available. The frozen SPAN stack cannot size options (`MissingRiskArray` on every option leg), and `NseMarginEngine` is never handed this book. Margin never enters the test statistic, whose unit is % of premium |
| D12 | Weighting | Equal-weight mean across names of r, one lot per name |
| D13 | Fees | `fees.py` schedule at trade date (0.15 % STT from 2026-04-01), ₹20 per order |
| D14 | Capture trigger | Scheduled task (**decided by the operator on 2026-09-27**) |

## 12. Post-freeze change log

*(empty)*

---

## Appendix A — Prior exposure

Copied verbatim from the frozen RFA declaration (`stock_straddle_m10.py`, `prior_exposure`):

> Every historical window of this construct has been read; there is NO unread history.
> (a) Discovery 2016-01 -> 2022-12: the entry offset (10 sessions before expiry) was selected here among six offsets (study s2.1).
> (b) Confirmation 2023-01 -> 2026-08-24: predictions written first (transcript-verified, audit s3), then read once -> SPENT. Liquidity cuts, the conservative exit and the >=100-contract screen were chosen after it was read (audit s4) and are descriptive only.
> (c) Post-reform sub-window 2024-11-20 -> 2026-08: spent with (b).
> (d) W6 (2026-09-27) re-read (a)-(c) for filter accounting only; it chose nothing.
> (e) The same 2023+ stock-option data underlies the Options-Wall and seller-edge index checks (index selling showed nothing).
> Consequence: confirmation can only be FORWARD, which is why n_available below counts future cycles.

**Written without new data reads.** This pre-registration used no stock-option data from 2023
or later, beyond numbers already published in the documents above. It used no index-option
data from 2016–2022 at all. The only live reads were:
- the instrument master, for listed names and expiry dates;
- the calendar;
- the Sunday smoke run, which returned no quotes.

## Appendix B — Stated threats (from the RFA, not re-litigated)

1. **Regime.** The forward window is entirely post-reform, where the observed Sharpe is about 1.0 on 21 cycles (t 1.35).
2. **Shrinkage.** A forward haircut is the base rate.
3. **Distribution.**
   - The book is short crash risk: W6 kinked beta gives β_down +0.55 (se 0.08), and confirmation skew is −1.19.
   - A t-test on a short-gamma book overstates what can be confirmed.
   - W6's restored crash rows averaged −350 % of premium.
4. **Costs.** Live T-10 and T-1 spreads replace the 2 % assumption (§6).
