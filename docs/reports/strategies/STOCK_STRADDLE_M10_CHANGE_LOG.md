# STOCK-STRADDLE-M10 — Post-Freeze Change Log

The pre-registration (`STOCK_STRADDLE_M10_PRE_REGISTRATION.md`, FROZEN 2026-09-28, SHA-256
`03672fd0ce4e90f30081a4d55d57303319120e0e9cad92dc9a03a5e6068c918b`) reserves §12 for
mechanical fixes to the capture tool. Appending to §12 would change the frozen file's digest, so
the entries live here instead. **No entry may alter a rule in the pre-registration.**

| # | Date | File | Change | Rule affected |
|---|---|---|---|---|
| M1 | 2026-09-28 | `straddle_cycle_capture.py` | `--immediate` and a manual `--role entry\|exit` now refuse to run without `--dry-run` (exit 2). Only the calendar-driven scheduled run can write production `entry`/`exit` rows. Before this, a manual non-dry run could give a cycle a second entry capture the pre-registration does not define. | None. Protects §5 and §8 |
| E1 | 2026-09-28 | `straddle_cycle_evaluate.py` (new) | The offline scorer implementing §3 (U1–U5), §4, §6, §7, §8, §1 and §9 from the capture store. It reads no forward P&L to choose anything. | None. Implements the frozen rules |

## E1 — how the scorer reads the rules

These are readings of the frozen text, written down before any cycle is scored.

1. **Per-rule exclusion counts** attribute each name to the *first* rule it fails, in the U1–U5 table order.
   - Example: in the ban period a name's options stop trading, so it usually fails U2 (no traded ATM pair) before U4 is reached.
   - It is excluded either way. Only the attribution in the report changes.
2. **D5 and combined purposes** (amended 2026-09-28, before any live CA list was captured).
   - NSE often puts several actions in one `PURPOSE`, e.g. "Bonus 1:1/ Dividend- Rs 5 Per Share" or "Annual General Meeting / Dividend - Re 0.60/- Per Share / Bonus 1 : 1". The register holds at least 15 such rows.
   - The scorer drops the `/-` rupee suffixes and any `(…)` notes, then splits the purpose into components on `/` and "and".
   - A component naming a general meeting is **neutral**. A dividend component contributes its amount, read as `Rs` or `Re`; "NIL Dividend" counts as 0.
   - **Any other component is a price-adjusting action and excludes the name, whatever the size of an accompanying dividend.** This follows D5's "any purpose other than a dividend".
   - A dividend whose amount cannot be read (a bare "Dividend" or "Special Dividend") excludes the name. An unsized dividend cannot be shown to be under 2 %.
   - Several dividend amounts, such as a final and a special dividend, are summed.
   - Swept over all 40 distinct dividend purposes in `corporate_actions`: none was misread as adjusting. The 7 without a readable amount were a bare "Dividend", "Final Dividend", "Interim Dividend", "Special Dividend", preference-share and mutual-fund dividends (neither can match a FUTSTK symbol), and "NIL Dividend", which is now read as 0.
3. **D5 symbol match** is on NSE `SYMBOL`, for any series.
   - The capture's universe is FUTSTK symbols, so a gold-bond or debt series can never match.
4. **§6 exit fallback reference** = the maximum of two values:
   - the highest LTP captured for that key in any exit pass that day, whether on time or not;
   - the T-1 bhavcopy close, or the settle if the leg did not trade.
   - If neither exists, the scorer **refuses to score** the cycle rather than guess. The cycle is then scored once the T-1 bhavcopy is ingested.
5. **§8 void** is tested on the entry capture's on-time passes only. A pass that started late counts as not taken.
6. **§9** is evaluated in expiry order from counted cycle 6 onward. The first trigger ends the test.
   - The §1 confirmation uses the first 36 counted cycles only.

## Smoke read (entry side only, dry capture, not a cycle)

Evaluating the 2026-09-28 dry-run capture as if it were an entry, for the 2026-10-27 expiry:
- universe 210; **203 eligible**;
- U2 excluded 2: MANAPPURAM and SAIL, both in the ban period;
- U3 excluded 3: ATHERENERG, MAHABANK and SAGILITY, recent F&O entrants short of 40 of 60 returns;
- U4 excluded 2: KAYNES and LICHSGFIN;
- U5 excluded 0.

This checks the mechanics only. No return was computed, and the dry capture is not a cycle.
