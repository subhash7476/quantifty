"""NiftyShield ops preflight — read-only go/no-go over the trading-window stack.

Pure tiered checks over a resolved PreflightContext (all IO happens in
build_context), so every check is unit-testable without processes. BLOCK checks
mean no valid session is possible; WARN checks surface but never block.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.database.utils.market_hours import MarketHours
from scripts.ops import pidfile

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


# --------------------------------------------------------------------------- #
# WARN checks (run, but surface — never gate)
# --------------------------------------------------------------------------- #
def check_span(ctx: PreflightContext) -> CheckResult:
    return CheckResult("span", "warn", ctx.span_present,
                       "SPAN snapshot present" if ctx.span_present
                       else "SPAN snapshot absent (PAPER tolerates — flat-rate margin)")


def check_master(ctx: PreflightContext) -> CheckResult:
    ok = ctx.master_age_days is not None and ctx.master_age_days <= MASTER_MAX_AGE_DAYS
    return CheckResult("instrument_master", "warn", ok,
                       f"master age {ctx.master_age_days}d" if ok
                       else f"instrument master stale/absent (age={ctx.master_age_days}d)")


def check_feeds(ctx: PreflightContext) -> CheckResult:
    stale = sorted(n for n, fresh in ctx.feed_fresh.items() if not fresh)
    ok = not stale
    return CheckResult("eod_feeds", "warn", ok,
                       "all EOD feeds fresh" if ok
                       else f"EOD feeds behind expected session: {', '.join(stale)}")


def check_eod_worker(ctx: PreflightContext) -> CheckResult:
    return CheckResult("eod_worker", "warn", ctx.eod_worker_alive,
                       "EOD worker alive" if ctx.eod_worker_alive
                       else "EOD worker not running (schedule_worker.py)")


def run_preflight(ctx: PreflightContext) -> list:
    return [
        check_token(ctx), check_stop_file(ctx), check_marks(ctx), check_vix(ctx),
        check_span(ctx), check_master(ctx), check_feeds(ctx), check_eod_worker(ctx),
    ]


def verdict(results) -> str:
    return "NO-GO" if any(r.tier == "block" and not r.ok for r in results) else "GO"


# --------------------------------------------------------------------------- #
# Real resolver (injectable paths/clock for tests)
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parents[2]
CHAIN_CACHE = ROOT / "data" / "options" / "chain_cache.duckdb"
POLLER_PID = ROOT / "data" / "options" / "chain_poller.pid"
POLLER_HB = ROOT / "data" / "options" / "chain_poller_heartbeat.json"
INGESTOR_STATUS = ROOT / "logs" / "market_ingestor_status.json"
LIVE_BUFFER = ROOT / "data" / "live_buffer" / "candles_today.duckdb"
MASTER_DB = ROOT / "data" / "instruments" / "nse_fo_instruments.duckdb"
SPAN_DIR = ROOT / "data" / "span"
EOD_LOCK = ROOT / "data" / "_eod_worker.lock"
VIX_SYMBOL = "NSE_INDEX|India VIX"


def _read_marks(path: Path, retries: int = 5, delay_s: float = 0.1):
    """Bounded-retry read of the latest snapshot's row + priceable-row counts.
    Read-only; retries transient sharing violations from the poller's os.replace."""
    import time
    import duckdb
    if not path.exists():
        return 0, 0
    for attempt in range(retries):
        try:
            con = duckdb.connect(str(path), read_only=True)
            try:
                names = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
                if "option_chain_snapshot" not in names:
                    return 0, 0
                row = con.execute(
                    "SELECT COUNT(*), COUNT(*) FILTER (WHERE ltp > 0) "
                    "FROM option_chain_snapshot WHERE snapshot_timestamp = "
                    "(SELECT MAX(snapshot_timestamp) FROM option_chain_snapshot)"
                ).fetchone()
                return int(row[0] or 0), int(row[1] or 0)
            finally:
                con.close()
        except Exception:
            if attempt == retries - 1:
                return 0, 0
            time.sleep(delay_s)
    return 0, 0


def _heartbeat_age_s(now: datetime) -> Optional[float]:
    try:
        payload = json.loads(POLLER_HB.read_text(encoding="utf-8"))
        ts = datetime.fromisoformat(payload["last_snapshot"])
        return (now - ts).total_seconds()
    except (OSError, ValueError, KeyError):
        return None


