"""GF-10 — Rule 8 time overbalance, DB profile (freeze §2.4 = GF-10 record v0.8 §1–§3.12).

GF-10 = Gann-faithful source concept + explicit operator/research conventions; not Gann's exact rule.
The primary score is the **event** score of v0.8, not R-5's state sentence (v0.8 §11.2).

The Stage-1 screen ends at Z = 2022-12-30 and 1m equities begin 2023-01-02, so every observation is
DB profile (v0.8 §1.2 row 1; freeze §2.4 note). `run_gf10` hard-fails on any session ≥ 2023-01-02.
In DB profile every instant is a session close, t_e = close(D_e), and there are no HF rules to apply.

Vectorized over columns with one pass over time, reading the K3 result. Per column it tracks:
- the episode E (constant S9 ∈ {BULL, BEAR}; reset when S9 changes at a switch close; OD-5, SC-3);
- the ledger of E (RQ-1, RQ-5, OD-1): same-type K3 moves completed in E, their greatest duration on
  K3 swing dates (OPEN-A) and literal magnitude (RQ-8), plus bull reactions (OPEN-2.x, RQ-6/7,
  OPEN-D/E) for the price leg, combined in one maximum (RQ-2);
- the current candidate M (bull: K3 decline from a swing high confirmed at c while E is BULL;
  bear mirror), active on (c, u];
- the time latch λ(E) (OD-4): at most one P1 event per episode.

Facts used on session D are those of close(D⁻) (the D−1 freeze): a candidate formed at c is first
checked on the session after c, and it is still checked on u, the session whose close ends it.

P2 (price flags) is a recorded fact, not a score (v0.8 §3.9), and is not computed here.
"""

from dataclasses import dataclass

import numpy as np

from scripts.ptms.gann.constants import HF_EARLIEST, OUTCOME_SESSIONS
from scripts.ptms.gann.k3 import DOWN, UP, K3Result

BULL, BEAR = 1, -1

# PENDING-2 = D_e (operator ruling 2026-09-19): a score-1 week counts if the stock is a PIT member on
# the event session D_e; a contrast week whose only contributors ended before D_L uses its first
# P3/P4 instant in the week. P1 detection and λ run on the stock's own series regardless of membership.
SCORE1_MEMBER_ON = "D_e"


@dataclass
class Trace:
    """Per-session state after each close, and the P1 events and completed candidates."""
    act_dir: np.ndarray          # (T, N) direction of the qualifying candidate active after close t (0 none)
    act_span: np.ndarray         # (T, N) its G-7 span start index (-1 if none)
    act_sz: np.ndarray           # (T, N) the active candidate can no longer score 1 (U_T empty or lambda set)
    ev_t: np.ndarray             # P1 events: session index D_e
    ev_col: np.ndarray
    ev_dir: np.ndarray
    ev_span: np.ndarray          # span start index
    ev_ref_lvl: np.ndarray       # X_ref level and extreme index (the swing preceding the start)
    ev_ref_t: np.ndarray
    cd_col: np.ndarray           # completed, matched, member candidates (contrast-eligible, DB)
    cd_dir: np.ndarray
    cd_c: np.ndarray
    cd_u: np.ndarray
    cd_st: np.ndarray            # P3 instant (session index) or -1
    cd_sp: np.ndarray            # P4 instant or -1
    cd_span: np.ndarray


def _nan_min(a, b):
    return np.where(np.isnan(a), b, np.where(np.isnan(b), a, np.minimum(a, b)))


def _nan_max(a, b):
    return np.where(np.isnan(a), b, np.where(np.isnan(b), a, np.maximum(a, b)))


