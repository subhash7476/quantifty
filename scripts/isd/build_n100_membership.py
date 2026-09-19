"""Nifty 100 point-in-time membership builder.

Reconstructs NIFTY 100 membership as the union of two independently walked
legs — NIFTY 50 and NIFTY NEXT 50 — from the parsed press-release event
corpus (data/isd/n200_membership.duckdb:n200_events, 228 PRs, 2011-2026),
then gates the result against the monthly MCWB snapshots
(data/reference/mcwb_*.zip, 2010-2026).

Method mirrors scripts/isd/build_n200_membership.py: per-leg backward walk
from today's official lists, forward replay to intervals, era-correct
relabeling across the 31 dated renames. Internal N50<->Next50 transfers
cancel in the union by construction.

Provenance rules (do not soften):
- n200_events is read-only input. This build never mutates it.
- Every deviation from the raw streams lives in OVERRIDES below with
  evidence (recon finding + PR file + MCWB months). An empty OVERRIDES
  with green gates would be ideal; each entry must earn its place.
- LAUNCH_DATE is the corpus start (first effective date), NOT an index
  launch. Pre-corpus membership is MCWB-attested (2010) and out of scope.
- Staged future-effective events (the Sep-2026 review, eff 2026-09-30)
  are excluded from the walk by the ANCHOR_DATE cap, as in the N200 build.

Gates:
  G1  zero backward/forward breaks per leg
  G2  event-flow counts == 50 per leg except manifest-documented months
      (N50 at 51: 2016-04..2017-08 Tata DVR era, 2023-08, 2025-01, 2025-02;
       Next50 at 49: 2020-09, 2020-10)
  G3  walk-implied month-end sets == MCWB month sets, all valid months
  G4  terminal open sets == anchors exactly
  G5  N100 union count == 100 except months implied by G2 allowlist
  G6  pre-listing screen (report-only): intervals pre-dating first trade

Usage:
    python scripts/isd/build_n100_membership.py
"""

import calendar
import csv
import glob
import json
import os
import sys

import duckdb

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from build_n200_membership import (
    ANCHOR_DATE,
    SYMBOL_ALIASES,
    canonical_label,
    era_chain,
    load_rename_dates,
)
from download_mcwb_archives import (
    MANIFEST_PATH,
    REF_DIR,
    read_leg_members,
)

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
PR_DIR = os.path.join(ROOT, 'data', 'reference', 'nse_index_pr')
N200_DB = os.path.join(ROOT, 'data', 'isd', 'n200_membership.duckdb')
OUT_DB = os.path.join(ROOT, 'data', 'isd', 'n100_membership.duckdb')

LAUNCH_DATE = '2011-03-25'  # corpus start: first effective date in the streams

LEGS = (('NIFTY 50', 'n50'), ('NIFTY NEXT 50', 'next50'))

# (leg, year, month) -> expected count; everything else must read 50.
COUNT_ALLOW = {}
for _m in range(4, 13):
    COUNT_ALLOW[('NIFTY 50', 2016, _m)] = 51
for _m in range(1, 9):
    COUNT_ALLOW[('NIFTY 50', 2017, _m)] = 51
COUNT_ALLOW[('NIFTY 50', 2023, 8)] = 51
COUNT_ALLOW[('NIFTY 50', 2025, 1)] = 51
COUNT_ALLOW[('NIFTY 50', 2025, 2)] = 51
COUNT_ALLOW[('NIFTY NEXT 50', 2020, 9)] = 49
COUNT_ALLOW[('NIFTY NEXT 50', 2020, 10)] = 49

