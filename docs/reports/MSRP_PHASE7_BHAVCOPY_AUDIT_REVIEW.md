# MSRP Phase 7 — Bhavcopy Ingestion: Lead Reviewer Assessment

**Document type:** Independent review of the Phase-7 precondition gate (a) deliverable
(`scripts/msrp/ingest_option_bhavcopy.py` + `docs/reports/MSRP_PHASE7_BHAVCOPY_AUDIT.md`).

**Date:** 2026-07-07

**Requirement under review** (`MSRP_PHASE7_STRATEGY_RESEARCH.md` §6.1): ingest NSE F&O
bhavcopy for Nifty weekly options **2023 → present** and audit liquidity/quality, as the
first of three precondition gates before the Phase-7 pre-registration.

---

## Verdict: GATE (a) NOT PASSED — coverage is 43% of the required span

The audit doc reports "Verdict: PASS," but that verdict is scoped only to ATM liquidity
on the ingested slice. The controlling requirement is **coverage**, and the database
stops at **2024-07-05**: 370 trading days ingested (2023-01-02 → 2024-07-05) out of the
~870 required (2023-01 → 2026-07, plus ongoing forward collection). Everything the
strategy design needs most is in the missing half — the 2024-H2→2025 dev-window tail,
the 2026 transition slice, and the forward held-out stream.

**The stated root cause is wrong, and the gap is fully recoverable.** The audit says
"Data beyond 2024-07-05 unavailable (NSE changed archive URL pattern)." NSE did not stop
publishing — it migrated F&O bhavcopy to the **UDiFF format** in July 2024. Verified
directly today (HTTP 200 with ~1 MB payloads):

```
https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_20240708_F_0000.csv.zip   → 200
https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_20260703_F_0000.csv.zip   → 200
```

2024-07-08 is the first trading day after the legacy archive ends — the two formats butt
join with no gap. The script's 20-consecutive-404 "archive exhausted" fast-skip then
silently abandoned the remaining two years.

## Findings

### F1 — BLOCKING: missing 2024-07-08 → present
As above. **Fix:** add a UDiFF ingestion path (`nsearchives.nseindia.com/content/fo/
BhavCopy_NSE_FO_0_0_0_{YYYYMMDD}_F_0000.csv.zip`) for dates > 2024-07-05. The UDiFF CSV
uses different column names (ticker/expiry/strike/option-type/OHLC/settlement/OI under
UDiFF tags; index options carry a distinct instrument-type code) — map them into the
existing `option_bhavcopy` schema so downstream consumers see one table. Re-run to
present, then re-run the audit over the full span.

### F2 — MAJOR: NIFTYNXT50 contamination
The filter `symbol.startswith("NIFTY")` admits **NIFTYNXT50** (49,408 rows from
2024-04-24, verified by query). The audit's ATM analysis dodged it accidentally (strike
window ±200 of the Nifty close excludes NXT50 strikes), but any strike-range or
per-expiry query over the table is polluted. **Fix:** filter `symbol == "NIFTY"` exactly
(both formats), and `DELETE FROM option_bhavcopy WHERE symbol <> 'NIFTY'`.

### F3 — MINOR: audit report sections are misleading
- The "Per-Expiry Liquidity (2025-2026)" table is far-dated monthly/half-yearly
  contracts observed from 2023-24 trade dates — of course they show near-zero volume;
  the table says nothing about weekly liquidity and invites misreading.
- "ZeroCtrDays" counts *rows* (strike × type × date), not days.
- The stale-open check groups by (strike, option_type) **without expiry_dt**, chaining
  settles across different contracts, and uses exact float equality — its "0 candidates"
  is not evidence. **Fix:** group by (expiry_dt, strike, option_type), or drop the check
  in favor of the simpler `open == 0 AND contracts > 0` test (see F5).

### F4 — OBSERVATION: expiry-weekday regime shift across the span
In the ingested era, Nifty weeklies expired **Thursday** (93 Thursday expiries; nearest
expiry is Thursday for 357/370 dates). Today they expire **Tuesday**. The strategy
research doc's 0DTE-collision discussion assumed the Tuesday regime; the pre-registration
must define contract selection **weekday-agnostically** (e.g., "nearest expiry with
DTE ≥ 2") so one rule spans both eras. Related: on 77/370 days no 2–7-DTE expiry exists
(nearest is 0–1 DTE, next is 8+) — the DTE rule must state what happens there (take the
8-DTE contract) rather than leave it to implementation.

### F5 — POSITIVE: on the ingested slice, quality genuinely passes
Independently verified: every trade date has a ≤ 6-DTE expiry available; on all 293 days
where a 2–7-DTE expiry exists, the nearest-strike straddle has **both legs with open > 0
and close > 0** (293/293); zero rows among 282,205 traded NIFTY contracts have a
missing/zero open; ATM OI is healthy. The D1 design's "enter at open, exit at close from
bhavcopy" execution is data-feasible. The slice is simply too short.

## Required remediation before gate (a) can close

1. UDiFF ingestion path + column mapping; backfill 2024-07-08 → present (F1).
2. Exact-symbol filter + purge NIFTYNXT50 rows (F2).
3. Re-run the audit over the full span with corrected sections (F3), reporting per-era
   (Thursday-regime vs Tuesday-regime) ATM liquidity separately.
4. Carry F4 into the Phase-7 pre-registration as a contract-selection requirement.

Gates (b) options fee model and (c) fee-impact triage remain queued behind (a).

---

*Reviewer: Claude (Lead Reviewer). Verification: independent DuckDB queries against
`data/market_data/options_bhavcopy.duckdb` (symbol census, per-year coverage, nearest-DTE
distribution, ATM straddle-leg completeness, zero-open census) and curl probes of the
UDiFF endpoint, 2026-07-07.*
