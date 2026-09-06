# MM.5_MATERIALIZATION_REPORT.md

**Type:** Operational report — first real instrument-master snapshot materialized + validated. **No code in the frozen areas changed.**
**Date:** 2026-06-08
**Phase:** MM.5 (Instrument Master Materialization). Closes 4C.7-readiness blocker **#2** ("master DB absent on disk", `PHASE_4C_7_READINESS.md`). Builds on the MM.1–MM.4 readiness gate (`f8b26cd`, `db7a7d4`).
**Basis (real run):** `scripts/mm5_materialization_check.py` against the live Upstox CDN, materialized into `data/instruments/nse_fo_instruments.duckdb`.
**Constraints honored:** no order-routing, no resolver, no startup-gate, no reconciliation changes. Every validation is a read-only resolver call or a pure `assess()`; materialization writes a **data** file only via the existing `parse_instruments` + `write_snapshot` production path.

---

## Verdict

**PASS — the first real master snapshot is materialized; identity, freshness, and coverage are trustworthy on the live F&O path.** All five deliverables are green. Validation also surfaced two **attribute** data-quality findings with **no live impact today** (the canonical attribute layer is dormant pre-4C.7): `tick_size` is stored 100× too large (raw paise, unnormalized — Finding 3), and NIFTY/BankNifty `lot_size` (65/30) should be confirmed against the published lot (Finding 4). Both are owned by the parser/4C.7 slice; neither blocks the materialization itself.

| Deliverable | Result |
|---|---|
| Materialized master | **65,383 rows**, one snapshot `2026-06-08`, 22.0 MB DuckDB at `data/instruments/nse_fo_instruments.duckdb` |
| Source-contract verification | **PASS** — derivative segments cleanly typed; every resolver-mapped type present; field shape matches `parse_instruments` |
| Coverage validation (real data) | **PASS** — all 4 segments non-empty, EQ-ISIN 100%, active weekly expiry present for NIFTY + BANKNIFTY |
| Startup-gate validation (real data) | **FRESH** — `assess(resolver, [NIFTY, BANKNIFTY])` → FRESH; absent-path proof → BLOCK/absent |
| Spot-resolve real contracts | **PASS** — NIFTY/BANKNIFTY futures, Nifty 50 index, RELIANCE equity all resolve to `CanonicalInstrument`, not `None` |

Re-runnable on demand via `python -m scripts.mm5_materialization_check` (idempotent within a `snapshot_date`).

---

## 1. Materialized master

Downloaded the live CDN once (`https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz`, **no auth**): 3.69 MB gzip, **135,424** total instruments. Filtered to the four accepted segments and written through the exact production path (`parse_instruments` → `write_snapshot`, `snapshot_date = date.today()` as `refresh()` defaults):

| Segment | Rows |
|---|---|
| NSE_FO | 40,522 |
| MCX_FO | 15,385 |
| NSE_EQ | 9,337 |
| NSE_INDEX | 139 |
| **Total** | **65,383** |

Single snapshot on disk (`snapshot_date=2026-06-08`, 65,383 rows) — the forward-only series begins here (Finding 1 / Decision 3: every day delayed is historical `as_of` accuracy never recoverable).

## 2. Source-contract verification (Q7)

The fields `parse_instruments` depends on, measured against the live payload:

- **Load-bearing identity/typing universal:** `instrument_key` 100%, `segment` 100%, `instrument_type` 100%, `name` 100%.
- **`trading_symbol` (snake_case) is what Upstox actually sends** — 100% via the `trading_symbol` key, **0%** via `tradingsymbol`. The parser's `tradingsymbol or trading_symbol` fallback is **load-bearing**, not cosmetic; a contract test must pin the snake_case key.
- **`expiry`/`strike` 85.5%** — present on exactly the 55,907 derivative rows; absent on the 9,476 EQ/INDEX rows (correct). `expiry` encoding is **ms-int** (55,907) — the `_parse_expiry` ms branch is the live path; the ISO-string branch is unexercised by the current source.
- **`lot_size`/`tick_size` 99.8%** — the 139 missing are exactly the NSE_INDEX rows (no lot/tick), correct.
- **`isin` 14.3%** = the 9,337 NSE_EQ rows; 100% of equities carry ISIN.