# Event-level overrides. Format:
#   ('drop', index_norm, effective, action, symbol, reason)
#   ('add', index_norm, effective, action, symbol, company, reason)
# Seeded ONLY from investigated walker breaks / MCWB-gate mismatches.
#
# Evidence key:
#   R1 recon 2012-MAR Next50 PR-ONLY ASIANPAINT + MCWB apr12 (N50 only)
#   R2 recon 2012-SEP Next50 PR-ONLY ULTRACEMCO + MCWB oct12 (N50 only)
#   R3 recon 2013-SEP Next50 PR-ONLY WIPRO/RELINFRA + MCWB oct13
#   R4 recon 2014-MAR: N50 moves absent from N50 stream, booked in the
#      Next50 stream of ind_prs27022014.pdf + MCWB Feb/Apr-14 leg sets
#   R5 May-2017 GRASIM/VEDL swap: zero broad-market PR rows in corpus;
#      MCWB apr17->may17 (GRASIM 50->--, VEDL NX->50); same-event strategy
#      exclusion eff 2017-05-26 in ind_prs09052017.pdf supplies the date
#      (eff_src inferred, stated). GRASIM re-entry 2018-04-02 is PR-covered.
#   R6 Mar-2020: N50 pair eff 2020-03-27 (ind_prs18022020) is the void-tranche
#      doublet of the executed 2020-03-19 rebalance (ind_prs16032020);
#      MCWB mar20 already reflects SHREECEM-in/YESBANK-out. Cf N200
#      VOID_COVID_DATE. n200_events is NOT amended (frozen artifact).
#   R7 ACC transient hole: Next50 Sep+Oct-2020 reports list 49 with Sr.No 1
#      missing; ACC returns Nov-2020 (oct->nov diff = +ACC, nothing else).
#      Zero PR rows anywhere for either move. Exit dated to the Sep-2020
#      review batch (2020-09-25, stated inference); re-entry dated to the
#      first trading day of the post month (2020-11-02, stated convention).
#      Treated as genuine (renumbered reports) over clerical-error theory.
#   R8 demerger/listing transients, zero PR rows anywhere in corpus:
#      JIOFIN listed 2023-08-21 (first trade, equity_bhavcopy), present only
#      in the Aug-2023 N50 snapshot (the transient 51st; DUMMYREL placeholder
#      in Jul-2023 reserves the slot). Entry at listing date; exit at
#      bracket-start 2023-09-01 (stated +-30d; exit bracket Aug/Sep-23).
#      ITCHOTELS listed 2025-01-29 (first trade), present Jan+Feb-2025
#      snapshots (transient 51st). Entry at listing date; exit dated to the
#      Mar-2025 review batch 2025-03-28 (sibling BPCL/BRITANNIA outs PR-covered).
OVERRIDES = [
    ('drop', 'NIFTY NEXT 50', '2012-04-27', 'include', 'ASIANPAINT', 'R1'),
    ('drop', 'NIFTY NEXT 50', '2012-09-28', 'include', 'ULTRACEMCO', 'R2'),
    ('drop', 'NIFTY NEXT 50', '2013-09-27', 'include', 'WIPRO', 'R3'),
    ('drop', 'NIFTY NEXT 50', '2013-09-27', 'exclude', 'RELINFRA', 'R3'),
    ('drop', 'NIFTY NEXT 50', '2014-03-28', 'exclude', 'JPASSOCIAT', 'R4'),
    ('drop', 'NIFTY NEXT 50', '2014-03-28', 'exclude', 'RANBAXY', 'R4'),
    ('drop', 'NIFTY NEXT 50', '2014-03-28', 'exclude', 'INFRATEL', 'R4'),
    ('drop', 'NIFTY 50', '2020-03-27', 'exclude', 'YESBANK', 'R6'),
    ('drop', 'NIFTY 50', '2020-03-27', 'include', 'SHREECEM', 'R6'),
    ('add', 'NIFTY 50', '2014-03-28', 'exclude', 'JPASSOCIAT',
     'Jaiprakash Associates Ltd.', 'R4 xstream'),
    ('add', 'NIFTY 50', '2014-03-28', 'exclude', 'RANBAXY',
     'Ranbaxy Laboratories Ltd.', 'R4 xstream'),
    ('add', 'NIFTY 50', '2014-03-28', 'include', 'TECHM',
     'Tech Mahindra Ltd.', 'R4 xstream'),
    ('add', 'NIFTY 50', '2014-03-28', 'include', 'MCDOWELL-N',
     'United Spirits Ltd.', 'R4 xstream'),
    ('add', 'NIFTY 50', '2017-05-26', 'exclude', 'GRASIM',
     'Grasim Industries Ltd.', 'R5 inferred-date xstream'),
    ('add', 'NIFTY 50', '2017-05-26', 'include', 'VEDL',
     'Vedanta Ltd.', 'R5 inferred-date xstream'),
    ('add', 'NIFTY NEXT 50', '2017-05-26', 'exclude', 'VEDL',
     'Vedanta Ltd.', 'R5 inferred-date xstream'),
    ('add', 'NIFTY NEXT 50', '2017-05-26', 'include', 'SUNTV',
     'Sun TV Network Ltd.', 'R5 inferred-date xstream'),
    ('add', 'NIFTY NEXT 50', '2020-09-25', 'exclude', 'ACC',
     'ACC Ltd.', 'R7 batch-date xstream (Sep-2020 review)'),
    ('add', 'NIFTY NEXT 50', '2020-11-02', 'include', 'ACC',
     'ACC Ltd.', 'R7 post-month-first-trading-day convention xstream'),
    ('add', 'NIFTY 50', '2023-08-21', 'include', 'JIOFIN',
     'Jio Financial Services Ltd.', 'R8 listing-date xstream'),
    ('add', 'NIFTY 50', '2023-09-01', 'exclude', 'JIOFIN',
     'Jio Financial Services Ltd.', 'R8 bracket-start xstream'),
    ('add', 'NIFTY 50', '2025-01-29', 'include', 'ITCHOTELS',
     'ITC Hotels Ltd.', 'R8 listing-date xstream'),
    ('add', 'NIFTY 50', '2025-03-28', 'exclude', 'ITCHOTELS',
     'ITC Hotels Ltd.', 'R8 batch-date xstream (Mar-2025 review)'),
]


