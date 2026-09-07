# NiftyShield's Credit-Multiple Stop Has the Options-Wall Defect

Investigation 2026-09-07. Systematic-debugging pass on
`core/execution/options/nifty_shield_exit.py:48`, opened by the "Related, not fixed" note at
the end of `docs/reports/OPTIONS_WALL_TP_NEVER_FIRES_2026-09-07.md`.

**Verdict: NiftyShield has the defect, but only on part of its book, and the fix cannot be
the wall's fix.** The strategy is *both* defined-risk and undefined depending on regime, and
the parameter the wall deleted is the legitimate rule for the undefined part.

---

## 1. The structure is regime-switched, not one shape

`strategies/nifty_shield_v1/structures.py::select_structure` routes on the 13:00 DayType
regime and VIX to **five** structures — three defined-risk, two genuinely naked:

| Regime / VIX | Structure | Bought wings? | Wing width |
|---|---|---|---|
| BullTrend | `bull_put_spread` | yes | `directional_wing_pts` = 150 |
| BearTrend | `bear_call_spread` | yes | 150 |
| Choppy, VIX > 16 | `short_strangle` | **no** | — |
| Choppy, 14 < VIX <= 16 | `iron_fly` | yes | `wing_offset_pts` = 100 |
| Choppy, VIX <= 14 | `short_straddle` | **no** | — |

`NiftyShieldExitManager` applied one credit-multiple stop to all five and had no structure
awareness at all. So the task's framing — "defined-risk *or* naked, pick one" — is false
here, and that changes the fix.

Entry mix over the certified 13pm facts (`day_type_facts.duckdb`, 804 sessions
2023-01-02 → 2026-08-28, after the VIX > 20 skip):

| Structure | Entries | Share |
|---|---:|---:|
| `bull_put_spread` | 274 | 34.1% |
| `bear_call_spread` | 218 | 27.1% |
| `short_straddle` | 218 | 27.1% |
| `iron_fly` | 56 | 7.0% |
| `short_strangle` | 38 | 4.7% |
| **defined-risk** | **548** | **68.2%** |
| **undefined** | **256** | **31.8%** |

---

## 2. The defect, on the defined-risk 68%

The old rule (`nifty_shield_exit.py:48`):

```python
pnl <= -self._sl_mult * max(credit_received, 0.0)      # _sl_mult = 2.0
```

A defined-risk credit structure's loss is capped at `wing_width x qty - credit`. So the stop
is reachable only when `max_loss / credit >= sl_mult`. NIFTY weekly EOD closes from
`data/market_data/options_bhavcopy.duckdb`, weekly era 2019-02-11 → 2026-07-17, entry at each
session against the nearest expiry >= 2 days out (mirroring `nearest_expiry`), ATM from the
put-call-parity forward rounded to the 50-point grid:

| Structure | Wing | n | Credit/unit (med) | Max loss/unit (med) | Ratio (med) | Ratio p95 | **Stop reachable** |
|---|---:|---:|---:|---:|---:|---:|---:|
| `iron_fly` | 100 | 1,792 | 85.00 | 15.00 | **0.176** | 0.417 | **0.45%** |
| `bear_call_spread` | 150 | 1,804 | 62.52 | 87.48 | **1.399** | 2.420 | **10.86%** |
| `bull_put_spread` | 150 | 1,792 | 55.10 | 94.90 | **1.722** | 2.783 | **25.67%** |

Joined to the structure the strategy would actually have picked on each session (the same
804-session fact set), scored only on sessions where the chosen structure prices:

| Structure | Entries | Priced | Ratio (med) | SL reachable |
|---|---:|---:|---:|---:|
| `bull_put_spread` | 274 | 274 | 1.688 | 18.25% |
| `bear_call_spread` | 218 | 215 | 1.375 | 3.26% |
| `iron_fly` | 56 | 56 | 0.138 | **0.00%** |

**488 of 545 priced defined-risk entries — 89.5% — carried a stop that was arithmetically
incapable of firing. That is 60.7% of all entries.** (545, not the 548 of §1: three
`bear_call_spread` sessions have no priced chain.) For `iron_fly` it is every single one: at
the median ratio of 0.138 a 100-point fly collecting ~85 points of credit has a ~15-point
risk budget, so the trigger sat at roughly **fourteen times** the worst outcome the structure
can produce on a median day.

This is the same dimensional error as the wall's, and worse in degree — the wall's wings are
1.5% of the underlying (~375 points), NiftyShield's are a fixed 100.

