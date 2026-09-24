"""GF-10 tests on synthetic bars only. No store is read."""

from datetime import date

import numpy as np
import pytest

from scripts.ptms.gann import formation, gf10
from scripts.ptms.gann.k3 import run_k3, swings_of


def reference_time_leg(res, ords, col, comparator="greatest"):
    """Independent single-column transcription of the time leg (v0.8 §3.2–§3.4, §3.8 P1, §4 B–F):
    returns P1 events [(D_e, dir)] and, per session, the direction of the active qualifying candidate."""
    T = res.state.shape[0]
    sw = swings_of(res, col)
    sigma, ledger, lam = 0, [], False
    events, act = [], [0] * T
    for i, (conf_t, kind, _, ext_t) in enumerate(sw):
        s9 = int(res.s9[conf_t, col])
        # the candidate of the previous swing ends at this close; bank its duration if E continues
        if i > 0:
            p_conf, p_kind, _, p_ext = sw[i - 1]
            p_sigma = 1 if p_kind == 1 else -1
            if s9 == sigma == p_sigma and cand is not None:
                ledger.append(ords[ext_t] - ords[p_ext])
        if s9 != sigma:
            sigma, ledger, lam = s9, [], False
        cand = None
        if (kind == 1 and sigma == 1) or (kind == -1 and sigma == -1):
            rt = (max(ledger) if comparator == "greatest" else ledger[-1]) if ledger else None
            u = sw[i + 1][0] if i + 1 < len(sw) else T - 1
            end = u if i + 1 < len(sw) else T - 1
            cand = (conf_t, ext_t, rt)
            for d in range(conf_t + 1, end + 1):
                if i + 1 < len(sw) or d <= T - 1:
                    act[d - 1] = sigma if d - 1 >= conf_t else act[d - 1]
                if rt is not None and not lam and ords[d] - ords[ext_t] > rt:
                    events.append((d, sigma))
                    lam = True
            if i + 1 >= len(sw):
                act[T - 1] = sigma
    return events, act


def random_paths(seed, T=500, N=12):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.02, (T, N)), axis=0))
    h = np.round(c * (1 + np.abs(rng.normal(0, 0.012, (T, N)))), 2)
    lo = np.round(c * (1 - np.abs(rng.normal(0, 0.012, (T, N)))), 2)
    days = np.cumsum(rng.choice([1, 1, 1, 1, 3], T))           # calendar gaps like weekends
    ords = (date(2015, 1, 1).toordinal() + days).tolist()
    return h, lo, ords


@pytest.mark.parametrize("seed", [1, 2, 3])
@pytest.mark.parametrize("comparator", ["greatest", "preceding"])
def test_time_leg_matches_independent_reference(seed, comparator):
    h, lo, ords = random_paths(seed)
    res = run_k3(h, lo)
    tr = gf10.run_gf10(h, lo, ords, res, comparator=comparator)
    n_events = 0
    for col in range(h.shape[1]):
        ref_events, ref_act = reference_time_leg(res, ords, col, comparator)
        got = sorted((int(t), int(d)) for t, c, d in zip(tr.ev_t, tr.ev_col, tr.ev_dir) if c == col)
        assert got == sorted(ref_events)
        assert tr.act_dir[:, col].tolist() == ref_act
        n_events += len(got)
    assert n_events > 0                                          # the fixture exercises the event path


def test_db_only_guard():
    h, lo, _ = random_paths(1, T=50, N=2)
    ords = [date(2022, 12, 1).toordinal() + i for i in range(50)]
    with pytest.raises(SystemExit):
        gf10.run_gf10(h, lo, ords, run_k3(h, lo))


def test_one_event_per_episode_and_structural_zeros_flagged():
    h, lo, ords = random_paths(4, T=800, N=10)
    res = run_k3(h, lo)
    tr = gf10.run_gf10(h, lo, ords, res)
    # between two events of one column the episode must have changed (S9 changed at some switch)
    for col in range(h.shape[1]):
        ts = sorted(int(t) for t, c in zip(tr.ev_t, tr.ev_col) if c == col)
        for a, b in zip(ts, ts[1:]):
            assert len(set(res.s9[a:b, col].tolist())) > 1
    # after an event, the rest of that candidate's life is a structural zero
    for t, col in zip(tr.ev_t, tr.ev_col):
        if tr.act_dir[t, col] != 0:
            assert tr.act_sz[t, col]


