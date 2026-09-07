# NiftyShield Trade-Evidence Page — Four Defects, 2026-09-07

Raised from the live slide-over for group `50a9357e-2b94-5dfc-804a-5d12317f7236`
(bear call spread, SELL `NIFTY15SEP2623750CE` @ 193.95 / BUY `NIFTY15SEP2623900CE` @ 114.00,
entered 13:01). Four reported issues; **they are three root causes** — the empty SPAN/ELM and
the wrong margin are the same fault.

| # | Reported | Root cause | Status |
|---|---|---|---|
| 1 | Lot size should be 65, shows 75 | Certified config pins 75; handler sizes from it; the instrument-layer resolver is never wired | **Fixed** (value), resolver **recommended** |
| 2 | MTM Δ nonsense | Two arithmetic bugs in the slide-over, both reproduced to the rupee | **Fixed** |
| 3 | Margin ₹4,619 vs Upstox ₹79,901.74 | SPAN archive a month stale → silent downgrade to flat-rate `MarginTracker` | **Made loud**; refresh is an operator action |
| 4 | SPAN and ELM empty | Same cause as #3 — they only exist under `NseMarginEngine` | **Explained on the page** |

---

## 1. Lot size — NSE moved NIFTY to 65

The instrument master is unambiguous:

```
data/instruments/nse_fo_instruments.duckdb, latest snapshot
NIFTY CE/PE: lot_size 65, 1,580 contracts, expiries 2026-09-08 -> 2031-06-24
```

The live chain cache agrees — every one of the 340 rows in the latest snapshot carries
`lot_size = 65`, including both traded legs. **Only the strategy disagreed.**

`strategies/nifty_shield_v1/config.py` pinned `"lot_size": 75`, and
`nifty_shield_handler.py:283` sizes the structure straight off it
(`lot_size = int(self._strategy_cfg.get("lot_size", 75))`, then `qty = lots * lot_size`).
That is why the ledger shows **75** units per leg — an un-tradeable quantity.

A second copy lived in `core/execution/options/nifty_shield_gates.py:45`
(`DEFAULT_CERTIFIED_CONFIG`), feeding `max_position_size = max_lots × lot_size`. Both are now
65, and a test pins them equal so they cannot drift apart again.

### The real fix is not a constant — recommended, not done

`core/execution/options/nifty_shield_groups.py::build_leg_order` already resolves the true
per-contract lot size from `InstrumentResolver` and treats the config only as a fallback.
That is the ADR-016 design: the source names a strike/expiry, the **execution boundary**
builds the tradable instrument against the instrument layer. But the handler never imports
`assemble_group`/`build_leg_order` — it builds its own path and reads the frozen constant. So
this number will rot again at the next NSE revision.

Wiring the resolver into the handler's entry path changes how every leg is sized in a
CONFORMANT-certified strategy — that is a re-expression of the certified artifact, not a
defect fix, so it is **left as a recommendation** rather than done in this pass.

### Restart safety, checked

`_nifty_shield_used_margin` recovers lots as `filled_quantity / lot_size`. Against the
existing 75- and 150-unit positions in `execution.db` this now yields fractional lots
(75/65 = 1.1538). That is harmless: the margin call is
`abs(lots) × lot_size × price × rate`, and `lots × lot_size` reconstructs `filled_quantity`
exactly, so open positions price identically across the change.

---

## 2. MTM Δ — two bugs, both reproduced exactly

The page showed **−₹19,10,756** on a leg whose entire structural risk is a few hundred rupees.
`flask_app/templates/nifty_shield/index.html`, old `legMtm`:

```javascript
const avg = cost / Math.abs(signedQty);
const lot = m.lot_size || 75;
return (m.ltp - avg) * signedQty * lot;
```

**Bug A — a short leg's average entry came out negative.** For the SELL leg,
`cost = 193.95 × 75 × (−1) = −14,546.25` and `signedQty = −75`, so
`cost / |signedQty| = −193.95`. The mark difference then became `198.00 − (−193.95) = 391.95`
instead of `4.05`.

**Bug B — lot size applied twice.** The ledger `quantity` is already in units
(`qty = lots × lot_size`, `nifty_shield_handler.py:303`), so multiplying by `m.lot_size`
again scales the result by 65.

Both bugs reproduce the screenshot to the rupee:

| Leg | Old shown | Old formula | Correct |
|---|---:|---|---:|
| SELL 23750 CE | −₹19,10,756 | (198.00 − **(−193.95)**) × (−75) × **65** = −1,910,756.25 | **−₹303.75** |
| BUY 23900 CE | +₹17,306 | (117.55 − 114.00) × 75 × **65** = +17,306.25 | **+₹266.25** |

The BUY leg is the clean proof of Bug B on its own — it is exactly 65× the right answer.

**Bug C, found while fixing — fills were pooled across sessions.**
`flask_app/blueprints/nifty_shield.py::_leg_fills` keyed the ledger by **symbol alone**, with
no session or group scope, so every session that ever traded a strike contributed to that
leg's quantity and average. This is live, not hypothetical: `NIFTY25AUG2624250PE` already has
2 rows summing 225 units in the ledger today.

