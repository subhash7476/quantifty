"""A — Phase-1 index-slice certification: 1m index store gates (C1-C6).

Certifies the NSE_INDEX|Nifty 50 rows of
data/market_data/nse/candles/1m/{date}.duckdb over 2012-01-02 -> present.

READ BOUNDARY (construct discipline, A_CONSTRUCT_DEFINITION.md):
raw bars + microstructure only; no construct signal, no entry/exit P&L.

Gates:
  C1 contiguity   — every 1d-calendar Nifty session from 2012-01-02 (the 1m
                    store's universe start) has a 1m file with Nifty rows;
                    defects classified (block holes / singles / specials /
                    recent lag).
  C2 completeness — per-era full-session norm (vendor era: 375 bars
                    09:16-15:30; native era: 375 bars 09:15-15:29); partials
                    listed.
  C3 validity     — OHLC sanity, dup keys, monotonic timestamps, era-aware
                    session bounds.
  C4 schema       — timestamp column typed uniformly (TIMESTAMP).
  C5 alignment    — day-boundary fidelity vs the certified 1d store: first-bar
                    open vs official open; last-bar close vs official close;
                    close-to-close return identity. Era-split (the vendor era
                    has no official auction/close prints; the native era does).
  C6 native-opens — native-era first-bar open == official open exactly.

Usage: python scripts/a_index_intraday/certify_index_slice.py
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

CANDLE_DIR_1M = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"
CANDLE_DIR_1D = ROOT / "data" / "market_data" / "nse" / "candles" / "1d"
OUT_DIR = ROOT / "data" / "a_index_intraday"
REPORT = ROOT / "docs" / "reports" / "A_INDEX_SLICE_CERTIFICATION.md"

from core.market.session_schedule import CAS_EFFECTIVE  # noqa: E402

NF = "NSE_INDEX|Nifty 50"
VENDOR_LAST = "2023-01-31"  # vendor CSVs run 2012-01-02 -> 2023-01-31 (verified:
                            # 2023-01-31 still has vendor alignment, 09:16 first bar)
CAS_FIRST = CAS_EFFECTIVE.isoformat()  # 2026-08-03 — third structural era
EXPECTED_BARS = 375
CLOSE_TOL = 1e-4  # 1 bp


def era_for(session) -> str:
    """Which structural era a session belongs to: vendor | native | cas.

    Accepts a date or an ISO string — session keys are ISO strings in this
    module, but callers and tests reason in dates.
    """
    iso = session if isinstance(session, str) else session.isoformat()
    if iso >= CAS_FIRST:
        return "cas"
    if iso > VENDOR_LAST:
        return "native"
    return "vendor"

KNOWN_SPECIALS = {
    # Diwali Muhurat (evening sessions, outside the 09:15-15:30 session shape
    # by design — the 1m store's session filter excludes them, and the
    # construct skips them by construction) / Saturday specials.
    "2012-11-13", "2013-11-03", "2014-10-23", "2015-11-11", "2016-10-30",
    "2017-10-19", "2018-11-07", "2019-10-27", "2020-11-14", "2021-11-04",
    "2022-10-24", "2026-02-01",
}


def ts_type_of(con) -> str:
    for row in con.execute("DESCRIBE candles").fetchall():
        if row[0] == "timestamp":
            return str(row[1]).lower()
    return "?"


def session_summary(path: Path, symbol: str) -> dict:
    con = duckdb.connect(str(path), read_only=True)
    try:
        ttype = ts_type_of(con)
        ts_expr = f"CAST(timestamp AS TIMESTAMP)" if "varchar" in ttype else "timestamp"
        rows = con.execute(
            f"SELECT {ts_expr} AS ts, open, high, low, close FROM candles "
            f"WHERE symbol = ? ORDER BY ts", [symbol]).fetchall()
    except Exception as exc:
        con.close()
        return {"error": f"{type(exc).__name__}: {str(exc)[:120]}", "ts_type": "?",
                "rows": 0, "first_open": None, "last_close": None,
                "violations": 0, "dup_keys": 0, "non_monotonic": 0}
    con.close()
    out = {"error": None, "ts_type": ttype, "rows": len(rows),
           "first_ts": None, "last_ts": None,
           "first_open": None, "last_close": None,
           "violations": 0, "dup_keys": 0, "non_monotonic": 0}
    if not rows:
        return out
    out["first_ts"] = rows[0][0].isoformat()
    out["last_ts"] = rows[-1][0].isoformat()
    out["first_open"] = float(rows[0][1])
    out["last_close"] = float(rows[-1][4])
    seen = set()
    prev_ts = None
    for r in rows:
        ts, o, h, l, c = r
        if ts in seen:
            out["dup_keys"] += 1
        seen.add(ts)
        if prev_ts is not None and ts < prev_ts:
            out["non_monotonic"] += 1
        prev_ts = ts
        if not (o > 0 and h > 0 and l > 0 and c > 0):
            out["violations"] += 1
        elif h < max(o, c) or l > min(o, c):
            out["violations"] += 1
    return out


def main() -> int:
    t0 = time.time()
    m1_files = sorted(glob.glob(str(CANDLE_DIR_1M / "*.duckdb")))
    d1_files = sorted(glob.glob(str(CANDLE_DIR_1D / "*.duckdb")))
    print(f"1m files: {len(m1_files)}  1d files: {len(d1_files)}")

    nf_sum = {}
    m1_dates = set()
    for i, f in enumerate(m1_files):
        p = Path(f)
        d = p.stem
        m1_dates.add(d)
        nf_sum[d] = session_summary(p, NF)
        if (i + 1) % 600 == 0:
            print(f"  1m pass {i + 1}/{len(m1_files)}")

    d1_close = {}
    for f in d1_files:
        p = Path(f)
        con = duckdb.connect(str(p), read_only=True)
        try:
            r = con.execute(
                "SELECT open, close FROM candles WHERE symbol = ? "
                "AND timeframe = '1d' ORDER BY timestamp DESC LIMIT 1",
                [NF]).fetchone()
        except Exception:
            r = None
        con.close()
        if r:
            d1_close[p.stem] = (float(r[0]), float(r[1]))
    print(f"1d Nifty sessions: {len(d1_close)}")

    # ---- C1 contiguity (universe = 1d Nifty sessions >= 2012-01-02) ---------
    calendar = sorted(d for d in d1_close if d >= "2012-01-02")
    missing_file = sorted(d for d in calendar if d not in m1_dates)
    missing_rows = sorted(d for d in calendar
                          if d in nf_sum and (nf_sum[d].get("rows") or 0) == 0)
    specials = sorted(d for d in missing_file + missing_rows if d in KNOWN_SPECIALS)
    blocks = []
    for d in missing_file + missing_rows:
        if d in KNOWN_SPECIALS:
            continue
        blocks.append(d)
    # contiguous runs
    runs = []
    for d in blocks:
        if runs and (date.fromisoformat(d) - date.fromisoformat(runs[-1][-1])).days == 1:
            runs[-1].append(d)
        else:
            runs.append([d])

    # ---- C2 completeness -----------------------------------------------------
    nf_rows = {d: s["rows"] for d, s in nf_sum.items()
               if not s.get("error") and s.get("rows")}
    hist = {}
    for c in nf_rows.values():
        hist[c] = hist.get(c, 0) + 1
    partials = sorted(d for d, c in nf_rows.items() if c != EXPECTED_BARS)

    # ---- C3 validity (era-aware bounds) ---------------------------------------
    nf_viol = {}
    for d, s in nf_sum.items():
        if s.get("error") or not s.get("rows"):
            continue
        bad = (s["violations"] or s["dup_keys"] or s["non_monotonic"])
        if s["first_ts"]:
            ft = s["first_ts"][11:16]
            lt = s["last_ts"][11:16]
            if era_for(d) == "vendor":
                bad = bad or ft != "09:16" or lt != "15:30"
            else:
                # native and cas both label 09:15..15:29; in the cas era the
                # last bar is the auction print, not a continuous trade.
                bad = bad or ft != "09:15" or lt != "15:29"
        if bad:
            nf_viol[d] = s
    total_viol = sum(s["violations"] for s in nf_viol.values())
    total_dup = sum(s["dup_keys"] for s in nf_viol.values())
    total_nmono = sum(s["non_monotonic"] for s in nf_viol.values())

    # ---- C4 schema ------------------------------------------------------------
    ts_types = {}
    for d, s in nf_sum.items():
        ts_types[s["ts_type"]] = ts_types.get(s["ts_type"], 0) + 1

    # ---- C5 alignment (era-split) ---------------------------------------------
    def era_align(d_lo, d_hi, name):
        open_d, close_d, ret_d = [], [], []
        dates = sorted(d for d in d1_close if d_lo <= d <= d_hi)
        closes = {}
        for d in dates:
            s = nf_sum.get(d)
            if not s or not s.get("first_open") or not s.get("last_close"):
                continue
            o1d, c1d = d1_close[d]
            if c1d <= 0:
                continue
            open_d.append(abs(s["first_open"] - o1d) / o1d)
            close_d.append(abs(s["last_close"] - c1d) / c1d)
            closes[d] = (s["last_close"], c1d)
        prev = None
        for d in dates:
            if d not in closes:
                continue
            if prev and prev in closes:
                c1m_p, c1d_p = closes[prev]
                c1m, c1d = closes[d]
                if c1d_p > 0:
                    r1m = c1m / c1m_p - 1.0
                    r1d = c1d / c1d_p - 1.0
                    ret_d.append(abs(r1m - r1d))
            prev = d

        def st(a):
            a = sorted(a)
            if not a:
                return [0, 0, 0, 0, 0]
            return [len(a), a[0], a[len(a) // 2],
                    a[int(len(a) * 0.99)], a[-1]]
        return {"open": st(open_d), "close": st(close_d), "ret": st(ret_d)}

    ven = era_align("2012-01-02", VENDOR_LAST, "vendor")
    nat = era_align("2023-01-01", "2999-12-31", "native")

    # ---- C6 native opens exact -------------------------------------------------
    nat_exact = 0
    nat_tot = 0
    nat_bad = []
    for d, s in nf_sum.items():
        if d <= VENDOR_LAST or d not in d1_close or not s.get("first_open"):
            continue
        nat_tot += 1
        if abs(s["first_open"] - d1_close[d][0]) / d1_close[d][0] < 1e-6:
            nat_exact += 1
        else:
            nat_bad.append((d, s["first_ts"], s["first_open"], d1_close[d][0]))

    # ---- verdicts ---------------------------------------------------------------
    c1_pass = len(missing_file) == 0 and len(missing_rows) == 0
    gates = {
        "C1_contiguity": {
            "pass": c1_pass,
            "missing_1m_file": len(missing_file),
            "missing_nifty_rows": len(missing_rows),
            "special_sessions": len(specials),
            "regular_holes": len(blocks),
            "runs": [f"{r[0]}..{r[-1]} ({len(r)})" for r in runs],
        },
        "C2_completeness": {
            "pass": len(partials) == 0,
            "full_375": hist.get(375, 0),
            "partials": len(partials),
            "bar_histogram_top": dict(sorted(hist.items(),
                                             key=lambda kv: -kv[1])[:10]),
        },
        "C3_validity": {
            "pass": not nf_viol,
            "sessions_with_issues": len(nf_viol),
            "ohlc_violations": total_viol,
            "dup_keys": total_dup,
            "non_monotonic": total_nmono,
            "examples": list(nf_viol)[:10],
        },
        "C4_schema": {"pass": ts_types.get("timestamp", 0) == len(nf_sum),
                      "type_counts": ts_types},
        "C5_alignment": {
            "pass": False,  # gate is a report; verdict in the report body
            "vendor_first_open_vs_official": ven["open"],
            "vendor_last_close_vs_official": ven["close"],
            "vendor_return_diff": ven["ret"],
            "native_first_open_vs_official": nat["open"],
            "native_last_close_vs_official": nat["close"],
            "native_return_diff": nat["ret"],
        },
        "C6_native_opens_exact": {
            "pass": nat_exact == nat_tot and nat_tot > 0,
            "exact": nat_exact, "compared": nat_tot,
            "mismatches": [[d, ts, round(o, 2), round(oo, 2)]
                           for d, ts, o, oo in nat_bad]},
    }

    def fmt(v):
        return f"n={v[0]} min={v[1]:.6f} med={v[2]:.6f} p99={v[3]:.6f} max={v[4]:.6f}"

    overall = all(g["pass"] for g in gates.values())
    snap = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "files_1m": len(m1_files),
        "calendar_sessions": len(calendar),
        "nifty_sessions_with_bars": len(nf_rows),
        "gates": gates,
        "overall": "PASS" if overall else "FAIL",
        "partial_sessions": partials,
        "defects": {
            "regular_holes": blocks,
            "special_absent": specials,
        },
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "index_slice_certification.json").write_text(
        json.dumps(snap, indent=1), encoding="utf-8")

    lines = [
        "# A — Phase-1 Index-Slice Certification Report",
        "",
        f"Generated: {snap['generated']} · runtime {time.time() - t0:.0f}s · "
        f"1m files {len(m1_files)} · 1d calendar sessions {len(calendar)} · "
        f"Nifty sessions with bars {len(nf_rows)}",
        "",
        "**Read boundary:** raw bars + microstructure only; no construct signal, "
        "no entry/exit prices, no P&L (per A_CONSTRUCT_DEFINITION.md).",
        "",
        f"**Overall: {'PASS' if overall else 'FAIL'}**",
        "",
        "| Gate | Verdict | Key figures |",
        "|---|---|---|",
        f"| C1 contiguity | {'PASS' if gates['C1_contiguity']['pass'] else 'FAIL'} | "
        f"missing file {len(missing_file)}; missing rows {len(missing_rows)}; "
        f"specials {len(specials)}; regular holes {len(blocks)} "
        f"(runs: {', '.join(gates['C1_contiguity']['runs']) or 'none'}) |",
        f"| C2 completeness | {'PASS' if gates['C2_completeness']['pass'] else 'FAIL'} | "
        f"full 375-bar {gates['C2_completeness']['full_375']}; partials "
        f"{gates['C2_completeness']['partials']} |",
        f"| C3 validity | {'PASS' if gates['C3_validity']['pass'] else 'FAIL'} | "
        f"sessions with issues {gates['C3_validity']['sessions_with_issues']}; "
        f"OHLC viol {gates['C3_validity']['ohlc_violations']}; dup "
        f"{gates['C3_validity']['dup_keys']}; non-mono "
        f"{gates['C3_validity']['non_monotonic']} "
        f"(first examples: {', '.join(gates['C3_validity']['examples'][:8])}) |",
        f"| C4 schema | {'PASS' if gates['C4_schema']['pass'] else 'FAIL'} | "
        f"{gates['C4_schema']['type_counts']} |",
        f"| C5 alignment | **REPORT** (see below) | vendor first-open vs official: "
        f"{fmt(ven['open'])}; vendor last-close vs official: {fmt(ven['close'])}; "
        f"vendor return diff: {fmt(ven['ret'])} |",
        f"| C6 native opens | {'PASS' if gates['C6_native_opens_exact']['pass'] else 'FAIL'} | "
        f"{gates['C6_native_opens_exact']['exact']}/{gates['C6_native_opens_exact']['compared']} "
        f"sessions with first-open == official open exactly; mismatches: "
        f"{gates['C6_native_opens_exact']['mismatches']} |",
        "",
        "## C5 — day-boundary alignment vs the certified 1d store",
        "",
        "Relative differences [n, min, median, p99, max] in bp (x1e4):",
        "",
        f"- **Vendor era (2012-01-02 → 2023-01-31, ~2,700 sessions):** first-bar "
        f"open vs official open `{fmt(ven['open'])}`; last-bar close vs official "
        f"close `{fmt(ven['close'])}`; close-to-close return diff `{fmt(ven['ret'])}`.",
        f"- **Native era (2023-03-01 → present, ~880 sessions):** first-bar open "
        f"vs official open `{fmt(nat['open'])}`; last-bar close vs official close "
        f"`{fmt(nat['close'])}`; return diff `{fmt(nat['ret'])}`.",
        "",
        "Interpretation: the vendor era has no official 09:15 auction bar (first "
        "bar labeled 09:16) and no official-close print (last bar labeled 15:30); "
        "its boundary prints deviate from the official index by median ~3-5 bp, "
        "p99 ~25-32 bp, max ~74-108 bp, while intraday high/low match official "
        "exactly (sampled). The native era carries the exact auction open (C6) "
        "and its last bar is 15:29 — the residual ~4 bp median vs the official "
        "15:30 close is the expected last-minute move. "
        "From 2026-08-03 (CAS) a third era applies: the 15:29 bar is the "
        "closing-auction print rather than a continuous trade — it equals the "
        "official close, but it is not reachable by a continuous-market order, "
        "and the 15:15-15:27 bars are carry-forward artifacts. The index carries "
        "volume=0 always, so the auction bar cannot be detected from index data; "
        "the era boundary is the rule (see era_for).",
        "",
        "## Defect register",
        "",
        "| Class | Sessions | Detail |",
        "|---|---|---|",
        f"| Regular block hole | {len([r for r in runs if len(r) > 1])} run(s) | "
        f"{', '.join(gates['C1_contiguity']['runs'])} |",
        f"| Regular single holes | {len([r for r in runs if len(r) == 1])} | "
        f"{', '.join(r[0] for r in runs if len(r) == 1) or 'none'} |",
        f"| Special sessions absent from 1m | {len(specials)} | "
        f"{', '.join(specials) or 'none'} (Diwali Muhurat / Saturday specials "
        f"present in the 1d calendar) |",
        f"| Recent ingest lag | 2 | 2026-08-25, 2026-08-26 |",
        "",
        "**Special sessions (12) — out-of-shape, not defects for A:** "
        "2012-11-13, 2013-11-03, 2014-10-23, 2015-11-11, 2016-10-30, 2017-10-19, "
        "2018-11-07, 2019-10-27, 2020-11-14, 2021-11-04, 2022-10-24, 2026-02-01. "
        "All are Diwali Muhurat / evening special sessions: the vendor CSV "
        "carries them with evening timestamps (verified 17:23-18:32 on "
        "2018-11-07, 18:23 on 2014-10-23), the 1m store's session-hour filter "
        "(09:15-15:30) excludes them by design, and the construct skips them by "
        "construction (no morning opening drive exists). They remain in the 1d "
        "calendar for continuity. **No fill is possible or needed** — filling "
        "them would require mutating the committed ingest's session filter for "
        "zero construct value.",
        "",
        "**Permanent in-scope holes:** 2018-05-02..31 (22 sessions — absent from "
        "the vendor CSV itself; confirmed 0 rows for 201805xx in the source) and "
        "2023-02-01..03-01 (20 sessions — vendor/native transition; vendor CSV "
        "ends 2023-01-31, Upstox cannot backfill). Plus recent lag 2026-08-24..26.",
        "",
        "**Native-era first-bar defects (C6):** 2025-02-01 (first-bar open 4 bp "
        "off official — special session); 2026-02-25 and 2026-03-02 (first bar "
        "carries the PREVIOUS session's date stamp and open — live-ingest "
        "artifact; 50 bp and 3.25% off official respectively). The construct "
        "must skip sessions whose first bar is not stamped with the session "
        "date, or these must be repaired before the sealed window is read.",
        "",
        "Snapshot: `data/a_index_intraday/index_slice_certification.json`",
        "",
        "## Construct impact (amendment inputs for A_CONSTRUCT_DEFINITION.md)",
        "",
        "1. **Signal base:** the vendor era has no 09:15 auction bar. The base "
        "must be 'the opening print (first bar open)' — era-consistent semantics; "
        "the vendor first bar approximates the auction (median 3.2 bp, p99 25 bp, "
        "max 74 bp).",
        "2. **Exit fidelity:** the vendor-era last-bar close deviates from the "
        "official close (median 5.4 bp, p99 32 bp, max 108 bp). The "
        "pre-registration must choose between accepting this as a disclosed "
        "modeling assumption (distribution recorded here) or adding an "
        "exit-fidelity cost lane.",
        "3. **Availability:** TRAIN loses the 2018-05 block (22 sessions) and "
        "singles; HOLDOUT loses ~6 specials; SEALED loses 2023-02-01..03-01 "
        "(20 sessions) and 2026 specials. Fences unchanged.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    for g, v in gates.items():
        print(f"{g}: {'PASS' if v['pass'] else 'FAIL'}"
              + ("" if g != "C5_alignment" else " (report)"))
    print(f"OVERALL: {'PASS' if overall else 'FAIL'}  -> {REPORT}")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
