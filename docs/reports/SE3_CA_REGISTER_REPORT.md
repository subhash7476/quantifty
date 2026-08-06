# SE-3 — Corporate-Action Register for the Derivatives Store

**Date:** 2026-08-06 | **Status:** Register built, guard fixed, predictions run.
**Authority for the finding:** `docs/reports/SE3_CA_CONTAMINATION_REVIEW.md` (confirmed, verdict not moved).
**Scope:** FUTSTK/OPTSTK underlyings, 2016-02-11 → present. Substrate-only; Phase 2 one-shot NOT reopened.

---

## 1. The defect, in one line

Raw bhavcopy futures settles are un-adjusted for splits/bonuses. A split changes the *price basis*
without changing the *contract identity*, so the §3.5 roll-gap guard (`expiry_dt` change) is blind
to it, and the ex-date log-return survives into the 21-day RV as a fabricated crash
(`SE3_CA_CONTAMINATION_REVIEW.md` §7).

## 2. Register source and provenance — the authority

The register is **not** derived from futures prices. It is reused from the existing equity CA
machinery:

- **`adjustment_factors`** table in `equity_bhavcopy.duckdb` — built by
  `scripts/csmp/ingest_corporate_actions.py` from the **NSE CF-CA feed** (sole source for
  SPLIT/BONUS, carrying the true ex-date and the ratio from the PURPOSE text). 591 SPLIT + 603
  BONUS rows, 2010 → present.
- **`symbol_entity_intervals`** — time-aware entity resolution, because NSE recycles tickers and
  re-issues ISINs on face-value changes ("an entity is not one symbol for all time").
- Only **SPLIT/BONUS** rows are kept. Dividends do not move the futures basis.

**Coverage decision (investigated before building, per Task 2):** the existing machinery
**already covers** the 17 Nifty-50 names (25 in-window CA events) and the wider universe. Nothing
new was built as a data source; the only new code is the loader
(`certify_substrate._load_ca_register`) that reads `adjustment_factors`, resolves symbols to
entities, and re-aliases each CA ex-date onto **every symbol the entity has traded as**, so a CA
registered under a legacy ticker (e.g. `MOTHERSUMI`) drops the return on the current ticker
(`MOTHERSON`). **Symbol identity mismatch was the first-fix bug**: the register was initially
keyed by entity, which missed every renamed name (BAJFINANCE→BAJAUTOFIN, INFY→INFOSYSTCH,
CASTROLIND→CASTROL, …); keying by raw symbol + entity aliases fixed it.

## 3. Validation — register ratio vs implied futures ratio

For every register entry with a futures row on the ex-date, `implied = settle_t / settle_{t-1}`
(front-month series) is compared to the register ratio. Agreement within 5% = OK; outside = a CA
coinciding with a real move, requiring individual disposition (Task 2 validation gate).

| Metric | Count |
|---|---|
| Register entries in 2016-02-11 → 2022-12-31 | 103 |
| OK (register ≈ implied, within 5%) | 73 |
| NO_FUTURES_ROW (name not a FUTSTK underlying on that date) | 26 |
| MISMATCH (>5% off) | 4 |

### The 4 mismatches — individually dispositioned (all are CA + coincident real move)

| Name | Ex-date | Register | Implied | Disposition |
|---|---|---|---|---|
| ICIL | 2016-11-11 | 0.200 (1:5 split) | 0.186 | Split correct; stock also fell ~7% that day. **Register correct.** |
| IRCTC | 2021-10-28 | 0.200 (1:5 split) | 0.220 | Split correct; ex-date also saw a genuine +5% move the next session. **Register correct.** |
| MINDTREE | 2016-03-09 | 0.500 (1:1 bonus) | 0.466 | Bonus correct; stock dropped ~3.4% more. **Register correct.** |
| MOTHERSUMI | 2018-10-30 | 0.667 (1:3 bonus) | 0.707 | Bonus correct; stock rose ~4% vs ratio. **Register correct.** |

None requires a register change. The drop-idiom nulls the ex-date return regardless, which is the
correct outcome for all four.

### The 17 Nifty-50 subset — all 23 in-window entries OK

RELIANCE 0.500/0.499, JSWSTEEL 0.100/0.099, TATASTEEL 0.100/0.105, BAJAJFINSV 0.100/0.102,
BAJFINANCE 0.100/0.102, BEL ×3, BPCL ×2, IOC ×3, WIPRO ×2, TCS, INFY, HDFCBANK, HCLTECH, M&M,
GRASIM, BRITANNIA, EICHERMOT — all within 5% of the observed futures ratio.

