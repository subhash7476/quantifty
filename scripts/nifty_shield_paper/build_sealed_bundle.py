#!/usr/bin/env python
"""Build the self-contained NiftyShield sealed-validation bundle.

Stages engine + corrected models + EOD context + slim index-only bars + a patched
run.py into a portable folder that runs OUTSIDE F:\\Nifty. The operator drops their
per-date options DuckDB files into options/ and runs run.py; only output/summary.json
is meant to leave the sealed folder.

Finding-4 harness patches applied here (asserted, never silent):
  1. options timestamps normalized to naive IST wall-clock (TIMESTAMPTZ-safe)
  2. the manual +5:30 shift removed from get_timestamps_for_date
  3. regime_checkpoint recorded + lock-checkpoint histogram in summary
  4. sessions_attempted in summary for trades+skips reconciliation
"""
from __future__ import annotations
import shutil, sys, zipfile
from datetime import date
from pathlib import Path

import duckdb

SRC = Path(r"F:\Nifty")
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\Users\devou\AppData\Local\Temp\claude\F--Nifty\592f8f62-678b-4a9d-a79d-5219c428e93d\scratchpad\sealed_validation")
BAR_START, BAR_END = date(2025, 1, 1), date(2026, 7, 31)
IDX = ("NSE_INDEX|Nifty 50", "NSE_INDEX|Nifty Bank")
MODELS = ("logistic_10am", "logistic_11am", "logistic_13pm_prod")
EOD_YEARS = (2023, 2024, 2025, 2026)   # exactly what DayTypeEngine._load_eod_context loads

# ── harness patches (old, new) — every old MUST be found or we abort ──────────────
HELPER = '''

def _to_naive_ist(series):
    """Timestamps as naive IST wall-clock, robust to tz-aware (options TIMESTAMPTZ) or
    naive-UTC (legacy CSV) input. utc=True pins a UTC instant either way, then convert to
    IST and drop tz so (hour, minute) reads true IST."""
    ts = pd.to_datetime(series, utc=True)
    return ts.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
'''

PATCHES = [
    ("utf8_stdout",
     "ROOT = Path(__file__).resolve().parent\nsys.path.insert(0, str(ROOT))\n",
     "try:\n    sys.stdout.reconfigure(encoding=\"utf-8\")\nexcept Exception:\n    pass\n\n"
     "ROOT = Path(__file__).resolve().parent\nsys.path.insert(0, str(ROOT))\n"),
    ("helper",
     "_chain_cache: pd.DataFrame | None = None\n_cache_source: str | None = None\n",
     "_chain_cache: pd.DataFrame | None = None\n_cache_source: str | None = None\n" + HELPER),
    ("load_full_chain",
     '    df = pd.read_csv(path, parse_dates=["timestamp"])\n    df["timestamp"] = pd.to_datetime(df["timestamp"])\n',
     '    df = pd.read_csv(path)\n    df["timestamp"] = _to_naive_ist(df["timestamp"])\n'),
    ("duckdb_read",
     '            df = con.execute("SELECT * FROM options").df()\n            con.close()\n            df["timestamp"] = pd.to_datetime(df["timestamp"])\n            return df\n',
     '            df = con.execute("SELECT * FROM options").df()\n            con.close()\n            df["timestamp"] = _to_naive_ist(df["timestamp"])\n            return df\n'),
    ("csv_perdate",
     '                return pd.read_csv(f, parse_dates=["timestamp"])\n',
     '                _df = pd.read_csv(f)\n                _df["timestamp"] = _to_naive_ist(_df["timestamp"])\n                return _df\n'),
    ("drop_shift",
     '        t = row["timestamp"]\n        ist = t + pd.Timedelta(hours=5, minutes=30)\n        ts_map[(ist.hour, ist.minute)] = t\n',
     '        t = row["timestamp"]                       # already naive IST wall-clock\n        ts_map[(t.hour, t.minute)] = t\n'),
    ("regime_cp_result",
     '        "regime": state.predicted_state,\n        "confidence": state.confidence,\n',
     '        "regime": state.predicted_state,\n        "regime_checkpoint": state.checkpoint,\n        "confidence": state.confidence,\n'),
    ("regime_cp_csv",
     '                "regime": t["regime"],\n                "confidence": t["confidence"],\n',
     '                "regime": t["regime"],\n                "regime_checkpoint": t.get("regime_checkpoint"),\n                "confidence": t["confidence"],\n'),
    ("summary_attempted",
     '        summary = {\n            "total_trades": len(trades),\n',
     '        summary = {\n            "sessions_attempted": len(dates),\n            "total_trades": len(trades),\n'),
    ("always_summary",
     '    else:\n        print("\\nNo trades generated.")\n        print(f"Skipped: {sum(skipped.values())} sessions")\n',
     '    else:\n'
     '        summary = {"sessions_attempted": len(dates), "total_trades": 0,\n'
     '                   "period": f"{dates[0]} - {dates[-1]}", "skipped": skipped,\n'
     '                   "lock_checkpoints": {}}\n'
     '        with open(output_dir / "summary.json", "w") as f:\n'
     '            json.dump(summary, f, indent=2)\n'
     '        print("\\nNo trades generated. Wrote summary.json (skips only).")\n'
     '        print(f"Skipped: {sum(skipped.values())} sessions")\n'),
    ("summary_lockhist",
     '            "skipped": skipped,\n        }\n',
     '            "lock_checkpoints": {cp: sum(1 for t in trades if t.get("regime_checkpoint") == cp)\n'
     '                                 for cp in sorted({t.get("regime_checkpoint") for t in trades})},\n'
     '            "skipped": skipped,\n        }\n'),
]