def load_anchor_n100_next50():
    cands = sorted(glob.glob(os.path.join(PR_DIR, 'ind_niftynext50list_*.csv')))
    if not cands:
        raise SystemExit('next50 anchor CSV missing')
    anchor = {}
    with open(cands[-1], encoding='utf-8') as f:
        for r in csv.DictReader(f):
            sym = (r.get('Symbol') or '').strip().upper()
            if sym:
                anchor[sym] = (r.get('Company Name') or '').strip()
    return anchor, os.path.basename(cands[-1])


def load_anchor_n100():
    cands = sorted(glob.glob(os.path.join(PR_DIR, 'ind_nifty100list_*.csv')))
    if not cands:
        raise SystemExit('n100 anchor CSV missing')
    out = set()
    with open(cands[-1], encoding='utf-8') as f:
        for r in csv.DictReader(f):
            sym = (r.get('Symbol') or '').strip().upper()
            if sym:
                out.add(sym)
    return out, os.path.basename(cands[-1])


def load_leg_events(idx):
    """Walkable (effective, action, symbol, company, pr_file) for one leg."""
    con = duckdb.connect(N200_DB, read_only=True)
    rows = con.execute(
        "select effective_date, action, symbol, company, pr_file from n200_events "
        "where index_norm = ? and action in ('include','exclude') "
        "and symbol is not null and symbol <> '' "
        "and symbol_status not in ('superseded','duplicate','void_covid') "
        "and effective_date <= ?", [idx, ANCHOR_DATE]).fetchall()
    con.close()
    return [(str(e), a, s, c, p) for e, a, s, c, p in rows]


def apply_overrides(evs):
    evs = [list(e) for e in evs]
    for ov in OVERRIDES:
        if ov[0] == 'drop':
            _, idx, eff, act, sym, _reason = ov
            before = len(evs)
            evs = [e for e in evs
                   if not (e[5] == idx and e[0] == eff and e[1] == act and e[2] == sym)]
            if len(evs) == before:
                raise SystemExit(f'override drop matched nothing: {ov}')
        elif ov[0] == 'add':
            _, idx, eff, act, sym, co, _reason = ov
            evs.append([eff, act, sym, co, 'OVERRIDE', idx])
        else:
            raise SystemExit(f'bad override: {ov}')
    return evs