**Derivative segments are cleanly typed** `CE` (27,533) / `PE` (27,579) / `FUT` (795) — no stray types, so the "0 OPTION rows on a schema shift" risk (policy §8 #4) is **not** present today. The 135 distinct `instrument_type` codes overall are the expected NSE **equity-series** tail (`EQ`/`BE`/`BZ`/`SM`/`ST`/`SG`/`GS`/`TB`/`N0`…) plus MCX codes — all in NSE_EQ, deliberately inert downstream (the resolver maps only `{CE,PE,FUT,EQ,INDEX}`). **Not drift.**

## 3. Coverage validation against real data (policy §3)

Read through the resolver's coverage facts on the materialized master:

- `latest_snapshot_date()` = **2026-06-08** == `expected_snapshot_date` (2026-06-08).
- `segment_row_count()`: NSE_FO 40,522 · MCX_FO 15,385 · NSE_EQ 9,337 · NSE_INDEX 139 — all non-empty.
- **EQ rows / EQ-with-ISIN = 2,452 / 2,452 (100%)** (the tradable `EQ`-series equities; the other ~6,885 NSE_EQ rows are non-`EQ` series the resolver intentionally excludes).
- **Underlying-token reconciliation:** 216 distinct NSE_FO underlyings; both `NIFTY` and `BANKNIFTY` tokens present after `normalize_underlying` (BANKNIFTY was the flagged risk — confirmed reconciled).
- `active_expiry_present(>= expected)`: **NIFTY True, BANKNIFTY True** (nearest NIFTY weekly = 2026-06-09, Tuesday).
- **Gate coverage** (NSE_FO/MCX_FO present + active expiry, exactly what `assess()` asserts) = **True**. Broader policy §3 evidence (+ EQ-ISIN 100% + INDEX present) = **True**.

## 4. Startup-gate validation against real data (policy §4/§5)

The read-only verdict the LoopDriver `_check_master_readiness` gate consumes, evaluated against the real master — **no checker was wired into a live entry script** (that is blocker #4 / a separate slice, and would be a startup-gate change):

```
assess(resolver, [NIFTY, BANKNIFTY], now=IST) -> FRESH  (reason=None, latest=2026-06-08, expected=2026-06-08)
absent-path proof: assess(<missing-db resolver>) -> BLOCK (reason=absent)
```

FRESH means a live F&O LoopDriver would proceed; the absent-path BLOCK confirms the gate has teeth (would `abort_startup()` → STOPPED + CRITICAL had the master been missing).

## 5. Spot-resolve real contracts

Row counts can pass while a token mismatch silently returns `None`; resolution was exercised end-to-end:

| Call | Result | (`tick_size` raw → ₹, see Finding 3) |
|---|---|---|
| `resolve_future("NIFTY")` | FUTURE · NIFTY FUT 30 JUN 26 · lot=65 · tick_raw=10.0 | ₹0.10 |
| `resolve_future("BANKNIFTY")` | FUTURE · BANKNIFTY FUT 30 JUN 26 · lot=30 · tick_raw=20.0 | ₹0.20 |
| `resolve_index("Nifty 50")` | INDEX · NIFTY · lot=1 · tick_raw=0.0 | n/a |
| `resolve_equity("INE002A01018")` | EQUITY · RELIANCE · lot=1 · tick_raw=10.0 | ₹0.10 |

All return a `CanonicalInstrument` — none `None`. **Identity/lookup is proven; the `tick_size` attribute is mis-scaled (Finding 3) and `lot_size` needs a published-value sanity check (Finding 4).**

---

## Operational findings (for the implementing/ops slice — out of MM.5 scope)

1. **`snapshot_date` is stamped machine-local (`date.today()`); the gate computes `expected` in IST.** They agreed today (box date 2026-06-08 == IST date; `assess` → FRESH). But off an IST-aligned clock they can diverge by a day near the date boundary, which would make `evaluate` return WARN — or BLOCK("stale") — on a perfectly fresh download. **The scheduled refresh job (policy §2) must run on an IST clock or stamp the IST date**, otherwise materialization and the gate disagree. Not a code change for MM.5; a requirement on the refresh-job slice.
2. **`trading_symbol` snake_case + ms-int `expiry` are the live encodings.** The forthcoming committed source-contract test (policy §7) must assert the `trading_symbol` key and the ms-int `expiry` branch specifically — the variants the live source actually uses.

3. **`tick_size` is stored in raw Upstox units (paise, ×100 the rupee tick) and is NOT normalized — latent data-quality defect.** The live payload encodes `tick_size` as paise: NIFTY **options** carry `5.0` (= ₹0.05, the canonical option tick), and the entire distinct-value set is clean paise — `5.0`(₹0.05), `1.0`(₹0.01), `50.0`(₹0.50), `10.0`(₹0.10), `100.0`(₹1), `500.0`(₹5), `1000.0`(₹10). `parse_instruments` does `float(tick_size or 0.0)` with **no `/100`**, so the DB — and therefore `CanonicalInstrument.tick_size` (resolver carries it through unscaled, `resolver.py:230`) — holds a value **100× the rupee tick**. **No live impact today:** nothing in `core/` scales or consumes `CanonicalInstrument.tick_size` yet (the legacy `options_provider` path reads expiry/strikes/lot from the master, never tick), and the canonical layer is dormant pre-4C.7. But once 4C.7 wires canonical attributes into order pricing/rounding, a 100× tick would mis-round prices. The platform's own convention is rupees (`database/schema.py:229` defaults `tick_size` to `0.05`), confirming the mismatch. **Fixing the parser is out of MM.5 scope ("validate, not repair"); this is the surfaced finding** — owned by the parser/4C.7 slice (normalize at ingest, or scale at the resolver boundary, with a regression test on the paise→₹ conversion).

4. **`lot_size` needs a published-value sanity check.** Materialized NIFTY FUT/OPT `lot_size=65`, BANKNIFTY=30. These are carried raw from Upstox (unscaled, correct unit) and the whole point of the as_of architecture is lot correctness — but 65 differs from the `75` the repo's synthetic fixtures assume (`test_master_ingest.py`; CLAUDE.md's "post-2024 SEBI 50→75" note). It may be a legitimate later revision (the live master is authoritative over a stale doc), but the next slice should confirm 65/30 against the currently-published NSE lot before live F&O routing trusts it.

## Explicitly out of scope (not done here, by constraint)

- **Committed sanitized-fixture contract test** (policy §7) — verification was done against the live payload only; the CI fixture test is a follow-up.
- **`fetch_instrument_master.py` "after OAuth" docstring fix** (policy §1) — noted, not touched.
- **OS-scheduled refresh job** (policy §2, blocker #3) and **production `master_readiness` checker wiring** into a live F&O entry script (blocker #4) — separate slices; wiring the checker would be a startup-gate change.

## Artifacts

- `data/instruments/nse_fo_instruments.duckdb` — the materialized master (gitignored under `/data/`; not committed).
- `scripts/mm5_materialization_check.py` — the on-demand acceptance check (download → contract → materialize → coverage → spot-resolve → gate). Uncommitted pending review.

> **No commits.** PROJECT_STATE / CHANGELOG_PLATFORM sync is **deferred to post-review** (the MM-phase KB sync lands with its commit, per the `KB Sync: MM.4` precedent) — nothing committed per the MM.5 instruction.
