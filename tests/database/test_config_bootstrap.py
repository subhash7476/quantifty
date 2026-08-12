"""F5 (ops shakedown 2026-08-10): the config schema (incl. `websocket_status`)
was never bootstrapped at runtime, so the ingestor's bare INSERT errored every
1.5s. `bootstrap_config_db` applies the idempotent config schema at startup."""
from __future__ import annotations

import sqlite3

from core.database.manager import DatabaseManager
from core.database.schema import bootstrap_config_db


def _config_conn(tmp_path) -> sqlite3.Connection:
    return sqlite3.connect(str(tmp_path / "config" / "config.db"))


def test_bootstrap_config_db_creates_websocket_status(tmp_path):
    DatabaseManager.reset_instance()
    dm = DatabaseManager(data_root=tmp_path)
    bootstrap_config_db(dm)
    con = _config_conn(tmp_path)
    try:
        tables = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        con.close()
    assert "websocket_status" in tables


def test_bootstrap_config_db_is_idempotent(tmp_path):
    DatabaseManager.reset_instance()
    dm = DatabaseManager(data_root=tmp_path)
    bootstrap_config_db(dm)
    bootstrap_config_db(dm)               # second run must not raise or duplicate
    con = _config_conn(tmp_path)
    try:
        n_roles = con.execute("SELECT COUNT(*) FROM roles").fetchone()[0]
        n_status = con.execute(
            "SELECT COUNT(*) FROM websocket_status").fetchone()[0]
    finally:
        con.close()
    assert n_roles == 2                   # seed not duplicated (ON CONFLICT)
    assert n_status == 0                  # status rows are written by the ingestor
