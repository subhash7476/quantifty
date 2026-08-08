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
import numpy as np
import pandas as pd
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


def _craft_session_bars(seed: int, base: float, min_count: int = 226) -> pd.DataFrame:
    """A deterministic 9:15..13:00 1m session (226 bars at 1-min cadence)."""
    rng = np.random.default_rng(seed)
    closes = base + np.cumsum(rng.normal(0, 3, min_count))
    opens = np.concatenate([[closes[0]], closes[:-1]])
    highs = np.maximum(opens, closes) + rng.uniform(0.1, 2.0, min_count)
    lows = np.minimum(opens, closes) - rng.uniform(0.1, 2.0, min_count)
    times = pd.date_range("2023-01-02 09:15", periods=min_count, freq="1min")
    return pd.DataFrame({
        "timestamp": times,
        "open": opens, "high": highs, "low": lows, "close": closes,
        "volume": np.full(min_count, 1000.0),
    })


def _write_candle_db(path: Path, rows: dict) -> None:
    """Write a candles table (symbol, timestamp, OHLCV) with all symbols at once."""
    con = duckdb.connect(str(path))
    con.execute("""
        CREATE TABLE IF NOT EXISTS candles (
            symbol VARCHAR, timestamp TIMESTAMP, open DOUBLE, high DOUBLE,
            low DOUBLE, close DOUBLE, volume BIGINT
        )
    """)
    for symbol, df in rows.items():
        con.executemany(
            "INSERT INTO candles VALUES (?,?,?,?,?,?,?)",
            [(symbol, ts.to_pydatetime(), float(o), float(h), float(l),
              float(c), int(v))
             for ts, o, h, l, c, v in zip(
                 df["timestamp"], df["open"], df["high"], df["low"],
                 df["close"], df["volume"])],
        )
    con.close()


def _point_live_at(temp_1m: Path, temp_1d: Path, monkeypatch) -> None:
    """Point the live publisher's data sources at synthetic per-day stores."""
    import scripts.daytype.publish_live_fact as live
    monkeypatch.setattr(live, "CANDLE_DIR_1M", temp_1m)
    monkeypatch.setattr(live, "LIVE_BUFFER", temp_1m.parent / "no_live_buffer.duckdb")
    monkeypatch.setattr(pf, "CANDLE_DIR_1M", temp_1m)
    monkeypatch.setattr(pf, "CANDLE_DIR_1D", temp_1d)


@pytest.mark.skipif(not _model_present(), reason="models/daytype not present")
def test_live_offline_parity_shared_columns_and_vix_per_ds2_3(tmp_path, monkeypatch):
    """§4D parity: a live fact and an offline fact over identical session bars are
    byte-identical on all shared columns (regime, confidence, provenance triple);
    VIX per DS2-3 — live carries the intraday 13:00 value in `vix_at_checkpoint`
    (vix_close NULL), offline carries the EOD value in `vix_close`."""
    d = date(2023, 1, 2)
    nf = _craft_session_bars(seed=1, base=24000.0)
    bn = _craft_session_bars(seed=2, base=52000.0)
    vix = _craft_session_bars(seed=3, base=14.0)
    vix_at_13 = float(vix["close"].iloc[-1])
    eod_vix = 16.7

    candle_dir = tmp_path / "candles_1m"
    day_dir = tmp_path / "candles_1d"
    candle_dir.mkdir()
    day_dir.mkdir()
    _write_candle_db(candle_dir / f"{d.isoformat()}.duckdb", {
        pf.NF_SYMBOL: nf, pf.BN_SYMBOL: bn, pf.VIX_SYMBOL: vix,
    })
    _write_candle_db(day_dir / f"{d.isoformat()}.duckdb", {
        pf.VIX_SYMBOL: pd.DataFrame({
            "timestamp": [pd.Timestamp("2023-01-02 15:30")],
            "open": [eod_vix], "high": [eod_vix], "low": [eod_vix],
            "close": [eod_vix], "volume": [0],
        }),
    })
    _point_live_at(candle_dir, day_dir, monkeypatch)

    off_db = tmp_path / "offline.duckdb"
    pf.publish(d, d, off_db, produced_by=f"offline@{pf.commit_ref()}",
               dates_only={d}, progress_every=0)
    live_res = _live_publish(tmp_path, d)
    assert live_res["ready"] is True
    assert live_res["vix_at_checkpoint"] == pytest.approx(vix_at_13)

    con = duckdb.connect(str(off_db), read_only=True)
    off = con.execute(
        "SELECT regime, regime_confidence, vix_close, vix_at_checkpoint, "
        "       regime_fact_version, model_hash, trained_on "
        "FROM day_type_facts WHERE session_date = ?", [d]
    ).fetchone()
    con.close()
    live_row = None
    con = duckdb.connect(str(tmp_path / "live.duckdb"), read_only=True)
    live_row = con.execute(
        "SELECT regime, regime_confidence, vix_close, vix_at_checkpoint, "
        "       regime_fact_version, model_hash, trained_on "
        "FROM day_type_facts WHERE session_date = ?", [d]
    ).fetchone()
    con.close()
    assert live_row is not None

    # Shared columns byte-identical (vix_close/vix_at_checkpoint are the DS2-3
    # divergence, asserted explicitly below — they are NOT shared columns).
    assert live_row[0] == off[0]                       # regime
    assert live_row[1] == off[1]                       # regime_confidence
    assert live_row[4] == off[4]                       # regime_fact_version
    assert live_row[5] == off[5]                       # model_hash
    assert live_row[6] == off[6]                       # trained_on
    # VIX per DS2-3: live has the intraday checkpoint value, NULL EOD close.
    assert off[2] == pytest.approx(eod_vix)            # offline EOD vix_close
    assert off[3] is None                              # offline has no checkpoint VIX
    assert live_row[2] is None                         # live has no EOD close
    assert live_row[3] == pytest.approx(vix_at_13)     # live checkpoint VIX


