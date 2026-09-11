# NiftyShield — Audit Findings and Remediation, 2026-09-08

Reference record of a full audit of the NiftyShield PAPER strategy and the
changes made in response. Written to be readable cold, months later, by someone
who was not in the conversation.

**Status of this document:** narrative change record. Every number it quotes is
produced by one of the three generated reports it cites; none is hand-computed
here.

| | |
|---|---|
| Trigger | Operator question: is the regime prediction on our side, and were the structures entered the best available? |
| Evidence base | 12 sessions with a 13:00 regime fact, 8 entered structures, 3 sessions of intraday option-chain history, 1,606 out-of-sample sessions for the regime diagnostic |
| Governance | Parameter change inside the MM12.5 promotion pipeline (operator decision). Not a new construct; no RFA pre-registration |
| Outcome | 4 defects fixed, 3 decision rules re-anchored, 1 observe-only integration added, 1 audit finding amended after it failed a wider test |

---

## 1. The three generated reports

Read these for the numbers; this document explains what they mean and what was
done about them.

| Report | Script | What it establishes |
|---|---|---|
| `NIFTY_SHIELD_REGIME_AND_STRUCTURE_AUDIT.md` | `scripts/nifty_shield/audit_regime_and_structures.py` | The audit itself: ledger, exit efficiency, structure choice, counterfactuals |
| `NIFTY_SHIELD_REGIME_HORIZON_DIAGNOSTIC.md` | `scripts/nifty_shield/diagnose_regime_horizon.py` | Whether the regime call separates the move the strategy holds, at n=1,606 |
| `NIFTY_SHIELD_ANCHORING_DERIVATION.md` | `scripts/nifty_shield/derive_anchoring_params.py` | Where every replacement parameter came from |

All three are read-only against every store and re-runnable.

---

## 2. What the audit found

### 2.1 The single most important structural finding

**Every trading decision in this strategy was made by an absolute constant
chosen once and never re-validated against the regime it now runs in.**

- `iron_fly_vix_above = 14`, `vix_reduce_above = 16` — India VIX sat at
  10.57–11.65 across every live session, so neither ever fired. The Choppy
  branch could only ever emit `short_straddle`; three of the five structures in
  the catalogue were unreachable.
- `directional_wing_pts = 150`, `wing_offset_pts = 100` — 1σ to expiry ranged
  189–448 points across the eight trades, so the same nominal structure was
  0.79σ wide one day and 0.34σ the next. Not one strategy repeated; a different
  bet each day.
- `profit_target_pct = 0.50` — a 2.5-hour hold of a 4–8 DTE structure can decay
  3.6–7.3% of its premium. The target asked for 50%. It never fired once.

That is the pattern the remediation addresses. Each constant is replaced by a
scale-invariant equivalent — a percentile, a σ fraction, a fraction of modelled
available decay — so the parameter cannot silently expire again.

### 2.2 Defects

| # | Severity | Finding |
|---|---|---|
| 1 | HIGH | **Exit routing by symbol.** On 2026-08-21 a stop-loss fired on a group that had been manually closed 6 minutes earlier. It closed by *symbol*, and by then `NIFTY25AUG2624250PE` was the short put of a straddle entered 71 seconds before. The stop bought 150 units (the straddle's size, not the closed spread's 75) and flattened the straddle's put leg. Ledger effect: 08-20 and 08-21 were booked as −10,018 / +9,689 when the true figures are −556 / +227. Totals unaffected (−165.69 either way) — only attribution moved |
| 2 | HIGH | **Wrong fee schedule.** Option legs are charged `ExecutionHandler._calculate_fees`, the NSE *equity intraday* schedule: STT at a flat 0.025% of turnover on **every** leg instead of 0.15% of sell-leg premium; exchange txn ~10× too low; stamp duty on both sides instead of buy-only. Correct net over the 8 structures is **−468.60**, not −165.69. The correct model already exists at `core/execution/options/fees.py`, unused on this path |
| 3 | HIGH | **Unreachable profit target** (see 2.1). `time_exit` was the only exit that ever fired. Worse, the exit block was *asymmetric in reachability* — the stop-loss side is reachable — so config alone imposed a negative-skew shape |
| 4 | MEDIUM (amended) | **Horizon mismatch** — see §3, this one partly failed |
| 5 | MEDIUM | **Structure selection reads only `regime` and `vix`.** No IV/RV, skew, term structure, credit, reward/risk, gamma, OI or expected move — while the platform computes most of them in `data/options/wall_scan_results.duckdb` on the same clock |
| 6 | MEDIUM | Three of five structures unreachable at current vol (see 2.1) |
| 7 | MEDIUM | Strikes fixed in points, not σ (see 2.1) |
| 8 | LOW | Two structures open concurrently on overlapping strikes — what made #1 reachable |
| 9 | LOW | Chain history retained for 3 sessions, near-expiry only; the traded expiry is not archived |

