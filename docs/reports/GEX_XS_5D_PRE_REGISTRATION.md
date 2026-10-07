# GEX-XS-5D — Pre-Registration

**Status: FROZEN 2026-10-06.** D1–D11 were approved as recommended by the operator on 2026-10-06, and P1 was certified the same day (§11, calendar digest `067fa688…`, E_s 2026-10-05). From the freeze commit on, everything above the §14 heading is immutable. **The frozen SHA-256 is taken over the file's LF bytes up to, but not including, the line `## 14. Post-freeze change log`**, so the appendices are covered and appends to §14 do not move it. It is recorded in the freeze commit message and the CLAUDE.md RFA table, and pinned in the stage runner (P3). §14, at the end of the file, may be appended to only to log mechanical fixes.

| Item | Reference |
|---|---|
| RFA declaration (FROZEN 2026-10-06) | `governance/rfa/declarations/gex_xs_5d.py`, whole-file SHA-256 `b9e33df2d4825ed1e94c961caef4e7bb22541f4318fdcb16ab8841d9796da700`, body `a0bc30c4…` |
| RFA report | `docs/reports/GEX-XS-5D_RFA.md`: **PROCEED**, n_required 19 / 101 / 2005 against 184 |
| Parent | GEX Stage A (`docs/superpowers/specs/2026-09-23-gex-regime-stage-a-design.md`, `GEX_REGIME_STAGE_A_{TRAIN,HOLDOUT}.md`) |
| GEX code (reused, NOT edited) | `core/analytics/gex_history.py` (`select_strikes`, `day_regime`, `implied_vol`, `bs_gamma`) |

This document sets the rules only. It authorizes a two-stage read of historical data and nothing
else: no strategy code, no `SignalEvent`, no paper book, no capital. **A PASS is a state-variable
finding** (like Stage A), never a trade.

The declaration binds this document. Its construct definitions and control set are not
re-opened here. This document pins only what the declaration leaves to it: implementation
detail, exclusions, the stage design and the runner guards.

---

## 1. Hypothesis and test

- **H1 (one-sided):** the mean per-formation cross-sectional Spearman IC between residualized
  normalized net GEX and the residualized 5-session outcome is **< 0**.
- **H0:** the mean IC is ≥ 0.
- **Statistic:** mean IC over the stage's valid formations; Newey–West HAC standard error,
  **lag 4**; t = mean / se; one-sided p from t(n − 1).
- **Two stages (D1):**
  1. **DEV** 2016-02-11 → 2022-12-30, read once. **PASS:** mean IC < 0 and one-sided p < 0.05.
     DEV FAIL ends the construct and leaves SEALED unread.
  2. **SEALED** 2023-01-02 → the end date fixed at freeze (§2), read once, only after a DEV PASS.
     **PASS:** mean IC < 0 and one-sided p < 0.05.
- **Nothing is selected on DEV.** Every definition, threshold and control is pinned here before
  either stage is read. DEV is a cheap kill that protects the sealed window, not a fitting
  surface.
- **The RFA's PROCEED was computed on SEALED alone.** It says nothing about the joint two-stage
  test. The joint power is in §9.

## 2. Windows and formations (D10, D11)

- **Formation dates:** every 5th session from the stage's first session (phase pinned: the first
  session is formation 1).
- **Sessions** are weekday dates present in `stock_options_bhavcopy`, **minus the special
  (Diwali Muhurat) sessions**: 2017-10-19, 2018-11-07, 2021-11-04, 2022-10-24, 2024-11-01,
  2025-10-21. Those are the six weekday Muhurat dates the store holds. The weekend ones (2016,
  2019, 2020, 2023) are not in it, and it holds no weekend date at all. A one-hour session would
  put a near-zero-range day into a 5-day Parkinson mean.
  - `core/market/trading_calendar.is_session` covers only 2023–2026, so it cannot define DEV
    sessions. The pinned list is the rule for both stages.
  - Any special session after 2025 that falls inside the SEALED span at freeze is added to the
    list in the freeze commit, before the read.