def run_gf10(high, low, ords, res: K3Result, comparator="greatest", rt_scale=1.0) -> Trace:
    """comparator: "greatest" (primary, OD-1) or "preceding" (V10-IP: the most recent completed
    same-type move of E). rt_scale: 1.0 (primary) or 0.75 / 1.33 (ratio placebos, off-path)."""
    if comparator not in ("greatest", "preceding"):
        raise ValueError(comparator)
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    ords = np.asarray(ords, dtype=np.int64)
    if ords.size and ords.max() >= HF_EARLIEST.toordinal():
        raise SystemExit("GF-10 Stage-1 is DB-only: a session on or after 2023-01-02 reached run_gf10")
    T, N = high.shape
    nan = lambda: np.full(N, np.nan)
    neg = lambda: np.full(N, -1, dtype=np.int64)

    # swing bookkeeping from the K3 result: last swing high / low (level, extreme index) after each close
    sw_lvl = {1: nan(), -1: nan()}
    sw_ext = {1: neg(), -1: neg()}
    ev_by_t = {}
    for t, j, k, lv, ex in zip(res.sw_t, res.sw_col, res.sw_kind, res.sw_level, res.sw_ext_t):
        ev_by_t.setdefault(int(t), []).append((int(j), int(k), float(lv), int(ex)))

    ep = np.zeros(N, dtype=np.int8)                 # episode σ (0 = no episode)
    lam = np.zeros(N, dtype=bool)
    led_dur = nan()                                 # greatest same-type duration in E
    led_last = nan()                                # most recent completed same-type duration (V10-IP)
    led_mag = nan()                                 # greatest magnitude in E (moves and reactions)
    led_first = neg()                               # start index of the earliest ledger member

    # UP-line reaction tracking (bull price leg)
    rh = nan()                                      # running line high (RH)
    last_est = neg()
    rx_len = np.zeros(N, dtype=np.int8)
    rx_top = nan()
    rx_low = nan()
    rx_e = neg()
    pend_mag, pend_first = nan(), neg()             # reactions completed after the line's max-high date
    conf_mag, conf_first = nan(), neg()             # completed at or before it
    since_max = nan()                               # min low since the line's max high (bull run seed)
    # mirror for a DOWN line: max high since the line's min low (bear run seed)
    line_min = nan()
    since_min = nan()

    # current candidate
    c_on = np.zeros(N, dtype=bool)
    c_dir = np.zeros(N, dtype=np.int8)
    c_c = neg()
    c_ds = neg()
    c_ps = nan()
    c_rt = nan()
    c_rp = nan()
    c_span = neg()
    c_ref_lvl, c_ref_t = nan(), neg()
    c_run = nan()                                   # bull: min low over (d_S, D]; bear: max high
    c_st, c_sp = neg(), neg()

    act_dir = np.zeros((T, N), dtype=np.int8)
    act_span = np.full((T, N), -1, dtype=np.int64)
    act_sz = np.zeros((T, N), dtype=bool)
    events, cands = [], []
    prev_state = np.zeros(N, dtype=np.int8)
    prev_low = nan()
    prev_bar = neg()                                # index of the column's previous available bar

    for t in range(T):
        h, lo = high[t], low[t]
        present = ~np.isnan(h)
        st = res.state[t]
        s9 = res.s9[t]

        # ---- 1. active-session checks on D = t for the candidate standing after close(t−1) ----
        on = c_on.copy()
        el = ords[t] - ords[np.maximum(c_ds, 0)]
        has_rt = ~np.isnan(c_rt)
        with np.errstate(invalid="ignore"):
            tc = on & has_rt & (el > c_rt)
        fire = tc & ~lam
        for j in np.nonzero(fire)[0]:
            events.append((t, j, int(c_dir[j]), int(c_span[j]), float(c_ref_lvl[j]), int(c_ref_t[j])))
        lam |= fire
        c_st = np.where(tc & (c_st < 0), t, c_st)
        with np.errstate(invalid="ignore"):
            c_run = np.where(on & present & (c_dir == BULL), _nan_min(c_run, lo), c_run)
            c_run = np.where(on & present & (c_dir == BEAR), _nan_max(c_run, h), c_run)
            run = np.where(c_dir == BULL, c_ps - c_run, c_run - c_ps)
            pc = on & ~np.isnan(c_rp) & (run > c_rp)
        c_sp = np.where(pc & (c_sp < 0), t, c_sp)

        # ---- 2. K3 switches at close(t) ----
        to_dn = present & (prev_state == UP) & (st == DOWN)
        to_up = present & (prev_state == DOWN) & (st == UP)
        init_up = present & (prev_state == 0) & (st == UP)
        init_dn = present & (prev_state == 0) & (st == DOWN)
        conf = ev_by_t.get(t, [])
        for j, kind, lv, ex in conf:
            sw_lvl[kind][j], sw_ext[kind][j] = lv, ex

        # a switch ends the current candidate (it was active on t = u) and completes the move
        ending = c_on & (to_dn | to_up)
        for j in np.nonzero(ending)[0]:
            if not np.isnan(c_rt[j]):               # matched and a member (members only are candidates)
                cands.append((j, int(c_dir[j]), int(c_c[j]), t, int(c_st[j]), int(c_sp[j]), int(c_span[j])))
        # the ended candidate's move enters the ledger if E continues (S9 unchanged at this close).
        # Every same-type move completed in E had a candidate: it was confirmed at a close where E
        # already had its σ (SC-3). dur on K3 swing dates (OPEN-A); mag = literal extreme over
        # (d_S, u], which is the candidate's running extreme (RQ-8).
        bank = ending & (s9 == ep) & (c_dir == ep)
        if bank.any():
            idx = np.nonzero(bank)[0]
            end_kind = np.where(c_dir[idx] == BULL, -1, 1)
            end_ext = np.where(end_kind == -1, sw_ext[-1][idx], sw_ext[1][idx])
            dur = (ords[end_ext] - ords[c_ds[idx]]).astype(float)
            mag = np.where(c_dir[idx] == BULL, c_ps[idx] - c_run[idx], c_run[idx] - c_ps[idx])
            led_dur[idx] = _nan_max(led_dur[idx], dur)
            led_last[idx] = dur
            led_mag[idx] = _nan_max(led_mag[idx], mag)
            start = c_ds[idx]
            led_first[idx] = np.where(led_first[idx] < 0, start, np.minimum(led_first[idx], start))
        c_on &= ~ending

        # ---- 3. reactions inside an UP line (bull price leg), on continuing UP sessions ----
        cont_up = present & (prev_state == UP) & (st == UP)
        with np.errstate(invalid="ignore"):
            ll = lo < prev_low
            new_high = h > rh
        # an open reaction: a further LL extends it, a non-LL session completes it
        ext2 = cont_up & (rx_len == 1) & ll
        done = cont_up & (rx_len > 0) & ~ll
        rx_low = np.where(ext2, lo, rx_low)
        rx_len = np.where(ext2, 2, rx_len).astype(np.int8)
        mag = rx_top - rx_low
        pend_mag = np.where(done, _nan_max(pend_mag, mag), pend_mag)
        pend_first = np.where(done & ((pend_first < 0) | (rx_e < pend_first)), rx_e, pend_first)
        rx_len = np.where(done, 0, rx_len).astype(np.int8)
        in_rx = cont_up & (rx_len > 0)              # a session still inside a reaction
        # opening: the session immediately after an establishing session, and LL
        opens = cont_up & (rx_len == 0) & ~done & ll & (last_est >= 0) & (last_est == prev_bar)
        rx_len = np.where(opens, 1, rx_len).astype(np.int8)
        rx_top = np.where(opens, rh, rx_top)
        rx_low = np.where(opens, lo, rx_low)
        rx_e = np.where(opens, last_est, rx_e)
        in_rx |= opens
        establishing = cont_up & new_high & ~in_rx
        last_est = np.where(establishing, t, last_est)
        # any new line high (establishing or an outside day in a reaction) moves the max-high date:
        # reactions completed at or before it become "confirmed" for a candidate whose d_S is here
        moved = cont_up & new_high
        conf_mag = np.where(moved, _nan_max(conf_mag, pend_mag), conf_mag)
        conf_first = np.where(moved & (pend_first >= 0) & ((conf_first < 0) | (pend_first < conf_first)),
                              pend_first, conf_first)
        pend_mag = np.where(moved, np.nan, pend_mag)
        pend_first = np.where(moved, -1, pend_first)
        rh = np.where(moved, h, rh)
        since_max = np.where(moved, np.nan, np.where(cont_up, _nan_min(since_max, lo), since_max))
        # DOWN line mirror for the bear run seed
        cont_dn = present & (prev_state == DOWN) & (st == DOWN)
        with np.errstate(invalid="ignore"):
            new_low = cont_dn & (lo < line_min)
        line_min = np.where(new_low, lo, line_min)
        since_min = np.where(new_low, np.nan, np.where(cont_dn, _nan_max(since_min, h), since_min))

        # ---- 4. episode update at switch closes (S9 changes only here) ----
        switched = to_dn | to_up | init_up | init_dn
        changed = switched & (s9 != ep)
        ep = np.where(changed, s9, ep).astype(np.int8)
        lam &= ~changed
        led_dur = np.where(changed, np.nan, led_dur)
        led_last = np.where(changed, np.nan, led_last)
        led_mag = np.where(changed, np.nan, led_mag)
        led_first = np.where(changed, -1, led_first)

        # ---- 5. new candidates ----
        # bull: at a down-switch close with E BULL; bear: at an up-switch close with E BEAR
        for mask, sigma, kind in ((to_dn, BULL, 1), (to_up, BEAR, -1)):
            new = mask & (ep == sigma)
            if not new.any():
                continue
            idx = np.nonzero(new)[0]
            rp_extra = conf_mag[idx] if sigma == BULL else np.full(idx.size, np.nan)
            first_extra = conf_first[idx] if sigma == BULL else np.full(idx.size, -1)
            if sigma == BULL:
                keep = ~changed[idx]                # line reactions belong to the old E if S9 changed
                rp_extra = np.where(keep, rp_extra, np.nan)
                first_extra = np.where(keep, first_extra, -1)
            c_on[idx] = True
            c_dir[idx] = sigma
            c_c[idx] = t
            c_ds[idx] = sw_ext[kind][idx]
            c_ps[idx] = sw_lvl[kind][idx]
            base_rt = led_dur[idx] if comparator == "greatest" else led_last[idx]
            c_rt[idx] = base_rt * rt_scale          # NaN = 𝒰_T empty (cannot trigger, OPEN-1 = A)
            c_rp[idx] = _nan_max(led_mag[idx], rp_extra)
            lf = led_first[idx]
            fe = np.asarray(first_extra)
            first = np.where(lf < 0, fe, np.where(fe < 0, lf, np.minimum(lf, fe)))
            ref_kind = -kind                        # bull: the swing low preceding X⁺
            c_ref_lvl[idx] = sw_lvl[ref_kind][idx]
            c_ref_t[idx] = sw_ext[ref_kind][idx]
            # G-7 span start (v0.8 §3.12): earliest of d_ref and the earliest ledger member; d_ref
            # alone when 𝒰_T = ∅
            c_span[idx] = np.where(np.isnan(led_dur[idx]) | (first < 0), c_ref_t[idx],
                                   np.minimum(c_ref_t[idx], first))
            seed = since_max[idx] if sigma == BULL else since_min[idx]
            if sigma == BULL:
                c_run[idx] = _nan_min(seed, lo[idx])
            else:
                c_run[idx] = _nan_max(seed, h[idx])
            c_st[idx] = -1
            c_sp[idx] = -1
        # bank the ended UP line's reactions into E (they are members for later candidates)
        if (to_dn & ~changed).any():
            idx = np.nonzero(to_dn & ~changed & (ep == BULL))[0]
            led_mag[idx] = _nan_max(_nan_max(led_mag[idx], conf_mag[idx]), pend_mag[idx])
            for arr in (conf_first, pend_first):
                a = arr[idx]
                led_first[idx] = np.where(a < 0, led_first[idx],
                                          np.where(led_first[idx] < 0, a, np.minimum(led_first[idx], a)))

        # ---- 6. a new line starts at a switch or initialization ----
        start_up = to_up | init_up
        rh = np.where(start_up, h, rh)
        last_est = np.where(start_up, t, last_est)
        rx_len = np.where(start_up | to_dn | init_dn, 0, rx_len).astype(np.int8)
        for arr in (pend_mag, conf_mag):
            arr[start_up] = np.nan
        pend_first[start_up] = -1
        conf_first[start_up] = -1
        since_max = np.where(start_up, np.nan, since_max)
        start_dn = to_dn | init_dn
        line_min = np.where(start_dn, lo, line_min)
        since_min = np.where(start_dn, np.nan, since_min)

        act_dir[t] = np.where(c_on, c_dir, 0)
        act_span[t] = np.where(c_on, c_span, -1)
        act_sz[t] = c_on & (np.isnan(c_rt) | lam)
        prev_state = np.where(present, st, prev_state).astype(np.int8)
        prev_low = np.where(present, lo, prev_low)
        prev_bar = np.where(present, t, prev_bar)

    ev = np.array(events, dtype=float).reshape(-1, 6)
    cd = np.array(cands, dtype=np.int64).reshape(-1, 7)
    return Trace(act_dir, act_span, act_sz,
                 ev[:, 0].astype(np.int64), ev[:, 1].astype(np.int64), ev[:, 2].astype(np.int8),
                 ev[:, 3].astype(np.int64), ev[:, 4], ev[:, 5].astype(np.int64),
                 cd[:, 0], cd[:, 1].astype(np.int8), cd[:, 2], cd[:, 3], cd[:, 4], cd[:, 5], cd[:, 6])


