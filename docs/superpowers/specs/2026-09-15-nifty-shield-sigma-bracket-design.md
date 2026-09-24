# NiftyShield — sigma-bracket take-profit and stop

**Date:** 2026-09-15 · **Status:** approved design, not implemented · **Scope:** `nifty_shield_v1`, PAPER

## 1. Problem

The exit rules are sized in units unrelated to what drives an intraday hold's P&L.

On the 2026-09-15 bear call spread (SELL 23300CE @ 174.50 / BUY 23500CE @ 83.25, 7 DTE, 65 qty):

| Rule | Rs | In Nifty points | In σ(2.5 h) |
|---|---:|---:|---:|
| Take-profit `0.50 × available_decay_frac × credit` | 121 | 8 | 0.08 |
| Stop `0.50 × max_loss` | 3,534 | 245 | 2.4 |
| Round-trip fees | 133 | | |

Stop ÷ take-profit is 29×; break-even needs a 96.7% win rate before fees and no win rate
clears fees, because a take-profit at threshold nets −Rs 12. The trade closed after two
minutes for Rs 6 net (`NIFTY_SHIELD_TRADE_2026-09-15_EARLY_TAKE_PROFIT.md`).

The underlying cause: a 13:00 → 15:35 hold on a 2–8 DTE structure decays only 2–7% of its
premium, so P&L is dominated by the index move, not theta. Nifty's 13:00 → 15:29 absolute
move over 666 sessions (2024 → 2026-09) has median 46 pts, p90 131, p95 166; the implied
1σ over 2.5 h on 2026-09-15 was 101 pts. Exits must be sized in that unit.

## 2. Decision

The strategy stays intraday (13:00 entry, 15:35 flatten). Take-profit and stop become a
symmetric bracket in index-move terms: the structure's P&L at spot ±1σ over the hold.

Nothing here is fitted to trade outcomes. Inputs are each leg's implied vol at its fill, the
entry spot and DTE, and the fee schedule. The width `k = 1.0` and the fee multiple `3.0` are
design choices, not tuned values; the historical move table is a sanity check only.

## 3. The rule

Computed once per structure, after all legs have filled.

1. **Leg IVs from fills.** For each leg, solve Black-Scholes implied vol from its own
   `average_price`, using the signal's `spot`, `dte` (years = dte / 365, the credit gate's
   convention), `strike`, `option_type` and `risk_free_rate`. Fill prices and signal metadata
   are both persisted, so a restart recomputes the identical bracket without new state.
2. **Hold sigma.** `σ_pts = spot × mean(IV of SELL legs) × √(hold_hours / (252 × session_hours))`
   with the existing `hold_hours = 2.5`, `session_hours = 6.25`.