- **Target window:** sessions t+1..t+5. A formation is kept only if t+5 lies inside its own
  stage, so no stage reads a bar outside itself. Targets never overlap.
- **DEV:** 1,697 sessions → **339 formations**, 2016-02-11 → 2022-12-22 (last target ends
  2022-12-29).
- **SEALED:** formations from 2023-01-02. Its end date **E_s = the minimum of the max
  `trade_date` of the stock-option, equity and futures bhavcopy stores on the freeze date**,
  recorded in the freeze commit. The last formation is the last one whose t+5 ≤ E_s. At drafting
  (E_s 2026-10-05): 923 sessions → **184 formations**, last formation 2026-09-23 (target ends
  09-30). The count matches the declaration, and the dates shift by the two SEALED Muhurat days
  removed. The count only grows.

## 3. Universe and mapping

A name enters formation t if all of the following hold on t:

| # | Rule |
|---|---|
| U1 | A FUTSTK underlying in `futures_bhavcopy` on t, with a stock-option chain in `stock_options_bhavcopy` on t |
| U2 | An `EQ`-series row in `equity_bhavcopy` on t |
| U3 | Passes the per-name validity rule (§4, D3) and every input in §5–§6 exists |
| U4 | Not excluded by the results rule (§7, D2) |

- **Mapping is time-aware.** The option and futures underlying symbol on t is joined to the
  same-date `equity_bhavcopy` symbol. Any join across dates (t+1..t+5 outcome bars, t−19..t
  control bars, returns) follows the entity through `symbol_entity_intervals`, never a bare
  symbol. Renames and recycled tickers are CLAUDE.md pitfalls.
- **Price bases.** Parkinson inputs (outcome and rv controls) use **as-traded same-day**
  high/low from `equity_bhavcopy`; a same-day ratio is basis-free. Signed returns use
  **`equity_bhavcopy_adjusted`**, because they span days. The 1m store is not used.

## 4. GEX construction (per name, per formation)

- **Expiries:** **every listed monthly expiry** of the name, as the declaration pins, except the
  series expiring on t. At T = 0 gamma is undefined, so that exclusion is implementation detail,
  not a narrowing. Stage A's 1 ≤ DTE ≤ 45 cap is **not** applied, because it would drop the far
  month the declaration includes.
- **Forward (D4):** F = the same-expiry stock future's `close` on t from `futures_bhavcopy`. An
  expiry with no future, or with |F / cash close − 1| > 0.03, is dropped. Stage A's
  `parity_forward` is not used for stocks.
- **Strikes, IV, gamma, N:** `select_strikes` and `day_regime` from `gex_history.py`, unchanged:
  rate 0.065, out-of-the-money leg only, traded (`contracts > 0`), close ≥ 0.5,
  |ln(K/F)| ≤ 0.10, IV solved in [0.01, 3.0], sign convention **dealers long calls, short puts**.
  `MIN_PRICE` and `MONEYNESS_BAND` stay hardcoded inside `select_strikes`.
- **N_i,t** = `day_regime(...).net_norm`, normalized net GEX in [−1, 1].
- **Per-name validity (D3), applied in the new runner, not in `gex_history.py`:** **≥ 6 kept
  strikes across the name's expiries, of which ≥ 2 lie below and ≥ 2 at or above their own
  expiry's F** (counted across expiries, exactly as the census counted). Stage A's
  `MIN_STRIKES = 10` is a per-day index rule and is not applied.
  - The 6 / 2 / 2 threshold was chosen from a structural census (Appendix A, item 8). Expected
    names per formation: ~100 (2016), 139–154 (2017–19), 128–190 (2020–22), 180–213 (2023+).
    The census counted expiries with DTE ≤ 45 only. Including the far month can only add kept
    strikes, so these are lower bounds and the threshold is conservative.

