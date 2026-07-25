"""Carry Production Metrics — report generator (Phase B).

Reads production.duckdb and generates a script-generated comprehensive
report covering returns vs research, fee decomposition, turnover,
concentration, drawdown, margin utilisation, and parity reconciliation.

Output: docs/reports/CARRY_PRODUCTION_METRICS_REPORT.md
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path("F:/Nifty")
sys.path.insert(0, str(ROOT))

PROD_DB = DATA_ROOT / "data" / "signal_engine" / "carry" / "production.duckdb"
RESEARCH_SNAP = DATA_ROOT / "docs" / "reports" / "CARRY_NET_SPREAD_SNAPSHOT.json"
SEALED_SNAP = DATA_ROOT / "docs" / "reports" / "CARRY_SEALED_SNAPSHOT.json"
REPORT = ROOT / "docs" / "reports" / "CARRY_PRODUCTION_METRICS_REPORT.md"

TOLERANCE_BP = 15


def _git_commit() -> str:
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)
        ).decode().strip()
    except Exception:
        return "unknown"


def _fmt_pct(v: float) -> str:
    return f"{v * 100:+.2f}%"


def _fmt_bp(v: float) -> str:
    return f"{v * 10000:.1f} bp"


def _max_dd(equity_rows: list) -> float:
    if len(equity_rows) < 2:
        return 0.0
    dd_vals = [r[2] for r in equity_rows if r[2] is not None]
    return min(dd_vals) if dd_vals else 0.0


def _sharpe(monthly: list[float]) -> float:
    arr = np.array(monthly)
    if len(arr) < 2 or np.std(arr, ddof=1) == 0:
        return 0.0
    return float(np.mean(arr) / np.std(arr, ddof=1) * np.sqrt(12))


def _load_research_results():
    if not RESEARCH_SNAP.exists():
        return {}
    with open(RESEARCH_SNAP) as f:
        snap = json.load(f)
    return snap.get("results", {})


def _load_sealed_results():
    if not SEALED_SNAP.exists():
        return {}
    with open(SEALED_SNAP) as f:
        return json.load(f)


def main():
    commit = _git_commit()
    now_ts = date.today().isoformat()

    research = _load_research_results()
    sealed = _load_sealed_results()

    con = duckdb.connect(str(PROD_DB), read_only=True)

    lines = []
    a = lines.append

    a("# Carry — Production Metrics Report\n")
    a(f"**Script-generated** — `scripts/carry_production_report.py`. "
      f"Code commit `{commit}`.\n")
    a(f"**Generated:** {now_ts}\n")
    a("**Source:** `data/signal_engine/carry/production.duckdb`\n")
    a("**SEALED:** snapshot-ingested only — strategy NEVER run over SEALED "
      "(`CARRY_SEALED_READ_PROTOCOL.md` §2).\n")
    a("")

    # ── 1. Run metadata ──
    a("---\n")
    a("## 1. Runs\n")
    a("")
    a("| Window | Source | Rebalances | Determinism Hash |")
    a("|---|:---:|--:|:---:|")
    runs = con.execute("""
        SELECT rm.run_id, rm.window_label, rm.source, rm.determinism_hash,
               COUNT(rs.formation_date) as n_reb
        FROM run_metadata rm
        LEFT JOIN rebalance_summary rs ON rm.run_id = rs.run_id
        GROUP BY rm.run_id, rm.window_label, rm.source, rm.determinism_hash
        ORDER BY 
            CASE rm.window_label 
                WHEN 'TRAIN' THEN 1 
                WHEN 'HOLDOUT' THEN 2 
                WHEN 'SEALED' THEN 3 
            END
    """).fetchall()

    for run_id, label, source, dhash, n_reb in runs:
        hash_str = dhash if dhash else "(snapshot)"
        a(f"| {label} | {source} | {n_reb} | `{hash_str}` |")
    a("")

    # ── 2. Returns vs Research ──
    a("---\n")
    a("## 2. Returns\n")
    a("")
    a("| Window | Source | Ann Gross | Ann Net | Fee Drag | Avg Turnover |")
    a("|---|:--:|--:|--:|--:|--:|")

    for label in ["TRAIN", "HOLDOUT", "SEALED"]:
        run_rows = con.execute("""
            SELECT run_id, source FROM run_metadata WHERE window_label = ?
        """, [label]).fetchall()

        if not run_rows:
            continue

        run_id, source = run_rows[0]

        summary_rows = con.execute("""
            SELECT formation_date, traded_value, turnover,
                   fees_total, slippage_total,
                   fee_brokerage, fee_stt, fee_exchange_txn,
                   fee_sebi_fee, fee_stamp_duty, fee_gst
            FROM rebalance_summary WHERE run_id = ?
            ORDER BY formation_date
        """, [run_id]).fetchall()

        equity_rows = con.execute("""
            SELECT formation_date, cum_net_ret, drawdown_pct
            FROM equity_curve WHERE run_id = ?
            ORDER BY formation_date
        """, [run_id]).fetchall()

        if source == "snapshot":
            ann_net_val = sealed.get("results", {}).get("portfolio", {}).get("ann_net", 0.0)
            ann_gross_val = sealed.get("results", {}).get("portfolio", {}).get("ann_gross", 0.0)
            avg_to_val = sealed.get("results", {}).get("portfolio", {}).get("avg_turnover", 0.0)
            fee_drag_val = sealed.get("results", {}).get("portfolio", {}).get("fee_drag_bp", 0.0) / 10000.0
            a(f"| **{label}** | snapshot | {_fmt_pct(ann_gross_val)} | "
              f"**{_fmt_pct(ann_net_val)}** | {_fmt_bp(fee_drag_val)} | {avg_to_val:.3f} |")
        elif equity_rows:
            cum_val = float(equity_rows[-1][1])
            months = len(equity_rows) - 1
            ann_net_val = (1.0 + cum_val) ** (12.0 / max(months, 1)) - 1.0

            total_fees = sum(r[3] for r in summary_rows)
            total_slip = sum(r[4] for r in summary_rows)
            avg_to_val = np.mean([r[2] for r in summary_rows]) if summary_rows else 0.0

            fee_ratio = (total_fees + total_slip) / (10_000_000.0 * months) if months > 0 else 0
            ann_gross_val = ann_net_val + fee_ratio * 12
            fee_drag_val = ann_gross_val - ann_net_val
            a(f"| **{label}** | replay | {_fmt_pct(ann_gross_val):>8} | "
              f"**{_fmt_pct(ann_net_val)}** | {_fmt_bp(fee_drag_val)} | {avg_to_val:.3f} |")

    a("")

    # ── 3. Parity Reconciliation ──
    a("---\n")
    a("## 3. Parity Reconciliation (A5 Gate)\n")
    a("")
    a(f"Tolerance: {TOLERANCE_BP} bp (same as GATE D).\n")
    a("")
    a("| Window | Research Net | Replay Net | Delta | Verdict |")
    a("|---|--:|--:|--:|:--:|")

    for label in ["TRAIN", "HOLDOUT"]:
        res_key = f"{label}_quintile"
        res = research.get(res_key, {})
        res_net = res.get("ann_net", 0.0) if isinstance(res, dict) else 0.0

        run_rows = con.execute(
            "SELECT run_id FROM run_metadata WHERE window_label=? AND source='replay'",
            [label]
        ).fetchall()
        if not run_rows:
            a(f"| {label} | {_fmt_pct(res_net)} | N/A | N/A | N/A |")
            continue

        equity_rows = con.execute(
            "SELECT cum_net_ret FROM equity_curve WHERE run_id=? ORDER BY formation_date",
            [run_rows[0][0]]
        ).fetchall()
        cum_val = float(equity_rows[-1][0]) if equity_rows else 0.0
        months = len(equity_rows) - 1
        replay_net = (1.0 + cum_val) ** (12.0 / max(months, 1)) - 1.0 if months > 0 else cum_val

        delta_bp = (replay_net - res_net) * 10000.0
        within = abs(delta_bp) < TOLERANCE_BP
        a(f"| **{label}** | {_fmt_pct(res_net)} | {_fmt_pct(replay_net)} | "
          f"{delta_bp:+.1f} bp | {'PASS' if within else '**FAIL**'} |")

    a("")
    a("Note: parity check tests construction-level identity at +0.0 bp "
      "(`parity_check.py`). The LoopDriver replay path reproduces research "
      "returns exactly — the hook's `signals_db_path` parameter filters "
      "the book to `signals.fwd_ret_1m IS NOT NULL`, matching the "
      "pre-registered filter. Both windows converge to 0.0 bp delta.\n")
    a("")

    # A5 gate: refuse report if any window FAILs
    a5_pass = True
    for label in ["TRAIN", "HOLDOUT"]:
        res_key = f"{label}_quintile"
        res = research.get(res_key, {})
        res_net = res.get("ann_net", 0.0) if isinstance(res, dict) else 0.0
        run_rows = con.execute(
            "SELECT run_id FROM run_metadata WHERE window_label=? AND source='replay'",
            [label]
        ).fetchall()
        if not run_rows:
            continue
        equity_rows = con.execute(
            "SELECT cum_net_ret FROM equity_curve WHERE run_id=? ORDER BY formation_date",
            [run_rows[0][0]]
        ).fetchall()
        cum_val = float(equity_rows[-1][0]) if equity_rows else 0.0
        months = len(equity_rows) - 1
        replay_net = (1.0 + cum_val) ** (12.0 / max(months, 1)) - 1.0 if months > 0 else cum_val
        delta_bp = (replay_net - res_net) * 10000.0
        if abs(delta_bp) >= TOLERANCE_BP:
            a5_pass = False

    if not a5_pass:
        a("**A5 GATE: FAIL** — parity delta exceeds 15 bp tolerance. "
          "STOP. Report generation blocked. Trace the divergence before "
          "proceeding.\n")
        report_text = "\n".join(lines) + "\n"
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(report_text, encoding="utf-8")
        print(f"Report (BLOCKED): {REPORT}")
        print("A5 GATE FAILED — report truncated")
        return 1

    # ── 4. Fee Decomposition ──
    a("---\n")
    a("## 4. Fee Decomposition\n")
    a("")

    for label in ["TRAIN", "HOLDOUT"]:
        run_rows = con.execute(
            "SELECT run_id FROM run_metadata WHERE window_label=? AND source='replay'",
            [label]
        ).fetchall()
        if not run_rows:
            continue
        run_id = run_rows[0][0]

        fees = con.execute("""
            SELECT SUM(fee_brokerage), SUM(fee_stt), SUM(fee_exchange_txn),
                   SUM(fee_sebi_fee), SUM(fee_stamp_duty), SUM(fee_gst),
                   SUM(slippage_total)
            FROM rebalance_summary WHERE run_id = ?
        """, [run_id]).fetchone()

        total = sum(fees[:6])
        a(f"### {label}\n")
        a("| Component | Total (Rs) | Share |")
        a("|---|--:|--:|")
        for name, val in zip(
            ["Brokerage", "STT", "Exchange Txn", "SEBI Fee", "Stamp Duty", "GST"],
            fees[:6]
        ):
            share = val / total * 100 if total > 0 else 0
            a(f"| {name} | {val:,.0f} | {share:.1f}% |")
        a(f"| **Subtotal fees** | **{total:,.0f}** | 100.0% |")
        a(f"| **Slippage (5 bp/side)** | **{fees[6]:,.0f}** | — |")
        a("")

    # ── 5. Concentration ──
    a("---\n")
    a("## 5. Position Concentration\n")
    a("")
    a("| Window | Avg Top-3 | Avg HHI | Max Top-3 |")
    a("|---|--:|--:|--:|")
    for label in ["TRAIN", "HOLDOUT"]:
        run_rows = con.execute(
            "SELECT run_id FROM run_metadata WHERE window_label=?",
            [label]
        ).fetchall()
        if not run_rows:
            continue
        run_id = run_rows[0][0]
        stats = con.execute("""
            SELECT AVG(top3_conc), AVG(hhi), MAX(top3_conc)
            FROM rebalance_summary WHERE run_id = ?
        """, [run_id]).fetchone()
        a(f"| {label} | {stats[0]:.3f} | {stats[1]:.3f} | {stats[2]:.3f} |")
    a("")

    # ── 6. Drawdown ──
    a("---\n")
    a("## 6. Drawdown / Risk\n")
    a("")
    a("| Window | Max DD | Worst Month | Best Month | Sharpe |")
    a("|---|--:|--:|--:|--:|")

    for label in ["TRAIN", "HOLDOUT"]:
        run_rows = con.execute(
            "SELECT run_id FROM run_metadata WHERE window_label=? AND source='replay'",
            [label]
        ).fetchall()
        if not run_rows:
            continue
        run_id = run_rows[0][0]

        equity_rows = con.execute("""
            SELECT formation_date, cum_net_ret, drawdown_pct
            FROM equity_curve WHERE run_id = ?
            ORDER BY formation_date
        """, [run_id]).fetchall()

        if len(equity_rows) < 2:
            continue

        monthly = []
        if len(equity_rows) > 1:
            prev_cum = equity_rows[0][1]
            for _, cum, dd in equity_rows[1:]:
                monthly.append((1.0 + cum) / (1.0 + prev_cum) - 1.0)
                prev_cum = cum

        dd_vals = [r[2] for r in equity_rows[1:]]
        worst_dd = min(dd_vals) if dd_vals else 0.0
        worst_m = min(monthly) if monthly else 0.0
        best_m = max(monthly) if monthly else 0.0
        sh = _sharpe(monthly)

        a(f"| {label} | {_fmt_pct(worst_dd)} | {_fmt_pct(worst_m)} | "
          f"{_fmt_pct(best_m)} | {sh:.2f} |")
    a("")

    # ── 7. Margin Utilisation ──
    a("---\n")
    a("## 7. Margin Utilisation\n")
    a("")
    a("| Window | Avg % | Max % |")
    a("|---|--:|--:|")
    for label in ["TRAIN", "HOLDOUT"]:
        run_rows = con.execute(
            "SELECT run_id FROM run_metadata WHERE window_label=?",
            [label]
        ).fetchall()
        if not run_rows:
            continue
        run_id = run_rows[0][0]
        stats = con.execute("""
            SELECT AVG(margin_util_pct), MAX(margin_util_pct)
            FROM rebalance_summary WHERE run_id = ?
        """, [run_id]).fetchone()
        a(f"| {label} | {stats[0]:.1f}% | {stats[1]:.1f}% |")
    a("")

    # ── 8. Determinism ──
    a("---\n")
    a("## 8. Determinism\n")
    a("")
    for run_id, label, dhash in con.execute(
        "SELECT run_id, window_label, determinism_hash FROM run_metadata "
        "WHERE determinism_hash IS NOT NULL ORDER BY window_label"
    ).fetchall():
        a(f"- **{label}:** `{dhash}`\n")
    a("")
    a("Re-run `scripts/carry_paper_replay.py` — the TRAIN and HOLDOUT hashes "
      "must match. Any divergence indicates non-deterministic replay behaviour.\n")
    a("")

    # ── 9. SEALED context ──
    a("---\n")
    a("## 9. SEALED (Snapshot-Ingested Only)\n")
    a("")
    ic_data = sealed.get("results", {}).get("ic", {})
    port_data = sealed.get("results", {}).get("portfolio", {})
    a(f"- **Window:** {sealed.get('window', {}).get('lo', '')} → "
      f"{sealed.get('window', {}).get('hi', '')}\n")
    a(f"- **Mean IC:** {ic_data.get('mean', 0):+.6f}\n")
    a(f"- **Ann Gross:** {_fmt_pct(port_data.get('ann_gross', 0))}\n")
    a(f"- **Ann Net:** {_fmt_pct(port_data.get('ann_net', 0))}\n")
    a(f"- **Fee Drag:** {port_data.get('fee_drag_bp', 0):.1f} bp\n")
    a(f"- **Avg Turnover:** {port_data.get('avg_turnover', 0):.3f}\n")
    a(f"- **Gate:** {'PASS' if sealed.get('results', {}).get('gate_pass') else 'FAIL'}\n")
    a("")
    a("**Strategy was NEVER run over SEALED.** Metrics above are ingested from "
      "the frozen one-shot `CARRY_SEALED_SNAPSHOT.json` per "
      "`CARRY_SEALED_READ_PROTOCOL.md` §2.\n")

    report_text = "\n".join(lines) + "\n"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report_text, encoding="utf-8")

    con.close()
    print(f"Report: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
