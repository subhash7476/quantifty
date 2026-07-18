"""MTO file parser — `20`-record-type positional parser.

Format (stable 2010–2020): comma-separated, data records are
`20,<srno>,<SYMBOL>,<SERIES>,<qty_traded>,<deliv_qty>,<deliv_pct>`.
The column-header line lists 6 fields (omits SERIES) — parse by record type only.
"""

from __future__ import annotations

import csv
import io
from typing import IO

SKIP_PREFIXES = {"Security Wise", "10,", "Trade Date", "Record Type"}
RECORD_TYPE = "20"


def parse_mto_file(f: str | IO) -> tuple[list, list]:
    """Parse an MTO file, return (rows, rejects).

    rows: list of (symbol, series, qty_traded, deliv_qty, deliv_pct)
          qty_traded/deliv_qty are int or None; deliv_pct is float or None.
    rejects: list of (line_num, raw, reason) for malformed lines.
    """
    rows = []
    rejects = []

    if isinstance(f, str):
        f = io.StringIO(f)

    for i, line in enumerate(f, start=1):
        raw = line.rstrip("\r\n")
        if not raw:
            continue
        stripped = raw.strip()
        if not stripped:
            continue

        if any(stripped.startswith(p) for p in SKIP_PREFIXES):
            continue

        parts = next(csv.reader([stripped]))
        if parts[0] != RECORD_TYPE:
            continue

        try:
            if len(parts) < 5:
                rejects.append((i, raw, f"too few fields ({len(parts)})"))
                continue

            symbol = parts[2].strip()
            series = parts[3].strip() if len(parts) > 3 else ""

            if not symbol:
                rejects.append((i, raw, "empty symbol"))
                continue

            if not parts[4].strip():
                rejects.append((i, raw, "empty qty_traded"))
                continue
            try:
                qty_traded = int(parts[4].replace(",", ""))
            except (ValueError, IndexError):
                rejects.append((i, raw, f"bad qty_traded: {parts[4]}"))
                continue

            deliv_qty = None
            deliv_pct = None
            if len(parts) > 5 and parts[5].strip():
                try:
                    deliv_qty = int(parts[5].replace(",", ""))
                except ValueError:
                    rejects.append((i, raw, f"bad deliv_qty: {parts[5]}"))
                    continue
            if len(parts) > 6 and parts[6].strip():
                try:
                    deliv_pct = float(parts[6].replace(",", ""))
                except ValueError:
                    rejects.append((i, raw, f"bad deliv_pct: {parts[6]}"))
                    continue

            if len(parts) > 7:
                rejects.append((i, raw, f"too many fields ({len(parts)})"))
                continue

            rows.append((symbol, series, qty_traded, deliv_qty, deliv_pct))

        except Exception as e:
            rejects.append((i, raw, str(e)))

    return rows, rejects
