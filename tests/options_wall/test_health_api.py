"""The health endpoint reads the heartbeat file, never the results DB."""
import json
from datetime import datetime, timedelta

import pytest

from flask_app.blueprints import options_wall as bp


def _write_hb(path, *, status, age_s):
    ts = (datetime.now() - timedelta(seconds=age_s)).isoformat()
    path.write_text(json.dumps({
        "last_snapshot": ts, "rows": {"NIFTY": 74}, "status": status,
        "steps": {"NIFTY": {"executor": {"ok": status == "OK"}}},
    }), encoding="utf-8")


def test_reports_degraded(tmp_path, monkeypatch):
    hb = tmp_path / "hb.json"
    _write_hb(hb, status="DEGRADED", age_s=2)
    monkeypatch.setattr(bp, "WALL_HEARTBEAT_PATH", hb)
    payload = bp._health_payload()
    assert payload["status"] == "DEGRADED"
    assert payload["stale"] is False
    assert payload["steps"]["NIFTY"]["executor"]["ok"] is False


def test_stale_heartbeat_is_unknown(tmp_path, monkeypatch):
    hb = tmp_path / "hb.json"
    _write_hb(hb, status="OK", age_s=120)
    monkeypatch.setattr(bp, "WALL_HEARTBEAT_PATH", hb)
    payload = bp._health_payload()
    assert payload["stale"] is True
    assert payload["status"] == "UNKNOWN"


def test_missing_heartbeat_is_unknown(tmp_path, monkeypatch):
    monkeypatch.setattr(bp, "WALL_HEARTBEAT_PATH", tmp_path / "absent.json")
    payload = bp._health_payload()
    assert payload["status"] == "UNKNOWN"
    assert payload["steps"] == {}


def test_heartbeat_without_a_timestamp_is_unknown(tmp_path, monkeypatch):
    hb = tmp_path / "hb.json"
    hb.write_text(json.dumps({"rows": {}, "status": "OK"}), encoding="utf-8")
    monkeypatch.setattr(bp, "WALL_HEARTBEAT_PATH", hb)
    payload = bp._health_payload()
    assert payload["status"] == "UNKNOWN"
    assert payload["stale"] is True