def stage():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "core").mkdir(parents=True)
    (OUT / "options").mkdir()
    (OUT / "output").mkdir()

    # ── core engine bundle ────────────────────────────────────────────────────
    (OUT / "core" / "__init__.py").write_text("")
    for sub, files in {
        "state": ["daytype_engine.py"],
        "analytics": ["day_features.py", "resampler.py"],
    }.items():
        d = OUT / "core" / sub
        d.mkdir()
        (d / "__init__.py").write_text("")
        for f in files:
            shutil.copy2(SRC / "core" / sub / f, d / f)

    # ── models (all 3 — engine loads every checkpoint; 10am/11am can lock) ─────
    for m in MODELS:
        dst = OUT / "models" / "daytype" / m
        dst.mkdir(parents=True)
        for f in ("model.pkl", "scaler.pkl", "metadata.json"):
            shutil.copy2(SRC / "models" / "daytype" / m / f, dst / f)

    # ── EOD context (10am/11am Block A + rolling percentiles) ──────────────────
    fd = OUT / "data" / "features" / "day_type"
    fd.mkdir(parents=True)
    for yr in EOD_YEARS:
        shutil.copy2(SRC / "data" / "features" / "day_type" / f"nifty_day_features_{yr}.csv",
                     fd / f"nifty_day_features_{yr}.csv")

    # ── slim index-only bars for the sealed window ────────────────────────────
    bars = OUT / "bars"
    bars.mkdir()
    srcbars = SRC / "data" / "market_data" / "nse" / "candles" / "1m"
    n = 0
    for p in sorted(srcbars.glob("*.duckdb")):
        try:
            d = date.fromisoformat(p.stem)
        except ValueError:
            continue
        if not (BAR_START <= d <= BAR_END):
            continue
        dst = bars / p.name
        con = duckdb.connect(str(dst))
        con.execute(f"ATTACH '{p.as_posix()}' AS s (READ_ONLY)")
        con.execute("CREATE TABLE candles AS SELECT * FROM s.candles WHERE symbol IN (?, ?)", list(IDX))
        con.close()
        n += 1
    return n


def patch_run_py():
    src = (SRC / "scripts" / "nifty_shield_paper" / "sealed_harness.py").read_text()
    for label, old, new in PATCHES:
        if old not in src:
            raise SystemExit(f"PATCH FAILED — anchor not found: {label}")
        src = src.replace(old, new, 1)
    (OUT / "run.py").write_text(src)


README = """# NiftyShield Sealed Validation Bundle

Self-contained. Runs OUTSIDE F:\\Nifty. Nothing here reads the training repo.

## Run
1. Drop your per-date options DuckDB files into `options/` — filenames `YYYY-MM-DD.duckdb`,
   one table named `options`, columns incl. timestamp, expiry_code, strike_relative,
   option_type, close, iv, strike_price, spot_price.
2. Run:
       python run.py --bars-dir bars --options-dir options --start 2025-01-01 --end 2026-07-31
3. Share back ONLY `output/summary.json`. Keep `output/trade_list.csv` sealed.

## What runs
- The corrected `logistic_13pm_prod` (v2.0, 38 features, trained==served, parity PASS)
  plus 10am/11am. The engine can lock at 10am/11am, so `summary.json.lock_checkpoints`
  shows which checkpoint each acted-on regime came from.
- Regime is computed from the bundled slim index bars (Nifty 50 + Bank Nifty). Options are
  used only for structure pricing / P&L.

## Reconciliation
`total_trades + sum(skipped.values()) == sessions_attempted` should hold. If most sessions
land in `skipped.no_options_data`, the options files are missing/mis-named or the table
isn't `options`.

## Disclosed approximations (unchanged from the harness)
ATM-CE IV as the VIX>20 gate proxy; expiry_code=1 assumed nearest weekly; close used for
entry and exit (no bid/ask/slippage); no delta-flatten exit. Fine for a forward P&L read;
not tick-accurate execution.
"""


def main():
    nbars = stage()
    patch_run_py()
    (OUT / "README.md").write_text(README)
    zpath = OUT.with_suffix(".zip")
    if zpath.exists():
        zpath.unlink()
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in OUT.rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(OUT.parent))
    print(f"bars staged: {nbars}")
    print(f"bundle dir : {OUT}")
    print(f"bundle zip : {zpath}  ({zpath.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