def _reaction_path(with_reaction):
    bars, marks = [], {}
    st = {"hi": 100.0, "lo": 98.0}

    def step(dh, dl, n, tag=None):
        for _ in range(n):
            st["hi"] += dh
            st["lo"] += dl
            bars.append((st["hi"], st["lo"]))
        if tag:
            marks[tag] = len(bars) - 1

    step(0, 0, 1); step(1, 1, 4); step(-1, -1, 3); step(1.2, 1.2, 5); step(-1, -1, 3)
    step(1.5, 1.5, 6)                      # S9 BULL from this up-switch: E opens
    step(-1, -1, 3); step(2, 2, 3)         # decline M1 (unmatched), completes and is banked
    step(2, 2, 1, "e")                     # establishing session
    if with_reaction:
        step(-0.2, -6, 1, "s1"); step(1, 7, 1)   # 1-session reaction, completes on the next session
    else:
        step(0.5, 0.5, 2)
    step(3, 3, 2); step(-1, -1, 3); step(-0.5, -0.5, 8); step(3, 3, 4)
    h = np.array([[x[0]] for x in bars])
    lo = np.array([[x[1]] for x in bars])
    ords = [date(2016, 1, 1).toordinal() + i for i in range(len(bars))]
    res = run_k3(h, lo)
    return h, lo, res, gf10.run_gf10(h, lo, ords, res), marks


def test_reaction_enters_the_price_reference():
    """An UP-line reaction completed before d_S enters R_P (RQ-2 combined maximum): the matched
    candidate's first P4 instant is the first session whose run exceeds the reaction magnitude."""
    h, lo, res, tr, marks = _reaction_path(True)
    _, _, _, tr0, _ = _reaction_path(False)
    assert tr.cd_col.size == 1 and tr0.cd_col.size == 1
    reaction_mag = h[marks["e"], 0] - lo[marks["s1"], 0]
    d_s = [s for s in swings_of(res, 0) if s[0] == tr.cd_c[0]][0][3]
    run = lambda d: h[d_s, 0] - lo[d_s + 1:d + 1, 0].min()
    sp = int(tr.cd_sp[0])
    assert run(sp) > reaction_mag >= run(sp - 1)
    assert tr0.cd_sp[0] < sp                # without the reaction, R_P is the smaller decline magnitude


def test_primary_obs_score1_membership_on_event_session():
    h, lo, ords = random_paths(2, T=300, N=6)
    res = run_k3(h, lo)
    tr = gf10.run_gf10(h, lo, ords, res)
    sw = formation.last_swings(res, *h.shape)
    weeks = np.arange(4, 300, 5)
    member = np.ones_like(h, dtype=bool)
    g7 = tuple(np.zeros(0, dtype=np.int64) for _ in range(6))
    assert gf10.SCORE1_MEMBER_ON == "D_e"
    obs = gf10.primary_obs(tr, weeks, h, lo, ords, member, g7, sw)
    assert set(np.unique(obs.score)) <= {0, 1} and obs.score.sum() > 0
    assert obs.sz[obs.score == 1].sum() == 0
    # PENDING-2 = D_e: a member on the event session keeps the 1 even if not a member on D_L
    k = 0
    t_e, col = int(tr.ev_t[k]), int(tr.ev_col[k])
    w = int(np.searchsorted(weeks, t_e))
    if w < weeks.size and weeks[w] + 5 <= 299:
        m2 = member.copy()
        m2[weeks[w], col] = False
        o2 = gf10.primary_obs(tr, weeks, h, lo, ords, m2, g7, sw)
        assert ((o2.week == w) & (o2.col == col) & (o2.score == 1)).any()
        m3 = member.copy()
        m3[t_e, col] = False
        o3 = gf10.primary_obs(tr, weeks, h, lo, ords, m3, g7, sw)
        assert not ((o3.week == w) & (o3.col == col) & (o3.score == 1)).any()


def test_event_outcome_prior_penetration_and_window():
    """y for a bull event: 0 if the reference was broken in (d_ref, D_e]; else 1 iff broken in O_1..O_5."""
    low = np.array([[10.0], [9.0], [9.5], [9.6], [9.7], [9.8], [8.5], [9.9], [9.9], [9.9]])
    high = low + 1
    assert gf10._y(high, low, 0, 9.0, 1, 3, gf10.BULL, 5) == 1          # 8.5 at index 6 in O_1..O_5
    assert gf10._y(high, low, 0, 9.0, 1, 6, gf10.BULL, 3) == 0          # 8.5 is prior (in (1, 6])
    assert gf10._y(high, low, 0, 8.5, 1, 3, gf10.BULL, 5) == 0          # equality is not a break (RR-1)


def test_contrast_obs_shared_outcome_and_single_direction():
    h, lo, ords = random_paths(5, T=900, N=12)
    res = run_k3(h, lo)
    tr = gf10.run_gf10(h, lo, ords, res)
    sw = formation.last_swings(res, *h.shape)
    weeks = np.arange(4, 900, 5)
    member = np.ones_like(h, dtype=bool)
    g7 = tuple(np.zeros(0, dtype=np.int64) for _ in range(12))
    obs = gf10.contrast_obs(tr, weeks, h, lo, ords, member, g7, sw, member_rule="D_L")
    assert obs.week.size > 0 and obs.score.sum() > 0 and obs.score_p.sum() > 0
    # one row per stock-week, both legs on it (OPEN-L), f_w outcome recomputed independently
    assert len(set(zip(obs.week.tolist(), obs.col.tolist()))) == obs.week.size
    for w, col, d, yv in zip(obs.week, obs.col, obs.dir, obs.y):
        t = int(weeks[w])
        kind = -1 if d == gf10.BULL else 1
        assert yv == gf10._y(h, lo, col, sw[kind][0][t - 1, col], int(sw[kind][1][t - 1, col]), t, d, 5)


