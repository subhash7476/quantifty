# ISD Phase 1 — Substrate Certification Plan

**Date:** 2026-08-24
**Status:** Plan — implements the APPROVED spec
`docs/superpowers/specs/2026-08-24-intraday-stocks-discovery-design.md`.
**Branch:** `research/intraday-stocks-program`
**Scope:** substrate certification only (Gates G1–G7). No strategy code, no signal
computation, no window construction beyond fence metadata, no mutation of any native
market-data store (Phase 1 is **read-only over sources**; derived artifacts land in
their own trees).

---

## 1. Definition of done

`docs/reports/ISD_PHASE1_SUBSTRATE_CERTIFICATION.md` exists, is entirely
script-generated, and prints a verdict table:

```
G1 contiguity        PASS/FAIL   <evidence digest>
G2 currency          PASS        (store current through <date>)
G3 normalization     PASS/FAIL
G4 validity          PASS/FAIL   (0 violations / N violations)
G5 PIT mapping       PASS/FAIL   (<n> entities, intervals built)
G6 cost+slippage     PASS        (fee module + measured bands)
G7 vendor archive    PASS/FAIL/* (skipped → program runs native-only)
```

Every FAIL stops the program at that gate (spec §9). All supporting numbers come from
the scripts below — nothing hand-edited.

## 2. Deliverables

| File | Purpose |
|---|---|
| `scripts/isd/__init__.py` | package marker + shared paths/constants (session grid 09:15–15:29, canonical capital ₹2 Cr) |
| `scripts/isd/read_1m.py` | the single normalized reader (D3): abstracts `instrument_key` schema drift, returns a uniform DataFrame contract `(symbol, timestamp, o,h,l,c,v,is_synthetic)` |
| `scripts/isd/gate_contiguity.py` | G1: per-session (symbol, minute) completeness ledger + holiday-calendar reconciliation incl. special closures |
| `scripts/isd/gate_validity.py` | G4: OHLC violations, duplicate keys, negative volumes, price-sanity vs prior close |
| `scripts/isd/build_pit_universe.py` | G5: PIT membership table from equity-bhavcopy presence ∩ futures-bhavcopy F&O membership, entity-resolved via CSMP `symbol_entity_intervals` + ISIN issuer-prefix linkage |
| `scripts/isd/ingest_vendor_archive.py` | G7a–d: zip → `data/market_data/nse/candles/1m_vendor/{SYMBOL}.duckdb` staging tree (never mixed with native), ticker→ISIN map, junk-tail policy (drop volume=0 bars outside 09:15–15:29), session fingerprint stats |
| `scripts/isd/cross_validate_vendor.py` | G7e: overlap census 2023-01→2025-08, per-bar close agreement vs native store |
| `scripts/isd/verify_adjustments.py` | G7f: CA-seam audit vs certified daily adjusted view (zero fabricated overnight returns across split/bonus seams — four-arm pattern) |
| `scripts/isd/slippage_bands.py` | G6b: measured slippage (next-open vs signal-close; minute high–low by liquidity decile) on the native store |
| `scripts/isd/run_certification.py` | orchestrates all gates, emits the report + machine-readable `ISD_PHASE1_SNAPSHOT.json` |
| `core/execution/equity/intraday_fees.py` | G6a: era-accurate intraday fee function (sibling of frozen `delivery_fees.py`, same interface style) |
| `tests/isd/*.py` | unit tests per gate (synthetic fixtures, no network): reader drift handling, contiguity ledger math, validity detectors, PIT interval correctness, vendor tail policy, fee arithmetic vs hand-computed cases, adjustment-seam detector |

## 3. Gate acceptance criteria

### G1 Contiguity
- Every eq session file yields exactly one row per (symbol, expected-minute) or an
  explicit missing-bar ledger row (session, symbol, missing-minute list count).
- Holiday reconciliation: zero weekday sessions absent without a matching NSE-holiday/
  special-closure entry (list embedded as code + provenance note; 53 gaps must all match,
  incl. 2024-11-20 election closure).