### Horizon caveat — read this before quoting the percentages

NiftyShield closes every position at **15:15 the same session** (`exit_time`), entering at
13:00 against an expiry >= 2 days out. Structural max loss is only realised at expiry, so
the position never approaches that bound in either direction intraday. The table therefore
**understates** unreachability rather than overstating it: the credit-multiple stop is
unreachable at the expiry horizon *and* further still at the ~2h15m horizon actually traded.
What the table cannot speak to is intraday *reachability of the new rule* — the repo holds no
intraday mark series for these structures, only EOD bhavcopy. See §5a.

### Why 15 execution tests did not catch it

`tests/execution/test_nifty_shield_execution.py::test_stop_loss_triggers` marks the shorts at
240 while pinning both wings flat at 100 on a 100-point fly. That is an arbitrage-violating
state a real fly cannot reach. The test asserted that the trigger *fires when the condition
holds*; it never asked whether the condition **can** hold. Every new test below prices all
legs coherently.

---

## 3. On the undefined 32%, the old rule is correct

`short_straddle` and `short_strangle` have no bought wings and no structural loss bound. A
credit multiple is the only rule available, and it is legitimate. **`stop_loss_multiplier` is
therefore kept, not deleted** — a deviation from the task's "delete the old parameter"
instruction and from the repo's no-back-compat-shims convention. The reason: this is not a
shim. It is the live stop for 256 of 804 entries, and deleting it would remove the only
downside control from the two structures that have unbounded downside. That would be a larger
defect than the one being fixed.

---

## 4. Fix applied

`core/execution/options/nifty_shield_exit.py` — the stop becomes two-branch:

```diff
-        if pnl <= -self._sl_mult * max(credit_received, 0.0):
+        if self._stop_hit(pnl, credit_received, max_loss):
             return "stop_loss"
```
```python
    def _stop_hit(self, pnl, credit_received, max_loss):
        if max_loss is not None and max_loss > 0.0:
            return pnl <= -self._sl_frac * max_loss
        return pnl <= -self._sl_mult * max(credit_received, 0.0)
```

`core/execution/options/nifty_shield_handler.py` — a new
`structure_max_loss(group_id) -> Optional[float]` supplies the bound, and
`NiftyShieldExitDriver` passes it per group. It is derived **from fills**, mirroring
`structure_credit()`, not from the declared `sl_distance`:

- `sl_distance` for `iron_fly`/verticals is the wing width, but for the undefined structures
  it is `undefined_risk_stress_pts = 200` — a *stated stress convention*, not a structural
  bound. Using it uniformly would silently promote a declaration convention into a risk
  bound. `structure_max_loss` returns `None` for those structures instead.
- `risk_r = sl_distance x lot_size x base_lots` uses **declared** lots; actual fills use
  `final_lots`, margin-clamped by `NseMarginEngine` and possibly smaller. Reading
  `state.filled_quantity` keeps the bound on the size actually routed.
- Every short leg must be matched by a bought leg of the same `option_type` at **equal filled
  quantity**; the widest such pair bounds the structure (only one side of a fly can be
  breached). If any short is unmatched the method returns `None` and the group falls back to
  the credit rule. This is the partial-entry guard: the handler already journals
  `"structure entry partial: some legs rejected by a gate"`, and **a fly missing a wing is not
  defined-risk** — a stop set to a fraction of a fabricated bound is worse than one that never
  fires.

`strategies/nifty_shield_v1/config.py` — `stop_loss_max_loss_frac: 0.50` added;
`stop_loss_multiplier: 2.0` retained per §3. `source.py` carries `sl_frac` in each leg's
`exit` metadata alongside `sl_mult`.

### Tests

Written before the change and confirmed failing against the old rule (RED: 4 failed /
15 passed on the exit-manager suite, then 3 failed / 17 passed on the handler suite).
The partial-fill test forces the state directly: entry with a missing mark is *skipped*, so
the only way a group reaches the exit driver wing-less is a leg rejected by a gate after
routing.

