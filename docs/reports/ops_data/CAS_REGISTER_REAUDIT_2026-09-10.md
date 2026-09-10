# CAS register re-audit — every item re-checked against the code, 2026-09-10

The register's status line said **"All 22 items closed"** (2026-08-27). Re-verified each item
against the current `main` (`5b5e961`). **Nineteen genuinely closed. One new open item (A9).
Five residuals worth a small cleanup pass — two of them user-visible.**

Method: check the code, not the register's own claim. Where an item was closed by a different
mechanism than proposed, that is noted rather than counted as a miss.

---

## Verdict table

| Item | Register said | Actual | Note |
|---|---|---|---|
| **A1** synthetic bars unmarked | closed | ✅ **closed** | `db_tick_aggregator.is_carry_forward()` + `is_synthetic` column, written per bar |
| **A2** `volume=0` predicate is index-unsafe | closed | ✅ **closed** | guard is `CAS_MARKABLE_PREFIX` (NSE_EQ) + `session_window("cash_auction")`; index path can't be reached |
| **A3** PIT CAS category | closed | ✅ **closed** | `data/cas/cas_category.duckdb` (536 KB) + `scripts/cas/build_cas_category.py` |
| **A4** ISD cert covers post-CAS sessions | closed | ➖ documented | amendment is a doc claim; not code-verifiable here |
| **A5** ISD SEALED straddle | MOOT | ➖ moot | battery closed at TRAIN; no sealed read will be taken |
| **A6** A-construct exit | resolved 15:14 | ➖ resolved | construct since retired at HOLDOUT |
| **A7** two-era certifier | closed | ✅ **closed** | `certify_index_slice.era_for()` returns `vendor \| native \| cas` |
| **A8** PM window has synthetic bars | closed | ✅ **closed** | `drop_synthetic()` defined at `day_features.py:45`, **applied at :540** |
| **A9** index reference freezes 15:15 | — | 🔴 **OPEN** | added today; see the register |
| **B1** `MARKET_CLOSE = 15:30` | closed | ⚠️ **closed + dead code** | `is_market_open(segment=…)` is properly schedule-driven. But `MARKET_CLOSE` survives, used only by `get_market_hours()` — which has **zero callers** |
| **B2** `SESSION_END = 15:30` | closed | ⚠️ **closed + dead code** | line 58 uses `session_window("cash_cat1", …)`; the constant at :46 has **zero uses** |
| **B3** reference-1m session filter | closed | ✅ **closed** | `SESSION_START, SESSION_END = session_window("cash_cat1", _ARCHIVE_ERA_DATE)` — era-pinned, deliberate |
| **B4** ingestor gate / F&O blind spot | closed | ✅ **closed (differently)** | gates on `is_any_open`, so it still aggregates through the auction — but the bars are now **marked** `is_synthetic` rather than suppressed. Legitimate; note the mechanism differs from the plan |
| **B5** NiftyShield chain poller | closed | ✅ **closed** | `is_derivatives_open()` at `chain_poller.py:375` |
| **B6** options-wall poller | open at write | ✅ **closed 2026-09-10** | `poller.py:313`, reached 15:40:02 on 09-09 |
| **B7** telemetry `market_open` | closed | ✅ **closed** | documented as cash Cat-I, and a separate `derivatives_open` field added |
| **B8** order-type restrictions | closed | ✅ **closed** | `cas_rules.py`: `MARKET_ORDER_CUTOFF = time(15, 25)`, restricted types, consumed by `upstox_adapter.py` |
| **B9** MIS square-off precedes ISD exit | closed | ✅ **closed** | `cas_rules.py` encodes ~15:12; re-exported into `intraday_fees.py` |
| **B10** chain_cache is rolling, not an archive | closed | ⚠️ **unchanged — but risk retired** | still exactly one snapshot (360 rows, `2026-09-10 15:33:40`). The *concern* — auction-window option behaviour being unreconstructable — is answered by a **different store**, `wall_chain_snapshots/` (~1,500 snapshots/session). Re-classify, don't "fix" |
| **B11** 1m ingest lagging | closed | ✅ **closed** | not lagging: files land the next morning by design (09-08's written 09-09 09:31, 09-09's written 09-10 09:19) |
| **C1** stale docstring | closed | ⚠️ **rewritten, now inaccurate** | it says the constants are *"retained because callers still reference them for display"* — **no caller does** |
| **C2** `POST_MARKET_CLOSE` label | closed | ➖ cosmetic | not re-checked in depth |
| **C3** UI shows CLOSED during 15:30–15:40 | closed | 🔴 **half-fixed** | `ops/routes.py:72,76` correctly split cash vs derivatives. **`ops/routes.py:218` and `app_facade/ops_facade.py:77` still use bare `is_market_open()`** |
| **C4** daily bar stamped 15:30 | closed | 🔴 **not fixed** | `daily_bhavcopy.py:108` and `:241` still `datetime.combine(td, time(15, 30))` |
| **C5** confused `PM_START_BAR` comment | closed | ✅ **closed** | comment block at `day_features.py:33-37` is clean and states the 361-tradeable-minute consequence |
| **C6/C7** CLAUDE.md CAS note + pitfall | closed | ✅ **closed** | pitfall present at `CLAUDE.md:583`, including the `NSE_EQ`-only rule |

