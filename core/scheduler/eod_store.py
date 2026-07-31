"""SQLite control store for the EOD automation worker.

SQLite (not DuckDB) because Flask and the worker are separate processes that
both write: DuckDB takes an exclusive file lock and would raise intermittent
lock errors. WAL mode makes concurrent reader/writer access safe.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

TERMINAL_OUTCOMES = frozenset({"success", "holiday", "exhausted", "chain_failed"})


class EodStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as con:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("""
                CREATE TABLE IF NOT EXISTS eod_automation (
                    id               INTEGER PRIMARY KEY CHECK (id = 1),
                    enabled          INTEGER NOT NULL DEFAULT 0,
                    run_now          INTEGER NOT NULL DEFAULT 0,
                    updated_at       TEXT,
                    worker_heartbeat TEXT,
                    worker_pid       INTEGER
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS eod_run_log (
                    run_date    TEXT NOT NULL,
                    attempt     INTEGER NOT NULL,
                    started_at  TEXT,
                    finished_at TEXT,
                    phase       TEXT,
                    outcome     TEXT,
                    detail      TEXT,
                    PRIMARY KEY (run_date, attempt)
                )
            """)
            con.execute("INSERT OR IGNORE INTO eod_automation (id) VALUES (1)")

    def _conn(self):
        con = sqlite3.connect(str(self.db_path), timeout=30)
        con.row_factory = sqlite3.Row
        return con

    def is_enabled(self) -> bool:
        with self._conn() as con:
            return bool(con.execute("SELECT enabled FROM eod_automation WHERE id=1").fetchone()[0])

    def set_enabled(self, value: bool) -> None:
        with self._conn() as con:
            con.execute("UPDATE eod_automation SET enabled=?, updated_at=? WHERE id=1",
                        [int(value), datetime.now().isoformat()])

    def heartbeat(self, pid: int) -> None:
        with self._conn() as con:
            con.execute("UPDATE eod_automation SET worker_heartbeat=?, worker_pid=? WHERE id=1",
                        [datetime.now().isoformat(), pid])

    def get_heartbeat(self) -> tuple[str | None, int | None]:
        with self._conn() as con:
            row = con.execute(
                "SELECT worker_heartbeat, worker_pid FROM eod_automation WHERE id=1").fetchone()
            return row[0], row[1]

    def request_run_now(self) -> None:
        with self._conn() as con:
            con.execute("UPDATE eod_automation SET run_now=1 WHERE id=1")

    def consume_run_now(self) -> bool:
        with self._conn() as con:
            row = con.execute("SELECT run_now FROM eod_automation WHERE id=1").fetchone()
            if not row[0]:
                return False
            con.execute("UPDATE eod_automation SET run_now=0 WHERE id=1")
            return True

    def record(self, run_date: date, attempt: int, phase: str, outcome: str, detail: str) -> None:
        now = datetime.now().isoformat()
        with self._conn() as con:
            existing = con.execute(
                "SELECT started_at FROM eod_run_log WHERE run_date=? AND attempt=?",
                [run_date.isoformat(), attempt]).fetchone()
            started = existing[0] if existing else now
            con.execute("""
                INSERT OR REPLACE INTO eod_run_log
                    (run_date, attempt, started_at, finished_at, phase, outcome, detail)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [run_date.isoformat(), attempt, started, now, phase, outcome, detail])

    def attempts_today(self, run_date: date) -> list[dict]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT * FROM eod_run_log WHERE run_date=? AND attempt >= 1 ORDER BY attempt",
                [run_date.isoformat()]).fetchall()
            return [dict(r) for r in rows]

    def last_attempt_started(self, run_date: date) -> datetime | None:
        attempts = self.attempts_today(run_date)
        if not attempts:
            return None
        return datetime.fromisoformat(attempts[-1]["started_at"])

    def last_attempt_finished(self, run_date: date) -> datetime | None:
        attempts = self.attempts_today(run_date)
        if not attempts:
            return None
        return datetime.fromisoformat(attempts[-1]["finished_at"])

    def is_date_terminal(self, run_date: date) -> bool:
        return any(a["outcome"] in TERMINAL_OUTCOMES for a in self.attempts_today(run_date))

    def latest_run(self) -> dict | None:
        with self._conn() as con:
            row = con.execute(
                "SELECT * FROM eod_run_log ORDER BY started_at DESC LIMIT 1").fetchone()
            return dict(row) if row else None