## 5. Outcome (D5, D9)

- **Parkinson variance per session:** P_d = (ln(H_d / L_d))² / (4 ln 2), as-traded `EQ` high/low.
- **RV_i,t** = mean of P_d over d = t+1..t+5, × 252 (annualized variance).
- **IV expiry:** the name's nearest expiry that expires **after** session t+5, so the pricing
  contract never expires inside the target window.
- **ATM IV:** from that expiry's kept strikes (§4): linear interpolation of IV in ln(K/F) between
  the nearest kept strike below F and the nearest kept strike at or above F. If either side has
  no kept strike, the name is dropped.
- **y_i,t = ln(RV_i,t / IV_ATM,i,t²)**, a variance ratio as in Stage A.
- **Missing or zero data:**
  - A missing `EQ` row on any of t+1..t+5 (suspension, delisting) drops the name from that
    formation. This uses information after t, so the count is reported per stage (§10).
  - A zero range (H = L) gives P_d = 0 and stays in the mean. If the mean is 0, the name is
    dropped.

## 6. Controls (binding — from the declaration, not re-opened)

On formation t, for each name:

| Control | Definition |
|---|---|
| ln IV | ln of the §5 ATM IV |
| ln rv5 | ln of mean P_d over t−4..t; ≥ 4 of 5 sessions present |
| ln rv20 | ln of mean P_d over t−19..t; ≥ 15 of 20 sessions present |
| r_t | ln(C_t / C_{t−1}), `equity_bhavcopy_adjusted` |
| r_5 | ln(C_t / C_{t−5}), `equity_bhavcopy_adjusted` |

A name missing any control is dropped. **No other control is added.** In particular there is no
IV term-structure ratio and no results-day control. Results are handled only by the §7
exclusion, which the declaration permits.

## 7. Results-day exclusion (D2)

The declaration requires results days to be handled "only from a point-in-time calendar". NSE's
board-meeting archive provides one: every intimation carries `bm_timestamp` (filing time) and
`sysTime` (dissemination time), back to at least January 2016. This was probed 2026-10-06
(Appendix A, item 9).

- **Rule:** name i is excluded from formation t if any archive row satisfies all three:
  1. it is a results meeting: case-insensitive `result` in `bm_purpose` or `bm_desc`;
  2. its meeting date `bm_date` falls on a **calendar date** from date(t) to the date of session
     t+5, **inclusive**. Weekend and holiday meetings inside that span count, and board meetings
     often fall on weekends. Day t is included because results released after the close on t
     land in t+1;
  3. its known time, the **later of `bm_timestamp` and `sysTime`**, is ≤ **the derivatives close
     on t per `core/market/session_schedule`** (15:30 before CAS, 15:40 from 2026-08-03).
- **Rescheduled meetings:** each row is taken as of its own known time, and only with the date
  fields that row carried when it was filed. A name is excluded if any row known by t's close
  dates a results meeting inside the window. A row whose `bm_date` was overwritten later (a
  non-null `oriiginalMeetingDate` / `proposedMeetingDate`) is a look-ahead hazard; P1(e) measures
  it. Withdrawn intimations may have been deleted from the archive. That can only under-exclude,
  which adds noise, not bias toward H1.
- **Not excluded:** a results meeting inside the window whose intimation became known after t's
  close. The name stays, as noise. A post-hoc split that excludes every window containing any
  results meeting is reported descriptively (§10), never as the test.
- **Mapping:** archive rows join to names by ISIN issuer prefix through `symbol_isin` /
  `symbol_entity_intervals`, with `bm_symbol` on the meeting date as a fallback. Face-value
  ISIN re-issues are a CLAUDE.md pitfall.

## 8. Per-formation statistic (D6, D8)

1. Winsorize y and each control at the 1st and 99th cross-sectional percentiles of the
   formation. N is bounded and is not winsorized.
2. OLS of N on [1, ln IV, ln rv5, ln rv20, r_t, r_5] → residual N̂. The same regression for y →
   residual ŷ.
