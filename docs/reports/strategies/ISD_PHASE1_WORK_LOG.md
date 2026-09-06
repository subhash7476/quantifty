# ISD Phase-1 — Work Log

Append-only operational log for ISD Phase-1 substrate certification. Each entry:
date, phase, action, commands, evidence, decisions. Numbers are script-generated;
nothing hand-edited.

---

## 2026-08-25 · Handoff assessment (previous agent's state)

**Findings from the stale certification run** (report generated 2026-08-25T16:05,
runtime 1072.2s, commit `2afaad8`, snapshot `data/isd/ISD_PHASE1_SNAPSHOT.json`):

| Gate | Reported | Reality |
|---|---|---|
| G3 | PASS | genuine |
| G2 | PASS | **stub** — code only checks `bool(last_file)`; real criterion never coded |
| G4 | FAIL | 37 rows: 36 V1 (one session, 2024-06-25, 09:15) + 1 all-zero junk row (2023-11-12 19:01) |
| G1 | FAIL | defects 2024-02-29 (file index-only), 2026-08-24 (no file); 2026-02-01 weekend special |
| G5 | FAIL | **stale** — snapshot run used older `build_pit_universe.py` (174,476/174,476 unresolved); current code resolves 197/197 (verified) |
| G6 | PASS | genuine |
| G7 | never run | vendor zip exists (`~/Downloads/archive.zip`, 949 MB, 100 members); `--skip-vendor` used |

**Verifications done this session:**
- `symbol_entity_intervals` is ticker-keyed; current G5 code resolves (197/197 on last day).
- 2024-02-29 file = 750 index-only rows; bhavcopy has 2,121 rows (real session; NSE cash-glitch day).
- 2026-08-24 (Monday): no file at all; bhavcopy has 2,872 rows.
- Spec §5.2 D1 claims "2024-02-29 refilled" — **not true for equity 1m** (file is index-only). The 2024-11-29 / 2024-12-02..11 refills DID land (equity bars present). Spec is a frozen artifact; correction recorded here and in the certification report.
- **Both dates are served by Upstox** (probe: RELIANCE 375 bars for 2024-02-29 and 2026-08-24) → both are backfillable. `fo_stocks` has 200 active equities; old-schema files carry the (symbol, timeframe, timestamp) PK → upsert-compatible.
- G4 first-bar artifact is **one-day systemic**: same probe symbols (INE028A01039, INE498L01015, INE628A01036, INE976G01028) have clean first bars on 2024-06-24/26 and 2024-07-01; only 2024-06-25 violates (open outside [low, high] on gap opens).
- 2023-11-12 file = **Diwali Muhurat session** (off-grid 18:15–19:15 bars are real trades); the all-zero row at 19:01 sits inside that session.

---

## 2026-08-25 · Phase 1 — code fixes (pre-backfill)

| Item | Change | Evidence |
|---|---|---|
| G5 cleanup | removed duplicated `_resolve`, dead `starts_cache` in `build_pit_universe.py` | syntax + tests green |
| G2 | `currency_check(present_dates, calendar_dates, today_iso)` in `gate_contiguity.py`; wired into `run_certification.py` (was a `bool(last)` stub) | `test_currency_check_real_criterion` |
| Report | G7 row printed as `skipped → native-only` when `--skip-vendor` | — |
| G4 | V1 split into `v1_ohlc_order` / `v1_first_bar_auction_artifact` (09:15 class) / `v1_unexplained`; PASS bar = zero UNEXPLAINED (the existing V5 explained/unexplained pattern) | probe: same symbols clean on 2024-06-24/26, 2024-07-01; only 2024-06-25 violates |
| **Store repair** | NEW `scripts/isd/repair_zero_rows.py` — baseline-copy-first (→ `data/isd/baseline/`), committed, re-runnable, dry-run by default; **applied**: deleted exactly 1 row (`NSE_EQ\|INE121A08PJ0`, 2023-11-12 19:01:00, o=h=l=c=0, Diwali Muhurat placeholder — no security trades at zero). Spec §6 permits mutation with baseline-first; Gate-A discipline | dry-run census = 1 row; post-apply census = 0 |
| G7f bug | `verify_adjustments.py` SQL: `arg_max(close, ts) close` → DuckDB reserved-word parse error (alias needs quoting); `cal_gap.days` vs int (DATE−DATE returns day-count) | caught by new `test_vendor_adjustment_seam_detector` |
| Tests | 11 → **15 passing** (+first-bar class, +repair, +currency, +seam detector) | `pytest tests/isd -q` |

