"""
MM9.1 — Margin Gate (capital-utilisation enforcement).

MM9.1-S1 scope: ExecutionConfig.max_capital_utilisation field only.
This file will receive additional tests in S2/S3/S4 (gate method,
call site wiring, full characterization) without modification to the
S1 tests below.
"""

from core.execution.handler import ExecutionConfig


# =========================================================================== #
# MM9.1-S1 — ExecutionConfig.max_capital_utilisation field
# =========================================================================== #

def test_execution_config_max_capital_utilisation_defaults_to_0_80():
    assert ExecutionConfig().max_capital_utilisation == 0.80


def test_execution_config_max_capital_utilisation_is_configurable():
    cfg = ExecutionConfig(max_capital_utilisation=0.5)
    assert cfg.max_capital_utilisation == 0.5


def test_execution_config_existing_fields_unaffected_by_s1():
    cfg = ExecutionConfig()
    assert cfg.broker_error_threshold == 3
    assert cfg.max_drawdown_limit == 0.05


def test_execution_config_max_capital_utilisation_type_is_float():
    assert isinstance(ExecutionConfig().max_capital_utilisation, float)
