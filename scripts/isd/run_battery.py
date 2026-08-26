"""ISD battery orchestrator — frozen TRAIN pass, then HOLDOUT if TRAIN passes.

Implements ISD_PHASE0_PRE_REGISTRATION §5-§9:
  - TRAIN 2023-01-02..2024-11-30: 4 cells/family; per-cell rank IC + random-entry
    null p (1,000 iters) vs BH alpha 0.0125; >=2 of 4 qualify; family = equal-
    weighted qualifying cells; family IC NW t + circular-shift null p (1,000 iters)
    one-sided alpha 0.05; net spread > 0 at measured tau (EOD-flat => tau = 2).
  - F4 sign registered to the trial ledger BEFORE cell verdicts (CARRY precedent;
    m = 2 disclosed).
  - HOLDOUT 2024-12-01..2025-12-31: one test per family on the FROZEN qualifying
    book; alpha 0.05 one-sided NW t + net spread > 0.
  - SEALED sessions are REFUSED by this script (spend floor n >= 317 not reached).

Ledger: data/isd/trial_ledger.jsonl — append-only, rows written as computed
(before later cells/results), sign-registration row first for F4.
Usage:
    python scripts/isd/run_battery.py [--train-only] [--null-iters 1000]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.isd import (
    CANONICAL_CAPITAL, ISD_DATA_DIR, REPORT_DIR, eq_sessions,
)
from scripts.isd import battery_features as bf
from scripts.isd import battery_stats as bs
from core.execution.equity.intraday_fees import round_trip_fees

TRAIN_LO, TRAIN_HI = "2023-01-02", "2024-11-30"
HOLD_LO, HOLD_HI = "2024-12-01", "2025-12-31"
ALPHA_CELL = 0.05 / 4          # BH per-cell (frozen §6)
ALPHA_FAMILY = 0.05
SEED = 42
LEDGER = ISD_DATA_DIR / "trial_ledger.jsonl"
SNAPSHOT = ISD_DATA_DIR / "battery_train_snapshot.json"
REPORT = REPORT_DIR / "ISD_BATTERY_TRAIN_REPORT.md"
REPORT_HOLD = REPORT_DIR / "ISD_BATTERY_HOLDOUT_REPORT.md"
PREREG = REPORT_DIR / "ISD_PHASE0_PRE_REGISTRATION.md"

# F1 cells: (id, entry column, window-end close column); F4: (id, entry column)
F1_CELLS = [("w0945", "open0946", "close0945"), ("w1000", "open1001",
                                                   "close1000")]
F4_CELLS = [("e_open", "open0916", None), ("e_close", "close0916", None)]
BANDS = (0.20, 0.40)


def _slip_bands() -> dict:
    snap = json.loads((ISD_DATA_DIR / "ISD_PHASE1_SNAPSHOT.json").read_text())
    return {r["decile"]: r["drift_p90_abs_bps"]
            for r in snap["results"]["G6"]["slippage"]["pooled_by_decile"]}


def _ledger(row: dict):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")


def _matrices(frames: list, cols: list) -> tuple:
    """Global symbol axis; per-session rows reindexed (NaN where absent)."""
    syms = sorted(set().union(*(fr.index for _s, fr in frames)))
    s_idx = pd.Index(syms)
    mats = {c: np.full((len(frames), len(syms)), np.nan) for c in cols}
    for i, (_iso, fr) in enumerate(frames):
        r = fr.reindex(s_idx)
        for c in cols:
            mats[c][i] = r[c].to_numpy(dtype=float)
    return syms, mats


def _cell_matrices(mats, entry_col, close_col):
    """(feat, label) global matrices for one cell; NaN where unusable."""
    if close_col is None:                       # F4: gap feature
        m = (mats["prev_close"] > 0) & ~mats["is_exdate"].astype(bool)
        feat = np.where(m, (mats["open0915"] - mats["prev_close"])
                        / mats["prev_close"], np.nan)
    else:                                       # F1: opening-drive
        m = mats[close_col] > 0
        feat = np.where(m, (mats[close_col] - mats["open0915"])
                        / mats["open0915"], np.nan)
    entry = mats[entry_col]
    label = np.where((entry > 0) & (mats["close1529"] > 0),
                     (mats["close1529"] - entry) / entry, np.nan)
    return feat, label


def _book_pnl(feat1d, label1d, slip1d, adv1d, band):
    """Weighted L/S book for one session: gross bp, mean slip bp, k.

    feat1d/label1d/slip1d/adv1d are the session's valid-name arrays (top-long
    orientation; the family sign is applied post-registration by the caller).
    """
    n = len(feat1d)
    k = max(1, round(band * n))
    order = np.argsort(feat1d)
    longs, shorts = order[-k:], order[:k]

    def _side(idx):
        w = np.full(k, 0.5 / k)
        for j, i in enumerate(idx):
            if adv1d[i] > 0:
                w[j] = min(w[j], bf.ADV_CAP * adv1d[i] / CANONICAL_CAPITAL)
        w = w / w.sum() * 0.5
        return w

    wl, ws = _side(longs), _side(shorts)
    gross = float(np.sum(wl * label1d[longs]) - np.sum(ws * label1d[shorts]))
    slip = float(np.nanmean(np.r_[slip1d[longs], slip1d[shorts]])) \
        if not np.isnan(np.r_[slip1d[longs], slip1d[shorts]]).all() else np.nan
    return {"gross_bp": gross * 1e4, "slip_bp": slip, "k": k}


def _slip_per_name(dvol1d, slip_map):
    """Per-name slippage (bp) from the G6 pooled bands by liquidity decile."""
    n = len(dvol1d)
    order = np.argsort(np.argsort(dvol1d))            # 0..n-1, ascending dvol
    dec = (np.floor(order / n * 10).astype(int)).clip(0, 9) + 1
    return np.array([slip_map[d] for d in dec])


def cell_pass(cid, band, mats, syms, sign, slip_map, adv_by_session, sessions,
              null_iters, rng) -> dict:
    entry_col, close_col = _cols_of(cid)
    feat, label = _cell_matrices(mats, entry_col, close_col)
    ic = bs.per_session_ic(feat, label)
    st = bs.series_stats(ic)
    nulls = bs.random_entry_null(feat, label, rng, iters=null_iters)
    p_one = bs.empirical_p(st["mean_ic"], nulls, sign)
    gross = np.full(len(sessions), np.nan)
    slip = np.full(len(sessions), np.nan)
    fee = np.full(len(sessions), np.nan)
    for i, (iso, _p) in enumerate(sessions):
        valid = ~np.isnan(feat[i]) & ~np.isnan(label[i]) & (mats["prev_close"][i] > 0)
        if valid.sum() < bf.MIN_NAMES:
            continue
        b = _book_pnl(feat[i][valid], label[i][valid],
                      _slip_per_name(mats["dvol"][i][valid], slip_map),
                      np.array([adv_by_session.get(iso, {}).get(s, 0.0)
                                for s in np.array(syms)[valid]]),
                      band)
        gross[i] = b["gross_bp"]            # raw orientation (top-long); the
        slip[i] = b["slip_bp"]              # family sign is applied post-registration
        d = dt.date.fromisoformat(iso)
        ticket = CANONICAL_CAPITAL * 0.5 / max(b["k"], 1)
        fee[i] = round_trip_fees(entry_value=ticket, exit_value=ticket,
                                 entry_date=d).total / ticket * 1e4
    net = bs.net_spread_series(gross, slip, fee)
    return {"cell": cid, "band": band, "ic_series": ic, "stats": st,
            "null_p_one_sided": p_one, "null_mean": float(np.nanmean(nulls)),
            "null_sd": float(np.nanstd(nulls)),
            "null_z": float((st["mean_ic"] - np.nanmean(nulls))
                            / max(np.nanstd(nulls), 1e-12)),
            "gross_bp": gross, "slip_bp": slip, "fee_bp": fee,
            "net_spread_bp": net, "net_total_bp": float(np.nansum(net)),
            "tau": 2.0, "qualifies": p_one <= ALPHA_CELL}


def family_result(fam, cells, month_starts, mats, sign, null_iters,
                  rng) -> dict:
    quals = [c for c in cells if c["qualifies"]]
    if len(quals) < 2:
        return {"qualifying": [c["cell"] for c in quals],
                "family_ic": {"n": 0, "mean_ic": float("nan"),
                              "t_nw": 0.0, "ac1": 0.0},
                "p_family_shift": float("nan"),
                "shift_null_mean": float("nan"),
                "shift_null_sd": float("nan"),
                "net_total_bp": 0.0, "pass": False}
    ic_mat = np.vstack([c["ic_series"] for c in quals])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        fam_ic = np.nanmean(ic_mat, axis=0)
    st = bs.series_stats(fam_ic)
    shift_nulls = _family_shift_nulls(quals, mats, month_starts, sign,
                                      null_iters, rng)
    p_fam = bs.empirical_p(st["mean_ic"], shift_nulls, sign)
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        gross = np.nanmean(np.vstack([c["gross_bp"] for c in quals]), axis=0)
        slip = np.nanmean(np.vstack([c["slip_bp"] for c in quals]), axis=0)
        fee = np.nanmean(np.vstack([c["fee_bp"] for c in quals]), axis=0)
        net = bs.net_spread_series(gross, slip, fee)
    return {"qualifying": [c["cell"] for c in quals], "family_ic": st,
            "p_family_shift": p_fam, "shift_null_mean":
            float(np.nanmean(shift_nulls)),
            "shift_null_sd": float(np.nanstd(shift_nulls)),
            "net_total_bp": float(np.nansum(net)),
            "pass": (len(quals) >= 2 and p_fam <= ALPHA_FAMILY
                     and float(np.nansum(net)) > 0)}


def _family_shift_nulls(cells, mats, month_starts, sign, null_iters, rng):
    """Month-block rotation null on the cell features (label matrix fixed)."""
    n_s, n_c = mats["open0915"].shape
    bounds = [b for b in month_starts if b < n_s] + [n_s]
    blocks = list(zip(bounds[:-1], bounds[1:]))
    n_b = len(blocks)
    nulls = np.empty(null_iters)
    cell_ics = []
    for c in cells:
        entry_col, close_col = _cols_of(c["cell"])
        f, l = _cell_matrices(mats, entry_col, close_col)
        cell_ics.append((f, l))
    for it in range(null_iters):
        k = rng.integers(1, n_b)
        fam_ics = []
        for f, l in cell_ics:
            shifted = np.vstack([f[a:b] for (a, b) in
                                 (blocks[(j - k) % n_b] for j in range(n_b))])
            fam_ics.append(bs.per_session_ic(shifted, l))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            fam_ic = np.nanmean(np.vstack(fam_ics), axis=0)
        nulls[it] = float(np.nanmean(fam_ic)) if not np.isnan(fam_ic).all() \
            else np.nan
    return nulls


def _cols_of(cid):
    return {"w0945": ("open0946", "close0945"),
            "w1000": ("open1001", "close1000"),
            "e_open": ("open0916", None),
            "e_close": ("close0916", None)}[cid]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-only", action="store_true")
    parser.add_argument("--null-iters", type=int, default=1000)
    args = parser.parse_args()

    all_sessions = eq_sessions()
    train = [(s, p) for s, p in all_sessions if TRAIN_LO <= s <= TRAIN_HI]
    hold = [(s, p) for s, p in all_sessions if HOLD_LO <= s <= HOLD_HI]
    # SEALED guard: the fences never include SEALED dates; if a future edit
    # leaks one in, refuse (spend floor n >= 317 not reached; SEALED untouchable).
    leaked = [s for s, _p in train + hold if s >= "2026-01-01"]
    if leaked:
        raise SystemExit(f"REFUSED: SEALED sessions leaked into fences: {leaked}")

    rng = np.random.default_rng(SEED)
    slip_map = _slip_bands()
    prereg_sha = hashlib.sha256(Path(PREREG).read_bytes()).hexdigest()[:16]
    run_id = dt.datetime.now().isoformat(timespec="seconds")
    _ledger({"event": "run_start", "run_id": run_id, "seed": SEED,
             "prereg_sha": prereg_sha, "null_iters": args.null_iters,
             "train_sessions": len(train), "hold_sessions": len(hold)})

    frames = bf.build(train)
    used_isos = {iso for iso, _p in frames}
    train_used = [(s, p) for s, p in train if s in used_isos]
    adv = bf.adv_series(frames)
    syms, mats = _matrices(frames, ["open0915", "close0945", "open0946",
                                    "close1000", "open1001", "open0916",
                                    "close0916", "close1529", "dvol",
                                    "prev_close", "is_exdate"])
    month_starts = [i for i, (s, _p) in enumerate(frames)
                    if i == 0 or frames[i - 1][0][:7] != s[:7]]

    results = {}
    for fam, cell_ids, sign_rule in (("F1", F1_CELLS, +1),
                                     ("F4", F4_CELLS, None)):
        cells = []
        for band in BANDS:
            for cid, _e, _c in cell_ids:
                cells.append(cell_pass(cid, band, mats, syms, sign_rule or 1,
                                       slip_map, adv, train_used,
                                       args.null_iters, rng))
        if sign_rule is None:
            raw = float(np.nanmean([np.nanmean(c["ic_series"]) for c in cells]))
            sign = +1 if raw >= 0 else -1
            _ledger({"run_id": run_id, "family": fam, "event":
                     "sign_registration", "sign": sign,
                     "raw_mean_ic": raw, "prereg_sha": prereg_sha})
            for c in cells:                 # book follows the registered sign
                c["gross_bp"] = sign * c["gross_bp"]
                c["net_spread_bp"] = bs.net_spread_series(
                    c["gross_bp"], c["slip_bp"], c["fee_bp"])
                c["net_total_bp"] = float(np.nansum(c["net_spread_bp"]))
        else:
            sign = sign_rule
        for c in cells:
            if sign_rule is None:
                c["null_p_one_sided"] = bs.empirical_p(c["stats"]["mean_ic"],
                                                       bs.random_entry_null(
                                                           *_cell_matrices(
                                                               mats, *_cols_of(
                                                                   c["cell"])),
                                                           rng,
                                                           args.null_iters),
                                                       sign)
                c["qualifies"] = c["null_p_one_sided"] <= ALPHA_CELL
            _ledger({"run_id": run_id, "family": fam, "event": "cell",
                     "cell": c["cell"], "band": c["band"],
                     "train_ic": c["stats"]["mean_ic"],
                     "nw_t": c["stats"]["t_nw"],
                     "ac1": c["stats"]["ac1"], "tau": c["tau"],
                     "gross_spread_bp": float(np.nanmean(c["gross_bp"])),
                     "net_spread_bp": float(np.nanmean(c["net_spread_bp"])),
                     "null_p": c["null_p_one_sided"], "null_z": c["null_z"],
                     "qualifies": c["qualifies"]})
        res = family_result(fam, cells, month_starts, mats, sign,
                            args.null_iters, rng)
        results[fam] = {"sign": sign, **res,
                        "cells": [{k: c[k] for k in ("cell", "band",
                                                     "null_p_one_sided",
                                                     "net_total_bp",
                                                     "qualifies")}
                                  for c in cells]}
        _ledger({"run_id": run_id, "family": fam, "event": "family",
                 "qualifying": res["qualifying"],
                 "family_ic": res["family_ic"]["mean_ic"],
                 "family_nw_t": res["family_ic"]["t_nw"],
                 "p_family_shift": res["p_family_shift"],
                 "net_total_bp": res["net_total_bp"], "pass": res["pass"]})

    snap = {"run_id": run_id, "prereg_sha": prereg_sha,
            "train_sessions": len(train), "results": results}
    SNAPSHOT.write_text(json.dumps(snap, indent=2, default=str))
    _write_report(snap, REPORT)
    print(json.dumps({fam: {k: v for k, v in r.items() if k != "cells"}
                      for fam, r in results.items()}, indent=2, default=str))

    if not args.train_only and all(r["pass"] for r in results.values()):
        return _run_holdout(results, args.null_iters, rng, prereg_sha, run_id,
                            slip_map)
    print("TRAIN verdict:", {fam: r["pass"] for fam, r in results.items()})
    return 0 if all(r["pass"] for r in results.values()) else 1


def _run_holdout(train_results, null_iters, rng, prereg_sha, run_id,
                 slip_map):
    all_sessions = eq_sessions()
    hold = [(s, p) for s, p in all_sessions if HOLD_LO <= s <= HOLD_HI]
    frames = bf.build(hold)
    adv = bf.adv_series(frames)
    _syms, mats = _matrices(frames, ["open0915", "close0945", "open0946",
                                     "close1000", "open1001", "open0916",
                                     "close0916", "close1529", "dvol",
                                     "prev_close", "is_exdate"])
    results = {}
    for fam, cell_ids, sign in (("F1", F1_CELLS, +1), ("F4", F4_CELLS, None)):
        quals = train_results[fam]["qualifying"]
        if sign is None:
            sign = train_results[fam]["sign"]
        cells = []
        for cid, _e, _c in cell_ids:
            for band in BANDS:
                c = cell_pass(cid, band, mats, _syms, sign, slip_map, adv,
                              hold, null_iters, rng)
                if c["cell"] in quals:
                    cells.append(c)
        ic_mat = np.vstack([c["ic_series"] for c in cells]) if cells else \
            np.full((1, len(mats["open0915"])), np.nan)
        fam_ic = np.nanmean(ic_mat, axis=0)
        st = bs.series_stats(fam_ic)
        gross = np.nanmean(np.vstack([c["gross_bp"] for c in cells]), axis=0) \
            if cells else np.full_like(fam_ic, np.nan)
        slip = np.nanmean(np.vstack([c["slip_bp"] for c in cells]), axis=0) \
            if cells else np.full_like(fam_ic, np.nan)
        fee = np.nanmean(np.vstack([c["fee_bp"] for c in cells]), axis=0) \
            if cells else np.full_like(fam_ic, np.nan)
        net = bs.net_spread_series(gross, slip, fee)
        results[fam] = {"qualifying": quals, "family_ic": st,
                        "net_total_bp": float(np.nansum(net)),
                        "pass": (st["p_nw_one_sided"] <= ALPHA_FAMILY
                                 and float(np.nansum(net)) > 0)}
        _ledger({"run_id": run_id, "family": fam, "event": "holdout",
                 "qualifying": quals, "family_ic": st["mean_ic"],
                 "nw_t": st["t_nw"], "p_nw_one_sided":
                 st["p_nw_one_sided"], "net_total_bp": results[fam][
                     "net_total_bp"], "pass": results[fam]["pass"]})
    snap = {"run_id": run_id, "prereg_sha": prereg_sha,
            "hold_sessions": len(hold), "results": results}
    (ISD_DATA_DIR / "battery_holdout_snapshot.json").write_text(
        json.dumps(snap, indent=2, default=str))
    _write_report(snap, REPORT_HOLD)
    print(json.dumps(results, indent=2, default=str))
    return 0 if all(r["pass"] for r in results.values()) else 1


def _write_report(snap, path):
    lines = ["# ISD Battery Report",
             "",
             f"Generated: {snap['run_id']} · prereg SHA-16 `{snap['prereg_sha']}` · "
             f"seed {SEED}",
             ""]
    if "train_sessions" in snap:
        lines += ["**TRAIN pass** — sessions: "
                  f"{snap['train_sessions']} (2023-01-02 → 2024-11-30)",
                  "", "| Family | Sign | Cells (p, qualifies) | Family IC | NW t | "
                  "p (shift null) | Net bp | Verdict |", "|---|---|---|---|---|---|---|---|"]
        for fam, r in snap["results"].items():
            cells = "; ".join(
                f"{c['cell']}@{c['band']}: {c['null_p_one_sided']:.4f} "
                f"{'✓' if c['qualifies'] else '✗'}" for c in r["cells"])
            lines.append(f"| {fam} | {r['sign']} | {cells} | "
                         f"{r['family_ic']['mean_ic']:.4f} | "
                         f"{r['family_ic']['t_nw']:.2f} | "
                         f"{r['p_family_shift']:.4f} | {r['net_total_bp']:.1f} | "
                         f"{'PASS' if r['pass'] else 'FAIL'} |")
        lines += ["", f"**TRAIN verdict: "
                  f"{'PASS' if all(r['pass'] for r in snap['results'].values()) else 'FAIL'}**"]
    else:
        lines += [f"**HOLDOUT pass** — sessions: {snap['hold_sessions']} "
                  f"(2024-12-01 → 2025-12-31)",
                  "", "| Family | Frozen cells | Family IC | NW t | p (one-sided) "
                  "| Net bp | Verdict |", "|---|---|---|---|---|---|---|"]
        for fam, r in snap["results"].items():
            lines.append(f"| {fam} | {', '.join(r['qualifying'])} | "
                         f"{r['family_ic']['mean_ic']:.4f} | "
                         f"{r['family_ic']['t_nw']:.2f} | "
                         f"{r['family_ic']['p_nw_one_sided']:.4f} | "
                         f"{r['net_total_bp']:.1f} | "
                         f"{'PASS' if r['pass'] else 'FAIL'} |")
        lines += ["", f"**HOLDOUT verdict: "
                  f"{'PASS' if all(r['pass'] for r in snap['results'].values()) else 'FAIL'}**"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