## 4. The guard fix

`certify_substrate._front_month_rv(g, ca_ex_dates=None)` now nulls the return on any CA ex-date
in addition to the roll-gap guard:

```python
fdf.loc[fdf["expiry_dt"] != fdf["prev_exp"], "ret"] = np.nan   # roll gap (existing)
if ca_ex_dates:
    ca_dates = pd.DatetimeIndex(sorted(pd.Timestamp(d) for d in ca_ex_dates))
    fdf.loc[fdf["trade_date"].isin(ca_dates), "ret"] = np.nan  # CA ex-date (new)
```

The **drop idiom** is used (set `ret = NaN`), not ratio-adjustment, for consistency with the
roll-gap handling. `RV_MIN_OBS` still binds (18 of 21): a CA nulls one observation; the window
retains 20, above the floor. **Verified:** no 2016-2022 date newly fell below the 18-observation
minimum as a result of the CA drops.

### Falsifiable predictions, stated before running, and outcomes

| # | Prediction | Observed | Verdict |
|---|---|---|---|
| P1 | Zero guard-surviving events for all 17 Nifty-50 splits after the fix | **0** (BAJFINANCE and INFY were missed on the first run due to the entity-keying bug; fixed by symbol+alias keying) | **HELD** (after bug fix) |
| P2 | Every genuine collapse still survives: YESBANK 2020-03-06/09/16/17, JETAIRWAYS 2019-04-18 and 2019-06-17/18/20, RCOM 2018-05-17 and 2019-02-04, IDEA 2019-03-29 and 2020-03-18, DHFL 2019-07-15 | **All 13 SURVIVED** | **HELD** |
| P3 | Post-fix surviving-event count = 33 (98 − 65 registered), each residual genuine | **33** | **HELD** |

**The first run's P1/P3 miss was a real bug, reported and fixed, not adjusted away.** The entity-keyed
register silently missed renamed names; switching to raw-symbol + entity-alias keying brought both
predictions to HELD.

## 5. Residual events (the 33, all genuine) and unresolved items

The 33 post-fix survivors are genuine single-day moves with **no** register entry: YESBANK
(2020-03 crash days), JETAIRWAYS (2019 collapse), RCOM, IDEA, DHFL, IBULHSGFIN, TATACHEM,
INDUSINDBK (+43%), PCJEWELLER (+44%), RPOWER, RELINFRA, RELCAPITAL, PNB, SINTEX, INFIBEAM
(2018-09-28, +29%), KPIT, M&MFIN, CENTURYTEX, ARVIND, CROMPGREAV, CGPOWER, PEL — all genuine.

**Unresolved (recorded, not guessed):** the 26 `NO_FUTURES_ROW` register entries are names with a
CA but no futures trading on that exact date in the store — harmless (no futures return to guard)
and left as-is. The 4 mismatch events are dispositioned above as register-correct. No register
ratio was derived from a futures jump.

## 6. Probe window (2023–2025)

4 guard-surviving events post-fix: **ABFRL 2025-05-22 (0.335), SIEMENS 2025-04-07 (0.573),
TATAMOTORS 2025-10-14 (0.599), ZEEL 2024-01-23 (0.672)** — all genuine moves or demergers absent
from the equity register (ABFRL/SIEMENS/TATAMOTORS demergers, ZEEL). **Immaterial to the verdict:**
contamination *inflates* dispersion, so the probe's contaminated `sd_IC` 0.1877 is conservative,
and the confirmatory's in-band 0.1940 already landed inside [0.1877, 0.26]. The probe window
cannot have made the declared band too generous.

## 7. What remains un-remediated

1. **The 2023–2025 probe window** still carries 4 un-guarded events (all genuine or unregistered
   demergers); the probe's `breadth_probe.py` was not modified (frozen artifact). Its `sd_IC` is
   conservative for the reason in §6.
2. **Demerger events are not in the equity `adjustment_factors` register** (ABFRL, SIEMENS,
   TATAMOTORS 2025, TMPV-era events). A futures-side demerger register is a separate, future task;
   they are genuine basis changes, not fabrication.
3. **The register spans SPLIT/BONUS only** — rights issues and special dividends that move the
   futures basis are not covered and were not scanned for.
4. **Phase 2 was NOT re-run** (frozen one-shot; review §5). The confirmatory point estimate
   −0.1124 carries the bounded CA bias (≤ ~0.04) disclosed in `SE3_CONFIRMATORY_REPORT.md`.