def walk_leg(idx, anchor, evs, canon):
    """Backward walk + forward replay. Returns dict with state and intervals."""
    by_date = {}
    for e in evs:
        by_date.setdefault(e[0], []).append(e)
    state = set(canon(s) for s in anchor)
    breaks = []
    for d in sorted(by_date, reverse=True):
        for e in reversed(by_date[d]):
            sym = canon(e[2])
            if e[1] == 'include':
                if sym not in state:
                    breaks.append((d, 'reverse-include-absent', sym, e[3], e[4]))
                else:
                    state.discard(sym)
            else:
                if sym in state:
                    breaks.append((d, 'reverse-exclude-present', sym, e[3], e[4]))
                else:
                    state.add(sym)
    n_backward = len(breaks)
    fwd = set(state)
    open_from = {s: LAUNCH_DATE for s in sorted(state)}
    for d in sorted(by_date):
        for e in by_date[d]:
            sym = canon(e[2])
            if e[1] == 'include':
                if sym in fwd:
                    breaks.append((d, 'forward-include-present', sym, e[3], e[4]))
                else:
                    fwd.add(sym)
                    open_from[sym] = d
            else:
                if sym not in fwd:
                    breaks.append((d, 'forward-exclude-absent', sym, e[3], e[4]))
                else:
                    fwd.discard(sym)
    counts = [(LAUNCH_DATE, len(state))]
    run = len(state)
    for d in sorted(by_date):
        run += sum(1 for e in by_date[d] if e[1] == 'include') - \
            sum(1 for e in by_date[d] if e[1] == 'exclude')
        counts.append((d, run))
    return {'by_date': by_date, 'breaks': breaks, 'n_backward': n_backward,
            'fwd': fwd, 'open_from': open_from, 'counts': counts,
            'launch': set(state)}


def month_end_sets(legs_data, canon):
    """{(y, m, leg): frozenset} — walk-implied membership at each month-end."""
    out = {}
    for idx, leg in LEGS:
        fwd = set(legs_data[idx]['launch'])
        cur_y, cur_m = 2011, 3
        evs = sorted(legs_data[idx]['by_date'].items())
        ei = 0
        y, m = 2011, 3
        while (y, m) <= (2026, 7):
            while ei < len(evs) and evs[ei][0] <= f'{y}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}':
                for e in evs[ei][1]:
                    sym = canon(e[2])
                    if e[1] == 'include':
                        fwd.add(sym)
                    else:
                        fwd.discard(sym)
                ei += 1
            out[(y, m, leg)] = frozenset(fwd)
            m += 1
            if m == 13:
                m, y = 1, y + 1
    return out


def mcwb_sets(canon):
    """{(y, m, leg): frozenset} for manifest-valid months."""
    manifest = json.loads(open(MANIFEST_PATH, encoding='utf-8').read())
    out = {}
    for r in manifest['records']:
        if r['status'] != 'valid':
            continue
        y, mo = int(r['month'][:4]), int(r['month'][5:7])
        members = read_leg_members(REF_DIR / r['filename'])
        for _, leg in LEGS:
            out[(y, mo, leg)] = frozenset(canon(t) for t in members[leg] if t)
    return out