---

## 3. The finding that did not survive — and why that matters

The audit's first issue reported that **0 of 6 directional regime calls hit**
over the holding window, and treated it as a finding about the model. It then
recommended moving the entry away from the 13:00 checkpoint.

That was wrong, and the way it was wrong is the most useful lesson in this
whole exercise.

Six observations of a quantity whose per-session dispersion dwarfs its mean
cannot distinguish "no edge" from "an edge and a bad week". A diagnostic over
**1,606 out-of-sample sessions** settled it the other way:

| checkpoint | BullTrend − BearTrend, checkpoint→close | 95% CI | carries direction? |
|---|---:|---|---|
| 10am | −0.011 pp | [−0.073, +0.051] | no |
| 11am | +0.001 pp | [−0.054, +0.058] | no |
| **13pm** | **+0.255 pp** | **[+0.197, +0.312]** | **yes** |

The 13:00 call *does* separate direction over its own forward window —
BullTrend sessions close +0.095% with a 62% up-share, BearTrend −0.160% with
40%. The 10:00 and 11:00 checkpoints carry nothing.

**Consequences:**

1. The planned move to a 10am/11am checkpoint was **abandoned before any code
   was written**. It would have traded the only checkpoint that carries
   direction for two that do not.
2. Finding #4 was downgraded from HIGH to MEDIUM and rewritten; the audit
   report carries a correction banner rather than a quiet edit.
3. The problem was **relocated**. The separation is ~0.25 pp ≈ 60 points on a
   24,000 index, against structures 150 points wide with an exit that never
   took profit. **The signal is not the weak link; the vehicle is.** That is
   what made the σ-anchoring and take-profit work the priority.

Two caveats kept on the record: the cluster boundaries were fit over the full
2012–2025 panel, so the label *definition* saw the test years (the forward-move
measurement itself is clean); and 0.255 pp measured precisely at n=1,606 is a
thin edge, not a strong one.

**Generalisable lesson: a rate computed on single-digit n is not a property of
the system.** The audit had every other finding right precisely because they
were mechanical — properties of code and fee schedules, not of the sample.

---

## 4. What was changed

### 4.1 Take-profit: fix the denominator, keep the 0.50

`profit_target_pct = 0.50` → `profit_target_decay_frac = 0.50`.

ATM premium scales roughly with `√T`, so holding `h` market-hours out of `T`
leaves `√((T−h)/T)`, and the decay reachable with spot unchanged is
`1 − √((T−h)/T)`:

| DTE | available decay | new effective target (% of credit) |
|---:|---:|---:|
| 2 | 15.15% | 7.6% |
| 4 | 7.26% | 3.6% |
| 8 | 3.56% | 1.8% |

The original intent — "take half of what is there" — is preserved exactly; only
the denominator is corrected to a quantity that exists. The available fraction
is computed per structure at entry from its own DTE and carried on the signal
(`exit.available_decay_frac`), so this is **not a constant in credit terms at
all** — it self-scales with time to expiry.

Cross-checked against the audit's observed paths: 09-04's straddle peaked at
5.8% of credit against a 3.6% threshold (**would have fired**); 09-07's spread
peaked at 1.5% against 1.8% (**would not**). A live, discriminating threshold.

**Deliberate design choice:** when `available_decay_frac` is absent the
take-profit is **disabled**, not defaulted. A structure whose reachable decay is
unknown has no defensible profit threshold, and a fabricated one either never
fires (the defect being replaced) or fires immediately. Locked by
`test_take_profit_is_disabled_without_an_available_decay_fraction`.

**Recorded tension:** a take-profit that now actually fires will close some
structures before the session ends, forgoing part of the +0.255 pp directional
separation. Whether take-profit beats holding to the clock is a live question
that *could not previously be asked* because the target never fired. It should
be measured on forward paper sessions, not decided now.

### 4.2 Volatility gates: absolute level → trailing percentile

| was | now |
|---|---|
| `iron_fly_vix_above = 14.0` | `vix_iron_fly_pctile = 36.8` |
| `vix_reduce_above = 16.0` | `vix_strangle_pctile = 59.0` |
| — | `vix_pctile_lookback_sessions = 756` (~3 years) |