### Fix

The arithmetic moved server-side, where it is testable and where the units are known:

- `_leg_fills` is now keyed by `(session, symbol)`.
- A new `_leg_position(fills)` returns `signed_qty` (units) and `avg_price`, dividing by the
  **signed** quantity so a short leg reports a positive average entry, and returning `None`
  for a flat round trip.
- The payload carries `leg_positions`; `legMtm` is now
  `(m.ltp - pos.avg_price) * pos.signed_qty` — no lot factor exists to double-apply.

Four tests in `tests/flask/test_nifty_shield_blueprint.py`, written first and confirmed
failing, pin the short-leg sign, both legs of this live trade (−303.75 / +266.25), the flat
round trip, and the session scoping.

---

## 3 + 4. Margin ₹4,619 and empty SPAN/ELM — one cause

**The SPAN archive is a month stale.** `data/span/` ends at `nse_fo_span_2026-08-06.parquet`;
`expected_span_date()` returns `2026-09-07`. Reproduced:

```
LOAD FAILED: FileNotFoundError No SPAN snapshot found for 2026-09-07
             at data\span\nse_fo_span_2026-09-07.parquet
```

`scripts/nifty_shield_paper_runner.py::_load_span_snapshot` caught that, wrote a
`logging.warning`, and returned `None`. `ExecutionHandler` selects its margin engine on
exactly that value (`handler.py:208`): a snapshot gives `NseMarginEngine(SPAN + ELM)`, `None`
gives the flat-rate `MarginTracker`. Hence the page's `Engine: MarginTracker`.

**Issue 4 follows directly.** `_journal_margin` only computes SPAN and ELM under
`isinstance(self.margin_tracker, NseMarginEngine)`. On the fallback they are `None` by
construction — the "--" was not a missing value, it was "this engine has no such concept."

**Issue 3 is the same fallback's arithmetic.** `MarginTracker.get_incremental_margin` is
`abs(quantity) × lot_size × price × 0.2` — a flat 20% of premium notional:

```
gross exposure  : (193.95 + 114.00) × 75 = ₹23,096.25     <- the page's "Gross exposure"
flat 20% margin :                          ₹4,619.25      <- the page's "Margin"
broker (Upstox) :                          ₹79,901.74
understated by  :                          17.3x
```

The two figures on the page are the same number scaled by 0.2. It is not a rounding gap and
it is not a lot-size gap — the flat model has no concept of a spread's risk offset or of
SPAN scanning risk, so it cannot approach a broker number.

### This is a departure from the certified margin architecture

ADR-011/012/013 and `CLAUDE.md` make `NseMarginEngine` the **sole** sizing authority
"in research, backtest, paper, and LIVE (unchanged in every mode)." A PAPER window silently
pricing on a flat 20% is not that. Two places encode the tolerance:

- `_load_span_snapshot`'s broad `except Exception` → `logging.warning`. A logger line is not
  an audit record — this is the "a freshness value that is printed but never asserted is
  documentation, not a control" pitfall from `CLAUDE.md`, applied to the margin authority.
- `scripts/ops/preflight.py::check_span` is severity **`warn`**, with the detail string
  *"SPAN snapshot absent (PAPER tolerates — flat-rate margin)"*.

### What was changed, and what was not

**Changed — the downgrade is now loud.** `_load_span_snapshot` takes the journal and records
a **CRITICAL** `ENTRY_MARGIN` event naming the expected date, the error, and
`engine=MarginTracker`, so the evidence trail states which engine priced the window instead
of leaving it to a log file. Verified firing against today's missing snapshot.

**Changed — the page now says why.** When the journalled engine is not `NseMarginEngine`, the
SPAN and ELM rows read `n/a — flat-rate engine` rather than `--`, and the panel carries a
note that the figure is not the certified SPAN+ELM number.

**Not changed — the SPAN archive was not refreshed, and preflight was not escalated.**
Fetching SPAN is an ops action against an external NSE source that would change what the
**currently running** orchestrator computes mid-window. And whether PAPER should refuse to
run flat-rate at all — i.e. whether `check_span` should be `block`, given ADR-011 — is a
governance decision about the certified architecture, not a defect fix. **Both are operator
calls.** The recommendation is to refresh `data/span/` (≈22 trading days missing) and then
decide the preflight severity.

---

## Governance — one re-cert now covers two parameter changes

`lot_size` is a certified strategy parameter feeding `config_hash`, as is the
`stop_loss_max_loss_frac` added earlier today
(`NIFTY_SHIELD_STOP_UNREACHABLE_2026-09-07.md` §5b). Both land in the same pending re-cert —
**one ledger entry, two parameters**, not two grants:

```
ledger E005/E006/E007 : c5b722ff204d4e434f5cbffb1674136738a79693a3ced17bf07e46676d5336c6
after both changes    : 14b71bed70e37f1360ddb6bdc03f3e375cf387ac9ecd345887ffba3ac6282378
```

