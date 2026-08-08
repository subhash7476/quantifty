"""NiftyShield — datasheet §9 risk-gate configuration (E007 deliverable B).

Builds the `ExecutionConfig` for a PAPER window from the frozen datasheet §9
declaration, so the strategy is validated against its own promises (§7.4.1):

    Drawdown limit      Rs 30,000 single day  -> handler drawdown gate, expressed
                          as a fraction of `initial_capital` (the handler's gate
                          is equity-peak-based). The Rs 150,000 5-day streak is a
                          stressed *declaration* (§7/§7a), not a separate gate.
    Daily trade limit   1 structure/session   -> the source's `_entered_today`
                          shadow flag is the structure gate (0 or 1/session);
                          the handler per-fill gate is set to the maximum legs a
                          single structure can emit (4 = iron fly) so it never
                          breaks a structure, and the audit tool verifies 1
                          structure/session by group_id.
    Max positions       1 structure           -> per-symbol stacking guard
                          (handler) + source shadow flag + audit verification.
    Margin budget       25% via NseMarginEngine -> `max_capital_utilisation`.
    Greek limits        |Δ|>500 flatten       -> the declared gate is the D1
                          close-only *structure* flatten, enforced by
                          NiftyShieldExitDriver at the exit layer. The handler's
                          per-leg `_check_greek_limits` is configured with delta
                          = 500 and vega/gamma effectively disabled, because the
                          datasheet declares no vega/gamma gate and the handler's
                          per-leg greek check computes with the option mark as
                          the underlying (not the index), so it is not the
                          structure-level declared gate.
"""
from __future__ import annotations

from typing import Any, Dict

from core.execution.handler import ExecutionConfig, ExecutionMode

# One structure's maximum leg count (iron fly = 4). The handler's per-fill
# daily-limit gate must never split a single structure.
MAX_LEGS_PER_STRUCTURE = 4

DEFAULT_CERTIFIED_CONFIG: Dict[str, Any] = {
    "vix_skip_above": 20.0,
    "vix_reduce_above": 16.0,
    "iron_fly_vix_above": 14.0,
    "max_portfolio_delta": 500,
    "max_lots": 2,
    "lot_size": 75,
}


def nifty_shield_execution_config(
    *,
    initial_capital: float,
    mode: ExecutionMode = ExecutionMode.PAPER,
    certified_config: Dict[str, Any] = DEFAULT_CERTIFIED_CONFIG,
) -> ExecutionConfig:
    """Datasheet §9 -> ExecutionConfig for a NiftyShield validation window.

    `initial_capital` is the PAPER cash balance the Rs-based declarations are
    expressed against (the datasheet's allocated capital pins @ Stage 3, so the
    PAPER operator supplies the number; the drawdown gate is 30000/initial_capital
    and the margin budget is 25% of it).
    """
    max_lots = int(certified_config.get("max_lots", 2))
    lot_size = int(certified_config.get("lot_size", 75))
    max_position_size = float(max_lots * lot_size)

    return ExecutionConfig(
        mode=mode,
        # 1 structure/session (4 legs max); the structure gate is the source's
        # shadow flag, this per-fill gate is a backstop that never splits a leg set.
        max_trades_per_day=MAX_LEGS_PER_STRUCTURE,
        # Rs 30,000 single-day drawdown, as a fraction of the PAPER equity base.
        max_drawdown_limit=30000.0 / initial_capital,
        max_position_size=max_position_size,
        default_quantity=max_position_size,
        # 25% margin budget (datasheet §7/§9).
        max_capital_utilisation=0.25,
        # Declared delta flatten-gate value; vega/gamma are undeclared by the
        # datasheet and effectively disabled (see module docstring).
        max_portfolio_delta=float(certified_config.get("max_portfolio_delta", 500)),
        max_portfolio_vega=1e12,
        max_gamma_exposure=1e12,
    )