Derived by mapping each legacy level onto the median percentile it has
historically occupied in the trailing India VIX distribution (3,040 sessions,
2014-05-14 → 2026-09-07). Design intent preserved; only the unit changes.

The p25–p75 spread is the drift the absolute level was hiding: VIX 14 has meant
the 19.6th percentile in some eras and the 44.0th in others.

**What this actually does to today's behaviour — stated precisely, because it is
less than "unlocks three structures".** Against the live trailing window
(756 sessions to 2026-09-07; min 9.15, median 13.48, max 27.89):

| gate | legacy absolute level | new percentile | equivalent VIX today |
|---|---:|---:|---:|
| iron_fly | 14.00 | 36.8 | **12.62** |
| short_strangle | 16.00 | 59.0 | **13.97** |

The bar is genuinely lower — but India VIX at 11.18 on 2026-09-08 sits at the
**13.2nd percentile of its own three-year range**, so the Choppy branch still
resolves to `short_straddle` today. **Immediate behaviour is unchanged.** What
changed is that the gate now tracks the distribution: it fires when vol is
unusual *for the prevailing regime* instead of waiting for a level that
compression had made unreachable. The straddle is not being overridden here — at
the 13th percentile it is the right answer.

`vix_skip_above = 20.0` **stays absolute on purpose.** It is a hard risk limit
("do not trade this book when vol is outright high"), not a read on how unusual
today's vol is — a percentile form would happily authorise trading at VIX 40 in
a period whose trailing window was also high.

Plumbing: `scripts/daytype/vix_percentile.py` maintains an incremental cache
(`data/nifty_shield/vix_history.duckdb`) so the intraday publisher does not
scan ~3,500 daily files inside the driver hook. `publish_live_fact.py` writes
`vix_pctile` onto the 13pm fact; `RegimeFactsReader` surfaces it.

### 4.3 Strike geometry: fixed points → σ fractions

| was | now | σ fraction |
|---|---|---:|
| `directional_wing_pts = 150` | `directional_wing_sigma_frac` | 0.541 |
| `wing_offset_pts = 100` | `wing_sigma_frac` | 0.361 |
| `strangle_otm_pts = 50` | `strangle_otm_sigma_frac` | 0.180 |

`sigma_points(spot, iv, dte) = spot × iv × √(dte/365)`, with `iv` = India VIX/100
at the checkpoint. Offsets round to the 50-point strike grid and are **floored
at one step** — a zero offset would collapse a vertical into a naked short and a
fly into a straddle, silently converting defined risk into unbounded risk.

Observable effect, from the smoke run on real sessions:

| session | DTE | 1σ | old wing | new wing |
|---|---:|---:|---:|---:|
| 2026-09-04 | 4 | 270 | 150 | 150 |
| 2026-09-07 | 8 | 396 | 150 | **200** |
| 2026-09-08 | 7 | 366 | 150 | **200** |

The structure now widens when there is more time and more expected movement,
which is exactly what the fixed constant could not do.

`_risk_declaration` now reads the wing width **actually struck** off the
computed legs rather than the config constant, because that width now differs
session to session.

### 4.4 Entry credit gate (new)

Structure selection chose a shape and then accepted whatever credit the market
offered; it never asked whether the credit was good. New:
`core/execution/options/nifty_shield_pricing.py` prices the same legs under
Black-Scholes at the session's own implied vol, and the handler skips an entry
whose marked net credit falls below `credit_fair_frac = 0.90` of that reference.

A **pure no-trade filter** — it can only reduce activity, and it fires on stale
or badly-spread quotes rather than on a view. Deliberately a *reference* price,
not a valuation engine (no smile, no dividend term): it is used only as a ratio
against the same legs' marks, where shared bias cancels.

**Missing inputs disable the gate rather than block the trade.** An entry is the
strategy's decision, and a gate that cannot compute its reference has no grounds
to overrule it. That is journaled, not silent. (This is the opposite of the
broker-margin path, which fails *closed* — correctly, because that one sizes the
trade rather than commenting on it.)

### 4.5 Options-Wall shadow read (observe-only)

`core/execution/options/nifty_shield_wall.py` records what the Options-Wall
poller was saying at each entry: its GEX regime, ATM IV, realized vol, IV−RV,
pin strike, walls, pin conviction, net GEX, and the shield's short strike
relative to the pin.

**This changes no behaviour, on purpose.** Three sessions of overlap is not
evidence that either read is better; wiring an unvalidated second opinion into a
live decision replaces one unmeasured rule with another. The shadow accumulates
paired observations so the comparison can eventually be made on evidence.

