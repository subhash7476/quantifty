"""Phase-6 composition root for the A2 Validation Harness (dossier §9).

Wires the certified FilesystemArtifactLoader + the frozen artifact + the pinned
substrate, scores an EXPLICIT window, and writes the sealed record. In Phase 5B this
is exercised only on dev/synthetic windows; the held-out run is Phase 6.

The evaluation window is a required CLI argument — NEVER hardcoded. The phase-6
duplicate guard prevents an accidental second official run over the same window.

Tech Stack: Python 3.10+, numpy, pandas, duckdb, scipy, pytest.
"""

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Tuple

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.msi.dra.filesystem_artifact_loader import FilesystemArtifactLoader  # noqa: E402
from core.msi.msrp.validation import (  # noqa: E402
    Methodology,
    Substrate,
    ValidationHarness,
    dataset_snapshot_hash,
    write_sealed_record,
)
from core.msi.msrp.validation_scoring import score_window  # noqa: E402

NIFTY_50 = "NSE_INDEX|Nifty 50"
INDIA_VIX = "NSE_INDEX|India VIX"
CANDLES_1M = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"
CANDLES_1D = ROOT / "data" / "market_data" / "nse" / "candles" / "1d"
ARTIFACT_DIR = ROOT / "core" / "msi" / "artifacts" / "forward_vol_v2"
VALIDATIONS_DIR = ROOT / "core" / "msi" / "validations"


def _iter_duckdb_days(root: Path, start: str, end: str):
    start_d = pd.Timestamp(start).date()
    end_d = pd.Timestamp(end).date()
    for f in sorted(root.glob("*.duckdb")):
        try:
            d = pd.Timestamp(f.stem).date()
        except ValueError:
            continue
        if start_d <= d <= end_d:
            yield f


def load_candles_over(window_start: str, window_end: str, warmup_days: int = 30):
    load_start = (pd.Timestamp(window_start) - pd.Timedelta(days=warmup_days * 2)).date().isoformat()
    load_end = (pd.Timestamp(window_end) + pd.Timedelta(days=7)).date().isoformat()
    files = []
    closes_by_day = {}
    for f in _iter_duckdb_days(CANDLES_1M, load_start, load_end):
        con = duckdb.connect(str(f), read_only=True)
        try:
            rows = con.execute(
                "SELECT timestamp, close FROM candles WHERE symbol = ? ORDER BY timestamp",
                [NIFTY_50],
            ).fetchall()
        finally:
            con.close()
        if not rows:
            continue
        files.append(f)
        day = pd.Timestamp(rows[0][0]).normalize()
        closes_by_day[day] = np.array([float(r[1]) for r in rows], dtype=float)
    records = []
    for f in _iter_duckdb_days(CANDLES_1D, load_start, load_end):
        con = duckdb.connect(str(f), read_only=True)
        try:
            rows = con.execute(
                "SELECT timestamp, close FROM candles WHERE symbol = ?", [INDIA_VIX]
            ).fetchall()
        finally:
            con.close()
        if rows:
            files.append(f)
        for ts, close in rows:
            records.append((pd.Timestamp(ts).normalize(), float(close)))
    vix = pd.Series([r[1] for r in records],
                    index=pd.DatetimeIndex([r[0] for r in records]), name="vix")
    files = sorted(set(files))
    return closes_by_day, vix, files


def phase6_guard(out_root, held_out_window: Tuple[str, str]) -> None:
    out_root = Path(out_root)
    if not out_root.exists():
        return
    for d in out_root.iterdir():
        rec = d / "record.json"
        if not rec.exists():
            continue
        try:
            rj = json.loads(rec.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if rj.get("phase") != "6":
            continue
        window = None
        res = d / "results.json"
        if res.exists():
            try:
                window = json.loads(res.read_text())["results"]["evaluation_window"]
            except (json.JSONDecodeError, KeyError, OSError):
                window = None
        if window == list(held_out_window):
            raise RuntimeError(
                f"A phase-6 validation for window {held_out_window} already exists at {d}. "
                "Refusing to run a duplicate official validation."
            )


def _lib_versions() -> dict:
    import statsmodels
    import sklearn
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "statsmodels": statsmodels.__version__,
        "scikit-learn": sklearn.__version__,
    }


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(ROOT)).decode().strip()
    except Exception:
        return "unknown"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window-start", required=True)
    ap.add_argument("--window-end", required=True)
    ap.add_argument("--phase", required=True, choices=["5B", "6"])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--block-length", type=int, default=10)
    ap.add_argument("--replicates", type=int, default=10000)
    args = ap.parse_args(argv)

    window = (args.window_start, args.window_end)
    if args.phase == "6":
        phase6_guard(VALIDATIONS_DIR, window)

    artifact = FilesystemArtifactLoader().load(str(ARTIFACT_DIR))
    artifact_checksum = json.loads((ARTIFACT_DIR / "checksum.sha256").read_text())["combined_hash"]

    closes_by_day, vix, files = load_candles_over(args.window_start, args.window_end)
    snapshot_hash = dataset_snapshot_hash(files)
    scored = score_window(artifact, closes_by_day, vix, args.window_start, args.window_end)

    methodology = Methodology(
        substrate=Substrate(
            block_length=args.block_length, n_replicates=args.replicates, seed=args.seed,
            lib_versions=_lib_versions(),
            commit=_git_commit(),
        ),
        median_window=20, delta_auc_bar=0.03, dossier_commit="d9233b1",
        calibration_nominal=0.90, calibration_tolerance=0.05,
    )
    harness = ValidationHarness(
        artifact=artifact, methodology=methodology, scored=scored,
        evaluation_window=window, phase=args.phase,
        artifact_checksum=artifact_checksum, dataset_snapshot_hash=snapshot_hash,
    )
    record = harness.run()
    out = write_sealed_record(
        record, VALIDATIONS_DIR, reviewer=None, approval_status=None,
        timestamp_iso=datetime.now().isoformat(timespec="seconds"),
    )
    print(f"Validation {record.validation_id} ({record.candidate_verdict}) -> {out}")
    print(f"  delta_auc_gate={record.results['delta_auc_gate']:.6f} "
          f"CI=({record.results['ci_lower']:.6f}, {record.results['ci_upper']:.6f}) "
          f"base_rate={record.results['base_rate']:.6f} n={record.results['n_scored']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
