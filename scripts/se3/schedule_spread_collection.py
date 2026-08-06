"""SE-3 forward spread collection — market-hours-gated scheduler wrapper.

The EOD worker (`scripts/schedule_worker.py`) cannot carry this job: it is
hardcoded to a post-market fire window (20:00–23:30 IST, `FIRE_HOUR`/`STOP_HOUR`)
and its design pins it as a thin EOD download/chain daemon (see
`docs/superpowers/specs/2026-07-31-eod-automation-scheduler-design.md` §3, §10).
The SE-3 collector reads LIVE quotes, so it is only meaningful during NSE market
hours (09:15–15:30 IST). Following the repo's MM.6 precedent for a non-EOD
scheduled job (`docs/reports/MM.6_REFRESH_JOB_PLAN.md` §11 — OS-scheduler
invocation, no in-repo daemon), this wrapper is invoked by the OS scheduler
(schtasks/cron) every 5 minutes Mon–Fri, and self-gates on market hours.

Cadence — every 5 minutes during market hours (09:15–15:30 IST):
  - 20 names × 1 CE contract = 20 rows/sweep.
  - A 5-min sweep over a 6.25h session = ~75 sweeps ≈ 1,500 rows/day ≈ 33k
    rows/month — trivial storage, good distributional resolution without the
    5× storage of 1-min sweeps for near-identical quotes.

Windows Task Scheduler (register once, every 5 min, daily — the wrapper
no-ops outside market hours and on holidays):
  schtasks /Create /TN "SE3SpreadCollector" /SC MINUTE /MO 5 ^
    /TR "python F:\\Nifty\\scripts\\se3\\schedule_spread_collection.py" ^
    /F

Unix (cron) equivalent:
  5,10,15,20,25,30,35,40,45,50,55 9-15 * * 1-5 ^
    python /path/to/Nifty/scripts/se3/schedule_spread_collection.py

Exit codes: 0 = no-op (market closed / not a trading day) or sweep OK;
non-zero = sweep recorded nothing during market hours or a fetch failed
(propagated from collect_option_spreads.py) — the OS scheduler surfaces it.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

COLLECTOR = ROOT / "scripts" / "se3" / "collect_option_spreads.py"

_logger = logging.getLogger("se3_spread_schedule")


def main() -> int:
    from core.database.utils.market_hours import MarketHours

    if not MarketHours.is_market_open():
        _logger.info("Market closed — no-op (exit 0)")
        return 0

    result = subprocess.run(
        [sys.executable, str(COLLECTOR), "--once"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    if result.stdout:
        _logger.info(result.stdout.strip())
    if result.returncode != 0:
        _logger.error("SE-3 sweep FAILED (exit %s): %s",
                      result.returncode, result.stderr.strip() or result.stdout.strip())
    return result.returncode


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    raise SystemExit(main())