def _ingestor_alive(now: datetime) -> bool:
    """Liveness = status file written today AND its PID alive.

    NOTE (plan deviation): the plan's 120 s heartbeat-recency window is dropped
    as REDUNDANT, not because the file is stale — `market_ingestor.py:318/324`
    calls `_update_heartbeat` every loop iteration (~1.5 s in-session, ~60 s when
    closed), so `last_heartbeat` is in fact fresh. PID-liveness is the
    authoritative "process is up" signal; data freshness is delegated to the
    VIX-bar check (BLOCK during market hours). The one case this does NOT catch
    that the window would: a wedged-but-alive ingestor pre-open (PID up, heartbeat
    frozen, date still today) — low-risk, and in-session the VIX check catches it.
    """
    try:
        payload = json.loads(INGESTOR_STATUS.read_text(encoding="utf-8"))
        pid = int(payload.get("pid", 0))
        if not pidfile.pid_alive(pid):
            return False
        hb = datetime.fromisoformat(payload["last_heartbeat"])
        return hb.date() == now.date()
    except (OSError, ValueError, KeyError):
        return False


def _vix_bar_age_s(now: datetime) -> Optional[float]:
    if not LIVE_BUFFER.exists():
        return None
    try:
        import duckdb
        con = duckdb.connect(str(LIVE_BUFFER), read_only=True)
        try:
            row = con.execute(
                "SELECT MAX(timestamp) FROM candles WHERE symbol = ?", [VIX_SYMBOL]
            ).fetchone()
        finally:
            con.close()
        if not row or row[0] is None:
            return None
        ts = row[0] if isinstance(row[0], datetime) else datetime.fromisoformat(str(row[0]))
        return (now - ts).total_seconds()
    except Exception:
        return None


def _span_present() -> bool:
    try:
        from core.risk.span.span_freshness import expected_span_date
        d = expected_span_date()
        return (SPAN_DIR / f"nse_fo_span_{d.isoformat()}.parquet").exists()
    except Exception:
        return False


def _master_age_days(now: datetime) -> Optional[float]:
    if not MASTER_DB.exists():
        return None
    return (now.timestamp() - MASTER_DB.stat().st_mtime) / 86400.0


def _prev_trading_session(today):
    from datetime import timedelta
    d = today - timedelta(days=1)
    while not MarketHours.is_trading_day(datetime.combine(d, datetime.min.time())):
        d -= timedelta(days=1)
    return d


def _feed_fresh(expected) -> dict:
    from core.scheduler.eod_decision import probe_feeds
    feeds = probe_feeds()
    return {name: (d is not None and d >= expected) for name, d in feeds.items()}


def build_context(now: Optional[datetime] = None, root: Optional[Path] = None) -> PreflightContext:
    now = now or MarketHours.get_ist_now().replace(tzinfo=None)
    root = root or ROOT
    market_open = MarketHours.is_market_open()
    from core.auth.credentials import credentials
    credentials._load()
    rows, priceable = _read_marks(CHAIN_CACHE)
    expected_eod = _prev_trading_session(now.date())
    return PreflightContext(
        now=now,
        market_open=market_open,
        stop_file_present=(root / "STOP").exists(),
        has_token=credentials.has_upstox_token,
        token_expired=credentials.is_token_expired,
        marks_rows=rows,
        marks_priceable=priceable,
        marks_heartbeat_age_s=_heartbeat_age_s(now),
        poller_alive=pidfile.lock_alive(POLLER_PID),
        ingestor_alive=_ingestor_alive(now),
        vix_last_bar_age_s=_vix_bar_age_s(now),
        span_present=_span_present(),
        master_age_days=_master_age_days(now),
        feed_fresh=_feed_fresh(expected_eod),
        eod_worker_alive=pidfile.lock_alive(EOD_LOCK),
    )


def main() -> int:
    ctx = build_context()
    results = run_preflight(ctx)
    v = verdict(results)
    print(f"NiftyShield preflight @ {ctx.now:%Y-%m-%d %H:%M}  "
          f"(market_open={ctx.market_open})\n" + "-" * 60)
    for r in results:
        mark = "OK " if r.ok else ("!! " if r.tier == "block" else " ~ ")
        print(f"  [{mark}] {r.tier.upper():5} {r.name:18} {r.detail}")
    print("-" * 60 + f"\n  VERDICT: {v}")
    return 0 if v == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
