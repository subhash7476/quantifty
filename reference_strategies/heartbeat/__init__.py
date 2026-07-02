from reference_strategies.heartbeat.source import HeartbeatSignalSource


def build_signal_source(config: dict = None) -> HeartbeatSignalSource:
    """Factory: return a configured HeartbeatSignalSource.

    Args:
        config: optional dict with keys entry_period_bars (default 60),
            holding_period_bars (default 15), sl_distance_pct (default 0.01),
            risk_r (default 500.0), symbols (default None — resolved later
            at the composition root; the source accepts any symbol it sees).

    This is the external-style factory ADR-016 specifies as the strategy
    package's public export — used by the composition script, never by the
    platform.
    """
    cfg = dict(config or {})
    return HeartbeatSignalSource(
        entry_period_bars=cfg.get("entry_period_bars", 60),
        holding_period_bars=cfg.get("holding_period_bars", 15),
        sl_distance_pct=cfg.get("sl_distance_pct", 0.01),
        risk_r=cfg.get("risk_r", 500.0),
    )