def main():
    if os.path.exists(OUT_DB):
        os.remove(OUT_DB)
    rename_dates = load_rename_dates()
    # N100-owned extension: INFOSYSTCH->INFY (eff 2011-06-29) predates the
    # N200 LAUNCH (2011-07-19) so the N200 build never needed it; the N100
    # corpus start (2011-03-25) does. Asserted from symbol_changes, same as
    # the base pairs. The N200 build and its pair list are untouched.
    RENAME_EXTRA = [('INFOSYSTCH', 'INFY')]
    eqdb0 = os.path.join(ROOT, 'data', 'market_data', 'equity_bhavcopy.duckdb')
    con0 = duckdb.connect(eqdb0, read_only=True)
    for old, new in RENAME_EXTRA:
        row = con0.execute(
            'select effective_dt from symbol_changes '
            'where old_symbol=? and new_symbol=? order by effective_dt limit 1',
            [old, new]).fetchone()
        if row is None:
            raise SystemExit(f'extra rename pair missing: {(old, new)}')
        rename_dates[old] = (new, str(row[0]))
    con0.close()
    print('rename pairs loaded:', len(rename_dates), flush=True)

    def canon(s):
        if not s or not s.strip():
            return None
        s = s.strip().upper()
        return canonical_label(SYMBOL_ALIASES.get(s, s), rename_dates)

    anchor_nx, nx_file = load_anchor_n100_next50()
    anchor_100, _ = load_anchor_n100()
    anchor_n50 = {s: '' for s in anchor_100 - set(anchor_nx)}
    print(f'anchors: N50={len(anchor_n50)} (N100[{nx_file}]-Next50) '
          f'Next50={len(anchor_nx)} [{nx_file}]', flush=True)
    if len(anchor_n50) != 50 or len(anchor_nx) != 50:
        raise SystemExit(
            f'anchor identity broken: N50={len(anchor_n50)} Next50={len(anchor_nx)}')
    # cross-check the derived N50 anchor against the independent current list
    ref50 = os.path.join(ROOT, 'data', 'reference', 'nifty50_constituents_current.csv')
    if os.path.exists(ref50):
        with open(ref50, encoding='utf-8') as f:
            ref = {(r.get('Symbol') or '').strip().upper()
                   for r in csv.DictReader(f) if (r.get('Symbol') or '').strip()}
        extra, missing = sorted(set(anchor_n50) - ref), sorted(ref - set(anchor_n50))
        print(f'N50 anchor vs nifty50_constituents_current.csv: '
              f'extra={extra} missing={missing}', flush=True)
        if extra or missing:
            raise SystemExit('N50 anchor disagrees with independent current list')

    anchors = {'NIFTY 50': anchor_n50, 'NIFTY NEXT 50': anchor_nx}
    legs_data, names = {}, {}
    tagged_all = []
    for idx, _leg in LEGS:
        for e in load_leg_events(idx):
            tagged_all.append([e[0], e[1], e[2], e[3], e[4], idx])
    tagged_all = apply_overrides(tagged_all)
    for idx, _leg in LEGS:
        core = [(e[0], e[1], e[2], e[3], e[4])
                for e in tagged_all if e[5] == idx]
        for e in core:
            names.setdefault(canon(e[2]), e[3])
        legs_data[idx] = walk_leg(idx, anchors[idx], core, canon)
        names.update({canon(s): c for s, c in anchors[idx].items()})
        ld = legs_data[idx]
        print(f'{idx}: events={len(core)} backward_breaks={ld["n_backward"]} '
              f'forward_breaks={len(ld["breaks"]) - ld["n_backward"]} '
              f'launch={len(ld["launch"])} terminal={len(ld["fwd"])}', flush=True)
        for b in ld['breaks'][:30]:
            print('  BREAK', idx, b, flush=True)

    con = duckdb.connect(OUT_DB)
    con.execute('create table n100_audit (check_name VARCHAR, detail VARCHAR)')
    audit = []

    # G1: breaks. Summary rows are written on pass too, so a passing gate leaves evidence.
    for idx, _leg in LEGS:
        ld = legs_data[idx]
        audit.append((f'G1_{idx}_backward_breaks', str(ld['n_backward'])))
        audit.append((f'G1_{idx}_forward_breaks', str(len(ld['breaks']) - ld['n_backward'])))
        for b in ld['breaks']:
            audit.append((f'{idx}_break', '|'.join(str(x) for x in b)))

    # G2: counts
    for idx, _leg in LEGS:
        bad = []
        for d, n in legs_data[idx]['counts']:
            y, m = int(d[:4]), int(d[5:7])
            want = COUNT_ALLOW.get((idx, y, m), 50)
            if n != want:
                bad.append((d, n, want))
        print(f'{idx}: count violations: {len(bad)}', flush=True)
        for d, n, want in bad:
            print(f'  COUNT {idx} {d}={n} (want {want})', flush=True)
        audit.append((f'{idx}_count_violations', str(len(bad))))
        for d, n, want in bad:
            audit.append((f'{idx}_count', f'{d}|{n}|want={want}'))

    # G3: MCWB month-end agreement
    wsets, msets = month_end_sets(legs_data, canon), mcwb_sets(canon)
    n_mm = 0
    for key in sorted(msets):
        y, m, leg = key
        if (y, m) < (2011, 3):
            continue
        want, got = msets[key], wsets.get(key, frozenset())
        extra, missing = sorted(got - want), sorted(want - got)
        if extra or missing:
            n_mm += 1
            audit.append(('mcwb_mismatch',
                          f'{y}-{m:02d}|{leg}|extra={",".join(extra)}|'
                          f'missing={",".join(missing)}'))
    n_g3 = sum(1 for k in msets if (k[0], k[1]) >= (2011, 3))
    print(f'G3 mcwb months compared: {n_g3}, mismatched: {n_mm}', flush=True)
    audit.append(('G3_mcwb_leg_months_compared', str(n_g3)))
    audit.append(('G3_mcwb_leg_months_mismatched', str(n_mm)))

    # G4: terminal identity per leg
    for idx, _leg in LEGS:
        anchor_canon = set(canon(s) for s in anchors[idx])
        fwd = legs_data[idx]['fwd']
        te, tm = sorted(fwd - anchor_canon), sorted(anchor_canon - fwd)
        print(f'{idx}: terminal EXTRA={te} MISSING={tm}', flush=True)
        audit.append((f'{idx}_terminal_extra', '|'.join(te)))
        audit.append((f'{idx}_terminal_missing', '|'.join(tm)))

    # union -> N100 intervals (canonical), then era-split
    spans = {}
    for idx, _leg in LEGS:
        by_date = legs_data[idx]['by_date']
        cur = set(legs_data[idx]['launch'])
        open100 = {s: LAUNCH_DATE for s in cur}
        live = dict(open100)
        for d in sorted(by_date):
            for e in by_date[d]:
                sym = canon(e[2])
                if e[1] == 'include':
                    if sym not in cur:
                        live[sym] = d
                    cur.add(sym)
                else:
                    if sym in cur:
                        spans.setdefault(sym, []).append((live.pop(sym), d))
                    cur.discard(sym)
        for s, vf in live.items():
            spans.setdefault(s, []).append((vf, None))
    # merge contiguous spans per symbol (transfers create back-to-back spans)
    intervals = []
    for sym, ss in spans.items():
        ss.sort(key=lambda t: (t[0], t[1] or 'zzzz'))
        merged = []
        for vf, vt in ss:
            if merged and merged[-1][1] == vf:
                merged[-1][1] = vt
            else:
                merged.append([vf, vt])
        for vf, vt in merged:
            for lab, bgn, end in era_chain(sym, rename_dates):
                lo = vf if bgn is None or vf >= bgn else bgn
                if vt is None:
                    hi = end
                elif end is None:
                    hi = vt
                else:
                    hi = min(vt, end)
                if hi is None or lo < hi:
                    intervals.append((lab, names.get(sym, ''), lo, hi))
    # G5: union month-end counts vs MCWB union
    n_u5 = 0
    g5_months = sorted({(k[0], k[1]) for k in msets if (k[0], k[1]) >= (2011, 3)})
    for (y, m) in g5_months:
        want = len(msets.get((y, m, 'n50'), ())) + len(msets.get((y, m, 'next50'), ()))
        wset = (wsets.get((y, m, 'n50'), frozenset())
                | wsets.get((y, m, 'next50'), frozenset()))
        if len(wset) != want:
            n_u5 += 1
            audit.append(('union_count',
                          f'{y}-{m:02d}|walk={len(wset)}|mcwb={want}'))
    print(f'G5 union-count mismatches: {n_u5}', flush=True)
    audit.append(('G5_union_months_compared', str(len(g5_months))))
    audit.append(('G5_union_months_mismatched', str(n_u5)))

    con.execute('create table n100_membership (symbol VARCHAR, company VARCHAR, '
                'valid_from DATE, valid_to DATE)')
    con.executemany('insert into n100_membership values (?,?,?,?)', intervals)
    audit.append(('intervals', str(len(intervals))))
    audit.append(('overrides', str(len(OVERRIDES))))
    for ov in OVERRIDES:
        audit.append(('override', '|'.join(str(x) for x in ov)))
    con.executemany('insert into n100_audit values (?,?)', audit)

    # G6: pre-listing screen (report-only)
    eqdb = os.path.join(ROOT, 'data', 'market_data', 'equity_bhavcopy.duckdb')
    con.execute(f"attach '{eqdb}' as eq (read_only)")
    pre = con.execute(
        'select m.symbol, m.valid_from, f.ft from n100_membership m '
        'left join (select symbol, min(trade_date) ft from eq.equity_bhavcopy '
        'group by 1) f on f.symbol = m.symbol '
        'where f.ft is null or f.ft > m.valid_from + INTERVAL 5 DAY '
        'order by f.ft - m.valid_from desc').fetchall()
    con.execute('detach eq')
    print('G6 pre-listing intervals:', len(pre), flush=True)
    for s, vf, ft in pre[:20]:
        print(f'  PRELIST {s} from {vf}, first trade {ft}', flush=True)
    con.executemany('insert into n100_audit values (?,?)',
                    [('pre_listing_intervals', str(len(pre)))] +
                    [('pre_listing', f'{s}|{vf}|{ft}') for s, vf, ft in pre])
    con.close()
    print('wrote', OUT_DB, flush=True)


if __name__ == '__main__':
    main()
