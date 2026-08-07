"""
DayType facts-publisher tests (DAYTYPE_FACTS_ADOPTION_SPEC §4/§7).

Covers the offline publisher's acceptance contract:
- Determinism: same corpus + same model -> identical facts (byte-for-byte on the
  schema columns).
- Schema + provenance: every row carries model_hash / regime_fact_version /
  trained_on / produced_by; the hash matches the recorded model files.
- Re-run reproducibility: re-running over the same corpus appends nothing new and
  changes nothing (INSERT OR REPLACE idempotency on the (session_date, checkpoint)
  PK) when dates_only is fixed.

Corpus: a fixed slice of the real 1m index store (Nifty 50 + Bank Nifty). Tests
skip when the store is not present in this tree (mirrors tests/msi).

The model files are required for a meaningful run; if models/daytype is missing
the determinism/identity tests skip (provenance would be empty).
"""
from datetime import date
from pathlib import Path

import duckdb
import pytest

import scripts.daytype.publish_facts as pf

REPO = Path(__file__).resolve().parents[2]

CORPUS = [date(2023, 1, 2), date(2023, 1, 3), date(2023, 1, 4), date(2023, 1, 5)]


def _corpus_present() -> bool:
    return all((pf.CANDLE_DIR_1M / f"{d.isoformat()}.duckdb").exists() for d in CORPUS)


def _model_present() -> bool:
    return (REPO / "models" / "daytype" / "logistic_13pm_prod" / "model.pkl").exists()


def _run_publish(db_path: Path):
    return pf.publish(
        CORPUS[0], CORPUS[-1], db_path, produced_by=f"offline@{pf.commit_ref()}",
        dates_only=set(CORPUS), progress_every=0,
    )


def _facts(db_path: Path) -> list:
    con = duckdb.connect(str(db_path), read_only=True)
    rows = con.execute(
        "SELECT session_date, checkpoint, regime, regime_confidence, vix_close, "
        "       regime_fact_version, model_hash, produced_by, trained_on "
        "FROM day_type_facts ORDER BY session_date, checkpoint"
    ).fetchall()
    con.close()
    return rows


@pytest.mark.skipif(not _corpus_present(), reason="real 1m index store not present in this tree")
@pytest.mark.skipif(not _model_present(), reason="models/daytype not present")
def test_offline_publisher_produces_facts_for_corpus(tmp_path):
    db = tmp_path / "facts.duckdb"
    summary = _run_publish(db)
    assert summary["new_rows"] >= 1
    assert summary["model_hash"] == pf.model_hash()
    assert summary["version"] == pf.regime_fact_version()
    rows = _facts(db)
    assert len(rows) == summary["new_rows"]


@pytest.mark.skipif(not _corpus_present(), reason="real 1m index store not present in this tree")
@pytest.mark.skipif(not _model_present(), reason="models/daytype not present")
def test_determinism_same_corpus_same_model_identical_facts(tmp_path):
    db1 = tmp_path / "a.duckdb"
    db2 = tmp_path / "b.duckdb"
    _run_publish(db1)
    _run_publish(db2)
    assert _facts(db1) == _facts(db2)


@pytest.mark.skipif(not _corpus_present(), reason="real 1m index store not present in this tree")
@pytest.mark.skipif(not _model_present(), reason="models/daytype not present")
def test_rerun_reproducibility_idempotent(tmp_path):
    db = tmp_path / "facts.duckdb"
    _run_publish(db)
    rows_before = _facts(db)          # snapshot after first publish
    s2 = _run_publish(db)
    assert s2["new_rows"] == 0        # already present -> nothing appended
    assert _facts(db) == rows_before  # and rows are unchanged


