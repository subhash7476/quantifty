# PTMS — Gann R-13 Leftovers: Closure Note

**Date:** 2026-09-19 · **Branch:** `research/ptms-price-time-market-structure`

**Scope:** the open items listed at the end of `PTMS_GANN_R13_N100_EOD_SCOPED_CERTIFICATION_2026-09-15.md`
("Still required for R-13").
- No price, return or outcome was read.
- One store was rebuilt, under copy-first and an identity check, with the operator's approval
  (2026-09-19).

| # | R-13 open item | Status |
|---|---|---|
| 1 | External CA enumeration | **CLOSED** — `PTMS_GANN_P2_CA_ENUMERATION_2026-09-19.md` (commit `156a2ce`); rulings P2-a … d |
| 2 | Exclusion-window rule (G-7) | **CLOSED** — full span (operator ruling 2026-09-19) |
| 3 | G1/G3/G5 persistence into `n100_audit` | **CLOSED** — §1 |
| 4 | 2016-04-19 confirmation | **CLOSED** — §2 |
| 5 | Declared dispositions: four ±1-month membership boundaries, 304 BE-series member-days, the TATAMTRDVR share class ("only if the eventual cadence requires them") | **CLOSED** — operator rulings 2026-09-19 (§3) |

---

## 1. G1/G3/G5 persistence

- **Defect.** `scripts/isd/build_n100_membership.py` wrote G1, G3 and G5 audit rows only on
  **failure**. A passing run therefore left no trace, and "passed" could not be told apart from "not
  run".
- **Change.** Commit `54ef174`: pass-state summary rows are written for every gate. The membership logic
  is unchanged.
- **Rebuild procedure:**
  1. Code committed first.
  2. Baseline snapshot `data/_baselines/n100_membership_pre_G135_2026-09-19.duckdb` (SHA-256
     `0be19812…2d78`, identical to the live store before the rebuild).
  3. Rebuild.
  4. Verification (the pre-registered prediction: membership identical, audit rows only added):

| Check | Result |
|---|---|
| `n100_membership` rows, old vs new, full-row equality | **Identical** (263 = 263) |
| Existing `n100_audit` rows preserved | **Yes** (32 of 32) |
| Rows added | **8**, all new gate summaries (below) |

| New row | Value |
|---|---|
| G1_NIFTY 50_backward_breaks / forward_breaks | 0 / 0 |
| G1_NIFTY NEXT 50_backward_breaks / forward_breaks | 0 / 0 |
| G3_mcwb_leg_months_compared / mismatched | 368 / 0 |
| G5_union_months_compared / mismatched | 184 / 0 |

The P-2 enumeration read `n100_membership`, which is unchanged, so it needs no rerun.

## 2. 2016-04-19 against NSE's official 2016 holiday list

| Field | Value |
|---|---|
| Source | NSE circular **NSE/CMTR/31297**, Circular Ref. 73/2015, 7 Dec 2015, Capital Market Segment, "Trading holidays for the calendar year 2016" |
| URL | `https://nsearchives.nseindia.com/content/circulars/CMTR31297.pdf` (found through NSE's own circular archive API) |
| SHA-256 of the file read | `bf33e9aade8773908fc5d6de105cc731e93bf063cd1564a82fe1998c5aaf6432` (195,966 bytes; downloaded with operator permission, not committed) |
| Entry | **No. 7: "April 19, 2016 Tuesday Mahavir Jayanti"** |
| Amendments | NSE's circular archive for 2016-03-01 → 2016-04-19 (382 circulars) holds no holiday or Mahavir-Jayanti amendment |
| Verdict | **2016-04-19 is an NSE trading holiday.** The feasibility audit's reading (0 rows in every store; exclude) is confirmed |

**Side confirmation relevant to CAL-1.** The same circular fixes Muhurat trading on **Sunday
2016-10-30**, a real in-window Sunday session. Under CAL-1 (ISO Monday–Sunday) it is the last session of
its week, and f_w is its close. `SPECIAL_SESSIONS` covers only 2023–2025, so the implementation must take
this session's window from a source (see robustness list §5.5 / CAL-1).

## 3. Remaining R-13 item (operator)

R-13 open item 5 was conditional on cadence. Cadence is now fixed (weekly formation, five-session
outcome), so the condition can be evaluated. Three dispositions are needed, none of them decided here:
1. **The four ±1-month membership boundaries.** How observations straddling a boundary month are
   treated.
2. **The 304 BE-series member-days.** BE is the trade-for-trade equity series. Are they eligible
   formation sessions? Note that P-2 already counts BE rows as equity.
3. **The TATAMTRDVR share class.** Is the DVR a separate stock-entity in the cross-section, alongside
   TATAMOTORS?

### 3.1 Operator rulings (2026-09-19)

| Item | Ruling | Not chosen |
|---|---|---|
| ±1-month boundaries in the screen window: R5 (2017-05-26), R7 (2020-09-25 / 2020-11-02). R8 (2023, 2025) falls outside the window and is moot | **Use the recorded dates**, disclosed in the report | Exclude the uncertain month |
| 304 BE-series member-days | **Include** as eligible sessions | Exclude |
| TATAMTRDVR, 2016-04-01 → 2017-09-29 | **Include as its own stock.** Disclose that it tracks TATAMOTORS closely. Note that `universe_eligibility` classes it `non_equity_isin`, so the implementation must **not** filter through that table | Exclude |

**R-13 is fully closed.**

**NO PRICE, RETURN OR OUTCOME READ.**
