# STOCK-STRADDLE-M10 — Cycle 1 status, 2026-10-14

Forward paper test, frozen pre-registration `STOCK_STRADDLE_M10_PRE_REGISTRATION.md`
(SHA-256 `03672fd0…`). Paper tracking only; no orders, no capital.

**Start date.** The test's first entry was **2026-10-12 15:35** (cycle 1, expiry 2026-10-27), not 10-08.
Sessions before 10-12 were no-op capture days.

## 1. State of the window

| Item | Value |
|---|---|
| Counted cycles | 0 scored of 36 (cycle 1 open; exit 2026-10-26) |
| Voids | 0 |
| F1 / F2 falsification | Not active until counted cycle 6 (§9) |
| Confirmation | Read once after cycle 36 (§1); no interim look |
| Rules changed since freeze | None. Change log: M1, E1 only (mechanical) |

## 2. Cycle 1 capture (entry 2026-10-12)

- Four passes (c-20 15:20, c-10 15:30, **c-5 15:35 primary**, c-2 15:38) started 0.03 s after plan; every pass has
  7,036–7,044 keys quoted, **0 api_fail**, futures coverage 100 %.
- `fo_secban` and `ca_forward` artifacts captured at 15:15, so D5/D6 use captured data, not fallbacks.
- The task ran 15:15:01 → 15:38:16, exit 0. 10-13 and 10-14 were correct no-ops.
- Cycle is not void (§8).

## 3. Book at entry

| | |
|---|---|
| Futures universe (U1) | 213 |
| Eligible | **204**, all selected on the primary c-5 pass |
| Excluded | U2 1 (BANDHANBNK) · U3 6 (ANANDRATHI, ATHERENERG, ENRIN, MAHABANK, SAGILITY, UJJIVANSFB) · U4 2 (AMBUJACEM, LICHSGFIN) · U5 0 |
| Premium collected (bids, 1 lot/name) | Rs 65.5 lakh; mean Rs 32 k, median Rs 28.6 k per name |
| Futures notional | about Rs 13 cr across the book |
| Straddle credit / future | median 4.86 %, p10 3.50 %, p90 6.09 % |
| Entry bid-ask spread / mid | median 1.89 %, mean 2.66 %, p90 3.66 % |
| ATM distance from future | mean 0.40 %, max 2.36 % |
| Estimated fees | about 0.57 % of premium (Rs 34.8 k, STT at 0.15 % sell side) |

Wide-spread names, passed by the frozen rules and shown for scale: BAJAJHLDNG 75 %, HYUNDAI 26 %, ALKEM 17 %,
SHREECEM 10 %. The RFA band assumed a 2 % round-trip spread; the entry half is about 1 % at the median, and the
exit half (T-1, shrunken premiums) is unmeasured until 10-26.

## 4. Indicative mid-cycle mark (not a result)

Marked at the **2026-10-13 bhavcopy settle** (the latest ingested; 10-14 lands with tonight's 22:00 run). Settle is not
the §6 exit fill (best ask), no fees, equal weight over all 204 names.

| | |
|---|---|
| Mean | **−2.0 %** of premium (−1.5 % excluding TCS) |
| Median | +2.1 % |
| p10 / p90 | −16.2 % / +8.1 % |
| Names under water | 42 % |
| Rupees | −Rs 1.13 lakh on Rs 65.5 lakh collected |
| Worst | TCS −88 %, KPITTECH −54 %, HCLTECH −47 %, HINDUNILVR −43 %, BAJAJHLDNG −40 % |
| Best | FORTIS +15.5 %, SAIL +15.3 %, APOLLOHOSP +14.4 % |

The IT cluster is the driver: TCS, KPITTECH and HCLTECH show deep in-the-money calls after a rally, i.e. the book is
short a sector gap, which is the short-crash/short-gap exposure the pre-registration discloses (Appendix B).

**How to read it.** It is day 1 of a 10-session hold, one observation out of 36, with 9 sessions of theta and
event risk still to come. The scored value is decided only by the §6 exit fills on 2026-10-26. The pre-registration
has no rule that acts on a mid-cycle mark, so nothing here changes any decision.

## 5. What happens next

1. **2026-10-26 15:15** `StraddleCapture` runs the exit passes, quoting exactly the 204 option keys captured at entry.
2. 2026-10-26 22:00 `DownloadAll` ingests the T-1 bhavcopy (the §6 fallback reference).
3. Score cycle 1:
   `python scripts/research/options_seller_edge/straddle_cycle_evaluate.py --expiry 2026-10-27`
   then `--summary`. The scorer refuses to score if the fallback reference is missing.
4. Cycle 2: expiry 2026-11-23, entry 2026-11-06, exit 2026-11-20.

## 6. Risks to watch

- **Exit capture.** An entry-only cycle is not scored; an exit failure falls to the 1.10x fallback and is flagged.
  The orchestrator is independent of this task, so the 15:15 job runs even if the stack is down, but it needs a
  valid Upstox token (re-read before every pass; first failed pass alerts at once).
- **Calendar.** 2026-10-20 Dussehra is a holiday inside the hold; T-1 = 10-26 is unaffected. The trading calendar
  ends 2026-12-31: add 2027 holidays before cycle 4 (entry in Jan 2027).
- **Power.** At 36 cycles the central corner is under-powered (needs 65); the expected outcome is NOT CONFIRMED,
  not falsified (§1).
- **Window length.** Nominal end is the Sep-2029 expiry.