3. **IC_t = Spearman(N̂, ŷ).**
4. **Minimum cross-section: 80 names** after every rule. A formation below 80 is **void**: not
   counted, and reported. If voids exceed 10 % of a stage's formations, the operator is told and
   the rules do not change.

## 9. Power of the two-stage design (stated before any read)

At the declared bands. DEV's spread is taken 0.01 above SEALED's, because 2016–19 cross-sections
are thinner (sampling floor ~0.09–0.10 against 0.075). The AC1 haircut is n_eff = n(1 − ρ)/(1 + ρ).

| Corner | AC1 | DEV → SEALED (D1 recommended) | Stage A style: TRAIN t ≤ −2.0 → HOLDOUT → SEALED | TRAIN one-sided → HOLDOUT → SEALED | SEALED only |
|---|--:|--:|--:|--:|--:|
| Optimistic (δ 0.060, sd 0.10) | 0 / 0.3 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| Central (δ 0.035, sd 0.14) | 0 / 0.3 | **0.96 / 0.75** | 0.78 / 0.36 | 0.83 / 0.43 | 0.96 / 0.80 |
| Pessimistic (δ 0.010, sd 0.18) | 0 / 0.3 | 0.05 / 0.02 | 0.00 / 0.00 | 0.01 / 0.00 | 0.19 / 0.14 |

- Pooling costs almost nothing against SEALED alone, yet keeps a kill that leaves SEALED unread.
  Three gates cost about half the power at central with AC1 0.3.
- **At the pessimistic corner every design fails.** A non-rejection is reported as **NOT
  DEMONSTRATED**, never as falsified.

## 10. Reported alongside (descriptive, not part of any pass rule)

Per stage:
- names per formation; voids; drops by reason (U1–U4, §5 missing bars, results exclusions);
- IC series AC1, so the power assumption is checked against the data;
- per-year mean IC;
- splits: before / after **2019-10** (physical settlement of all stock F&O, phased in from
  2018-07); before / after **2024-11-20** (SEBI F&O reform, SEALED only); before / after
  **2026-08-03** (CAS, SEALED only); windows containing a monthly expiry vs not;
- the post-hoc results split (§7);
- N's sign alone in place of N; Pearson IC in place of Spearman;
- the other four formation phases (mean of their ICs), so the phase choice is shown not to
  matter. They are never the test.

## 11. Preconditions (all before either read)

- **P1 — results calendar.** A committed ingest script writes the NSE board-meeting archive,
  2016-01-01 → E_s, to `data/research/gex_xs_5d/board_meetings.duckdb`, raw rows plus parsed
  known time. Certification reads no option, price or outcome data:
  - (a) every month from 2016-01 to E_s returns rows. The API filters on meeting date (verified
    2026-10-06), so month-by-month fetches cover every meeting. Fetches are by month, and a
    busy month was checked to return the same rows whole as in halves;
  - (b) for each calendar year, ≥ 90 % of that year's FUTSTK names have ≥ 3 **distinct**
    results meeting dates in that year. The denominator is names with a FUTSTK row on ≥ 60 %
    of that year's sessions, so names listed in F&O mid-year are not counted against the
    calendar;
  - (c) known date ≤ meeting date on ≥ 99 % of results rows;
  - (d) ≥ 98 % of FUTSTK names map to archive rows by ISIN or symbol;
  - (e) per year, the count and share of results rows with a non-null `oriiginalMeetingDate` or
    `proposedMeetingDate`, and of duplicate rows per (ISIN, meeting).
  - **A year that fails (b), or whose (e) revision share exceeds 2 %, has every formation whose
    window touches it declared void** in whichever stage it falls. It is not re-specified after
    the fact. If voids then exceed 10 % of a stage, the operator is told (§8) and the rules do
    not change.
  - **A failure of (a), (c) or (d) means P1 is not certified and the freeze is blocked.** The
    operator decides what to do, and any change is logged before the freeze. Calendar data is
    not outcome data, so the change stays pre-read, but it is disclosed.
  - These consequences were pinned 2026-10-06, before any archive month was ingested.
  - **Result 2026-10-06 (E_s 2026-10-05): CERTIFIED, no void years**
    (`GEX_XS_5D_BOARD_MEETINGS_CERT.md`). 133,747 rows (116,198 results); (a) no empty
    month; (b) 0.984–0.995 every year; (c) 0.9987; (d) 0.9946 of 369 names. (e) passes only
    vacuously, because the revision fields are null on every row; the report says so.
  - **Calendar digest:** `067fa6880c737571a3216a6898f00178f57bc7e9cc9c7a30ba355e43bdb299f9`.
    This is SHA-256 over the parsed rows with meeting date ≤ E_s. The store lives outside git
    and the open month is refetched on every run, so the digest is what pins the certified
    calendar. **If E_s has moved by the freeze date, ingest and certification are re-run with
    the new E_s first, and the freeze records that run's digest in place of this one.**