def reference_price_leg(h, lo, res, col):
    """Independent single-column transcription of the price leg (v0.8 §3.5–§3.7, §4 A–D): reactions,
    ledger magnitudes, the combined maximum R_P and the first P4 instant of every complete matched
    candidate. Returns [(c, u, first P4 session or -1)]."""
    T = h.shape[0]
    hc, lc = h[:, col], lo[:, col]
    st, s9 = res.state[:, col], res.s9[:, col]
    sw = {s[0]: s for s in swings_of(res, col)}
    sigma, items, n_same = 0, [], 0           # items: (completion index, magnitude)
    cand, out = None, []
    prev_state, prev_bar = 0, -1
    rh = est = None
    rx = None                                 # [len, top, low]
    for t in range(T):
        if np.isnan(hc[t]):
            continue
        # active checks for the standing candidate on D = t
        if cand is not None:
            d_s, p_s, direction, rp, sp = cand["d_s"], cand["p_s"], cand["dir"], cand["rp"], cand["sp"]
            seg_lo, seg_hi = lc[d_s + 1:t + 1], hc[d_s + 1:t + 1]
            run = p_s - np.nanmin(seg_lo) if direction == 1 else np.nanmax(seg_hi) - p_s
            if sp < 0 and rp is not None and run > rp:
                cand["sp"] = t
        switch = prev_state in (1, -1) and st[t] != prev_state
        if switch and cand is not None:
            if cand["matched"]:
                out.append((cand["c"], t, cand["sp"]))
            if s9[t] == sigma == cand["dir"]:
                d_s, p_s = cand["d_s"], cand["p_s"]
                mag = p_s - np.nanmin(lc[d_s + 1:t + 1]) if cand["dir"] == 1 else np.nanmax(hc[d_s + 1:t + 1]) - p_s
                items.append((t, mag, "move"))
            cand = None
        # reactions on continuing UP sessions
        if prev_state == 1 and st[t] == 1:
            ll = lc[t] < lc[prev_bar]
            if rx is not None:
                if ll:
                    rx[0], rx[2] = 2, lc[t]
                    if hc[t] > rh:
                        rh = hc[t]
                else:
                    items_line.append((t, rx[1] - rx[2]))
                    rx = None
                    if hc[t] > rh:
                        rh, est = hc[t], t
            elif prev_bar == est and ll:
                rx = [1, hc[est], lc[t]]
                if hc[t] > rh:
                    rh = hc[t]
            elif hc[t] > rh:
                rh, est = hc[t], t
        changed = switch and s9[t] != sigma
        if changed:
            sigma, items = int(s9[t]), []
        if st[t] == -1 and prev_state == 1:           # down-switch close c
            line = [] if changed else items_line
            if sigma == 1:
                conf = sw[t]
                d_s = conf[3]
                pool = [m for (ct, m, _) in items] + [m for (ct, m) in line if ct <= d_s]
                cand = {"c": t, "d_s": d_s, "p_s": conf[2], "dir": 1, "sp": -1,
                        "rp": max(pool) if pool else None,
                        "matched": any(k == "move" for (_, _, k) in items)}
            if sigma == 1 and not changed:
                items += [(ct, m, "rx") for (ct, m) in items_line]
            rx = None
        if st[t] == 1 and prev_state == -1 and sigma == -1:   # bear candidate at an up-switch close
            conf = sw[t]
            pool = [m for (_, m, _) in items]
            cand = {"c": t, "d_s": conf[3], "p_s": conf[2], "dir": -1, "sp": -1,
                    "rp": max(pool) if pool else None, "matched": any(k == "move" for (_, _, k) in items)}
        if st[t] == 1 and prev_state != 1:            # a new UP line
            rh, est, rx, items_line = hc[t], t, None, []
        prev_state, prev_bar = int(st[t]), t
    return out


@pytest.mark.parametrize("seed", [11, 12, 13, 14])
def test_price_leg_matches_independent_reference(seed):
    h, lo, ords = random_paths(seed, T=700, N=10)
    res = run_k3(h, lo)
    tr = gf10.run_gf10(h, lo, ords, res)
    n_sp = 0
    for col in range(h.shape[1]):
        ref = reference_price_leg(h, lo, res, col)
        got = [(int(c), int(u), int(sp)) for cc, c, u, sp in zip(tr.cd_col, tr.cd_c, tr.cd_u, tr.cd_sp)
               if cc == col]
        assert got == ref
        n_sp += sum(1 for *_, sp in got if sp >= 0)
    assert n_sp > 0
