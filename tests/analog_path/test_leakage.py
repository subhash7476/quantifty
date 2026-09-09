import json
import hashlib
from datetime import date
from pathlib import Path

import pytest

from scripts.analog_path import config
from scripts.analog_path.data_layer import load_session

CONFIG_PATH = Path(__file__).resolve().parents[2] / "scripts" / "analog_path" / "config.json"


# --- fence guard -----------------------------------------------------------

def test_fence_guard_allows_train_on_train_date():
    config.require_fence(date(2015, 6, 1), "train")


def test_fence_guard_blocks_wrong_fence():
    with pytest.raises(config.FenceError):
        config.require_fence(date(2020, 6, 1), "train")
    with pytest.raises(config.FenceError):
        config.require_fence(date(2015, 6, 1), "holdout")


def test_sealed_is_locked():
    with pytest.raises(config.FenceError):
        config.require_fence(date(2024, 6, 1), "sealed")


def test_sealed_dates_are_classified_sealed():
    assert config.fence_of(date(2023, 1, 2)) == "sealed"
    assert config.fence_of(date(2026, 9, 1)) == "sealed"
    assert config.fence_of(date(2022, 12, 30)) == "holdout"
    assert config.fence_of(date(2018, 12, 31)) == "train"


# --- a session's state uses only that session's own file --------------------

def test_session_state_derived_only_from_own_day(tmp_path, monkeypatch):
    # Point the loader at an isolated directory containing ONLY the query
    # day's file; state construction must succeed identically, proving no
    # hidden cross-day dependency.
    import scripts.analog_path.data_layer as dl
    src = dl.CANDLE_DIR_1M / "2012-06-04.duckdb"
    dst_dir = tmp_path / "1m"
    dst_dir.mkdir()
    (dst_dir / "2012-06-04.duckdb").write_bytes(src.read_bytes())
    monkeypatch.setattr(dl, "CANDLE_DIR_1M", dst_dir)
    s = dl.load_session(date(2012, 6, 4))
    assert s is not None and s.valid
    assert s.p_1230 == 4794.35


def test_query_day_never_reads_other_files(tmp_path, monkeypatch):
    # With ONLY an unrelated file present, the query day yields no rows —
    # the loader cannot silently borrow another date's bars.
    import scripts.analog_path.data_layer as dl
    src = dl.CANDLE_DIR_1M / "2024-06-03.duckdb"
    dst_dir = tmp_path / "1m"
    dst_dir.mkdir()
    (dst_dir / "2024-06-03.duckdb").write_bytes(src.read_bytes())
    monkeypatch.setattr(dl, "CANDLE_DIR_1M", dst_dir)
    assert dl.load_session(date(2012, 6, 4)) is None


# --- config discipline ------------------------------------------------------

def test_config_sha_matches_canonical_file_content():
    parsed = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":"))
    assert config.CONFIG_SHA256 == hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def test_frozen_grid_is_14_points():
    assert len(config.GRID_TIMES) == 14
    assert [t.strftime("%H:%M") for t in config.GRID_TIMES] == [
        "09:15", "09:30", "09:45", "10:00", "10:15", "10:30", "10:45",
        "11:00", "11:15", "11:30", "11:45", "12:00", "12:15", "12:30"]


def test_frozen_k_values_and_bins():
    assert config.K_VALUES == (5, 10, 20, 50)
    assert config.BIN_EDGES_PCT == [-100.0, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 100.0]
    assert config.DISTANCE == "euclidean"
