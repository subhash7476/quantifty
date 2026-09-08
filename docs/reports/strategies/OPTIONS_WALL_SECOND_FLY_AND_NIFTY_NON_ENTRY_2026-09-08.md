# Options-Wall — two live questions, 2026-09-08

Both answered from the live pilot DB (`trades`, `scan_results`, `session_regime`) and
the poller log, not from reasoning about the design.

---

## Q1 — "SENSEX 75700 fly is running, a new setup formed at 75600, trade it too?"

**No. It is not a new setup — it is the same setup, re-centered.**

### The farm screen cannot produce two setups on one index

`ChainScanner._farm_screen` (`core/analytics/chain_scanner.py:101-146`) returns a
**list of exactly one `ScanResult`**, whose `strike` is the ATM derived from spot:

```
atm = self._atm_strike(chain, spot)
...
return [ScanResult(..., strike=atm, screen="premium_farm", ...)]
```

There is no per-strike enumeration. So the 75600 row in the farm list *is* the 75700
row: SENSEX drifted from ~75,700 to **75,594.73**, the ATM snapped one strike down,
and the screen re-printed with the new centre.

`build_iron_fly` behaves identically — it centres on `spot`, not on any scan result.

### Live state at 15:18

| | |
|---|---|
| Open SENSEX fly | trade_id 8, entered 09:58:38 |
| Short strike | 75,700 · wings 76,900 / 74,600 |
| Qty / credit / max loss | 20 · ₹11,617 · **₹12,383** |
| Expiry | 2026-09-10 (DTE 2) |
| Spot / current farm strike | 75,594.73 / **75,600** |
| SENSEX regime | Positive GEX (Stable) |

### Why a second fly would be unsafe, not merely redundant

1. **The second trade would never be managed.** `PaperExecutor.step`
   (`core/options_wall/paper_executor.py:78-81`) is
   `if open_rows: return self._manage(open_rows[0], ...)`. Drop the
   one-per-underlying guard and only `open_rows[0]` is ever evaluated — the other
   fly gets **no TP, no SL, no regime-flip exit, no time stop**, and which one is
   managed depends on whatever row order `open_trades` happens to return.
2. **Near-total overlap.** Wings are `spot × (1 ± 1.5%)`. The open fly is
   76,900 / 74,600; a 75,600-centred fly would be ~76,700 / 74,500. Same index, same
   2026-09-10 expiry, centres 100 pts (0.13%) apart. Combined max loss ≈ **₹24,800**
   — 2× the risk, ~0× the diversification. Both would hit SL on the same move.
3. **No aggregate-exposure check exists.** Sizing is `lots=1 × lot_size` per trade,
   full stop. Nothing in the pilot caps total open risk across trades.
4. **Direction matters.** The ATM moved *down*, i.e. the open 75,700 fly's put side
   is the one under pressure. Adding a 75,600 fly is re-centring / averaging down —
   doubling short gamma exactly when the market has demonstrated it moves.

### The lever the operator actually wants

The gate is `open_trades(underlying)` — **per underlying**. The pilot already permits
three concurrent flies: one each on NIFTY, BANKNIFTY, SENSEX. More positions come from
another index or another expiry, never from a neighbouring strike on the same expiry.

If a laddered / scaled entry is worth testing, it is a **pre-registered change** with
its own rule fixed before the fact — not a rule invented because of what the screen
printed this afternoon (`CLAUDE.md`, C2 post-hoc-overlay note).

---

## Q2 — NIFTY 23650 premium-farm row showing but "not executing"

**Cause: the entry window closed at 15:00; the screen re-qualified at 15:11.**

Reconstructed from `session_regime` and `scan_results`:

| Time | Event |
|---|---|
| 10:14:39 | NIFTY fly opened, short 23,700 |
| 14:44:47 | Closed on `regime_flip`, **net +₹512.05** |
| 14:47:05 | Last `premium_farm` row before the gap |
| 14:47:42 → 15:10:49 | Regime **Negative GEX (Volatile)** — farm screen returns `[]` (it requires "Positive") |
| **15:00** | **`PaperConfig.entry_end` — entry window closes** |
| 15:11:21 | Regime back to Positive; farm row at 23,650 reappears |
| 15:11 → 15:17 | Row visible on the dashboard, `step()` returns `None` on the time gate |

The four legs are all quotable in the 15:17:36 snapshot (23650 CE 25.40/25.45,
23650 PE 24.50/24.60, 24000 CE 0.80/0.85, 23300 PE 0.60/0.65), so this is **not** the
quote or spread guard — it is purely `entry_start <= now <= entry_end`.

Secondary point: today was NIFTY expiry (DTE 0). Even on a 15:11 entry, the
`dte <= 1 and now >= 15:15` time stop would have closed it four minutes later.

**So both today's non-entries are the system behaving as specified.** The dashboard
farm list is fed by `scan_results`, which the poller persists every cycle regardless
of executor state — a row on the list is a *screen pass*, not an *entry signal*.

### Worth deciding (not changed here)

- The farm list gives no visual indication of *why* a row is not tradeable
  (window closed / position already open on that underlying). That is the whole
  source of both questions today.
- `entry_end` at 15:00 vs `squareoff` at 15:15 is a deliberate 15-minute buffer;
  moving it is an operator decision, not a bug fix.
