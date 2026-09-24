# Carry + TS Basis — Forward PAPER Plan

**Generated:** 2026-07-26
**Decision taken:** run Carry in forward PAPER; run TS Basis alongside it as a shadow sleeve
(de-authorized, observational only). Companion to `BASIS_MOMENTUM_DECISION_REVIEW.md`.
**Purpose:** assess the proposed implementation plan and correct it where it breaks a
platform guarantee.

---

## 1. Verification of the claimed blockers

| Claim | Verdict | Evidence |
|---|---|---|
| `has_derivatives` returns False for plain underlyings | **True but NOT a blocker** | see §1.1 |
| Facts DB stale at 2026-07-20 | **True, no formation missed yet** | see §1.2 |
| `LiveDuckDBMarketDataProvider` is the wrong shape | **True** | see §1.3 |
| TS Basis has no rebalancer / hook / PAPER wiring | **True** | 7 scripts, none is a rebalancer |
| LoopDriver should be bypassed for a direct runner | **REJECT** | see §2 — breaks the parity guarantee |

### 1.1 `has_derivatives` is not a blocker — it is a silently skipped safety gate

`core/runtime/instrument_scope.py:19` returns True only for `NSE_FO|` / `MCX_FO|` prefixes,
so plain underlyings (`RELIANCE`) return False. But the gate that consumes it reads
(`core/runtime/driver.py:409`):

```python
if not (self._config.is_live
        and has_derivatives(self._config.symbols)
        and self._master_readiness is not None):
    return True
```

With `has_derivatives` False the conjunction is False, so the guard **returns True and the
driver proceeds** — regardless of `is_live`. It does not halt the runner. The runner does not
"fail to start" on this.

**What is actually true is worse in a different way, and only for LIVE:** because the universe
is plain underlyings, the MM.4 instrument-master readiness check **never fires** for a Carry
book. In PAPER that is harmless. Before LIVE it is a real gap — a startup safety gate that
silently no-ops. **Log it as a LIVE blocker, not a PAPER one.**

Corroboration that symbol handling does not block the hook path: `CARRY_INTEGRATION_SMOKE_REPORT.md`
already drove `CarryRebalancerHook.__call__()` through a real `ExecutionHandler` + `PaperBroker`
on three formation dates with fills landing in `position_tracker` and gross exposure matching
target exactly.

### 1.2 Facts staleness — real, but no formation has been missed

Measured:

| Store | Latest |
|---|---|
| `carry_facts.formation_date` | **2026-07-20** (126 formations, from 2016-02-29) |
| `futures_bhavcopy.trade_date` | **2026-07-23** |
| Today | 2026-07-26 |

Cadence is monthly-on-the-roll, so the next formation is **upcoming, not skipped**. The
characterization "we're past that" overstates the urgency by one formation — but the fix is
still required *before* the next roll, and it is the same blocker `CARRY_IMPLEMENTATION_BRIDGE.md`
§6 step 4 already flags: nothing refreshes `carry_facts` forward, so the hook silently stops
firing with no error. Bhavcopy is current enough to publish the next formation today.

### 1.3 The provider observation is correct

`LiveDuckDBMarketDataProvider` (`core/database/providers/live_market.py:20`) is streaming-shaped
and wrong for a monthly rebalance. But the conclusion drawn from it does not follow — see §2.

### 1.4 Formation dates are month-end, not roll-aligned — and one trailing formation is spurious

Raised by the operator: should formations follow monthly futures expiry (last Tuesday) rather
than month-end? **The premise is correct.** Measured over all 126 formations:

| Check | Result |
|---|---|
| Weekday distribution | Fri 54, Thu 20, Tue 20, Wed 17, Mon 15 — **month-end, not last-Tuesday** |
| FUTSTK expiry weekday | **Thursday through 2025-08**, **Tuesday from 2025-09-30** onward |
| Near-contract DTE at formation | min 0, median 27, max 34 |

So `CLAUDE.md` / `CARRY_IMPLEMENTATION_BRIDGE.md` describing the cadence as **"monthly on the
roll" is inaccurate** — it is monthly on the last trading day of the calendar month. Doc defect,
worth correcting (fourth stale-doc finding this session).

**The feared consequence does not materialize.** The concern would be that formations landing on
expiry day (DTE=0) corrupt the annualized basis via the `365/DTE` term. Tested on the two DTE=0
formations against the other 123:

| Formation | Names | Eligible | mean abs(z_carry_neut) |
|---|--:|--:|--:|
| 2026-03-30 (DTE 0) | 203 | 203 | 0.647 |
| 2026-06-30 (DTE 0) | 208 | 208 | 0.710 |
| *Normal formations (median)* | *181* | *181* | *0.670* |

Statistically indistinguishable — the basis panel rolls to the next contract correctly and the
signal is not degenerate on expiry-day formations. **No defect here.**

**But one real bug surfaced:** the trailing formation **2026-07-20 is spurious** — a Monday,
mid-month, DTE 8, while every other formation is month-end. It is an artifact of running
`publish_facts.py` against a store ending 2026-07-23; July's true formation is ~2026-07-31.
**A forward PAPER runner would rebalance a real book on this fake formation date.** Piece 1 must
therefore emit formations **only** on genuine month-end formation dates and never on
"last available date."

