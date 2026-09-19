"""Synchronized stationary block bootstrap of daily bar vectors (freeze §8; memo §8.2; R-14; G-5, G-8,
RR-8).

- Bar vector of stock j on session s: (ln H_s/C_prev, ln L_s/C_prev, ln C_s/C_prev), C_prev = the
  stock's previous available close (ratio-adjusted basis). A stock's first bar has no vector.
- One sequence of source sessions is drawn per panel and used for **every** stock (synchronized):
  stationary bootstrap, mean block length L, circular over the window's sessions.
- The surrogate panel keeps the **real** calendar and presence masks (listing, missing bars) and, in the
  caller, the real PIT membership, G-7 ex-dates, OPEN-M and G-6b (RR-8a). A stock's path is rebuilt
  from its first observed bar: that bar is the real one, every later present session applies the drawn
  vector to the previous surrogate close.
- G-5: if stock j has no vector at the drawn source session, the nearest source session **in the same
  drawn block** with a vector is used, ties to the earlier one; if the block has none, the stock is
  missing on that surrogate date (K3 then skips it, OPEN-Q).

Seed layout (G-8, fixed at this commit): `np.random.SeedSequence(SEED).spawn(3)`:
  [0] the real test: child b = 0 … B−1 spawned from it gives surrogate panel b;
  [1] the size check: child p = 0 … 199 gives pseudo-real panel p (drawn from the real panel); that
      child's own spawn(B) gives the B inner surrogates of panel p, drawn from panel p (RR-8b);
  [2] V-B5 / V-B60: spawn(2) → one child per block length, each spawning B surrogates.
"""

import numpy as np

from scripts.ptms.gann.constants import MEAN_BLOCK, N_SURROGATES, SEED, SIZE_CHECK_PANELS


def streams():
    real, size, blocks = np.random.SeedSequence(SEED).spawn(3)
    return {
        "real": real.spawn(N_SURROGATES),
        "size": size.spawn(SIZE_CHECK_PANELS),
        "blocks": dict(zip((5, 60), (c.spawn(N_SURROGATES) for c in blocks.spawn(2)))),
    }


def bar_vectors(high, low, close):
    """(T, N, 3) log bar vectors; NaN where the stock has no bar or no previous close."""
    T, N = close.shape
    vec = np.full((T, N, 3), np.nan)
    prev_c = np.full(N, np.nan)
    for t in range(T):
        present = ~np.isnan(close[t])
        ok = present & ~np.isnan(prev_c)
        vec[t, ok, 0] = np.log(high[t, ok] / prev_c[ok])
        vec[t, ok, 1] = np.log(low[t, ok] / prev_c[ok])
        vec[t, ok, 2] = np.log(close[t, ok] / prev_c[ok])
        prev_c = np.where(present, close[t], prev_c)
    return vec


def draw_blocks(T, rng, mean_block=MEAN_BLOCK):
    """Stationary bootstrap: list of blocks, each an array of source indices (circular), total T."""
    blocks, n = [], 0
    p = 1.0 / mean_block
    while n < T:
        length = min(int(rng.geometric(p)), T - n)
        start = int(rng.integers(T))
        blocks.append((start + np.arange(length)) % T)
        n += length
    return blocks


def _resolve_block(idx, valid):
    """For one drawn block (source indices idx) and validity (T, N): the source index used per position
    and stock (G-5 nearest in the block, ties to the earlier), or -1 if the block has none."""
    L = idx.size
    ok = valid[idx]                                   # (L, N)
    pos = np.arange(L)[:, None]
    big = L + 1
    prev_pos = np.where(ok, pos, -big)
    prev_pos = np.maximum.accumulate(prev_pos, axis=0)
    next_pos = np.where(ok, pos, 2 * big)
    next_pos = np.minimum.accumulate(next_pos[::-1], axis=0)[::-1]
    d_prev = pos - prev_pos
    d_next = next_pos - pos
    choose = np.where(d_prev <= d_next, prev_pos, next_pos)          # ties → earlier
    choose = np.where((prev_pos < 0) & (next_pos >= big), -1, choose)
    return np.where(choose >= 0, idx[np.clip(choose, 0, L - 1)], -1)


def surrogate_panel(high, low, close, rng, mean_block=MEAN_BLOCK):
    """One synchronized surrogate panel with the real presence mask. Returns (high, low, close)."""
    T, N = close.shape
    vec = bar_vectors(high, low, close)
    valid = ~np.isnan(vec[..., 2])
    src = np.empty((T, N), dtype=np.int64)
    t = 0
    for idx in draw_blocks(T, rng, mean_block):
        src[t:t + idx.size] = _resolve_block(idx, valid)
        t += idx.size
    present = ~np.isnan(close)
    first = np.argmax(present, axis=0)
    has_any = present.any(axis=0)
    sh = np.full((T, N), np.nan)
    sl = np.full((T, N), np.nan)
    sc = np.full((T, N), np.nan)
    prev_c = np.full(N, np.nan)
    cols = np.arange(N)
    for t in range(T):
        is_first = has_any & (first == t)
        sh[t, is_first], sl[t, is_first], sc[t, is_first] = high[t, is_first], low[t, is_first], close[t, is_first]
        use = present[t] & ~is_first & (src[t] >= 0) & ~np.isnan(prev_c)
        v = vec[np.maximum(src[t], 0), cols]
        sh[t, use] = prev_c[use] * np.exp(v[use, 0])
        sl[t, use] = prev_c[use] * np.exp(v[use, 1])
        sc[t, use] = prev_c[use] * np.exp(v[use, 2])
        prev_c = np.where(is_first | use, sc[t], prev_c)
    return sh, sl, sc
