# Why the Options-Wall TP Never Fires

Investigation 2026-09-07. Systematic-debugging pass on `core/options_wall/paper_executor.py`.
Two defects found. The first is arithmetic on live rows; the second rests on a backtest and
carries a granularity caveat, stated inline.

---

## Finding 1 (proven) — the stop-loss cannot fire on 6 of 7 live trades

`sl_mult = 2.0` triggers when gross P&L ≤ −2 × `net_credit`. But an iron fly's structural
max loss is `wing_width × qty − credit`. So the stop is reachable only when
`max_loss / net_credit ≥ 2.0`. Straight arithmetic on the live book:

| trade | max_loss | net_credit | ratio | SL reachable? |
|---|---:|---:|---:|---|
| 1 | 21,071 | 8,929 | 2.36 | yes |
| 2 | 10,433 | 15,817 | 0.66 | **no** |
| 3 | 11,959 | 14,291 | 0.84 | **no** |
| 4 | 37,965 | 52,035 | 0.73 | **no** |
| 5 | 37,185 | 52,815 | 0.70 | **no** |
| 6 | 10,420 | 13,581 | 0.77 | **no** |
| 7 | 11,963 | 10,787 | 1.11 | **no** |

Six of seven trades ran with a stop that was mathematically incapable of firing — the only
real downside bound was max loss itself. Historically the ratio clears 2.0 in **14.7%** of
NIFTY weekly entries (median 1.20), and **0 of 521** backtested flies ever reached −200% of
credit.

The parameterisation is dimensionally wrong: `sl_mult × credit` bounds a loss by a credit
that has no fixed relationship to the position's risk. This holds regardless of anything
below.

---

## Finding 2 (supported, with caveat) — TP requires expiry day; the time stop removes it

### Not a silent failure

`unrealized_pnl()` returns `None` if any of the four legs is unquoted, and `_manage` then
skips the TP branch with no trace. Measured over the actual lifetimes of trades 3, 5, 6, 7
against the 0.9-second snapshot store:

| trade | snapshots in window | all 4 legs quoted | blind cycles |
|---|---:|---:|---:|
| 3 Nifty | 560 | 560 | 0 (0.0%) |
| 5 SENSEX | 545 | 545 | 0 (0.0%) |
| 6 SENSEX | 672 | 672 | 0 (0.0%) |
| 7 Nifty | 649 | 649 | 0 (0.0%) |

TP was evaluated on every cycle with a valid P&L. The branch works.

### The marks never came near the target

Mark-to-close path reconstructed from `wall_chain_snapshots`. `% of TP` = best gross P&L
reached ÷ (0.5 × credit):

| trade | TP gross | best gross reached | % of TP | worst |
|---|---:|---:|---:|---:|
| 3 Nifty | 7,146 | 1,202 | 16.8% | −743 |
| 5 SENSEX | 26,408 | 1,792 | 6.8% | −1,372 |
| 6 SENSEX | 6,790 | 1,054 | 15.5% | −108 |
| 7 Nifty | 5,393 | 904 | 16.8% | −317 |

Best excursion across every live trade: **16.8% of target.** (Trades 1–2 predate the
retained snapshot files.)

### When is 50% reachable?

Backtest: NIFTY weekly ATM iron fly, wing ±1.5%, EOD closes from
`data/market_data/options_bhavcopy.duckdb`, entries at DTE 1–5, marked daily to expiry.
**n = 521.** Prediction stated before the run: *if 0.5 is merely slow, most flies cross it
on expiry day and the all-life hit rate is high (>60%); if 0.5 is structurally too high,
the hit rate stays low even counting expiry day.*

| Reaches ... of credit at some point | rate |
|---|---:|
| 20% | 53.7% |
| 30% | 43.8% |
| 40% | 33.8% |
| **50%** | **28.4%** |
| 60% | 24.2% |

**Of the 148 flies that reached 50%, all 148 first crossed on DTE 0 — expiry day.** Zero
crossings on any pre-expiry session.

### The time stop removes expiry day

```python
dte = (date.fromisoformat(row["expiry"]) - now.date()).days
if reason is None and dte <= 1 and now.time() >= _hhmm(self.cfg.squareoff):
    reason = "time_stop"
```

`dte <= 1` at 15:15 squares off the **afternoon before expiry** — the session before the
only one in which TP has ever fired. `min_dte = 1` separately blocks opening on expiry day,
so no position can reach DTE 0 by any route.