What the three overlapping sessions showed, and why it is worth accumulating:
the poller read *Positive GEX (Stable)* — a pinning tape — on all three days,
while the day-type model called BearTrend on two of them and opened directional
spreads; and the shield's short strike sat one strike below the pin on every
one of the three.

The three prerequisites the audit named are discharged in this module:

1. **Expiry coverage.** The shield's own chain poller already fetches both the
   near and next weekly expiry, so the traded expiry *is* priced live. The gap
   is archival — the wall snapshots keep only the near expiry, and the shield's
   cache keeps only the latest snapshot. Recorded as an open item (§6), not
   silently closed.
2. **Cross-process read contract.** Read-only, no held connection, explicit
   staleness bound (`max_age_s = 300`), stale rows returned *marked* rather than
   silently used, and **fail-open because this is observation** — an entry must
   not be lost to a logging dependency. The module documents that this inverts
   the moment the read gates a decision.
3. **Taxonomy mapping.** `GEX_TO_DAYTYPE` records the correspondence explicitly.
   The two vocabularies are not equivalent — the day-type taxonomy separates
   direction from its absence, the GEX taxonomy separates damping from
   amplification and says nothing about direction — so the only comparison they
   support is trending-vs-pinning, and that is all `_classify_agreement`
   reports.

### 4.6 Journal: new `ENTRY_DIAGNOSTIC` event type

Observe-only evidence around an entry that neither sized it nor blocked it. It
is deliberately **not** `ENTRY_MARGIN` or `ENTRY_SKIPPED`: those two are the
lines an operator reads to answer "what sized this?" and "what did we lose?",
and diluting either with diagnostics destroys that signal. A first attempt did
overload `ENTRY_MARGIN`, and an existing test correctly caught it.

---

## 5. What was deliberately not changed

| | Why |
|---|---|
| The 13:00 checkpoint | The diagnostic showed it is the *only* checkpoint carrying direction (§3) |
| `vix_skip_above = 20.0` | A hard risk limit, not a regime read — a percentile form would authorise trading at VIX 40 (§4.2) |
| Structure selection driven by the day-type regime | The wall read is not yet validated; shadow first (§4.5) |
| `stop_loss_multiplier` / `stop_loss_max_loss_frac` | Reachable as they stand; not implicated by the audit |
| The ledger mis-attribution (#1) and fee schedule (#2) | Sequenced next by operator decision — **still open, see §6** |
| Choosing new parameters by what would have paid best over the 8 trades | That would repeat the original error in a worse form: fitting to n=8. Every replacement is a unit change, not a refit |

---

## 6. Open items

1. **Finding #1 — exit routing by symbol.** Not yet fixed. Exits must target the
   group's own open legs and quantities. **This is the highest-severity item
   still outstanding**; it can flatten an unrelated structure.
2. **Finding #2 — fee schedule.** **Fixed 2026-09-11** (branch
   `fix/nifty-shield-option-fees`): `NiftyShieldExecutionHandler._calculate_fees`
   charges `option_order_fees` (side- and date-effective) for its own strategy;
   other strategies keep the base equity schedule. Applies to fills from the
   next session start; rows already in `trading.db` / `execution.db` keep the
   fees they were written with. Reported P&L gets *worse* — a correctness
   repair, not a performance one. See
   `NIFTY_SHIELD_TRADE_2026-09-11_EARLY_TAKE_PROFIT.md` §4.
3. **Finding #9 — chain archival.** The traded expiry is priced live but not
   archived, so most of the audit cannot be repeated on the trades that matter.
4. **Finding #8 — concurrent structures on overlapping strikes.** Whether
   stacking is intended is still undecided in the code.
5. **Take-profit vs holding to the clock.** Newly askable (§4.1). Measure on
   forward paper.
6. **`config_hash` moved** to `07849cb19bfce652…`. Any artifact pinning the old
   hash needs re-pinning; the previous value is in git history.
7. **`vix_percentile.refresh()` must be wired into the EOD chain.**
   `percentile()` is a pure read by design — it never scans the candle store or
   writes, because doing so put minutes of file IO inside the intraday driver
   hook and made a unit-test run mutate a production data path (found by a
   test-isolation failure during this work). The cache is populated
   (3,040 sessions, 2014-05-14 → 2026-09-07), but **nothing currently tops it
   up nightly.** Until `python -m scripts.daytype.vix_percentile` runs from the
   EOD chain, the trailing window will drift stale and the gate will slowly
   describe an older distribution.

---

## 7. Incidental findings — three defects the change surfaced

None of these were the target of the work; all were found because changing the
contract forced every caller and test to be re-examined.