3. **Reprice.** With leg IVs held fixed and time unchanged, define
   `value(s) = Σ_legs sign × bs_price(s, strike, t, rate, iv_leg, option_type) × qty_leg`
   (SELL `+1`, BUY `−1`, `qty_leg` = the leg's filled quantity). Per-side P&L (Rs) is
   `gain_down = value(spot) − value(spot − kσ)` and `gain_up = value(spot) − value(spot + kσ)`;
   a positive value is a gain for the book.
4. **Bracket.** `tp_rs = max(gain_down, gain_up, 0)`; `sl_rs = −min(gain_down, gain_up)`.
5. **Fee floor.** `fee_floor_rs = tp_min_fee_multiple × (entry fees + exit fees estimated at
   the entry premia via option_order_fees)`. If `tp_rs < fee_floor_rs`, the take-profit is
   disabled for this structure. Straddles and iron flies lose on both sides, so `tp_rs = 0`
   and they are managed by the stop, the delta gate and the 15:35 clock.
6. **Unavailable.** If any leg's IV cannot be solved (e.g. a fill below intrinsic value) or a
   required input is missing, the bracket is unavailable: no TP and no SL for that structure,
   journaled at CRITICAL. The 15:35 hard exit and the delta gate still apply. No fallback
   numbers are substituted.

Exit triggers, in priority order, evaluated per bar on the group's unrealized P&L at marks:

| # | Trigger | Condition |
|---|---|---|
| 1 | `take_profit` | bracket available, TP enabled, `pnl ≥ tp_rs` |
| 2 | `stop_loss` | bracket available, `pnl ≤ −sl_rs` |
| 3 | `time_exit` | bar time ≥ 15:35 (unchanged) |
| 4 | `delta_flatten` | `|portfolio delta| > max_portfolio_delta` (unchanged) |

**Worked example (2026-09-15):** solved spot 23,334.5, both leg IVs 0.1091, σ = 101.4 pts;
P&L at −1σ +Rs 1,424, at +1σ −Rs 1,462 → **TP Rs 1,424, SL Rs 1,462**; fee floor
3 × 134 = Rs 402, TP enabled.

## 4. Components

| File | Change |
|---|---|
| `core/execution/options/nifty_shield_pricing.py` | Add pure `implied_vol(price, spot, strike, t_years, rate, option_type) -> Optional[float]` (bisection; None when no solution) and `sigma_bracket(legs, spot, dte_days, rate, sigma_mult, hold_hours, session_hours, fee_floor_rs) -> Optional[Bracket]`. `Bracket` is a frozen dataclass: `tp_rs, sl_rs, sigma_pts, leg_ivs, fee_floor_rs, tp_enabled`. `legs` carry `side, strike, option_type, price, qty`. Reuses `bs_price`. |
| `core/execution/options/nifty_shield_exit.py` | `evaluate(group_id, current_prices, bar_time, portfolio_delta, bracket: Optional[Bracket])`. Delete the decay-fraction take-profit, the max-loss stop and the credit-multiple stop, and their config keys. Module docstring rewritten to the bracket rule. |
| `core/execution/options/nifty_shield_handler.py` | New `structure_bracket(group_id) -> Optional[Bracket]`: builds legs from fills + leg metadata, computes the fee floor, calls `sigma_bracket`, caches per group, and journals once per group. Exit loop passes it to the manager. `_manager_for` drops the removed keys. Delete `structure_max_loss` (its only production caller was the stop). |
| `core/runtime/event_journal.py` | New `EventType.ENTRY_BRACKET` (INFO) carrying `group_id, tp_rs, sl_rs, sigma_pts, leg_ivs, fee_floor_rs, tp_enabled, sigma_mult`; unavailable → `ENTRY_BRACKET` at CRITICAL with `reason`. |
| `strategies/nifty_shield_v1/config.py` | Remove `profit_target_decay_frac`, `stop_loss_max_loss_frac`, `stop_loss_multiplier`. Add `bracket_sigma: 1.0`, `tp_min_fee_multiple: 3.0` with rationale comments. Keep `hold_hours`, `session_hours`. `config_hash` moves. |
| `strategies/nifty_shield_v1/source.py` | Signal `exit` block: remove `tp_decay_frac`, `available_decay_frac`, `sl_mult`, `sl_frac`; add `bracket_sigma`, `tp_min_fee_multiple`. |
| `strategies/nifty_shield_v1/structures.py` | Delete `available_decay_frac` (no remaining caller). |
| `strategies/nifty_shield_v1/__init__.py` | Docstring key list updated. |

Out of scope: `core/options_wall/paper_executor.py` and `core/strategies/knowledge_signal_source.py`
use similarly named keys but are different strategies and are not touched.
`scripts/nifty_shield/derive_anchoring_params.py` is a historical derivation record and keeps
its §3 as written.

## 5. Testing

Pricing (pure):
- `implied_vol` round-trips `bs_price` for CE/PE across moneyness; returns None below intrinsic.
- The 2026-09-15 spread reproduces TP ≈ Rs 1,424, SL ≈ Rs 1,462, σ ≈ 101.4 pts (tolerance ±1%).
- A short straddle yields `tp_rs = 0` and `tp_enabled = False`, with `sl_rs > 0`.
- A bracket whose `tp_rs` is below the fee floor has `tp_enabled = False`.
- An unsolvable leg returns None.

Exit manager:
- fires `take_profit` at `pnl ≥ tp_rs` only when enabled; never when disabled.
- fires `stop_loss` at `pnl ≤ −sl_rs`.
- bracket None → neither fires; `time_exit` and `delta_flatten` unchanged.
- The replaced tests (`test_take_profit_triggers`, `test_take_profit_is_disabled_without_an_available_decay_fraction`,
  `test_stop_loss_triggers`, the iron-fly / vertical / undefined stop tests, and the four
  `structure_max_loss` tests) are rewritten or deleted, not left asserting removed behaviour.

Handler:
- `structure_bracket` from fills equals the pure computation, and is identical after a
  simulated restart (group rebuilt from persisted orders).
- `ENTRY_BRACKET` journaled exactly once per group; CRITICAL variant when unavailable.

Strategy:
- conformance tests updated for the new config keys and signal `exit` block; `config_hash` re-pinned.

## 6. Documentation and rollout

- `NIFTY_SHIELD_REMEDIATION_2026-09-08.md`: new §4.x recording this decision and its evidence;
  §5 row for the stop parameters updated; §6 open item 5 marked superseded; new `config_hash`
  recorded.
- `NIFTY_SHIELD_TRADE_2026-09-15_EARLY_TAKE_PROFIT.md`: link to this spec.
- PAPER only. Takes effect at the next session start; the session running on 2026-09-15
  keeps the old rule.
- Evidence to watch on forward paper: the distribution of exit reasons and of P&L in units of
  the journaled `sl_rs`. A stop that fires on most sessions, or a take-profit that never
  fires, is the signal to revisit `k` — as a recorded design decision, not a refit.
