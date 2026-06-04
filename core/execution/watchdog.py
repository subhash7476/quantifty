"""
Runtime Watchdog
----------------
Heartbeat file generation + data-staleness detection.

Extracted (logic-preserving) from core/runner.py — platform infrastructure,
strategy-agnostic. Implements PLATFORM_CONSTITUTION Principle 5 (No Trading On
Stale Data) and the §6 Observability heartbeat requirement.

Passive by design: an external loop driver feeds it bar arrivals via
record_bar(), and calls check_data_staleness() / write_heartbeat() each tick.
This module contains no thread or scheduler of its own.
"""
import os
import json
import time
import tempfile
from datetime import datetime, timedelta
from typing import Optional

from core.execution.handler import ExecutionHandler
from core.database.utils.market_hours import MarketHours
from core.alerts.alerter import alerter
from core.logging import setup_logger

logger = setup_logger("watchdog")


class RuntimeWatchdog:
    """Heartbeat writer + data-staleness watchdog for a live trading process."""

    # Data staleness threshold: 5 minutes without a new bar during market hours
    DATA_STALE_THRESHOLD = timedelta(minutes=5)
    # Heartbeat write interval (seconds)
    HEARTBEAT_INTERVAL_S = 10.0

    def __init__(self, execution: ExecutionHandler,
                 heartbeat_path: str = os.path.join("logs", "heartbeat.json")):
        self.execution = execution
        self.heartbeat_path = heartbeat_path

        self._last_bar_timestamp: Optional[datetime] = None
        self._data_stale_alerted = False
        self._data_healthy = True
        self._last_heartbeat_time: float = 0.0

    @property
    def data_healthy(self) -> bool:
        return self._data_healthy

    def record_bar(self) -> None:
        """Relocated bar-arrival hook (was inline in runner._process_symbol).

        Call once whenever a new bar is received so staleness can be measured
        and a recovery transition logged.
        """
        self._last_bar_timestamp = datetime.now()
        if self._data_stale_alerted:
            logger.info("DATA RECOVERED — Bars flowing again.")
            self._data_stale_alerted = False
            self._data_healthy = True

    def check_data_staleness(self) -> None:
        """Detect silent data feed failure during market hours."""
        if self._last_bar_timestamp is None:
            return  # No bar received yet — still in warmup
        if self._data_stale_alerted:
            return  # Already alerted, don't spam

        now = datetime.now()
        if not MarketHours.is_market_open():
            return  # Only check during market hours

        elapsed = now - self._last_bar_timestamp
        if elapsed > self.DATA_STALE_THRESHOLD:
            self._data_stale_alerted = True
            self._data_healthy = False
            mins = elapsed.total_seconds() / 60
            msg = f"DATA STALE — No new bars for {mins:.1f} minutes. Activating soft kill switch."
            logger.critical(msg)
            alerter.critical(msg)
            self.execution.activate_kill_switch(f"Data feed stale ({mins:.1f}m)")

    def write_heartbeat(self, bars_processed: int = 0) -> None:
        """Write heartbeat file atomically for external watchdog monitoring."""
        now_mono = time.time()
        if now_mono - self._last_heartbeat_time < self.HEARTBEAT_INTERVAL_S:
            return
        self._last_heartbeat_time = now_mono

        try:
            heartbeat = {
                "timestamp": datetime.now().isoformat(),
                "market_open": MarketHours.is_market_open(),
                "data_healthy": self._data_healthy,
                "equity": self.execution.metrics.cash_balance,
                "bars_processed": bars_processed,
                "trades_today": self.execution._trades_today,
                "kill_switched": self.execution._kill_switched,
            }
            heartbeat_dir = os.path.dirname(self.heartbeat_path) or "."
            os.makedirs(heartbeat_dir, exist_ok=True)
            # Atomic write: write to temp file then rename
            fd, tmp_path = tempfile.mkstemp(dir=heartbeat_dir, suffix=".tmp")
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(heartbeat, f, indent=2)
                # On Windows, os.replace is atomic within the same volume
                os.replace(tmp_path, self.heartbeat_path)
            except Exception:
                # Clean up temp file if rename failed
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise
        except Exception as e:
            logger.debug(f"Heartbeat write failed: {e}")