That supersedes the intermediate hash quoted in the earlier report's §5b. `datasheet.md` and
`STRATEGY_PROMOTION_LEDGER.md` are operator artifacts and were not edited.

**Deployment:** the running orchestrator holds the old config and the old page in memory.
Lot size and the margin journaling apply after a restart; the MTM and SPAN/ELM display fixes
apply on a page reload.

---

## Tests

`tests/execution/ tests/strategies/ tests/flask/ tests/ops/ tests/nifty_shield_paper/
tests/options_wall/`: **all green** (521 + the 46 paper-tools tests, 4 skipped).

New tests, each confirmed failing before its fix:

| Test | Pins |
|---|---|
| `test_leg_position_short_leg_average_is_positive` | short leg's average entry is +193.95, not −193.95 |
| `test_leg_position_mtm_matches_the_live_spread` | −303.75 / +266.25 on this exact trade |
| `test_leg_position_is_none_for_a_closed_round_trip` | flat leg reports no MTM |
| `test_leg_fills_are_scoped_to_the_session` | a re-traded strike does not pool across sessions |
| `test_certified_nifty_lot_size_is_65` | 65 in both declaration sites, and they agree |

Consequential updates: five paper-execution tests carried 75-derived constants
(`2 × 75 = 150` quantities, credit/max-loss figures) and now carry the 65-derived ones; two
`_load_span_snapshot` monkeypatch stubs gained the `journal` parameter.

The template JS was syntax-checked with `node --check` after editing — worth noting because
the first attempt at the SPAN note contained a broken quote escape that would have taken the
whole page down, and no Python test would have caught it.

**One caveat on the test run:** three `tests/daytype/test_daytype_facts.py` live-publisher
tests failed in one combined run and pass in isolation and in a second combined run
(`tests/execution/ tests/daytype/`: 371 passed). They read live-buffer state that the running
poller mutates, and the ledger already records this file as environment-sensitive
("test_live_publisher_not_ready_without_data [live buffer present in tree]"). Not caused by
these changes, but recorded rather than hidden.


---

## Postscript — the SPAN-downgrade fix broke `/api/window`, and why no test caught it

Within the hour, `/api/window` started returning 500:

```
File "scripts/nifty_shield_paper/audit.py", line 102, in audit_window
    gid = md["group_id"]
KeyError: 'group_id'
```

**My regression.** The CRITICAL notice added above was journalled as `ENTRY_MARGIN` — an
event type whose every consumer treats a row as *one structure* and indexes
`metadata["group_id"]`. A session-level notice has no structure and no group, so the first
page load after the runner started took the endpoint down.

Three consumers shared the assumption, and one of them miscounted rather than raised:

| Consumer | Effect |
|---|---|
| `audit.py:102` | `KeyError` — the 500 |
| `metrics_report.py:115,130` | `KeyError`, **and** `structures_entered` counted the notice as an entry |
| `recover_session.py:102` | `KeyError` in the group-id backfill |

### Why the tests passed

Three gaps, and the third is the one that matters:

1. **The producer is monkeypatched out.** Both tests that exercise the runner replace
   `_load_span_snapshot` with `lambda journal=None: None`, so the journaling branch never
   executes under test.
2. **No fixture journal contains a groupless `ENTRY_MARGIN`.** `_margin_event()` always
   builds a well-formed structure row, so no consumer was ever handed the shape I introduced.
3. **I verified the wrong half of the contract.** I wrote the event to a throwaway journal
   and read the line back to confirm severity and metadata — proving it was *written*, never
   that anything downstream could *read* it. A new event type is a contract with its
   consumers, and I tested only the producer side of it.

The full suite going green was consistent with all three: every fixture journal is
well-formed, so the suite could not distinguish a valid event from an invalid one.

### Fix

- The notice moved to **`EventType.STARTUP`** — a session-level fact with no `group_id`
  contract, already in the page's journal whitelist so it stays visible. Severity stays
  CRITICAL.
- The invariant is now stated once, in `audit.py::is_structure_entry(event)`: an
  `ENTRY_MARGIN` row is auditable **iff it carries a group**. All three consumers filter
  through it, so a groupless row is skipped rather than crashing — needed regardless of the
  event-type change, because the journal is append-only and the bad row is already on disk.
- Four tests, each confirmed failing first: the audit skipping a groupless row, the metrics
  count not inflating, the recover-session backfill surviving it, and — the one that was
  missing — a **producer→consumer contract test** that lets the real `_load_span_snapshot`
  write its event and then feeds that journal to `audit_window`.

Verified against the live journal that actually broke: `load_window_evidence` returns 7
entered / 10 attempted, and the `api_window` path returns 10 merged structures with the
2026-09-07 spread carrying `signed_qty −75 @ 193.95` and `+75 @ 114.00`.

`tests/nifty_shield_paper/ tests/flask/ tests/execution/ tests/strategies/ tests/ops/`:
**495 passed, 4 skipped.**
