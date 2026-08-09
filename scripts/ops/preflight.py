"""NiftyShield ops preflight — read-only go/no-go over the trading-window stack.

Pure tiered checks over a resolved PreflightContext (all IO happens in
build_context, Task 4), so every check is unit-testable without processes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

MARKS_HEARTBEAT_MAX_S = 60.0
VIX_BAR_MAX_S = 300.0
MASTER_MAX_AGE_DAYS = 1.0


@dataclass(frozen=True)
class CheckResult:
    name: str
    tier: str      # "block" | "warn"
    ok: bool
    detail: str


@dataclass(frozen=True)
class PreflightContext:
    now: datetime
    market_open: bool
    stop_file_present: bool
    has_token: bool
    token_expired: bool
    marks_rows: int
    marks_priceable: int
    marks_heartbeat_age_s: Optional[float]
    poller_alive: bool
    ingestor_alive: bool
    vix_last_bar_age_s: Optional[float]
    span_present: bool
    master_age_days: Optional[float]
    feed_fresh: dict
    eod_worker_alive: bool


def check_token(ctx: PreflightContext) -> CheckResult:
    ok = ctx.has_token and not ctx.token_expired
    detail = ("token present and fresh" if ok
              else "Upstox token absent" if not ctx.has_token
              else "Upstox token expired — re-login via /ops/login/upstox")
    return CheckResult("upstox_token", "block", ok, detail)


def check_stop_file(ctx: PreflightContext) -> CheckResult:
    ok = not ctx.stop_file_present
    return CheckResult("stop_file", "block", ok,
                       "no STOP file" if ok else "STOP kill-switch file present")


def check_marks(ctx: PreflightContext) -> CheckResult:
    if not ctx.market_open:
        return CheckResult("marks_warm", "block", ctx.poller_alive,
                           "pre-open: poller alive" if ctx.poller_alive
                           else "pre-open: chain poller not running")
    fresh = (ctx.marks_heartbeat_age_s is not None
             and ctx.marks_heartbeat_age_s <= MARKS_HEARTBEAT_MAX_S)
    ok = ctx.marks_rows > 0 and ctx.marks_priceable > 0 and fresh
    detail = (f"{ctx.marks_priceable} priceable rows, "
              f"heartbeat {ctx.marks_heartbeat_age_s}s"
              if ok else
              f"marks not warm (rows={ctx.marks_rows} priceable="
              f"{ctx.marks_priceable} hb_age={ctx.marks_heartbeat_age_s}s)")
    return CheckResult("marks_warm", "block", ok, detail)


def check_vix(ctx: PreflightContext) -> CheckResult:
    if not ctx.market_open:
        return CheckResult("live_vix", "block", ctx.ingestor_alive,
                           "pre-open: ingestor alive" if ctx.ingestor_alive
                           else "pre-open: market ingestor not running")
    fresh = (ctx.vix_last_bar_age_s is not None
             and ctx.vix_last_bar_age_s <= VIX_BAR_MAX_S)
    ok = ctx.ingestor_alive and fresh
    detail = (f"VIX bar {ctx.vix_last_bar_age_s}s old" if ok
              else f"VIX not flowing (ingestor_alive={ctx.ingestor_alive} "
                   f"bar_age={ctx.vix_last_bar_age_s}s) — 13:00 fact would be skipped")
    return CheckResult("live_vix", "block", ok, detail)
