# MM9.3-S1B — Portfolio Greek Aggregation
## Implementation Specification

**Status:** PENDING IMPLEMENTATION
**Parent spec:** `docs/reports/MM9_3_IMPLEMENTATION_SPEC.md` (§5, Slice S1B)
**Preceded by:** MM9.3-S1A COMPLETE (commit `c7acbc8`, 687 tests passing)
**Followed by:** MM9.3-S2 (PortfolioView runtime integration)
**Date drafted:** 2026-06-28
**Scope:** Replace the marginal-only body of `_check_greek_limits` with portfolio-level
aggregation. Signature, EXIT bypass, and call site from S1A are unchanged.

---

## 0. Corrections to the parent spec (§5 / S1B.3)

Same defect as S1A: the parent spec line 385 uses `logger.warning("[%s] Greek limits
breached: %s", self.runner_id, "; ".join(breaches))`. Two errors:

1. **`self.runner_id` does not exist** on `ExecutionHandler` (grep-verified).
2. **`logger`** is not a bare name in the handler — the logger is `self.logger`
   (`setup_logger("execution_handler")`, handler.py:246).

S1B uses the D4 WARNING token pattern established by S1A, extended for multi-Greek
breaches:

```
GREEK_LIMIT_BREACH symbol=%s signal_id=%s delta=%.1f vega=%.1f gamma=%.1f limits=%s
```

The S1A token `GREEK_DELTA_BREACH` is superseded (S1A was delta-only; S1B checks all
three). S1A test U5 (`test_greek_gate_logs_warning_on_breach`) must be updated to assert
the new token.

---

## 1. Repository Impact

### Files modified — exactly ONE

| File | Change |
|------|--------|
| `core/execution/handler.py` | Replace the body of `_check_greek_limits` (lines ~978-1030) with portfolio aggregation. Signature `-> bool`, EXIT bypass, and call site at :615 are unchanged. |

### Files NOT modified