Decisions (governance, operator can veto — recorded here):
1. **First-bar V1 rows are an explained capture artifact** (auction-open outside [low,high] on gap opens), same evidence standard as V5's CA class; published in the ledger, not silently dropped.
2. **Zero-price row removed by committed repair** (baseline copied first) rather than left as a permanent unexplained FAIL — a zero-price bar is definitionally garbage and corrupts downstream returns.
3. Spec §5.2 D1's "2024-02-29 refilled" claim is **incorrect for equity 1m** — the file was index-only. Correction lives here + the certification report (spec stays frozen).

## 2026-08-25 · Phase 2 — G1/G2 backfill (ops action)

**Backfilled both missing sessions from Upstox** (token valid; `fo_stocks` equity
universe, 200 keys, index keys excluded so 2024-02-29's certified index rows were
untouched — verified 750 index rows preserved):

| Session | Result |
|---|---|
| 2024-02-29 | 194/200 symbols written (6 had no data — not yet listed/traded) → 73,500 rows |
| 2026-08-24 | 197/200 symbols written → 73,875 rows (matches sibling days' composition) |

One symbol (INE732I01013) 400s on both dates. Post-backfill gate re-runs:
- **G1 PASS** — 903/903 sessions; sole absence = 2026-02-01 weekend special (out of scope by rule; published).
- **G2 PASS** — latest file 2026-08-24 = last completed session (calendar-anchored check now real).
- **G4 PASS** — v1=36 all first-bar artifact (explained, ledgered); v2=0 after repair; v5 unexplained=0.

## 2026-08-25 · Stall diagnosis — orphaned previous-agent run

PID 288 `run_certification.py --cv-stride 7` (full run incl. G7) left running
unattended since 18:18 by the previous agent. Vendor ingest finished 18:37, then it
sat in `cross_validate_vendor.consolidate()` for **4.3h+ with no end in sight**
(vendor_flat.duckdb only 52MB). Root cause: **Python `executemany` loop over ~97M
vendor bars** — hours-to-days job, invisible progress (no log capture). It saturated
a core and held DuckDB locks on the vendor tree, making every concurrent gate run
slow/hang-feeling. **Terminated (killed) after operator approval.**

## 2026-08-25 · Phase B — consolidate() fix + vendor universe facts

- `cross_validate_vendor.consolidate()` rewritten: DuckDB-native ATTACH +
  INSERT INTO SELECT with bound params (no Python row loop); stale `vendor_flat`
  (+ WAL) unlinked first.
- **Verified on the real staging tree: 88,266,013 rows in 78.5s** (vs 4.3h+ and
  unfinished before — ~200×). Unit test added (`test_vendor_consolidate_native_bulk`);
  **16/16 tests passing**.
- **Vendor universe (operator fact confirmed against the manifest):** 100 members,
  all running to 2025-08-06; **85 start in 2015** (the Nifty-100-era core), 15 start
  2016–2024 (BAJAJHFL, ETERNAL, HYUNDAI, JIOFIN, LICI, LODHA, SWIGGY, …). So
  "100 names × 11.5y" is **85 at full depth** — the deep-narrow option is
  "~85 names from 2015, 100 names from ~2018", per-ticker spans recorded in the
  manifest (first_date/last_date). 99/100 tickers ISIN-resolved (1 unresolved, listed).
- The 2015+ window is **not used by any gate** — G1–G6 are native-store only
  (2023-01-02 → 2026-08-24); the vendor deep window unlocks only on G7 PASS.

## 2026-08-25 · Phase C — G7e cross-validation + G7f adjustment audit

**Bugs found + fixed during the phase (test suite 16/16 green after each):**
1. `cross_validate_vendor.run()`: unfiltered vendor join built an 88M-row hash table
   per session → MemoryError. Fixed: filter `vendor_closes` on its own
   `trade_date` (each session's join is now ~37K rows; run went from crash → 17s).
2. `cross_validate_vendor.run()`: months past the vendor's last date (2025-08-06)
   had zero compared bars → ZeroDivisionError. Fixed: census skips empty months.
3. `verify_adjustments._ca_ex_dates()`: `corporate_actions.purpose` does not exist
   (schema uses `purpose_raw`) → BinderException on the first real run. Fixed.
4. **G7e design correction (review-confirm, per plan's "proposed bar"):** raw
   agreement is only 0.828 because the vendor series and the native store sit on
   different CA-adjustment bases (HDFCBANK exactly 2.0000×, SIEMENS 0.7618×,
   ITC 0.8649× = ITC-Hotels demerger; 17 constant-ratio tickers). Constant ratio
   ≠ corruption — the comparison now aligns per-ticker-day (vendor ÷ median
   ratio) and applies the 0.05% tolerance to the residual. Raw share, basis-offset
   list, and a per-ticker-day low-agreement census are all published.

**Results (stride 7, 130 native sessions):**
| Metric | Value |
|---|---|
| Compared bars | 2,594,882 |
| Raw within 0.05% | 0.8278 (basis-offset inflated) |
| **Aligned within 0.05%** | **0.990568 ≥ 0.99 → PASS** |
| Aligned median \|Δclose\| | **0.0 → PASS** |
| Basis-offset tickers | 17 (constant ratio, documented) |
| Low-agreement ticker-days | 1,600/12,870 (≤1-min tick noise per day, worst VEDL 74/130, BPCL 66/130) |
| **G7f seams** | **782 checked, 0 fabricated (|gap|>20%) → PASS**; overnight-gap p50 39 bp, p99 480 bp |
| G7e elapsed | 17.8 s (was: crash) |

**Phase C verdict: G7e PASS, G7f PASS.** Vendor archive is now certified for the
overlap window on the aligned basis — the deep-window (2015+) choice is unlocked
for Phase 0 subject to the per-ticker depth disclosure (~85 names from 2015).

## 2026-08-25/26 · Phase D — full certification re-run + report

`python scripts/isd/run_certification.py` (all gates, incl. G7a-d re-ingest) —
**runtime 828.2 s · exit 0 · Overall: PASS.**

| Gate | Verdict | Key figures |
|---|---|---|
| G3 | PASS | normalized reader, drift abstracted |
| G2 | PASS | latest file 2026-08-24 = last completed session |
| G4 | PASS | v1=36 (first-bar artifact=36, unexplained=0), v2=0, v3=0, v4=0, v5 unexplained=0 (ca-adjusted expected=5,629) |
| G1 | PASS | 903/903 sessions; defects=[]; special=[2026-02-01]; ledger entries=282 |
| G5 | PASS | rows=173,900; cross-feed agreement=1.0; unresolved=0 |
| G6 | PASS | ticket table @ ₹2Cr; slippage deciles over 9,237,259 obs |
| G7a-d | PASS | 100 members; resolution=0.99; tail dropped=4,701 |
| G7e | PASS | 2,594,882 bars; aligned within-tol=0.990568 (raw 0.827781); median \|Δ\|=0.0; basis-offset=17; low-agree ticker-days=78 |
| G7f | PASS | 782 CA seams; fabricated=0 |

Report regenerated: `docs/reports/ISD_PHASE1_SUBSTRATE_CERTIFICATION.md` (script-generated,
digests embedded; snapshot at `data/isd/ISD_PHASE1_SNAPSHOT.json` — gitignored data tree
by design, report carries commit + script SHAs + digests per plan §6).

**Phase-1 exit state: ALL GATES PASS.** ISD Phase 0 (pre-registration) is now unblocked;
the vendor deep-window option (~85 names from 2015, 100 from ~2018, certified on the
aligned basis) is available for the Phase-0 substrate choice alongside the native
2023-01-02 → 2026-08-24 store.

---

## 2026-08-26 · Phase 0 — pre-registration investigation, review cycle, freeze

**Investigation** (`ISD_PHASE0_CANDIDATE_RANKING.md` v1→v3): five candidate families
assessed on the certified substrate + calendar arithmetic + in-house priors; two
rounds of operator/lead review (R1–R11) applied. Key findings: the SEALED window's
power problem resolved via a mechanical spend floor n ≥ 317 (central 0.8002 at the
floor); **#3 (market-relative drive) collapsed into #1** — rank(x_i − x̄) ≡ rank(x_i),
translation invariance; battery = {1 opening-drive continuation, 4 overnight-gap};
#2 (mirror of 1), #5 (expiry; contrast power + Nov-2024 SEBI regime break) and OI
dropped.

**RFA (both PROCEED, max power 0.9938 at n=317, one-sided):**
- `governance/rfa/declarations/isd_opening_drive.py` — whole-file SHA
  `934c069a395a…` (report `ISD-OPEN-DRIVE_RFA.md`)
- `governance/rfa/declarations/isd_overnight_gap.py` — whole-file SHA
  `e476a03b0d13…` (report `ISD-OVERNIGHT-GAP_RFA.md`)

**Pre-registration freeze** (`ISD_PHASE0_PRE_REGISTRATION.md`, FROZEN 2026-08-26).
Operator review cycle fixed five pre-freeze defects: (1) power block regenerated
verbatim from power.py (0.4116 / 0.8002 / 0.9938); (2) F1 feature corrected to
window-end CLOSE with next-bar-open entry (09:46/10:01 — no look-ahead, no label
overlap); (3) banded-exit dimension dropped — EOD-flat book has no exit-band role;
grids 4 cells/family, BH per-cell α 0.0125, ≥2-of-4 qualifying cells; (4) ADV cap
pinned to trailing 20-session ADV as of T−1 (no intraday look-ahead); (5)
declaration headers corrected, gate reports + §11 SHAs regenerated.

**Frozen contract (the battery):** F1 = rank on (window-end close − 09:15 open)/
09:15 open, entry next-bar-open, label entry→15:29 close, sign continuation
(mechanism-pinned); F4 = rank on overnight gap (auction open vs prev_close, CA
ex-dates excluded), entry 09:16 open/close cells, sign TRAIN-burned once (m=2
disclosed). Both: ~200-name PIT universe, EOD-flat dollar-neutral, ADV-capped,
measured-τ net-spread gates, matched nulls, family-wise BH, sealed spend at
n ≥ 317 + paper ≥ 3 months (contamination rule) after HOLDOUT PASS.

---

## 2026-08-26 · Battery — TRAIN pass executed, both families FAIL (closed per §9)

**Harness built** (`scripts/isd/battery_features.py`, `battery_stats.py`,
`run_battery.py`, `tests/isd/test_battery.py` — 22 tests green). Frozen-contract
exact: hold-leg-only labels, next-bar-open entry, PIT universe, ADV cap (trailing
20-session as of T−1), G6 decile slippage, era-accurate fees, per-cell random-entry
nulls (1,000), family circular-shift nulls (1,000), BH per-cell α 0.0125, ≥2-of-4
qualifying, family α 0.05, net-spread gate at measured τ (EOD-flat ⇒ τ = 2).
SEALED guard: any fence leak into 2026-01-01+ refuses to run.

**Bugs found during bring-up (all fixed, tests re-run green):** aliased numpy array
(`gross = slip = fee = np.full(...)` — all three shared one buffer; the 
net-spread gate was reading fee values as gross/slip); missing liquidity-decile
step in the slippage lookup; module-global symbol axis (refactored to explicit
params); month-block rotation with unequal block lengths (vstack of rotated
contents, not fixed-slice copy).

**TRAIN verdict (run 2026-08-26T20:28, seed 42, prereg SHA-16 `f77b163c…`):**

| Family | Cells | Family IC | NW t | p (shift null) | Net bp | Verdict |
|---|---|---|---|---|---|---|
| F1 opening-drive continuation | 0/4 qualify (p=1.000) | −0.0155 (mean of cells) | −2.7 (cells) | — | −20.6 bp/session | **FAIL** |
| F4 overnight-gap | 4/4 qualify (p=0.000), sign **−1 fade** | **−0.0289** | **−6.09** | 0.0000 | **−3,196** (≈ −6.8/session) | **FAIL** |

**What happened:**
- **F1: the pinned sign reads negative.** All four cells have IC ≈ −0.015
  (NW t ≈ −2.6 to −2.8) — intraday opening-drive *reverses*, consistent with
  CB-N50's "daily momentum IS reversal" prior and the index-pair trending
  (reversal of the stock-level component). The frozen rule applies: **sign is
  pinned, no flip-fishing — family closed.**
- **F4: a genuinely strong effect, eaten by costs.** Gap-fade (sign registered
  −1) shows family IC −0.0289 (NW t −6.09, shift-null p 0.000, AC1 0.02) with
  all four cells qualifying — the strongest signal this repo has measured on a
  fresh window. But the fade spread is +3.2 to +6.0 bp/session gross vs
  **10.5 bp/session measured costs** (2×2.7 slippage + ~5.1 fees) → net
  −4.6 to −8.9 bp/session → **the R4 measured-τ net-spread gate kills it.**
  This is the PSB-1/2 fee-dominance result reproduced at intraday scale, for
  the first time with a statistically significant effect behind it.

**Program status (spec §9):** TRAIN fail → both families closed. HOLDOUT was
NOT read (chain stop — the pre-reg's gate structure held). SEALED 2026-01-01 →
spend date remains **untouched and unread** (n ≥ 317 floor preserved). The
battery's safeguards did exactly their job: a real, significant effect was
refused on costs — no tuning, no rescue, no sign-flip, no cell added after the
first run. Any successor family starts its own pre-registration; the trial
ledger, snapshot, and this log are the record.



