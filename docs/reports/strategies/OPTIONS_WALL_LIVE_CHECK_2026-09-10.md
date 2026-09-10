# Options-Wall — live check, 2026-09-10 12:07 IST

Market open, poller running, both fixes from 2026-09-09 deployed. Three questions answered:
the live behaviour of (D) + the pin fix, whether the 15:35 / 15:29 session work reached
options-wall, and branch state.

---

## 1. Live state — both fixes are running

Poller PID 24120, heartbeat `2026-09-10T12:06:11`, status OK, all three chains quoting
(NIFTY 182 / BANKNIFTY 290 / SENSEX 286 rows).

| | trade 29 | trade 30 |
|---|---|---|
| Index | **NSE_INDEX\|Nifty 50** | BSE_INDEX\|SENSEX |
| Expiry / DTE | 2026-09-15 / **5** | **2026-09-10 / 0 — expires today** |
| Entered | 09:30:00.89 | 09:30:05.40 |
| Short / wings | 23,450 · 23,800 / 23,100 | 74,800 · 75,900 / 73,700 |
| Qty · credit · max_loss | 65 · ₹12,399 · ₹10,351 | 20 · ₹7,061 · ₹14,940 |
| Spot now | 23,440.45 | 74,796.26 |
| **Gross now** | **+₹250** | **+₹1,203** |
| Net if closed now | +₹21 | **+₹997** |
| TP (25% credit) | +₹3,100 — no | +₹1,765 — no (**68% of the way**) |
| SL (50% max_loss) | −₹5,176 — no | −₹7,470 — no |
| Time stop | **not until 2026-09-14 15:15** | **fires 15:15 today** |

**Two things confirmed live:**

- **NIFTY is trading for the first time.** The pin fix works in production: trade 29 is
  centred on 23,450 against spot 23,440 — 0.04% away. Under the old signed-exposure pin,
  NIFTY was locked out of 1,649 of 1,649 snapshots yesterday.
- **Zero round trips in 2.6 hours on both indices.** Yesterday by this time SENSEX had
  churned through 12 round trips.

### The honest caveat on today as evidence

**Today has been a quiet regime day and therefore proves little about (D).** Regime changes
so far: **1 on NIFTY, 1 on SENSEX** — against **55** on SENSEX yesterday. The old rule would
have produced roughly one round trip today, not nineteen. So the absence of churn today is
*consistent with* the fix but is not a test of it; the load-bearing evidence remains
yesterday's replay. The first real test is the next high-flip session.

What today *does* establish, independently of regime: the pin fix admits NIFTY, at the right
strike, in production.

---

## 2. The 15:35 / 15:29 session work never reached options-wall

**It is NiftyShield's, not options-wall's.**

| where | value |
|---|---|
| `core/execution/options/nifty_shield_exit.py:10,51-52` | hard time exit, default **15:35** |
| `nifty_shield_marks.py:233`, `nifty_shield_handler.py:28-30,657` | the **15:29 → 15:35** bridge: the underlying's 1m bars stop at the cash auction print, so marks need another source to reach the 15:35 exit |
| `core/options_wall/paper_executor.py:33` | `squareoff: str = "15:15"` — **unchanged since 2026-08-14** |

### This leaves options-wall internally inconsistent

The **poller** was made CAS-aware — `poller.py:313` gates on
`MarketHours.is_derivatives_open()`, which resolves to the derivatives segment and ran to
**15:40:02** yesterday. That closes CAS register item **B6**.

The **executor** was not. `squareoff = "15:15"` is a bare string, and 15:15 is the
**`cash_cat1`** close. Options-wall trades **derivatives**:

```
derivatives window today: (09:15, 15:40)
cash_cat1  window today: (09:15, 15:15)
```

So the pilot now **collects data to 15:40 and stops managing positions at 15:15** — the wrong
segment's boundary, by 25 minutes.

Two things make this citable rather than a matter of taste:

- **CLAUDE.md is explicit:** *"Session windows come from `core/market/session_schedule.py`
  (segment-named, date-keyed), never from a bare constant."* `"15:15"` and `entry_end
  "15:00"` are exactly that bare constant.
- **The CAS register does not cover it.** B6 flags the options-wall *poller* gate; the
  executor's `squareoff` appears nowhere in `CAS_ADAPTATION_REGISTER.md`. It was missed, not
  decided.

### It bites today

**SENSEX trade 30 expires today.** Its time stop fires at 15:15, forfeiting the 15:15–15:40
derivatives window on its own expiry day — the highest-theta window it will ever see. It is
currently +₹1,203 gross and 68% of the way to TP.

### Not changed — this needs your call

I have **not** touched the squareoff. Changing a live exit rule mid-session, with an expiring
position open, is not a thing to do unilaterally. It is also a genuine design question, not a
one-line fix:

- **15:40 (derivatives close)** — the segment-correct answer, maximises theta. But 15:15–15:35
  is the cash auction: the underlying is not continuously traded, option quotes can be erratic,
  and on expiry day this is peak pin risk. NiftyShield needed a dedicated mark path
  (`nifty_shield_marks.py`) precisely to survive this window.
- **15:35 (auction end)** — matches NiftyShield, so both strategies flatten on one clock.
- **15:15 (status quo)** — defensible as "flat before the auction", and it is what every
  observation in this pilot so far was produced under. But it is currently an accident, not a
  decision.

Whichever is chosen, it should be **read from `session_schedule` rather than hardcoded**, and
it should be recorded in the CAS register.

Note the dependency: options-wall marks from the **option chain**, not from underlying 1m
bars, so it does *not* automatically inherit NiftyShield's 15:29 bar-gap problem — chain
quotes continue to 15:40. Whether those quotes are *reliable* through the auction is
unmeasured, and `data/options/wall_chain_snapshots/` has been accumulating the 15:15–15:40
window since the poller fix, so it can now be measured before anything is changed.

---

## 3. Branch state

| | |
|---|---|
| Work was done on | `fix/options-wall-regime-flip-exit` (4 commits) |
| Now | **merged into `main` by another session**; `git branch --contains 84903a2` lists `main` |
| Working tree | checked out on **`main`** at `258e780` |
| Both fixes present in the tree | yes — verified in `paper_executor.py` and `chain_scanner.py` |

The tree is on `main`, so any further change needs a new branch first.

**Pre-existing unrelated failure:** `tests/g1/test_g1_closure_guard.py::test_no_unwhitelisted_legacy_option_future_construction_in_core` fails on `nifty_shield_groups.py`. It fails identically at `8421e47`, before any of this work. It belongs to the NiftyShield Stage 1 work — not touched.

---

## Reproduction

- Live marks: `data/options/wall_chain_snapshots/2026-09-10.duckdb`, newest snapshot per index
- Open trades: `wall_scan_results.duckdb` → `trades where exit_ts is null`
- Regime flips today: `session_regime`, `cast(ts as date) = '2026-09-10'`
- Session windows: `core.market.session_schedule.session_window('derivatives', date(2026,9,10))`