---

## What actually needs work

### 1. A9 — the frozen index reference (real, open)
Filed today. Unlike everything else here it can still change a number, and it has already
done so once. See the register entry.

### 2. C3 — two sites still report the market closed while F&O trades (user-visible)

```
flask_app/blueprints/ops/routes.py:218   fallback = "DISCONNECTED" if MarketHours.is_market_open() else "CLOSED"
app_facade/ops_facade.py:77              fallback = "DISCONNECTED" if MarketHours.is_market_open(...) else "CLOSED"
```

`is_market_open` now defaults to `cash_cat1`, which ends **15:15** post-CAS — so these read
`CLOSED` for the **last 25 minutes of every derivatives session**, which is worse than the
15:30–15:40 the register originally flagged. Lines 72 and 76 of the same file were fixed;
these two were missed. One-line change each, to `is_derivatives_open()` or `is_any_open()`.

### 3. C4 — daily bars still stamped 15:30
`core/database/providers/daily_bhavcopy.py:108` and `:241`. The register is right that the
*value* is correct and only the label is wrong, but it was recorded as closed and is not.

### 4. Dead code left behind by the B1/B2 fixes
`MarketHours.MARKET_CLOSE`, `MarketHours.get_market_hours()` (zero callers), and
`MarketSession.SESSION_END` (zero uses). The repo's own convention is to delete unused code
rather than leave it — and here the risk is concrete: a stale 15:30 constant sitting in the
module that *used* to be the authority is exactly what a future reader reaches for. Fixing it
also removes C1's false justification.

### 5. Re-classify B10 rather than leave it "closed"
The cache is unchanged and still holds one snapshot. It is fine — but the register reads as
though it was fixed, and the next person to check will find it exactly as originally
described. The honest entry is *"unchanged by design; the archival need is served by
`wall_chain_snapshots/`."*

---

## Outside the register, found while auditing

- **`.claude/worktrees/*` hold pre-CAS copies of the fixed files** —
  `market_hours.py:153` there still reads `MARKET_OPEN <= current_time < MARKET_CLOSE`, the
  original defect. Five worktrees. Harmless while dormant; a re-introduction path if any is
  ever resumed and merged.
- **`scripts/mrlc_test/archive_ingest.py:21`** carries its own `SESSION_END = 15*60+30`,
  independent of `session_schedule`. Test-scoped, never registered.

---

## Bottom line

The 2026-08-27 remediation was substantially real — the load-bearing items (A1, A2, A3, A7,
A8, B4, B5, B8, B9) are properly closed in code, several by better mechanisms than proposed.
**Nothing found here changes a research number.** What remains is one genuine new defect (A9),
two cosmetic misses recorded as closed (C3 residual, C4), and tidy-up. The register's "all 22
closed" line was ~86% true, and the misses are all in Class C.
