"""Tests for the NiftyShield PAPER wall blueprint (flask_app/blueprints/nifty_shield.py).

Covers the read-helper layer against a synthetic data root (no real window
data touched) and the JSON endpoints on a minimal Flask app. The blueprint is
read-only by contract — the tests assert it renders facts and never writes.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import duckdb
import pytest
from flask import Flask

import flask_app.blueprints.nifty_shield as ns

ROOT = Path(__file__).resolve().parents[2]


def _write_journal(path: Path, events) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


def _event(etype: str, *, session="2026-08-13", group_id="g1", **md):
    return {
        "timestamp": f"{session}T13:01:00.000000+05:30",
        "event_type": etype,
        "severity": "INFO",
        "source_component": "NiftyShieldExecutionHandler",
        "message": etype.lower(),
        "metadata": dict(md, group_id=group_id, session=session),
    }


def _make_window(tmp_path: Path):
    journal = [
        _event("ENTRY_MARGIN", structure="short_straddle", group_id="g1",
               leg_symbols=["NIFTY18AUG2624350CE", "NIFTY18AUG2624350PE"],
               margin_total=185000.0, span=170000.0, elm=15000.0,
               engine="NseMarginEngine", lots=2, lot_size=75, risk_r=30000.0),
        _event("STRUCTURE_CLOSE", group_id="g1", reason="exit time"),
        _event("ENTRY_SKIPPED", group_id="g2", structure="iron_fly",
               reason="missing option marks (E7-4, no synthetic fallback)",
               missing_legs=["NIFTY18AUG2624350CE"]),
    ]
    _write_journal(tmp_path / "journal.jsonl", journal)
    trades_dir = tmp_path / "trading"
    trades_dir.mkdir()
    con = sqlite3.connect(trades_dir / "trading.db")
    con.execute("CREATE TABLE trades (symbol TEXT, side TEXT, quantity REAL, "
                "entry_price REAL, pnl REAL, fees REAL, timestamp TEXT)")
    con.executemany(
        "INSERT INTO trades VALUES (?, ?, ?, ?, ?, ?, ?)",
        [("NIFTY18AUG2624350CE", "SELL", 150, 210.0, 0.0, 0.0, "2026-08-13T13:02:00"),
         ("NIFTY18AUG2624350PE", "SELL", 150, 190.0, 0.0, 0.0, "2026-08-13T13:02:00"),
         ("NIFTY18AUG2624350CE", "BUY", 150, 180.0, 4500.0, 120.0, "2026-08-13T15:15:00"),
         ("NIFTY18AUG2624350PE", "BUY", 150, 165.0, 3750.0, 120.0, "2026-08-13T15:15:00")])
    con.commit()
    con.close()
    return journal


def _patch_root(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(ns, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(ns, "CHAIN_DB", tmp_path / "missing_chain.duckdb")
    monkeypatch.setattr(ns, "CHAIN_HB", tmp_path / "missing_poller_hb.json")
    monkeypatch.setattr(ns, "CHAIN_POLLER_PID", tmp_path / "missing.pid")
    monkeypatch.setattr(ns, "SESSION_PID", tmp_path / "missing.pid")
    monkeypatch.setattr(ns, "ORCHESTRATOR_PID", tmp_path / "missing.pid")
    monkeypatch.setattr(ns, "STOP_FILE", tmp_path / "STOP")
    monkeypatch.setattr(ns, "SPAN_DIR", tmp_path / "span")


# ------------------------------------------------------------------ helpers

def test_sanitize_replaces_nonfinite_floats():
    out = ns._sanitize({"a": float("inf"), "b": {"c": float("-inf")}, "d": [1.0, float("nan")], "e": 1})
    assert out["a"] is None
    assert out["b"]["c"] is None
    assert out["d"] == [1.0, None]
    assert out["e"] == 1


def test_pnl_series_cumulative_in_session_order():
    structs = [
        {"session": "2026-08-11", "closed": True, "pnl_rs": 100.0},
        {"session": "2026-08-12", "closed": False, "pnl_rs": 50.0},
        {"session": "2026-08-12", "closed": True, "pnl_rs": -30.0},
        {"session": "2026-08-10", "closed": True, "pnl_rs": 5.0},
    ]
    series = ns._pnl_series(structs)
    assert [s["cum"] for s in series] == [5.0, 105.0, 75.0]
    assert series[1]["session"] == "2026-08-11"


def test_merged_structures_entered_skipped_and_fills(monkeypatch, tmp_path):
    _patch_root(monkeypatch, tmp_path)
    _make_window(tmp_path)

    ev = ns._window_evidence()
    merged = ns._merged_structures(ev)

    by_gid = {s["group_id"]: s for s in merged}
    assert set(by_gid) == {"g1", "g2"}
    entered = by_gid["g1"]
    assert entered["status"] == "entered"
    assert entered["closed"] is True
    assert entered["exit_reason"] == "exit time"
    assert entered["pnl_rs"] == 8250.0
    assert entered["r"] == pytest.approx(0.275)
    assert entered["margin_rs"] == 185000.0
    assert entered["filled_legs"] == entered["leg_symbols"]
    assert sum(len(f) for f in entered["fills"]) == 4
    skipped = by_gid["g2"]
    assert skipped["status"] == "skipped"
    assert skipped["reason"].startswith("missing option marks")
    assert skipped["pnl_rs"] == 0.0
    assert skipped["r"] is None


def test_latest_fact_reads_and_selects_structure(monkeypatch, tmp_path):
    _patch_root(monkeypatch, tmp_path)
    con = duckdb.connect(str(tmp_path / "facts.duckdb"))
    con.execute("CREATE TABLE day_type_facts (session_date DATE, checkpoint VARCHAR, "
                "regime VARCHAR, regime_confidence DOUBLE, vix_close DOUBLE, "
                "vix_at_checkpoint DOUBLE, regime_fact_version VARCHAR, "
                "model_hash VARCHAR, produced_by VARCHAR, trained_on VARCHAR)")
    con.execute("INSERT INTO day_type_facts VALUES (DATE '2026-08-14', '13pm', "
                "'Choppy', 0.7952, 11.5, 11.33, 'dt-v2.0', 'abcdef1234567890', "
                "'live@test', 'TRAIN')")
    con.close()

    fact = ns._latest_fact()
    assert fact["session_date"] == "2026-08-14"
    assert fact["regime"] == "Choppy"
    assert fact["vix"] == 11.33
    assert fact["vix_source"] == "13:00 checkpoint"
    assert fact["structure"] == "short_straddle"     # Choppy, VIX <= 14
    assert fact["model_hash"] == "abcdef12"


def test_chain_summary_missing_cache_is_graceful(monkeypatch, tmp_path):
    _patch_root(monkeypatch, tmp_path)
    summary = ns._chain_summary()
    assert summary["available"] is False
    assert summary["error"] == "chain cache not present"
    assert summary["strikes"] == []


def test_live_status_reads_stop_and_pids(monkeypatch, tmp_path):
    _patch_root(monkeypatch, tmp_path)
    status = ns._live_status()
    assert status["stop_present"] is False
    assert status["processes"] == {"session": False, "orchestrator": False, "poller": False}
    assert status["heartbeat"]["present"] is False

    (tmp_path / "STOP").write_text("", encoding="utf-8")
    assert ns._live_status()["stop_present"] is True


# ------------------------------------------------------------------- routes

def _client():
    app = Flask(__name__, template_folder=str(ROOT / "flask_app" / "templates"))
    app.config["SECRET_KEY"] = "test"
    app.register_blueprint(ns.nifty_shield_bp)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["username"] = "tester"
    return client


def test_window_endpoint_empty_root(monkeypatch, tmp_path):
    _patch_root(monkeypatch, tmp_path)
    client = _client()
    resp = client.get("/nifty-shield/api/window")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["exists"] is False
    assert payload["structures"] == []


def test_window_endpoint_with_data(monkeypatch, tmp_path):
    _patch_root(monkeypatch, tmp_path)
    _make_window(tmp_path)
    client = _client()
    resp = client.get("/nifty-shield/api/window")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["exists"] is True
    assert {s["group_id"] for s in payload["structures"]} == {"g1", "g2"}
    assert payload["journal"][0]["event_type"] == "ENTRY_SKIPPED"  # newest first
    assert payload["metrics"]["profit_factor"] is None  # inf sanitized away


def test_session_endpoint_requires_date(monkeypatch, tmp_path):
    _patch_root(monkeypatch, tmp_path)
    client = _client()
    assert client.get("/nifty-shield/api/session").status_code == 400


def test_marks_and_live_endpoints_respond(monkeypatch, tmp_path):
    _patch_root(monkeypatch, tmp_path)
    client = _client()
    marks = client.get("/nifty-shield/api/marks")
    assert marks.status_code == 200
    assert "available" in marks.get_json()
    live = client.get("/nifty-shield/api/live")
    assert live.status_code == 200
    assert "stop_present" in live.get_json()