**Do not change the construction to roll-aligned.** It is frozen and immutable
(`CARRY_IMPLEMENTATION_BRIDGE.md` §0, §8: *"No re-optimization of the construction for live"*).
Changing formation dates changes the construction, which voids TRAIN/HOLDOUT/SEALED and the
+0.0 bp parity gate — **and there is no sealed window left to re-validate in** (spent by Carry,
TS Basis, IVOL). A roll-aligned Carry would be a permanently unvalidatable variant. It would
also have to straddle the 2025-09 Thursday→Tuesday expiry regime change, a fresh look-ahead
risk. If genuinely wanted, it is a **new pre-registered construct**, not an edit to this one —
and it inherits the same no-window problem.

---

## 2. The architectural correction — do NOT bypass LoopDriver

The proposal is: *"no LoopDriver, no instrument keys, no streaming data"* — a bespoke daily
scheduler calling the hook directly.

**Reject this.** It discards the single control that de-risks the entire implementation.

- `CARRY_IMPLEMENTATION_BRIDGE.md` §5: *"The load-bearing risk is **not** the signal — it is
  whether the production code path faithfully reproduces the research harness."* The +0.0 bp
  parity gate is the evidence for that, and it was established **through LoopDriver**.
- `scripts/carry_paper_replay.py:1-3` states it plainly: *"full LoopDriver path... Drives the
  REAL production path (DailyBhavcopyProvider → LoopDriver → ...)"*, `Mode.REPLAY`,
  `rebalance_hook=hook.__call__`.
- `CLAUDE.md` Architecture Principle 4 — *"Runner is Neutral — live and backtest data treated
  identically"* — is the stated **basis** of that parity guarantee (bridge §1).

A bespoke runner means forward PAPER executes on a code path **that was never parity-verified**,
while the +0.0 bp number continues to be cited as if it covered it. That is precisely the class
of provenance defect this project has already been burned by twice (the TS Basis Pearson/Spearman
gate; the un-rebuildable 1d index store).

**The proposal correctly diagnoses that the streaming provider is the wrong shape — and then
prescribes deleting the wrong component.** `carry_paper_replay.py` already runs LoopDriver on
`DailyBhavcopyProvider` (daily bars, no streaming, no instrument keys). The fix is to run **that
same stack forward** rather than over a bounded window.

---

## 3. Corrected work plan

### Piece 1 — Facts refresh (blocking, both sleeves)
Extend `publish_facts.py` to run for upcoming formation dates and schedule it ahead of each
roll. **Add a staleness assertion that fails loudly**: if today is a formation date and
`MAX(formation_date) < today`, raise — do not no-op. The failure mode being fixed is a silent
stop, so the fix must not itself be silent.

### Piece 2 — Forward PAPER runner (keep LoopDriver)
Take `carry_paper_replay.py` and change the driver mode from bounded `Mode.REPLAY` to a
forward-running loop over `DailyBhavcopyProvider`, keeping `ExecutionMode.PAPER`,
`rebalance_hook=hook.__call__`, and the `CarryMetricsDB` sink unchanged. Do **not** introduce
`LiveDuckDBMarketDataProvider`.

**Acceptance:** re-run the parity check against the forward path and confirm it still reproduces
research at +0.0 bp over the historical span. If parity cannot be demonstrated on the forward
runner, the runner is wrong — not the gate.

### Piece 3 — TS Basis shadow sleeve
TS Basis today has signals only (`z_ts`), with no facts layer and no rebalancer. It needs:
1. A facts publisher producing the `carry_facts`-shaped table (`formation_date`, `underlying`,
   `z_ts`, `quintile`, `eligible`) — TS Basis has no sector/beta neutralization, so the
   neutralization columns are legitimately absent.
2. A rebalancer hook following `CarryRebalancerHook`.
3. The same metrics sink, writing to a **separate** book.

**Guardrails, given de-authorization:**
- Runs as a **shadow/observational book**, not a co-equal capital allocation.
- **Do not deploy the 50/50 blend.** The Sharpe 2.09 estimate is TRAIN-flavored
  (`BASIS_MOMENTUM_DECISION_REVIEW.md` §4.3). Run the two books separately and let the live
  correlation accumulate against the +0.46 estimate.
- TS Basis remains **not a LIVE candidate**. Forward paper is the only path that can ever
  re-qualify it.

### Sequence
Piece 1 → Piece 2 (Carry live-paper running, parity re-verified) → Piece 3. Do not start
Piece 3 before Carry is running — the TS Basis wiring should copy a pattern proven forward,
not a pattern proven only in replay.

---

## 4. Open LIVE blockers (unchanged, recorded here so they are not lost)

1. MM.4 master-readiness gate silently no-ops for plain-underlying universes (§1.1).
2. LIVE gross-exposure policy is an explicit `NotImplementedError` — no code path sizes a live book.
3. Broker margin reconciliation: deferred LIVE-only capability, no code (ADR-011/012/013).
4. Realized-slippage validation against the 5 bp/side assumption needs real broker fills.