**Observation status:** `time_stop` has fired **0 times** — no trade has yet been alive at
DTE-1 15:15 (all seven exited manually or on regime flip first). The path is nonetheless
live: the poller demonstrably runs past the cutoff, reaching **15:39** on both 2026-09-04
and 2026-09-02. So this is verified-reachable code, not yet verified-executed.

### Granularity caveat on the "never" claim

The backtest marks once a day at settlement; the executor marks every ~0.9s, so EOD marking
**understates** the true max favorable excursion. Measured inflation factor on trades 3/5/6/7
(intraday MFE ÷ same-window session-end-only MFE): **1.06, 1.14, 1.34, 1.25.**

Max capture before expiry day, at EOD granularity and rescaled by that factor range
(n = 337 entries surviving to a pre-expiry mark):

| | EOD (×1.00) | ×1.06 | ×1.20 | ×1.34 |
|---|---:|---:|---:|---:|
| p99 | +0.41 | +0.43 | +0.49 | +0.55 |
| max | +0.47 | +0.49 | +0.56 | +0.62 |
| **would fire at 50%** | **0.0%** | **0.0%** | **1.2%** | **2.4%** |
| would fire at 25% | 20.5% | 22.6% | 29.1% | 34.7% |

So the honest figure is **0–2.4% of pre-expiry trades**, not a flat zero. Effectively never,
but not provably never.

Thresholds that would actually fire within the current holding window (EOD granularity,
so these are floors):

| Threshold | % of trades |
|---:|---:|
| 10% | 48.7% |
| 15% | 39.8% |
| 20% | 31.2% |
| 25% | 20.5% |
| 30% | 11.3% |
| 50% | 0.0% |

---

## Options

1. **Re-express the stop as a fraction of `max_loss`, not of credit** (e.g. −0.5 × max_loss).
   Fixes Finding 1. Correct regardless of what is done about TP.
2. **Lower `tp_frac` to ~0.20–0.25.** Fires on 31%/21% of trades inside the current holding
   window. Keeps the time stop. Smallest change; banks small wins.
3. **Change the time stop to `dte <= 0`** so the fly is held into expiry day, where the 50%
   capture lives (28.4%). Bigger P&L per win — but expiry-day gamma is exactly where max loss
   is realised, so variance rises sharply and this must not be done before (1).

Recommendation: **(1) first, then (2).** Do not take (3) until the stop is real.

## Note on the live book

Five of seven trades were closed manually before any rule could fire, so the live record
alone cannot separate "operator is impatient" from "rule is broken". The backtest is what
separates them.

---

## Resolution (applied 2026-09-07)

`core/options_wall/paper_executor.py`, `PaperConfig`:

```diff
-    tp_frac: float = 0.5
-    sl_mult: float = 2.0
+    tp_frac: float = 0.25       # of net credit
+    sl_frac: float = 0.5        # of max_loss, NOT of credit: a fly cannot lose a multiple of its own credit
```
```diff
-            elif pnl is not None and pnl <= -self.cfg.sl_mult * row["net_credit"]:
+            elif pnl is not None and pnl <= -self.cfg.sl_frac * row["max_loss"]:
```

`sl_mult` is deleted, not deprecated — no shim. Option 3 (holding into expiry day) was
**not** taken: the `dte <= 1` time stop is unchanged, so TP now fires inside a window where
the backtest says it is reachable on ~21% of trades rather than ~0%.

Four tests added to `tests/options_wall/test_paper_executor.py`, written before the change
and confirmed failing against the old config:

| test | asserts |
|---|---|
| `test_tp_fires_at_quarter_of_credit` | +30% of credit → `"tp"` (would not fire at 0.5) |
| `test_tp_does_not_fire_below_threshold` | +10% of credit → `None` |
| `test_sl_fires_on_fraction_of_max_loss` | −29.25 vs max_loss 30 → `"sl"` (old rule needed −390, unreachable) |
| `test_sl_does_not_fire_inside_the_band` | −9.75, inside 0.5 × max_loss → `None` |

`tests/options_wall/`: **37 passed.**

**Deployment:** the running orchestrator holds the old `PaperConfig` in memory. The new
thresholds apply only after the poller restarts. Zero open trades at the time of the change,
so a restart orphans nothing.

**Related, not fixed:** `core/execution/options/nifty_shield_exit.py:48` uses the same
`pnl <= -sl_mult × credit_received` shape (`sl_mult` 2.0). If NiftyShield's structure is
defined-risk, its stop has the same reachability problem. Not touched here — separate
strategy, separate change.