# ---------------------------------------------------------------------------------------------
# Observations (v0.8 §3.9 – §3.12)
# ---------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Obs10:
    week: np.ndarray
    col: np.ndarray
    score: np.ndarray            # primary: s; contrast: s_T
    score_p: np.ndarray          # contrast: s_P (primary: copy of score)
    y: np.ndarray
    dir: np.ndarray              # BULL / BEAR (N-DIR)
    sz: np.ndarray               # structural zero (N-SZ; primary only)
    n_excluded_open_m: int
    n_excluded_g7: int
    n_excluded_open_n: int


def _penetrated(high, low, sessions, col, d, ref_lvl):
    """Strictly beyond the reference over the given sessions (RR-1); no bar = no penetration (IR-4)."""
    if not sessions:
        return False
    with np.errstate(invalid="ignore"):
        if d == BULL:
            return bool(np.any(low[sessions, col] < ref_lvl))
        return bool(np.any(high[sessions, col] > ref_lvl))


def _y(high, low, col, ref_lvl, ref_t, anchor, d, horizon):
    """O-R10 in EOD form (v0.8 §3.10 / §3.11): no penetration in (d_ref, anchor] and a penetration in
    the `horizon` sessions after the anchor session. The anchor is D_e (score 1) or D_L (f_w rule)."""
    if ref_t < 0:
        raise AssertionError("GF-10 reference swing must exist for every eligible observation (v0.8 §3.11)")
    prior = list(range(ref_t + 1, anchor + 1))
    window = list(range(anchor + 1, anchor + horizon + 1))
    return int(not _penetrated(high, low, prior, col, d, ref_lvl)
               and _penetrated(high, low, window, col, d, ref_lvl))


