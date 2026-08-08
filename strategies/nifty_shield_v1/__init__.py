"""nifty_shield_v1 — external strategy package (ADR-016 factory export).

Exports the `build_signal_source(config)` factory the composition root /
conformance harness uses. The package imports only core.events +
core.runtime.signal_source from core.* (conformance import-surface rule).
"""
from __future__ import annotations

from typing import Any, Dict

from strategies.nifty_shield_v1.config import DEFAULT_CONFIG, config_hash
from strategies.nifty_shield_v1.source import NiftyShieldSignalSource


def build_signal_source(config: Dict[str, Any] = None) -> NiftyShieldSignalSource:
    """Return a configured NiftyShieldSignalSource (external-style factory).

    Args:
        config: optional dict merged over DEFAULT_CONFIG. Recognised keys:
            underlying, entry_checkpoint, exit_time, profit_target_pct,
            stop_loss_multiplier, delta_adjustment_threshold,
            max_portfolio_delta, max_lots, lot_size, regime_sizing,
            vix_skip_above, vix_reduce_above, iron_fly_vix_above,
            wing_offset_pts, directional_wing_pts, strangle_otm_pts,
            expiry_days_min, strike_step, risk_free_rate, iv_default,
            undefined_risk_stress_pts, facts_db_path (runtime seam).
    """
    cfg = dict(DEFAULT_CONFIG)
    if config:
        cfg.update(config)
    return NiftyShieldSignalSource(cfg)


__all__ = ["build_signal_source", "config_hash", "DEFAULT_CONFIG"]