- **P2 — order of commits:**
  1. The P1 ingest is committed and certified. This may happen before the freeze, because it
     reads calendar data only.
  2. This document is frozen, and its SHA is recorded.
  3. The runner and its tests are committed with that SHA pinned (P3).
  4. Every stage report's header records the runner's commit hash and this document's SHA.
- **P3 — runner guards:**
  - `--stage dev` refuses any date ≥ 2023-01-01 and refuses unless the frozen SHA (header definition: LF bytes before the §14 heading) matches the
    value pinned in the runner;
  - `--stage sealed` refuses unless the frozen SHA matches **and** the DEV report records PASS;
  - both stages refuse unless `calendar_digest(store, E_s)` recomputed from the board-meeting
    store equals the digest pinned in P1;
  - each stage writes its report once and refuses to overwrite it (the `run_sealed.py` pattern).

## 12. Files and tests

| File | Purpose |
|---|---|
| `scripts/gex_xs_5d/ingest_board_meetings.py` | P1 ingest + certification report |
| `scripts/gex_xs_5d/run_stage.py` | Panel build, pre-run checks, IC series, test; `--stage dev\|sealed` |
| `tests/gex_xs_5d/` | Unit tests below |
| `docs/reports/GEX_XS_5D_{BOARD_MEETINGS_CERT,DEV,SEALED}.md` | Script-generated reports, no hand-edited numbers |

Tests, at minimum:
- formation grid: every 5th session, t+5 inside the stage, phase starts at the first session,
  the six Muhurat dates skipped;
- results rule: a row known at 15:29 on t excludes, one known at 15:31 does not (and the
  15:40 CAS close from 2026-08-03); a meeting on t excludes; a Saturday meeting between t and
  session t+5 excludes; a meeting on the calendar day after session t+5 does not;
- ATM IV interpolation at K = F on a synthetic chain; the IV expiry skips one expiring inside
  the window;
- residualization: the IC is invariant to adding a linear function of the controls to N;
- per-name validity: 5 kept strikes, or 1 on a side, fails;
- guards: a 2023 date in `--stage dev` raises; `--stage sealed` without a DEV PASS raises; a
  report is not overwritten.

## 13. Operator decisions

| # | Decision | Recommendation |
|---|---|---|
| D1 | Stage design | **Pooled DEV 2016–22 → SEALED**, both one-sided p < 0.05. Alternatives in §9 |
| D2 | Results handling | Exclude on the NSE board-meeting archive: meeting in [t, t+5], known (later of `bm_timestamp`, `sysTime`) by the derivatives close on t (§7) |
| D3 | Per-name validity | ≥ 6 kept strikes, ≥ 2 each side of F (§4) |
| D4 | Forward | Same-expiry future close; drop the expiry if more than 3 % off the cash close |
| D5 | IV | Nearest expiry beyond t+5; linear interpolation in ln(K/F) at K = F |
| D6 | Minimum cross-section | 80 names; below is void, reported, and the rules are unchanged |
| D7 | Inference | Newey–West lag 4 (about a month of weekly formations); t(n − 1) |
| D8 | Winsorization | 1st / 99th cross-sectional percentiles on y and the controls |
| D9 | Missing / zero range | Missing outcome bar drops the name (reported); zero range stays |
| D10 | Sessions and formation phase | Weekday bhavcopy dates minus the six pinned Muhurat sessions; every 5th session from each stage's first session |
| D11 | SEALED end | Minimum of the three stores' max dates on the freeze date |