def _g7_hit(ex, ords, start_idx, end_idx):
    """IR-5: an ex-date in [start, end], both ends inclusive."""
    if ex.size == 0:
        return False
    i = np.searchsorted(ex, ords[start_idx], side="left")
    return bool(i < ex.size and ex[i] <= ords[end_idx])


def _member_ok(member, col, d_l, instant, rule):
    if rule == "D_L":
        return bool(member[d_l, col])
    if rule == "D_e":
        return bool(member[instant, col])
    raise SystemExit("PENDING-2 (score-1 membership instant) is unruled; refusing to build GF-10 observations")


def _week_of(week_last_idx, T):
    """Formation-week number of every session: the week whose D_L is the first D_L at or after it."""
    return np.searchsorted(np.asarray(week_last_idx, dtype=np.int64), np.arange(T), side="left")


def primary_obs(tr: Trace, week_last_idx, high, low, ords, member, g7_ord, swings,
                member_rule=None, horizon=OUTCOME_SESSIONS) -> Obs10:
    """Primary score s(i, w): 1 in the ISO week holding a P1 event (the first event anchors, OPEN-K(c));
    0 when a qualifying candidate is active on D_L (A1, incl. structural zeros); else excluded."""
    member_rule = member_rule or SCORE1_MEMBER_ON
    T, N = high.shape
    ords = np.asarray(ords, dtype=np.int64)
    wk_of = _week_of(week_last_idx, T)
    first_event = {}
    for k in np.lexsort((tr.ev_t, tr.ev_col)):
        first_event.setdefault((int(wk_of[tr.ev_t[k]]), int(tr.ev_col[k])), k)
    rows, n_m, n_g7 = [], 0, 0
    for w, t in enumerate(week_last_idx):
        t = int(t)
        for col in range(N):
            k = first_event.get((w, col))
            if k is not None:
                d_e = int(tr.ev_t[k])
                if not _member_ok(member, col, t, d_e, member_rule):
                    continue
                d, anchor, span = int(tr.ev_dir[k]), d_e, int(tr.ev_span[k])
                ref_lvl, ref_t, score, sz = tr.ev_ref_lvl[k], int(tr.ev_ref_t[k]), 1, False
            elif t >= 1 and tr.act_dir[t - 1, col] != 0 and member[t, col]:
                d, anchor, span = int(tr.act_dir[t - 1, col]), t, int(tr.act_span[t - 1, col])
                kind = -1 if d == BULL else 1
                ref_lvl, ref_t = swings[kind][0][t - 1, col], int(swings[kind][1][t - 1, col])
                score, sz = 0, bool(tr.act_sz[t - 1, col])
            else:
                continue
            if anchor + horizon > T - 1:                 # OPEN-M: O_h beyond Z
                n_m += 1
                continue
            if _g7_hit(g7_ord[col], ords, span, anchor + horizon):
                n_g7 += 1
                continue
            rows.append((w, col, score, score, _y(high, low, col, ref_lvl, ref_t, anchor, d, horizon), d, sz))
    return _pack(rows, n_m, n_g7, 0)


