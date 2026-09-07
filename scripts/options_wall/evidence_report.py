"""Generate the Options-Wall evidence report from the pilot's results DB.

Reads `wall_scan_results.duckdb` (read-only) and writes a Markdown expectancy
report to docs/reports/OPTIONS_WALL_EVIDENCE.md — overall, then broken down by
exit reason, GEX regime at entry, and the IV−RV band the farm signal fired on.

    python scripts/options_wall/evidence_report.py [--index NIFTY|ALL]
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.options_wall.evidence import evidence_summary  # noqa: E402

OUT = Path("docs/reports/OPTIONS_WALL_EVIDENCE.md")


def _pct(x):
    return "--" if x is None else f"{x * 100:.1f}%"


def _money(x):
    return "--" if x is None else f"₹{x:,.0f}"


def _rom(x):
    return "--" if x is None else f"{x * 100:.2f}%"


def _table(title, groups):
    lines = [f"### {title}", "",
             "| Bucket | n | Win rate | Total net | Avg net | Avg RoM |",
             "|---|--:|--:|--:|--:|--:|"]
    if not groups:
        lines.append("| _(no closed trades)_ | | | | | |")
    for k, a in groups.items():
        lines.append(f"| {k} | {a['n']} | {_pct(a['win_rate'])} | "
                     f"{_money(a['total_net'])} | {_money(a['avg_net'])} | "
                     f"{_rom(a['avg_rom'])} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default="ALL",
                    help="NIFTY / BANKNIFTY / SENSEX / ALL (default ALL)")
    args = ap.parse_args()
    index = args.index.upper()
    name = None if index == "ALL" else index
    s = evidence_summary(name)
    o = s["overall"]

    md = [f"# Options-Wall Evidence — {index}", "",
          f"_Generated {datetime.now():%Y-%m-%d %H:%M} from `wall_scan_results.duckdb` "
          f"(closed paper flies joined to entry regime). Read-only._", "",
          "## Overall", "",
          f"- Closed trades: **{o['n']}** (wins {o['wins']})",
          f"- Win rate: **{_pct(o['win_rate'])}**",
          f"- Total net P&L: **{_money(o['total_net'])}**",
          f"- Avg net / trade: **{_money(o['avg_net'])}**",
          f"- Avg return on margin: **{_rom(o['avg_rom'])}**", "",
          _table("By exit reason", s["by_exit_reason"]),
          _table("By GEX regime at entry", s["by_regime"]),
          _table("By IV−RV band at entry", s["by_iv_band"])]
    if o["n"] == 0:
        md.append("> No closed trades yet — the report populates as the pilot runs "
                  "and the executor closes flies. Evidence accrues in the wall store.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(md), encoding="utf-8")
    print(f"wrote {OUT} ({o['n']} closed trades)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
