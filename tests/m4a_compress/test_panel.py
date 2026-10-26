"""Panel loading: only the hashed BKV-1 dev snapshot, fenced at 2022-12-30."""
import pytest

from scripts.m4a_compress import common as C
from scripts.m4a_compress import panel as PL
from tests.m4a_compress.synth import make_frames


def _write(tmp, panel, cal, memb):
    panel.to_parquet(tmp / "panel_dev.parquet", index=False)
    cal.to_parquet(tmp / "calendar_dev.parquet", index=False)
    memb.to_parquet(tmp / "membership_dev.parquet", index=False)


def test_load_refuses_a_snapshot_whose_hash_is_not_the_frozen_bkv_panel(tmp_path, monkeypatch):
    panel, cal, memb, _ = make_frames(E=4, T=40)
    _write(tmp_path, panel, cal, memb)
    monkeypatch.setattr(C, "SNAPSHOT_DIR", tmp_path)
    with pytest.raises(RuntimeError, match="panel snapshot hash"):
        PL.load_panel()


def test_load_refuses_any_price_after_the_dev_cutoff(tmp_path, monkeypatch):
    panel, cal, memb, _ = make_frames(E=4, T=40, start="2022-12-01")     # runs past 2022-12-30
    _write(tmp_path, panel, cal, memb)
    monkeypatch.setattr(C, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(C, "BKV_PANEL_SHA256", PL.sha256_file(tmp_path / "panel_dev.parquet"))
    with pytest.raises(RuntimeError, match="fence"):
        PL.load_panel()


def test_load_accepts_a_matching_fenced_snapshot(tmp_path, monkeypatch):
    panel, cal, memb, _ = make_frames(E=4, T=40, start="2015-01-05")
    _write(tmp_path, panel, cal, memb)
    monkeypatch.setattr(C, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(C, "BKV_PANEL_SHA256", PL.sha256_file(tmp_path / "panel_dev.parquet"))
    pn = PL.load_panel()
    assert len(pn.entities) == 4
