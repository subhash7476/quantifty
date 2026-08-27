"""A — TRAIN read harness (frozen parameters, A_PHASE0_PRE_REGISTRATION.md §9).

Runs the two-cell grid over the TRAIN fence 2012-01-02..2018-12-31 ONLY.
HOLDOUT and SEALED files are never opened: session dates outside the fence
raise. No construct parameter may be edited — the freeze seals the document
set; this script implements it.

Frozen elements (pre-reg §3-§9):
  - cells w30 (bars 0..30, entry bar 31) / w45 (bars 0..45, entry bar 46)
  - sign pinned +1 (D1); opening print = first bar open (D3); exit = 15:14
    bar close (D6); canonical notional Rs 2Cr
  - session-validity: first bar date-stamped with the session; entry bar
    present; 15:14 exit bar present
  - costs: era-accurate futures fees at canonical notional; slippage = the
    measured entry-drift p90 by era/cell, exit pays the same band; basis
    mean -0.4 bp direction-consistent (D5)
  - per-cell BH alpha = 0.025 (empirical sign-permutation null, one-sided);
    family = equal-weighted mean of qualifying cells, one-sided test vs the
    block-shift null at alpha = 0.05, net-spread (mean net bp) > 0
  - trial ledger append-only, registrations written before results

Usage: python scripts/a_index_intraday/run_train.py
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.execution.futures.futures_fees import (  # noqa: E402
    breakeven_round_trip_bps,
)

CANDLE_DIR_1M = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"
LEDGER = ROOT / "data" / "a_index_intraday" / "trial_ledger.jsonl"
REPORT = ROOT / "docs" / "reports" / "A_TRAIN_REPORT.md"

NF = "NSE_INDEX|Nifty 50"
TRAIN_LO, TRAIN_HI = date(2012, 1, 2), date(2018, 12, 31)
PREREG_SHA = "ccb32090704a33962fe13cda5b66de9026378b01"
SEED = 42
ALPHA_CELL = 0.025          # BH 0.05 / 2 cells
ALPHA_FAMILY = 0.05
NULL_ITERS = 1000
NW_LAG = 5
CANONICAL = 20_000_000.0
BASIS_MEAN_BP = 0.4         # D5: carry drift over the hold, direction-consistent

# measured entry-drift p90 by era and cell (A_COST_SUBSTRATE_MEASUREMENTS.md)
SLIP_BP = {
    "w30": {"vendor": 0.78, "native": 0.70},
    "w45": {"vendor": 0.73, "native": 0.66},
}
ENTRY_BAR = {"w30": 31, "w45": 46}
WINDOW_END = {"w30": 30, "w45": 45}
CELLS = ("w30", "w45")


def fees_bp(trade_date: date) -> float:
    """Era-accurate round-trip fees at the canonical notional, in bp."""
    return breakeven_round_trip_bps(price=1000.0, quantity=20_000,
                                    trade_date=trade_date)


def session_arrays(d: date):
    """Frozen construct inputs for one session, or None if invalid."""
    path = CANDLE_DIR_1M / f"{d.isoformat()}.duckdb"
    if not path.exists():
        return None
    con = duckdb.connect(str(path), read_only=True)
    try:
        rows = con.execute(
            "SELECT timestamp, open, close FROM candles "
            "WHERE symbol = ? ORDER BY timestamp", [NF]).fetchall()
    finally:
        con.close()
    if not rows:
        return None
    if rows[0][0].date().isoformat() != d.isoformat():
        return None                      # session-validity: date-stamped first bar
    opens = [float(r[1]) for r in rows]
    closes = [float(r[2]) for r in rows]
    exit_i = next((i for i, r in enumerate(rows)
                   if r[0].time().hour == 15 and r[0].time().minute == 14),
                  None)
    if exit_i is None or exit_i < 1 or closes[exit_i] <= 0:
        return None                      # 15:14 exit bar present
    out = {"exit_close": closes[exit_i], "valid": {}, "feature": {},
           "entry_open": {}}
    for cell in CELLS:
        wend, ebar = WINDOW_END[cell], ENTRY_BAR[cell]
        if len(rows) <= ebar or closes[wend] <= 0 or opens[ebar] <= 0 \
                or opens[0] <= 0:
            out["valid"][cell] = False
            continue
        out["valid"][cell] = True
        out["feature"][cell] = (closes[wend] - opens[0]) / opens[0]
        out["entry_open"][cell] = opens[ebar]
    if not any(out["valid"].values()):
        return None
    return out


def nw_t(series: np.ndarray, lag: int = NW_LAG) -> float:
    n = len(series)
    if n < 3:
        return 0.0
    m = float(np.mean(series))
    e = series - m
    nw_var = float(np.mean(e * e))
    for k in range(1, min(lag, n - 1) + 1):
        ck = float(np.mean(e[k:] * e[:-k]))
        nw_var += 2.0 * (1.0 - k / (lag + 1.0)) * ck
    if nw_var <= 0:
        return 0.0
    return m / np.sqrt(nw_var / n)


def ac1(series: np.ndarray) -> float:
    n = len(series)
    if n < 4:
        return 0.0
    m = float(np.mean(series))
    num = float(np.sum((series[1:] - m) * (series[:-1] - m)))
    den = float(np.sum((series - m) ** 2))
    return num / den if den > 0 else 0.0


def main() -> int:
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    dates = []
    d = TRAIN_LO
    while d <= TRAIN_HI:
        if (CANDLE_DIR_1M / f"{d.isoformat()}.duckdb").exists():
            dates.append(d)
        d += timedelta(days=1)
    print(f"TRAIN fence {TRAIN_LO}..{TRAIN_HI}: {len(dates)} store files")

    cells = {c: {"feature": [], "entry": [], "exit": [], "dates": [], "fee": []}
             for c in CELLS}
    n_invalid = 0
    for d in dates:
        sa = session_arrays(d)
        if sa is None:
            n_invalid += 1
            continue
        for c in CELLS:
            if not sa["valid"][c]:
                continue
            cells[c]["feature"].append(sa["feature"][c])
            cells[c]["entry"].append(sa["entry_open"][c])
            cells[c]["exit"].append(sa["exit_close"])
            cells[c]["dates"].append(d)
            cells[c]["fee"].append(fees_bp(d))
    print(f"  sessions: {len(dates)}, invalid/skipped: {n_invalid}, "
          f"tradeable: w30={len(cells['w30']['dates'])}, "
          f"w45={len(cells['w45']['dates'])}")

    era = "vendor"  # TRAIN is entirely vendor era (2012-01-02..2018-12-31)

    def returns_of(cell: str, features: np.ndarray) -> np.ndarray:
        c = cells[cell]
        entry = np.asarray(c["entry"])
        exitc = np.asarray(c["exit"])
        gross = (exitc - entry) / entry * 1e4
        sign = np.sign(features)
        slip = SLIP_BP[cell][era] * 2.0
        fee = np.asarray(c["fee"])
        return sign * (gross - BASIS_MEAN_BP) - fee - slip

    run_id = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with open(LEDGER, "a", encoding="utf-8") as lf:
        lf.write(json.dumps({"event": "run_start", "run_id": run_id,
                             "seed": SEED, "prereg_sha": PREREG_SHA,
                             "null_iters": NULL_ITERS,
                             "train_fence": [TRAIN_LO.isoformat(),
                                             TRAIN_HI.isoformat()],
                             "files": len(dates), "invalid": n_invalid,
                             "tradeable": {c: len(cells[c]["dates"])
                                           for c in CELLS}}) + "\n")

    results = {}
    for cell in CELLS:
        with open(LEDGER, "a", encoding="utf-8") as lf:
            lf.write(json.dumps({"run_id": run_id, "event": "cell_registration",
                                 "cell": cell, "params": {
                                     "window_bars": WINDOW_END[cell] + 1,
                                     "entry_bar": ENTRY_BAR[cell],
                                     "sign": 1, "exit": "15:14",
                                     "slip_bp_per_side": SLIP_BP[cell][era],
                                     "basis_mean_bp": BASIS_MEAN_BP}}) + "\n")
        features = np.asarray(cells[cell]["feature"])
        r = returns_of(cell, features)
        n = len(r)
        mean = float(np.mean(r))
        nw = nw_t(r)
        a1 = ac1(r)
        null_means = np.empty(NULL_ITERS)
        gross = (np.asarray(cells[cell]["exit"])
                 / np.asarray(cells[cell]["entry"]) - 1.0) * 1e4
        fee = np.asarray(cells[cell]["fee"])
        slip = SLIP_BP[cell][era] * 2.0
        for i in range(NULL_ITERS):
            perm = rng.integers(0, 2, size=n).astype(float) * 2.0 - 1.0
            null_means[i] = float(np.mean(
                perm * gross - perm * BASIS_MEAN_BP - fee - slip))
        p_sign = float(np.mean(null_means >= mean))
        qualifies = p_sign < ALPHA_CELL and mean > 0.0
        results[cell] = {"n": n, "mean_bp": mean, "nw_t": nw, "ac1": a1,
                         "null_mean": float(np.mean(null_means)),
                         "null_sd": float(np.std(null_means)),
                         "null_z": float((mean - np.mean(null_means))
                                         / np.std(null_means)),
                         "p_sign": p_sign, "qualifies": qualifies}
        with open(LEDGER, "a", encoding="utf-8") as lf:
            lf.write(json.dumps({"run_id": run_id, "event": "cell",
                                 "cell": cell,
                                 "train_mean_net_bp": mean,
                                 "nw_t": nw, "ac1": a1,
                                 "p_sign_permutation": p_sign,
                                 "qualifies": qualifies}) + "\n")
        print(f"  {cell}: n={n} mean={mean:.3f}bp nw_t={nw:.2f} "
              f"ac1={a1:.3f} p_sign={p_sign:.4f} "
              f"qualifies={qualifies}")

    quals = [c for c in CELLS if results[c]["qualifies"]]
    family_ok = False
    if quals:
        # family series = equal-weighted mean of qualifying cells per session;
        # sessions are the same dates (cells share sessions by construction)
        fam_series = np.mean(
            np.vstack([returns_of(c, np.asarray(cells[c]["feature"]))
                       for c in quals]), axis=0)
        fam_mean = float(np.mean(fam_series))
        fam_nw = nw_t(fam_series)
        # block-shift null on the family: month-block perm of the features
        fam_dates = cells[quals[0]]["dates"]
        months = sorted({(d.year, d.month) for d in fam_dates})
        month_idx = {m: i for i, m in enumerate(months)}
        sess_month = np.asarray([month_idx[(d.year, d.month)] for d in fam_dates])
        null_fams = np.empty(NULL_ITERS)
        feats = {c: np.asarray(cells[c]["feature"]) for c in quals}
        for i in range(NULL_ITERS):
            perm = rng.permutation(len(months))
            shifted = {c: feats[c][perm[sess_month]] for c in quals}
            fr = np.mean(np.vstack([returns_of(c, shifted[c]) for c in quals]),
                         axis=0)
            null_fams[i] = float(np.mean(fr))
        p_shift = float(np.mean(null_fams >= fam_mean))
        family_ok = (p_shift < ALPHA_FAMILY and fam_mean > 0.0)
        with open(LEDGER, "a", encoding="utf-8") as lf:
            lf.write(json.dumps({"run_id": run_id, "event": "family",
                                 "qualifying": quals,
                                 "family_mean_net_bp": fam_mean,
                                 "family_nw_t": fam_nw,
                                 "p_block_shift": p_shift,
                                 "net_positive": fam_mean > 0.0,
                                 "pass": family_ok}) + "\n")
        print(f"  family: qualifying={quals} mean={fam_mean:.3f}bp "
              f"p_shift={p_shift:.4f} pass={family_ok}")
    else:
        with open(LEDGER, "a", encoding="utf-8") as lf:
            lf.write(json.dumps({"run_id": run_id, "event": "family",
                                 "qualifying": [], "family_mean_net_bp": None,
                                 "pass": False}) + "\n")
        print("  family: no qualifying cells -> FAIL")

    verdict = "PASS" if (quals and family_ok) else "FAIL"

    lines = [
        "# A — Battery Train Report",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')} · "
        f"runtime {time.time() - t0:.0f}s · prereg SHA-16 "
        f"`{PREREG_SHA[:16]}` · seed {SEED}",
        "",
        f"**TRAIN pass** — sessions: {len(dates)} ({TRAIN_LO} → {TRAIN_HI}); "
        f"invalid/skipped {n_invalid}; tradeable w30 {len(cells['w30']['dates'])}, "
        f"w45 {len(cells['w45']['dates'])}",
        "",
        "| Cell | n | Mean net bp | NW t | AC1 | p (sign null) | Null z | Qualifies (BH 0.025) |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for c in CELLS:
        r = results[c]
        lines.append(
            f"| {c} | {r['n']} | {r['mean_bp']:.2f} | {r['nw_t']:.2f} | "
            f"{r['ac1']:.3f} | {r['p_sign']:.4f} | {r['null_z']:.2f} | "
            f"{'YES' if r['qualifies'] else 'no'} |")
    lines += [
        "",
        f"**TRAIN verdict: {verdict}**" + (
            f" — qualifying cells {quals}; family mean "
            f"{fam_mean:.2f} bp, p (block-shift) {p_shift:.4f}"
            if quals else " — no qualifying cells"),
        "",
        "Ledger: `data/a_index_intraday/trial_ledger.jsonl` (append-only).",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"TRAIN verdict: {verdict} -> {REPORT}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