All other production files. `portfolio_greeks.py`, `greeks_calculator.py`,
`black76_engine.py` are complete and tested. `InstrumentParser` stays (G1 carve-out #3);
S1B adds the migration TODO comment on the `parse` call per parent spec S1B.2.

### Test files

| File | Change |
|------|--------|
| `tests/execution/test_greek_limits.py` | +7 S1B tests (B1-B7); update C2 (warm cache) → delete at close; update U5 (token `GREEK_DELTA_BREACH` → `GREEK_LIMIT_BREACH`); update U6/I1 if needed for portfolio-aware semantics |

---

## 2. Implementation Plan

### 2.1 Body replacement (S1B.1 + S1B.2 + S1B.3)

The method keeps the S1A signature and EXIT bypass. The body after the EXIT check
becomes:

```python
def _check_greek_limits(self, signal: SignalEvent, current_price: float) -> bool:
    if signal.signal_type == SignalType.EXIT:
        return True

    # S1B.1: current portfolio Greeks (empty dicts → PortfolioGreeks applies
    # IV=0.20 / TTE=0.0 defaults internally; Black76 T=0 is intrinsically safe).
    market_prices = {sym: snap.price for sym, snap in self._price_cache.items()}
    current_pf_greeks = self.portfolio_greeks.calculate_portfolio_greeks(
        market_prices=market_prices,
        volatilities={},
        time_to_expiry_map={},
        risk_free_rate=0.05,
    )

    # S1B.2: marginal signal Greeks
    meta = signal.metadata or {}
    # TODO(MM10): Migrate from InstrumentParser to canonical InstrumentResolver if
    # PHASE 1 gate ordering changes. InstrumentParser.parse() is intentionally
    # retained here because this gate runs at [9C], before PHASE 1 instrument
    # resolution. Asset-class dispatch only is needed; broker-resolution is not.
    instrument = InstrumentParser.parse(signal.symbol)
    qty = self._calculate_position_size(signal, current_price)
    if signal.signal_type == SignalType.SELL:
        qty = -qty
    from core.risk.greeks.greeks_calculator import GreeksCalculator
    marginal_greeks = GreeksCalculator.calculate(
        instrument=instrument,
        quantity=qty,
        underlying_price=meta.get('underlying_price', current_price),
        volatility=meta.get('iv', 0.20),
        time_to_expiry=meta.get('tte', 0.0),
    )

    # S1B.3: combined limit check
    combined_delta = current_pf_greeks.delta + marginal_greeks.delta
    combined_vega = current_pf_greeks.vega + marginal_greeks.vega
    combined_gamma = current_pf_greeks.gamma + marginal_greeks.gamma

    breaches = []
    if abs(combined_delta) > self.config.max_portfolio_delta:
        breaches.append(f"delta {combined_delta:.1f} vs limit {self.config.max_portfolio_delta}")
    if abs(combined_vega) > self.config.max_portfolio_vega:
        breaches.append(f"vega {combined_vega:.1f} vs limit {self.config.max_portfolio_vega}")
    if abs(combined_gamma) > self.config.max_gamma_exposure:
        breaches.append(f"gamma {combined_gamma:.1f} vs limit {self.config.max_gamma_exposure}")

    if breaches:
        self.metrics.rejected_trades += 1
        sig_id = getattr(signal, 'signal_id',
                         (signal.metadata or {}).get('signal_id'))
        if not sig_id:
            from hashlib import sha256
            raw_id = f"{signal.symbol}_{signal.strategy_id}_{signal.timestamp.isoformat()}"
            sig_id = sha256(raw_id.encode()).hexdigest()
        self.logger.warning(
            "GREEK_LIMIT_BREACH symbol=%s signal_id=%s delta=%.1f vega=%.1f "
            "gamma=%.1f limits=delta<%.1f vega<%.1f gamma<%.1f breaches=%s",
            signal.symbol, sig_id, combined_delta, combined_vega, combined_gamma,
            self.config.max_portfolio_delta, self.config.max_portfolio_vega,
            self.config.max_gamma_exposure, "; ".join(breaches),
        )
        return False
    return True
```

### 2.2 Behavioural contract (post-S1B)

| Pre-condition | Action | Outcome |
|--------------|--------|---------|
| `signal.signal_type == EXIT` | Early return | `True` |
| Empty book + marginal within all limits | Compute + return | `True` |
| `abs(combined_delta) > max_portfolio_delta` | `rejected_trades += 1`, WARNING | `False` |
| `abs(combined_vega) > max_portfolio_vega` | `rejected_trades += 1`, WARNING | `False` |
| `abs(combined_gamma) > max_gamma_exposure` | `rejected_trades += 1`, WARNING | `False` |
| Multiple limits breached | Single rejection, all in one WARNING | `False` |

---

## 3. TDD Plan

**Baseline:** 687 tests passing (post-S1A).

### 3.1 C2 update (warm the cache so it goes red at S1B)

C2 currently doesn't warm `_price_cache`, so the injected position contributes zero
Greeks (no price → `_calculate_position_greeks` returns zeros). Update C2 to warm the
cache so the position contributes real Greeks; it will go red when S1B lands (combined
delta exceeds limit). Then delete C2 at slice close.

### 3.2 New S1B tests (B1-B7)

Mock `self.portfolio_greeks.calculate_portfolio_greeks` for controlled portfolio Greeks.
Use tight limits to trigger breaches without realistic position sizes.

| ID | Test name | What it verifies |
|----|-----------|------------------|
| B1 | `test_greek_gate_returns_true_on_empty_book` | No positions → portfolio = 0; marginal within limits → `True` |
| B2 | `test_greek_gate_returns_false_on_portfolio_delta_breach` | Mock pf delta=50; marginal=95; limit=100 → combined 145 > 100 → `False` |
| B3 | `test_greek_gate_returns_false_on_vega_breach` | Mock pf vega=400; equity marginal vega=0; vega limit=300 → breach |
| B4 | `test_greek_gate_returns_false_on_gamma_breach` | Mock pf gamma=80; equity marginal gamma=0; gamma limit=50 → breach |
| B5 | `test_greek_gate_uses_price_cache_for_market_prices` | Spy on `calculate_portfolio_greeks`; assert `market_prices` matches `_price_cache` projection |
| B6 | `test_greek_gate_uses_signal_metadata_iv_for_marginal` | Spy on `GreeksCalculator.calculate`; signal with `iv=0.5` → `volatility=0.5` |
| B7 | `test_greek_gate_defaults_iv_when_metadata_absent` | Signal without `iv` → spy captures `volatility=0.20` |

### 3.3 S1A test updates

| Test | Change | Reason |
|------|--------|--------|
| U5 (`test_greek_gate_logs_warning_on_breach`) | Assert `GREEK_LIMIT_BREACH` instead of `GREEK_DELTA_BREACH` | Token changed (delta-only → all-Greek) |
| C2 (`test_current_greek_gate_checks_only_marginal_not_portfolio`) | Warm cache → goes red → **deleted** at close | Portfolio scope fixed |

### 3.4 Expected counts

| Stage | Count |
|-------|-------|
| Baseline (post-S1A) | 687 |
| + C2 updated (no net change) | 687 |
| + B1-B7 | 694 |
| − C2 deleted | 693 |
| **Final** | **693** |

---

## 4. Acceptance Checklist

- [ ] Portfolio Greeks computed via `calculate_portfolio_greeks(market_prices={sym: snap.price ...}, volatilities={}, time_to_expiry_map={})`
- [ ] `_price_cache` projected to `market_prices`
- [ ] Marginal Greeks use `meta.get('iv', 0.20)` / `meta.get('tte', 0.0)`
- [ ] TODO comment on `InstrumentParser.parse()` present
- [ ] Combined delta + vega + gamma checked
- [ ] Multiple breaches → single WARNING with all details
- [ ] WARNING token `GREEK_LIMIT_BREACH`; carries `symbol` + `signal_id`
- [ ] `rejected_trades` increments exactly once per rejection
- [ ] Gate never raises
- [ ] U5 updated for new token; C2 deleted
- [ ] B1-B7 green; suite ≥ 693 passing