| Test | Asserts |
|---|---|
| `test_iron_fly_stop_fires_on_fraction_of_max_loss` | P&L −1,650 vs a −1,500 trigger → `"stop_loss"`. Old rule needed −24,000 against a −3,000 floor |
| `test_iron_fly_stop_holds_inside_the_max_loss_band` | P&L −900 → `None` |
| `test_vertical_spread_stop_fires_on_fraction_of_max_loss` | 150-wide put spread, ratio 1.73 → old stop unreachable, new fires at −7,200 |
| `test_undefined_structure_keeps_the_credit_multiple_stop` | `short_straddle` still stops at −2× credit; holds above it |
| `test_structure_max_loss_is_wing_width_less_credit` | credit 12,000 → max_loss 3,000 from real fills |
| `test_structure_max_loss_is_none_for_undefined_structure` | straddle → `None` |
| `test_structure_max_loss_for_a_vertical_spread` | the 61.2%-of-book case: credit 8,250 → max_loss 14,250, both legs sharing an `option_type` |
| `test_structure_max_loss_is_none_when_a_wing_did_not_fill` | bound exists, then the wing's fill is stripped → `None`, no fabricated bound |
| `test_exit_driver_stop_closes_on_fraction_of_max_loss` | end-to-end close through the driver |
| `test_exit_driver_holds_inside_the_max_loss_band` | end-to-end hold |

`tests/execution/ tests/strategies/ tests/daytype/ tests/options_wall/`: **431 passed,
4 skipped.** The three pre-existing `sl_mult == 2.0` assertions
(`test_nifty_shield_execution.py:53`, `test_nifty_shield_paper_execution.py:59`,
`test_nifty_shield_v1_conformance.py:163`) remain valid and are kept — the conformance one
gained a companion `sl_frac == 0.50` assertion rather than a value swap.

---

## 5. Two things the operator must decide — neither is mine to grant

### 5a. `sl_frac = 0.50` is a rule, not a calibration

0.50 is carried over from the wall's fix. It does **not** transfer cleanly, because
NiftyShield's wings are fixed-point rather than a percentage of the underlying:

| Structure | Wing | 0.5 × max_loss | As % of credit |
|---|---:|---:|---:|
| `bull_put_spread` | 150 | 47.45 pts | 86.1% |
| `bear_call_spread` | 150 | 43.74 pts | 70.0% |
| **`iron_fly`** | **100** | **7.50 pts** | **8.8%** |

On the fly that is a ~7.5-point MTM stop on a four-leg structure whose round-trip spread is
plausibly 4–8 points. **It is arithmetically correct** — 15 points *is* the fly's entire risk
budget, and risking half of it is coherent — **but it is close enough to quote noise that it
may fire on the spread rather than on the market.** The honest position: no intraday mark
series for these structures exists in the repo (bhavcopy is EOD; the hold is 13:00→15:15), so
there is nothing here to calibrate the fraction against. The rule is now dimensionally right;
the number is a judgement the operator should set knowingly, and `iron_fly` may warrant its
own value.

### 5b. This moves the certified `config_hash`

`stop_loss_max_loss_frac` sits in `DEFAULT_CONFIG` and is not a `_RUNTIME_SEAM`, so it feeds
`config_hash`:

```
was (ledger E005/E006/E007): c5b722ff204d4e434f5cbffb1674136738a79693a3ced17bf07e46676d5336c6
now:                         14b71bed70e37f1360ddb6bdc03f3e375cf387ac9ecd345887ffba3ac6282378
```

> **Updated later the same day.** `lot_size` also moved (75 -> 65, NSE revision) in
> `NIFTY_SHIELD_TRADE_PAGE_DEFECTS_2026-09-07.md` §1. The hash above is the final value after
> **both** parameter changes. This is **one** re-cert entry covering two parameters, not two
> grants; the intermediate hash `d063d7a1…d4c3` this section first carried never shipped.

Per MM12.5 §5.2 this needs an **operator re-cert ledger entry** (next free slot after E007)
before the PAPER window resumes. The alternative — hiding the change from the hash by putting
the fraction only in the execution layer — was considered and rejected: E006's own *"STANDING
SEMANTICS NOTE (config_hash cannot detect…)"* is the repo recording that a behaviour change
invisible to the hash is the worse failure mode. `datasheet.md` and
`STRATEGY_PROMOTION_LEDGER.md` are operator artifacts and were **not** edited here.

**Deployment:** as with the wall, a running orchestrator holds the old config in memory; the
new rule applies only after restart.

---

## 6. Adjacent, not fixed

`profit_target_pct = 0.50` is the same 50%-of-credit target the wall found reachable only on
expiry day (148/148 crossings on DTE 0). NiftyShield never holds to expiry — it exits at 15:15
on an expiry >= 2 days out — so by the wall's own finding its TP is suspect too. Out of scope
here; flagged for a separate pass.
