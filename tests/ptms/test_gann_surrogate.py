"""Surrogate tests on synthetic panels only. No store is read."""

import numpy as np
import pytest

from scripts.ptms.gann import surrogate
from scripts.ptms.gann.constants import N_SURROGATES, SIZE_CHECK_PANELS


def panel(seed=0, T=300, N=6, gaps=0.0):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, (T, N)), axis=0))
    h = c * (1 + np.abs(rng.normal(0, 0.01, (T, N))))
    lo = c * (1 - np.abs(rng.normal(0, 0.01, (T, N))))
    if gaps:
        m = rng.random((T, N)) < gaps
        h[m] = lo[m] = c[m] = np.nan
    h[:20, 0] = lo[:20, 0] = c[:20, 0] = np.nan          # a late listing
    return h, lo, c


def test_stream_layout_is_fixed_and_deterministic():
    a, b = surrogate.streams(), surrogate.streams()
    assert len(a["real"]) == N_SURROGATES and len(a["size"]) == SIZE_CHECK_PANELS
    assert set(a["blocks"]) == {5, 60}
    draw = lambda s: np.random.default_rng(s).integers(1 << 30)
    assert draw(a["real"][17]) == draw(b["real"][17])
    assert draw(a["real"][0]) != draw(a["size"][0])


def test_blocks_cover_T_and_are_contiguous_circular():
    rng = np.random.default_rng(1)
    blocks = surrogate.draw_blocks(1000, rng, 20)
    assert sum(b.size for b in blocks) == 1000
    for b in blocks:
        assert np.all(np.diff(b) % 1000 == 1)
    lengths = [b.size for b in blocks[:-1]]
    assert 12 < np.mean(lengths) < 30


def test_nearest_in_block_ties_to_earlier_and_missing_when_none():
    valid = np.array([[True, False], [False, False], [True, False], [False, False], [False, False]])
    idx = np.array([0, 1, 2, 3, 4])
    got = surrogate._resolve_block(idx, valid)
    assert got[:, 0].tolist() == [0, 0, 2, 2, 2]       # position 1: tie between 0 and 2 → 0
    assert got[:, 1].tolist() == [-1] * 5


def test_synchronized_and_presence_mask_kept():
    h, lo, c = panel(gaps=0.02)
    h[:, 1], lo[:, 1], c[:, 1] = h[:, 2], lo[:, 2], c[:, 2]        # two identical stocks
    sh, sl, sc = surrogate.surrogate_panel(h, lo, c, np.random.default_rng(5))
    np.testing.assert_allclose(sc[:, 1], sc[:, 2], equal_nan=True)  # same draws for every stock
    assert np.all(np.isnan(sc) >= np.isnan(c))                      # never a bar where reality has none
    first = np.argmax(~np.isnan(c[:, 0]))
    assert sc[first, 0] == c[first, 0] and sh[first, 0] == h[first, 0]


def test_path_applies_drawn_vectors():
    h, lo, c = panel()
    vec = surrogate.bar_vectors(h, lo, c)
    sh, sl, sc = surrogate.surrogate_panel(h, lo, c, np.random.default_rng(9))
    j = 3
    rh = np.log(sh[1:, j] / sc[:-1, j])
    rl = np.log(sl[1:, j] / sc[:-1, j])
    rc = np.log(sc[1:, j] / sc[:-1, j])
    got = np.stack([rh, rl, rc], axis=1)
    real = vec[1:, j]
    # every surrogate vector is one of the stock's real vectors
    for row in got:
        assert np.min(np.abs(real - row).sum(axis=1)) < 1e-9
    assert np.all((sl <= sh + 1e-12) | np.isnan(sh))


def test_reproducible_from_seed():
    h, lo, c = panel()
    a = surrogate.surrogate_panel(h, lo, c, np.random.default_rng(surrogate.streams()["real"][3]))
    b = surrogate.surrogate_panel(h, lo, c, np.random.default_rng(surrogate.streams()["real"][3]))
    np.testing.assert_array_equal(a[2], b[2])