- PASS = zero unexplained absences AND missing-intraday-bars census published.

### G2 Currency
- Latest per-day file date ≥ last completed trading session. (Verified 2026-08-21;
  re-checked at run time.)

### G3 Normalization
- Reader round-trips every file variant; a sampled diff across the 2026-03-04/05
  boundary shows identical values under both schemas; `is_synthetic`=0 asserted
  globally (any nonzero row fails the gate).

### G4 Validity
- Zero rows where `high < max(o,c)` or `low > min(o,c)` or `low <= 0`; zero duplicate
  (symbol, timestamp); volume ≥ 0; close within [0.5×, 2×] prior daily close band
  (violations listed, not silently dropped).

### G5 PIT mapping
- Membership table keyed `(entity_id, session_date)` covering 2023-01-02→present;
  spot-check set (≥10 names incl. one known ticker-recycle case) verified against
  manual NSE records; intervals survive the recycled-ticker test from CSMP contracts.

### G6 Cost + slippage
- Fee function reproduces hand-computed order scenarios exactly (₹20 floor regime and
  0.03% regime; STT sell-leg only; GST on brokerage+txn charges; stamp buy-side);
  ticket-size table printed at ₹2 Cr capital for book widths {10, 20, 40, 100} names.
- Slippage bands published per liquidity decile (p50/p90 next-open-vs-close drift,
  minute range distributions). Measurement only — no viability verdicts in Phase 1.

### G7 Vendor archive
- (a) ticker→ISIN resolution ≥95% automated; unresolved tickers listed, never guessed.
- (b) fingerprint: modal first-bar 09:15 / last-bar 15:29 per session; holiday alignment
  matches the same calendar as G1.
- (c) OHLC/duplicate audits pass at vendor grain before comparison.
- (d) junk-tail policy applied and counted (bars dropped, by symbol).
- (e) overlap census vs native: distribution of |Δclose| per matched (symbol, minute);
  **proposed PASS bar (confirm at review): ≥99% of bars |Δclose| ≤ 0.05% and median
  |Δclose| = 0**, plus disagreement census by month/vendor-symbol retained regardless.
- (f) adjustment verification: across known split/bonus seams, vendor overnight gap ≈ 0
  after the same adjustment basis as the daily adjusted view; any seam with a
  fabricated >|20%| gap fails the gate outright.
- Overall G7 PASS unlocks the §6b deep-window choice in Phase 0; FAIL leaves native-only
  (program still viable).

## 4. Execution order

1. Reader (G3) — everything depends on it.
2. G4 validity audit (cheap, immediate defect census).
3. G1 contiguity + calendar reconciliation.
4. `intraday_fees.py` + tests (independent of market data).
5. G5 PIT build (depends on existing CSMP/ISIN machinery).
6. Slippage measurement (G6b) on certified-clean sessions only.
7. Vendor ingest (G7a–d) → cross-validation (e) → adjustments (f).
8. Orchestrator + report generation; snapshot JSON committed alongside the report.

## 5. Test & verification commands

```
python -m pytest tests/isd -q
python scripts/isd/run_certification.py            # full gates → report
python scripts/isd/run_certification.py --gate G3  # single-gate reruns
```

## 6. Provenance rules (binding)

- Native stores are opened read-only throughout Phase 1.
- The vendor staging tree is new-write but append-only once written; its ingest script
  records zip member CRCs + row counts in a manifest for reproducibility.
- The certification report embeds: repo commit, script SHAs (via `git rev-parse`),
  row-count digests per gate — the Gate-A lesson (a certification certifies provenance).

## 7. Non-goals

Strategy families, feature computation, window fences, backtest harness changes, and
any LIVE/PAPER infra work are out of scope. Phase 0 (pre-registration) begins only
after this plan's report shows G1–G6 PASS and an explicit G7 disposition.