@pytest.mark.skipif(not _model_present(), reason="models/daytype not present")
def test_vix_at_checkpoint_reads_last_1m_close_before_13_00(tmp_path, monkeypatch):
    """DS2-3: the live publisher's VIX is the India VIX 1m close at/before 13:00,
    from the same per-day 1m store shape used for NF/BN — never the EOD 1d store."""
    import scripts.daytype.publish_live_fact as live
    d = date(2023, 1, 2)
    vix = _craft_session_bars(seed=3, base=14.0)
    last_close = float(vix["close"].iloc[-1])
    candle_dir = tmp_path / "candles_1m"
    candle_dir.mkdir()
    _write_candle_db(candle_dir / f"{d.isoformat()}.duckdb", {pf.VIX_SYMBOL: vix})
    monkeypatch.setattr(live, "CANDLE_DIR_1M", candle_dir)
    monkeypatch.setattr(live, "LIVE_BUFFER", tmp_path / "no_live_buffer.duckdb")
    assert live.vix_at_checkpoint(d) == pytest.approx(last_close)


@pytest.mark.skipif(not _corpus_present(), reason="real 1m index store not present in this tree")
@pytest.mark.skipif(not _model_present(), reason="models/daytype not present")
def test_live_publisher_matches_offline_regime_on_real_session(tmp_path, monkeypatch):
    """The live publisher over the real corpus NF/BN bars produces the same
    regime/confidence as the offline publisher (parity on the engine path);
    VIX now needs the intraday 1m series, so it is supplied by the seam."""
    import scripts.daytype.publish_live_fact as live
    d = CORPUS[0]
    db = tmp_path / "offline.duckdb"
    _run_publish(db)
    off = _facts(db)[0]                      # regime, conf at index 2/3
    monkeypatch.setattr(live, "vix_at_checkpoint", lambda day: 13.5)
    res = _live_publish(tmp_path, d)
    assert res["ready"] is True
    assert res["regime"] == off[2]
    assert abs(res["confidence"] - off[3]) < 1e-9
    assert res["produced_by"].startswith("live@")
    assert res["vix_at_checkpoint"] == 13.5


@pytest.mark.skipif(not _corpus_present(), reason="real 1m index store not present in this tree")
@pytest.mark.skipif(not _model_present(), reason="models/daytype not present")
def test_live_fact_carries_vix_at_checkpoint_and_null_vix_close(tmp_path, monkeypatch):
    """A live row's meaning never depends on produced_by (DS2-3): it carries the
    intraday value in vix_at_checkpoint and leaves the EOD vix_close NULL."""
    import scripts.daytype.publish_live_fact as live
    d = CORPUS[0]
    monkeypatch.setattr(live, "vix_at_checkpoint", lambda day: 13.5)
    db = tmp_path / "live.duckdb"
    _live_publish(tmp_path, d)
    con = duckdb.connect(str(db), read_only=True)
    row = con.execute(
        "SELECT checkpoint, regime, produced_by, trained_on, "
        "       vix_close, vix_at_checkpoint "
        "FROM day_type_facts").fetchone()
    con.close()
    assert row[0] == "13pm"
    assert row[2].startswith("live@")
    assert row[3] == pf.TRAINED_ON
    assert row[4] is None                        # vix_close NULL on live rows
    assert row[5] == 13.5                        # intraday checkpoint VIX


@pytest.mark.skipif(not _corpus_present(), reason="real 1m index store not present in this tree")
@pytest.mark.skipif(not _model_present(), reason="models/daytype not present")
def test_live_publisher_not_ready_without_intraday_vix(tmp_path, monkeypatch):
    """F2 / DS2-4: a session with no India VIX at 13:00 writes nothing — the live
    publisher reports not-ready and no fact row exists."""
    import scripts.daytype.publish_live_fact as live
    d = CORPUS[0]
    monkeypatch.setattr(live, "vix_at_checkpoint", lambda day: None)
    db = tmp_path / "live.duckdb"
    res = _live_publish(tmp_path, d)
    assert res["ready"] is False
    assert "VIX" in res["reason"]
    assert not db.exists() or duckdb.connect(str(db), read_only=True).execute(
        "SELECT COUNT(*) FROM day_type_facts").fetchone()[0] == 0


def test_live_publisher_not_ready_without_data(tmp_path):
    import scripts.daytype.publish_live_fact as live
    future = date(2099, 1, 2)                # no store file -> not ready
    res = live.publish_live(tmp_path / "live.duckdb", today=future)
    assert res["ready"] is False