1. **`hard_exit` was a hardcoded string.** The source advertised `"15:35"` as a
   literal on every signal while the exit manager read the actual flatten time
   from `exit_time` config. Nothing kept them in step — the metadata could
   advertise a flatten time the driver did not honour. Now derived from config.
2. **`test_entry_latches_after_window_expiry` had been failing before this work
   started.** It hardcoded a 10-minute entry window; the operator widened
   `entry_window_minutes` to 30 in an earlier session and the test was never
   updated. Confirmed pre-existing via `git diff HEAD` — the config line is
   untouched by this change. Fixed by pinning the window in the test config, so
   a test of the *latch* no longer depends on the production window length.
3. **A conformance assertion expected `hard_exit == "15:15"`**, a value the
   source stopped emitting when the flatten moved to 15:35. It was masked: the
   test failed one line earlier on `tp_pct`, so the stale assertion never ran.

The general lesson: **assertions downstream of a failing assertion are not being
checked.** Two of these three were sitting behind a failure and were invisible
until the first one was fixed.

## 8. Verification

Full sweep over `tests/execution`, `tests/nifty_shield_paper`, `tests/daytype`,
`tests/runtime`, `tests/flask`, `tests/strategies`, `tests/options_wall`.

- `tests/execution` NiftyShield suites — **55 passed**, including a new test
  locking in that the take-profit is *disabled*, not defaulted, when no decay
  fraction is available.
- `tests/strategies` — **24 passed** after migrating the frozen conformance
  corpus (§8.1).
- One failure during the work was a genuine defect in the change itself
  (event-type overloading, §4.6) and was fixed in the code, not the test.
- Smoke run over the three chain-covered sessions confirms every branch of the
  selector is reachable when fed the corresponding percentile, and that the wing
  widens with DTE (§4.3). Note this is branch reachability, not a claim about
  today's vol — see §4.2 for what the gates resolve to at the live VIX. A run of
  the wall
  shadow read against the real store returns fresh rows (age 1.7–15.1 s against
  a 300 s bound) and fails open with a reason on a session with no wall data.

### 8.1 The frozen conformance corpus was migrated, not bypassed

`strategies/nifty_shield_v1/corpus/facts.csv` carries six sessions whose VIX
levels were chosen to exercise every branch (two Choppy sessions at 14.39/14.69
produced iron flies under the old gates). With selection now keyed to the
percentile, an un-migrated corpus falls through to `short_straddle` everywhere
and the corpus stops testing what it was built to test.

A `vix_pctile` column was added carrying the percentile that selects the **same
structure the absolute level used to select** — the same mapping discipline used
for every other parameter here. The corpus's coverage is preserved exactly; only
the unit changed.

## 9. File index

| File | Change |
|---|---|
| `strategies/nifty_shield_v1/config.py` | Parameters re-anchored; provenance recorded |
| `strategies/nifty_shield_v1/structures.py` | σ-anchored geometry, percentile gate, `available_decay_frac` |
| `strategies/nifty_shield_v1/source.py` | Passes percentile + IV; carries decay/spot/IV on the signal; `hard_exit` derived from config |
| `strategies/nifty_shield_v1/facts.py` | Surfaces `vix_pctile` |
| `scripts/daytype/publish_live_fact.py` | Publishes `vix_pctile` |
| `scripts/daytype/vix_percentile.py` | **new** — incremental trailing-VIX cache |
| `core/execution/options/nifty_shield_exit.py` | Decay-based take-profit |
| `core/execution/options/nifty_shield_pricing.py` | **new** — BS reference for the credit gate |
| `core/execution/options/nifty_shield_wall.py` | **new** — observe-only poller read |
| `core/execution/options/nifty_shield_handler.py` | Credit gate, shadow journal, decay wiring |
| `core/runtime/event_journal.py` | `ENTRY_DIAGNOSTIC` |
| `core/execution/options/nifty_shield_gates.py` | Certified config carries percentile gates |
| `flask_app/blueprints/nifty_shield.py` | Reads `vix_pctile`; degrades cleanly on stores without it |
| `scripts/nifty_shield_paper_smoke.py` | Updated to the new signature |
| `strategies/nifty_shield_v1/corpus/facts.csv` | Migrated: `vix_pctile` added, branch coverage preserved |
| `scripts/nifty_shield/audit_regime_and_structures.py` | **new** — the audit |
| `scripts/nifty_shield/diagnose_regime_horizon.py` | **new** — the horizon diagnostic |
| `scripts/nifty_shield/derive_anchoring_params.py` | **new** — parameter derivation |
