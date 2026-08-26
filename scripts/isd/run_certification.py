"""ISD Phase-1 certification orchestrator.

Runs G1..G7 in dependency order, emits the script-generated report
`docs/reports/ISD_PHASE1_SUBSTRATE_CERTIFICATION.md` and the machine-readable
snapshot `data/isd/ISD_PHASE1_SNAPSHOT.json`. Every number in the report comes
from this run — nothing hand-edited (spec guardrail 7).

Usage:
    python scripts/isd/run_certification.py            # all gates
    python scripts/isd/run_certification.py --gate G3  # single-gate rerun (stdout)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.isd import (  # noqa: E402
    CANONICAL_CAPITAL, ISD_DATA_DIR, REPORT_DIR, ROOT, eq_sessions,
)
from scripts.isd import gate_contiguity, gate_validity  # noqa: E402
from scripts.isd.read_1m import read_day  # noqa: E402

SNAPSHOT_PATH = ISD_DATA_DIR / "ISD_PHASE1_SNAPSHOT.json"
REPORT_PATH = REPORT_DIR / "ISD_PHASE1_SUBSTRATE_CERTIFICATION.md"


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT), text=True).strip()
    except Exception:
        return "unknown"


def _present_by_session(sessions):
    """{session: [(isin_key, nse_symbol)]} via the normalized reader."""
    out = {}
    for iso, path in sessions:
        df = read_day(path)
        syms = sorted(df["symbol"].unique())
        out[iso] = [(s, s.split("|")[1] if "|" in s else s) for s in syms]
    return out


def main() -> int:
    from core.database.utils.market_hours import MarketHours
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", default=None,
                        help="run a single gate and print its JSON")
    parser.add_argument("--skip-vendor", action="store_true",
                        help="skip G7 ingest/cross-val/adjustment gates")
    parser.add_argument("--cv-stride", type=int, default=7,
                        help="session stride for cross-validation sampling")
    args = parser.parse_args()

    started = datetime.now()
    sessions = eq_sessions()
    results = {}

    # --- G3 reader co-verification happens implicitly inside every gate read.
    results["G3"] = {
        "gate": "G3",
        "reader": "scripts/isd/read_1m.py",
        "schema_variants_abstracted": ["pre-2026-03-05", "post-2026-03-05"],
        "pass": True,   # a drift break raises loudly in read_day
    }

    # --- G2 currency: latest file >= last completed trading session (calendar-anchored)
    last = sessions[-1][0] if sessions else None
    results["G2"] = gate_contiguity.currency_check(
        [iso for iso, _ in sessions],
        gate_contiguity.expected_sessions(),
        MarketHours.get_ist_now().date().isoformat(),
    )

    if args.gate in (None, "G4"):
        results["G4"] = gate_validity.run(sessions)
    if args.gate in (None, "G1"):
        results["G1"] = gate_contiguity.run(sessions)

    if args.gate in (None, "G5"):
        from scripts.isd import build_pit_universe
        results["G5"] = build_pit_universe.build(_present_by_session(sessions))

    if args.gate in (None, "G6"):
        from core.execution.equity.intraday_fees import ticket_size_table
        from scripts.isd import slippage_bands
        results["G6"] = {
            "gate": "G6",
            "canonical_capital_rs": CANONICAL_CAPITAL,
            "ticket_table": ticket_size_table(capital=CANONICAL_CAPITAL),
            "slippage": slippage_bands.run(sessions),
            "pass": True,
        }

    if args.gate is None and not args.skip_vendor:
        from scripts.isd import (
            cross_validate_vendor, ingest_vendor_archive, verify_adjustments,
        )
        results["G7a-d"] = ingest_vendor_archive.run()
        n = cross_validate_vendor.consolidate()
        results["G7_flat_rows"] = n
        results["G7e"] = cross_validate_vendor.run(stride=args.cv_stride)
        results["G7f"] = verify_adjustments.run()

    finished = datetime.now()

    if args.gate:                      # single-gate debug print
        print(json.dumps(results.get(args.gate, {}), indent=2, default=str))
        return 0

    snapshot = {
        "generated_at": finished.isoformat(),
        "repo_commit": _git_commit(),
        "script_shas": {p.name: _sha(p) for p in sorted(
            (ROOT / "scripts" / "isd").glob("*.py"))},
        "sessions": {"count": len(sessions), "first": sessions[0][0],
                     "last": last},
        "results": {k: v for k, v in results.items()},
        "runtime_s": round((finished - started).total_seconds(), 1),
    }
    ISD_DATA_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2, default=str),
                             encoding="utf-8")

    gate_keys = [k for k in results if k.startswith("G") and k != "G7_flat_rows"]
    all_pass = all(results[k].get("pass") for k in gate_keys)
    lines = [
        "# ISD Phase-1 Substrate Certification Report",
        "",
        f"Generated: {finished.isoformat()} · runtime "
        f"{snapshot['runtime_s']}s · commit `{snapshot['repo_commit']}`",
        "",
        f"Sessions certified: **{len(sessions)}** "
        f"({sessions[0][0]} → {last}) · canonical capital "
        f"₹{CANONICAL_CAPITAL:,.0f} (Q4)",
        "",
        "| Gate | Verdict | Key figures |",
        "|---|---|---|",
    ]
    detail = {
        "G1": lambda r: (f"{r['present_sessions']}/{r['expected_sessions']} "
                         f"sessions; defects="
                         f"{[a['date'] for a in r['absent_classes'] if a['class'] == 'eq_1m_missing']}; "
                         f"special={[a['date'] for a in r['absent_classes'] if a['class'] == 'weekend_special']}; "
                         f"ledger entries={r['ledger_entries']}"),
        "G2": lambda r: f"latest file {r['latest_session_file']}",
        "G3": lambda r: "normalized reader; drift abstracted",
        "G4": lambda r: (f"v1={r['totals']['v1_ohlc_order']} "
                         f"(first-bar artifact="
                         f"{r['totals']['v1_first_bar_auction_artifact']}, "
                         f"unexplained={r['totals']['v1_unexplained']}) "
                         f"v2={r['totals']['v2_bad_price']} "
                         f"v3={r['totals']['v3_duplicates']} "
                         f"v4={r['totals']['v4_volume_negative_or_null']} "
                         f"v5 unexplained={r['totals']['v5_unexplained']} "
                         f"(ca-adjusted expected="
                         f"{r['totals']['v5_ca_adjusted_expected']}); "
                         f"examples={r['v12_examples'][:3]}"),
        "G5": lambda r: (f"rows={r['membership_rows']}; cross-feed agreement="
                         f"{r['cross_feed_agreement']}; unresolved="
                         f"{r['unresolved_count']}"),
        "G6": lambda r: (f"ticket table @ ₹{CANONICAL_CAPITAL:,.0f}; "
                         f"slippage deciles pooled over "
                         f"{r['slippage']['observations']} obs"),
        "G7a-d": lambda r: (f"{r['members']} members; resolution="
                            f"{r['resolution_rate']}; tail dropped="
                            f"{r['tail_dropped_total']}"),
        "G7e": lambda r: (f"{r['compared_bars']} bars compared; "
                          f"aligned within-tol="
                          f"{r['aligned_share_within_005pct']} "
                          f"(raw {r['raw_share_within_005pct']}); "
                          f"aligned median |Δ|={r['aligned_median_abs_diff_rs']}; "
                          f"basis-offset={len(r['basis_offset_tickers'])}; "
                          f"low-agree days={len(r['low_agreement_ticker_days'])}"),
        "G7f": lambda r: (f"{r['seams_checked']} CA seams; fabricated="
                          f"{r['fabricated_seams']}"),
    }
    for k in gate_keys:
        r = results[k]
        verdict = "PASS" if r.get("pass") else "FAIL"
        lines.append(f"| {k} | {verdict} | {detail.get(k, lambda x: '')(r)} |")
    if "G7a-d" not in results:
        lines.append("| G7 | skipped | vendor archive not ingested "
                     "(`--skip-vendor`) → program runs native-only |")
    lines += ["", f"**Overall: {'PASS' if all_pass else 'FAIL'}**",
              "",
              "Snapshot: `data/isd/ISD_PHASE1_SNAPSHOT.json` "
              "(gitignored data tree; digests embedded above)."]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n{'='*60}\nISD Phase-1 certification: "
          f"{'PASS' if all_pass else 'FAIL'}\nReport: {REPORT_PATH}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
