"""
core.runtime — platform runtime orchestration.

Home of the Deterministic Loop Driver and its strategy-agnostic seam, as
specified in docs/DRIVER_SPECIFICATION.md and governed by ADR-006 (the
LoopDriver is the sole runtime orchestrator). This package contains platform
infrastructure only — no strategy, signal-generation, or alpha logic
(PLATFORM_CONSTITUTION Principle 5; ADR-002 Platform/Strategy Separation).
"""