def contrast_obs(tr: Trace, week_last_idx, high, low, ords, member, g7_ord, swings,
                 member_rule=None) -> Obs10:
    """Contrast stock-weeks (v0.8 §3.7, §3.9, §3.11): s_T / s_P from P3 / P4 instants of complete,
    matched, DB-homogeneous candidates in the week; 0 by A1 on such a candidate active on D_L. One
    shared outcome by the f_w rule (OPEN-L). Opposite-direction contributors ⇒ excluded (OPEN-N)."""
    member_rule = member_rule or SCORE1_MEMBER_ON
    T = high.shape[0]
    ords = np.asarray(ords, dtype=np.int64)
    wl = np.asarray(week_last_idx, dtype=np.int64)
    wk_of = _week_of(wl, T)
    cells = {}
    for k in range(tr.cd_col.size):
        col, c, u = int(tr.cd_col[k]), int(tr.cd_c[k]), int(tr.cd_u[k])
        weeks = {w for w in range(len(wl)) if c < wl[w] <= u}           # active on D_L
        for inst in (tr.cd_st[k], tr.cd_sp[k]):
            if inst >= 0:
                weeks.add(int(wk_of[inst]))
        for w in weeks:
            if w < len(wl):
                cells.setdefault((w, col), []).append(k)
    rows, n_m, n_g7, n_n = [], 0, 0, 0
    for (w, col), ks in sorted(cells.items()):
        t = int(wl[w])
        lo_t = int(wl[w - 1]) if w > 0 else -1

        def in_week(i):
            return lo_t < i <= t

        active = [k for k in ks if tr.cd_c[k] < t <= tr.cd_u[k]]
        s_t = int(any(in_week(tr.cd_st[k]) for k in ks))
        s_p = int(any(in_week(tr.cd_sp[k]) for k in ks))
        if active:
            if not member[t, col]:
                continue
        else:
            first_inst = min(i for k in ks for i in (tr.cd_st[k], tr.cd_sp[k]) if in_week(i))
            if not _member_ok(member, col, t, first_inst, member_rule):
                continue
        dirs = {int(tr.cd_dir[k]) for k in ks}
        if len(dirs) > 1:
            n_n += 1
            continue
        d = dirs.pop()
        if t + OUTCOME_SESSIONS > T - 1:
            n_m += 1
            continue
        kind = -1 if d == BULL else 1
        ref_lvl, ref_t = swings[kind][0][t - 1, col], int(swings[kind][1][t - 1, col])
        span = min(int(tr.cd_span[k]) for k in ks)
        if _g7_hit(g7_ord[col], ords, span, t + OUTCOME_SESSIONS):
            n_g7 += 1
            continue
        rows.append((w, col, s_t, s_p, _y(high, low, col, ref_lvl, ref_t, t, d, OUTCOME_SESSIONS), d, False))
    return _pack(rows, n_m, n_g7, n_n)


def _pack(rows, n_m, n_g7, n_n):
    a = np.array(rows, dtype=np.int64).reshape(-1, 7)
    return Obs10(a[:, 0], a[:, 1], a[:, 2].astype(np.int8), a[:, 3].astype(np.int8), a[:, 4].astype(np.int8),
                 a[:, 5].astype(np.int8), a[:, 6].astype(bool), n_m, n_g7, n_n)
