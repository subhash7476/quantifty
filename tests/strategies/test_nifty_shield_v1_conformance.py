"""
NiftyShield v1 — Stage-1 conformance suite (NIFTY_SHIELD_STAGE1_IMPLEMENTATION_PROMPT §2.C).

Certifies the re-expressed dumb SignalSource against MM12.2 Layers 1+2:
- run_conformance(...) over the committed recorded corpus (bars + facts);
- the same suite over GuardedSignalSource(nifty_shield_v1) (MM12.4 mandatory);
- replay-twice determinism: byte-identical signal streams;
- session-level emission contract (structure, legs, risk metadata).

The corpus is the committed fixtures under strategies/nifty_shield_v1/corpus/
(bars.csv = Nifty 50 1m, facts.csv = 13pm regime facts). A temp DuckDB is
materialised from the committed facts CSV so the source reads facts exactly as
it does in production (DuckDB read-only), with no dependency on the gitignored
store.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, time
from pathlib import Path

import duckdb
import pytest

from core.events import OHLCVBar, SignalType
from core.runtime.conformance import run_conformance
from core.runtime.guarded_signal_source import GuardedSignalSource

from strategies.nifty_shield_v1 import build_signal_source
from strategies.nifty_shield_v1.config import config_hash

REPO = Path(__file__).resolve().parents[2]
CORPUS = REPO / "strategies" / "nifty_shield_v1" / "corpus"
PACKAGE_ROOT = REPO / "strategies" / "nifty_shield_v1"
BARS_CSV = CORPUS / "bars.csv"
FACTS_CSV = CORPUS / "facts.csv"

CORPUS_SESSIONS = ["2023-01-02", "2023-01-03", "2023-01-04",
                   "2023-01-05", "2023-01-06", "2023-01-09"]


def _bars() -> list:
    bars = []
    with open(BARS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            bars.append(OHLCVBar(
                symbol="NSE_INDEX|Nifty 50",
                timestamp=datetime.fromisoformat(row["timestamp"]),
                open=float(row["open"]), high=float(row["high"]),
                low=float(row["low"]), close=float(row["close"]),
                volume=float(row["volume"]),
            ))
    return bars


def _materialise_facts_db(tmp_path: Path) -> Path:
    """Build a temp DuckDB from the committed facts.csv (same schema as the
    production day_type_facts store)."""
    db = tmp_path / "facts.duckdb"
    con = duckdb.connect(str(db))
    con.execute("""
        CREATE TABLE day_type_facts (
            session_date DATE, checkpoint VARCHAR, regime VARCHAR,
            regime_confidence DOUBLE, vix_close DOUBLE,
            regime_fact_version VARCHAR, model_hash VARCHAR,
            produced_by VARCHAR, trained_on VARCHAR
        )
    """)
    rows = []
    with open(FACTS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append((row["session_date"], row["checkpoint"], row["regime"],
                         float(row["regime_confidence"]),
                         float(row["vix_close"]) if row["vix_close"] else None,
                         row["regime_fact_version"], row["model_hash"],
                         row["produced_by"], row["trained_on"]))
    con.executemany(
        "INSERT INTO day_type_facts VALUES (?,?,?,?,?,?,?,?,?)", rows)
    con.close()
    return db


@pytest.fixture(scope="module")
def facts_db(tmp_path_factory) -> Path:
    return _materialise_facts_db(tmp_path_factory.mktemp("facts"))


@pytest.fixture(scope="module")
def bars() -> list:
    return _bars()


def _factory(facts_db: Path):
    cfg = {"facts_db_path": str(facts_db)}
    return lambda: build_signal_source(cfg)


def _drive(factory) -> list:
    src = factory()
    src.on_start()
    out = []
    for bar in _bars():
        out.extend(src.on_bar(bar))
    src.on_stop()
    return out


# --------------------------------------------------------------------------- #
# Layer 1 + Layer 2 conformance (raw + guard-wrapped).
# --------------------------------------------------------------------------- #
def test_conformant_layers_1_and_2(facts_db, bars):
    run_conformance(_factory(facts_db), bars, package_root=PACKAGE_ROOT,
                    latency_budget_s=0.05)


def test_conformant_guarded_wrapper(facts_db, bars):
    run_conformance(
        lambda: GuardedSignalSource(_factory(facts_db)()),
        bars, package_root=PACKAGE_ROOT, latency_budget_s=0.05)


# --------------------------------------------------------------------------- #
# Replay-twice determinism (MM12.1 §6).
# --------------------------------------------------------------------------- #
def test_replay_twice_byte_identical_streams(facts_db):
    first = _drive(_factory(facts_db))
    second = _drive(_factory(facts_db))
    assert first == second
    assert len(first) == 16          # 6 sessions: iron_fly x2 (4) + spread x4 (2)


# --------------------------------------------------------------------------- #
# Session-level emission contract (decomposition §3.2 / §3.3).
# --------------------------------------------------------------------------- #
def test_one_structure_per_session_distinct_group_ids(facts_db):
    signals = _drive(_factory(facts_db))
    by_date = {}
    for s in signals:
        d = s.timestamp.date().isoformat()
        by_date.setdefault(d, []).append(s)
    assert sorted(by_date.keys()) == CORPUS_SESSIONS
    for d, sigs in by_date.items():
        structures = {s.metadata["structure"] for s in sigs}
        groups = {s.metadata["group_id"] for s in sigs}
        assert len(structures) == 1
        assert len(groups) == 1     # all legs of one structure share group_id


def test_leg_encoding_and_risk_metadata(facts_db):
    signals = _drive(_factory(facts_db))
    for s in signals:
        assert s.strategy_id == "nifty_shield_v1"
        assert s.signal_type in (SignalType.SELL, SignalType.BUY)
        assert s.timestamp.time() == time(13, 0)
        md = s.metadata
        for key in ("group_id", "structure", "leg_role", "strike", "expiry",
                    "option_type", "base_lots", "regime_mult", "vix_reduce",
                    "sl_distance", "risk_r", "exit"):
            assert key in md, f"missing metadata key {key}"
        assert md["sl_distance"] > 0 and md["risk_r"] > 0
        assert md["exit"]["tp_pct"] == 0.50
        assert md["exit"]["sl_mult"] == 2.0
        assert md["exit"]["hard_exit"] == "15:15"
        assert s.context is not None
        assert s.context.regime_state in {"BullTrend", "BearTrend", "Choppy"}
        assert s.context.session_type == "PM"


def test_iron_fly_emits_four_legs(facts_db):
    signals = _drive(_factory(facts_db))
    iron_fly = [s for s in signals if s.metadata["structure"] == "iron_fly"]
    assert len(iron_fly) == 8        # 2 sessions x 4 legs
    roles = {s.metadata["leg_role"] for s in iron_fly}
    assert roles == {"short_ce", "short_pe", "wing_ce", "wing_pe"}
    # shorts are SELL, wings are BUY
    for s in iron_fly:
        if s.metadata["leg_role"].startswith("wing"):
            assert s.signal_type is SignalType.BUY
        else:
            assert s.signal_type is SignalType.SELL


def test_config_hash_is_stable_and_excludes_runtime_seams():
    base = build_signal_source({})._cfg
    h1 = config_hash(base)
    h2 = config_hash({**base, "facts_db_path": "/elsewhere/facts.duckdb"})
    assert h1 == h2                   # runtime seam not part of the identity
    assert len(h1) == 64