---

## Appendix A — Prior exposure

Items 1–7 are the frozen declaration's `prior_exposure`, summarized (the declaration holds the
full text):

1. GEX Stage A: NIFTY index N vs next-day RV/IV, 2016–22, spent. It fixes the sign. Index only,
   one-day horizon.
2. GEX fly B1: NIFTY iron fly P&L, STOP. Index only.
3. Seller-edge study + STOCK-STRADDLE-M10: unconditional single-stock straddle P&L over 2016–22
   and 2023-01 → 2026-08, spent for that construct. It exposes the average single-stock IV vs RV
   over ~9-session holds on the same sealed window, a horizon close to this one. It does not
   expose the ranking of RV/IV by GEX, which has never been computed.
4. IVOL: 60-day realized vol vs forward returns, sealed spent. Absorbed by the rv controls.
5. Options-Wall and HedgeWall claim-1: index-option walls and concentration. Index only.
6. Declaration-stage coverage census: chain row counts, 2016–2026; no outcome, no GEX.
7. A next-day draft (GEX-XS) was replaced the same day before any freeze or read.

Added by this document, none of which read an outcome or computed GEX:

8. **Strike census (2026-10-06):** per name and per sampled session (every 20th, 2016–2026),
   the count of traded out-of-the-money strikes with close ≥ 0.5 inside ±10 % of the same-expiry
   future. It set the D3 threshold.
9. **Board-meeting archive probe (2026-10-06):** three months (Jan-2016, Jul-2019, Jul-2024)
   fetched to confirm that the fields and timestamps exist. Calendar data only.
10. **Formation counts:** session counts per stage from `stock_options_bhavcopy` dates, plus
    total option contracts per date, which identified the weekday Muhurat sessions (the two
    lowest-volume dates in the store are 2018-11-07 and 2017-10-19).

## Appendix B — Stated threats (from the declaration, not re-litigated)

1. **Dealer side is assumed.** The fixed convention can be wrong per stock, which attenuates the
   IC toward zero.
2. **Mechanism is not identified.** A PASS validates the number, not the dealer story.
   Positioning or sentiment can give the same sign; the signed-return controls remove only the
   mechanical post-rally channel.
3. **Autocorrelation.** At AC1 0.3 the central joint power is 0.75 (§9).
4. **Mechanical coupling.** Gamma uses IV and IV is the outcome's denominator; ln IV sits in both
   residuals.
5. **Regime breaks.** Physical settlement (2018–19), the SEBI reform (2024-11-20) and CAS
   (2026-08-03) are descriptive splits only.

## 14. Post-freeze change log

- **2026-10-06 — frozen SHA recorded wrongly at freeze; corrected.** The freeze commit `bf8a418` and the CLAUDE.md row recorded `70a7c234…`, computed by cutting the file at the *first occurrence* of the §14 heading text. That occurrence sits inside the status paragraph's backticks, so the value covered only the first 389 of 21,655 bytes. Under this document's own definition (the bytes before the *line* `## 14. Post-freeze change log`) the frozen SHA-256 is **`0cd497ab40535a46be902d2b3add94903c8cabfcc85fb1cb41a2a29ef08f8a29`**. No text above §14 changed; only the recorded number was wrong. Caught while writing the runner guard, before any read. The runner matches the heading as a whole line.