@pytest.mark.skipif(not _corpus_present(), reason="real 1m index store not present in this tree")
@pytest.mark.skipif(not _model_present(), reason="models/daytype not present")
def test_vix_less_session_skipped_not_published(tmp_path, monkeypatch):
    # F2: a session with no VIX close must be counted in skipped_no_vix and must
    # NOT produce a fact row (a NULL-VIX fact is unusable by NiftyShield).
    db = tmp_path / "facts.duckdb"
    first = CORPUS[0]
    monkeypatch.setattr(pf, "vix_close", lambda d: None if d == first else 999.0)
    summary = _run_publish(db)
    assert summary["skipped_no_vix"] >= 1
    sessions = {r[0] for r in _facts(db)}
    assert first not in sessions


@pytest.mark.skipif(not _corpus_present(), reason="real 1m index store not present in this tree")
@pytest.mark.skipif(not _model_present(), reason="models/daytype not present")
def test_schema_and_provenance_columns_populated(tmp_path):
    db = tmp_path / "facts.duckdb"
    _run_publish(db)
    rows = _facts(db)
    assert rows
    for row in rows:
        session, cp, regime, conf, vix, ver, mhash, produced, trained = row
        assert cp == "13pm"
        assert regime in {"BullTrend", "BearTrend", "Choppy"}
        assert 0.0 <= conf <= 1.0
        assert ver == pf.regime_fact_version()
        assert mhash == pf.model_hash()
        assert produced.startswith("offline@")
        assert trained == pf.TRAINED_ON
        assert vix is None or 0.0 < vix < 100.0


def test_model_hash_is_content_based():
    if not _model_present():
        pytest.skip("models/daytype not present")
    h = pf.model_hash()
    assert len(h) == 64
    assert h == pf.model_hash()          # stable across calls
    # Tamper with the model file content -> hash changes (content identity).
    target = pf.MODEL_DIR / "metadata.json"
    original = target.read_bytes()
    try:
        target.write_bytes(original + b"x")
        assert pf.model_hash() != h
    finally:
        target.write_bytes(original)


def test_regime_fact_version_reflects_metadata():
    if not _model_present():
        pytest.skip("models/daytype not present")
    assert pf.regime_fact_version() == "dt-v2.0-train_thru2025"


# --------------------------------------------------------------------------- #
# Live 13:00 publisher (Stage-2 prerequisite; same engine path).
# --------------------------------------------------------------------------- #
def _live_publish(tmp_path: Path, d: date):
    import scripts.daytype.publish_live_fact as live
    return live.publish_live(tmp_path / "live.duckdb", today=d)


@pytest.mark.skipif(not _corpus_present(), reason="real 1m index store not present in this tree")
@pytest.mark.skipif(not _model_present(), reason="models/daytype not present")
def test_live_publisher_matches_offline_for_same_session(tmp_path):
    d = CORPUS[0]
    db = tmp_path / "offline.duckdb"
    _run_publish(db)
    off = _facts(db)[0]                      # session_date, checkpoint, regime, conf, vix, ...
    res = _live_publish(tmp_path, d)
    assert res["ready"] is True
    assert res["regime"] == off[2]
    assert abs(res["confidence"] - off[3]) < 1e-9
    assert res["produced_by"].startswith("live@")
    assert res["vix"] == off[4]


@pytest.mark.skipif(not _corpus_present(), reason="real 1m index store not present in this tree")
@pytest.mark.skipif(not _model_present(), reason="models/daytype not present")
def test_live_publisher_upserts_into_facts_db(tmp_path):
    d = CORPUS[0]
    db = tmp_path / "live.duckdb"
    _live_publish(tmp_path, d)
    con = duckdb.connect(str(db), read_only=True)
    row = con.execute("SELECT checkpoint, regime, produced_by, trained_on FROM day_type_facts").fetchone()
    con.close()
    assert row[0] == "13pm"
    assert row[2].startswith("live@")
    assert row[3] == pf.TRAINED_ON


def test_live_publisher_not_ready_without_data(tmp_path):
    import scripts.daytype.publish_live_fact as live
    future = date(2099, 1, 2)                # no store file -> not ready
    res = live.publish_live(tmp_path / "live.duckdb", today=future)
    assert res["ready"] is False
