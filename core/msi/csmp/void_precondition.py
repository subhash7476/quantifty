"""A1 VOID precondition — the sealed-run data-integrity gate (dossier §8 / §12.1).

Re-executes gate (b)'s `|move| >= 20%` single-day CA-classification screen over the
EVALUATION WINDOW (a parameter — dev for the dry run, sealed at Phase 6). If there is
any UNDOCUMENTED unexplained residue, the run is VOID: the A2 harness is structurally
incapable of emitting a verdict (it raises before scoring). A single wrong split factor
manufactures +/-50% phantom momentum and can inject a name into the top quintile — this
is the scariest inherited assumption (§12.1), so it is checked BEFORE any metric.

This RE-EXECUTES gate (b)'s screen; it does not re-derive its rates. The thresholds,
`is_ca_shaped`, and the non-equity predicate below are gate (b)'s frozen values
(`scripts/csmp/audit_corporate_actions.py`), reproduced verbatim because that audit is
a report script with no importable screen function. Classification consumes gate (b)'s
own artifacts: `adjustment_factors` (explained) and `ca_scope_exclusions` (documented
residue allow-list). On the dev window gate (b) certified 0 undocumented residue.

It is a DATA-QUALITY check, not a result (a residue count, never a return statistic), so
running it over the sealed window at Phase 6 preserves the seal (dossier §8).
"""

from dataclasses import dataclass
from datetime import date
from typing import List, Tuple

import duckdb

# --- gate (b) frozen screen constants (audit_corporate_actions.py §top) ------
_RESTRICTED_THRESHOLD = 200
_MOVE_LO = -0.20
_MOVE_HI = 0.25
_MAX_GAP_DAYS = 5
_MAGNITUDE_TOLERANCE = 0.25
_CA_RATIOS = [0.5, 0.4, 1 / 3, 0.25, 0.2, 1 / 6, 0.1, 0.05, 0.02, 0.01]
_CA_RATIO_TOLERANCE = 0.02
_CA_RATIO_MIN_PRICE = 5.0
_NON_EQUITY_PREDICATE = """
    COALESCE(si.isin, '') LIKE 'INF%'
    OR (si.symbol IS NULL AND (e.symbol LIKE '%BEES%' OR e.symbol LIKE '%ETF%'
                               OR e.symbol LIKE '%GOLD%'))
"""
_RESIDUE_CLASSES = ("magnitude-mismatch", "direction-mismatch", "CA-shaped-orphan")


def _is_ca_shaped(ret: float, prev_close) -> bool:
    if prev_close is None or prev_close < _CA_RATIO_MIN_PRICE:
        return False
    survived = 1.0 + ret
    return any(abs(survived - r) / r <= _CA_RATIO_TOLERANCE for r in _CA_RATIOS)


@dataclass(frozen=True)
class VoidResult:
    window: Tuple[date, date]
    max_trade_date: date
    n_screened: int
    n_true_moves: int
    residue_total: int
    residue_documented: int
    residue_undocumented: int
    undocumented_rows: Tuple[tuple, ...]
    passed: bool  # True == no undocumented residue == safe to score


class VoidPreconditionError(RuntimeError):
    """Raised when the VOID screen finds undocumented residue. The harness must NOT
    catch this and MUST NOT emit a verdict when it fires."""


def run_void_screen(db_path, win_start: date, win_end: date) -> VoidResult:
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        dates = [r[0] for r in con.execute(
            "SELECT trade_date FROM trading_calendar WHERE n_symbols >= ? "
            "AND trade_date BETWEEN ? AND ? ORDER BY trade_date",
            [_RESTRICTED_THRESHOLD, win_start, win_end]).fetchall()]
        if not dates:
            con.close()
            return VoidResult((win_start, win_end), win_start, 0, 0, 0, 0, 0, (), True)
        max_td = max(dates)
        date_set = set(dates)

        moves = con.execute(f"""
            WITH eqbe AS (
                SELECT e.trade_date, e.symbol, e.close
                FROM equity_bhavcopy e
                LEFT JOIN symbol_isin si ON si.symbol = e.symbol
                WHERE e.series IN ('EQ','BE') AND NOT ({_NON_EQUITY_PREDICATE})
                  AND e.trade_date BETWEEN ? AND ?
            ),
            gaps AS (
                SELECT trade_date, symbol, close,
                       LAG(close) OVER (PARTITION BY symbol ORDER BY trade_date) AS prev_close,
                       LAG(trade_date) OVER (PARTITION BY symbol ORDER BY trade_date) AS prev_td
                FROM eqbe
            )
            SELECT trade_date, symbol, close / prev_close - 1.0 AS ret,
                   trade_date - prev_td AS gap_days, prev_td, prev_close
            FROM gaps
            WHERE prev_close > 0 AND prev_td IS NOT NULL
              AND (close / prev_close - 1.0 <= {_MOVE_LO}
                   OR close / prev_close - 1.0 >= {_MOVE_HI})
            ORDER BY ret
        """, [win_start, win_end]).fetchall()
        # keep only moves whose both endpoints are full sessions in the window
        moves = [m for m in moves if m[0] in date_set and m[4] in date_set]
        true_moves = [m for m in moves if m[3] <= _MAX_GAP_DAYS]

        ca_by_sym = {}
        for sym, ex, f in con.execute(
                "SELECT symbol, ex_date, EXP(SUM(LN(factor))) FROM adjustment_factors "
                "GROUP BY symbol, ex_date").fetchall():
            ca_by_sym.setdefault(sym, []).append((ex, f))

        documented = {(r[0], r[1]) for r in con.execute(
            "SELECT symbol, move_date FROM ca_scope_exclusions").fetchall()}

        residue: List[tuple] = []
        for td, sym, ret, gap, ptd, prev_close in true_moves:
            survived = 1.0 + ret
            spanning = [(ex, f) for ex, f in ca_by_sym.get(sym, []) if ptd < ex <= td]
            if spanning:
                ex, f = min(spanning, key=lambda c: abs(c[1] - survived))
                if abs(f - survived) / survived <= _MAGNITUDE_TOLERANCE:
                    cls = "CA-explained"
                elif (f < 1.0) == (ret < 0):
                    cls = "magnitude-mismatch"
                else:
                    cls = "direction-mismatch"
            elif _is_ca_shaped(ret, prev_close):
                cls = "CA-shaped-orphan"
            else:
                cls = "genuine"
            if cls in _RESIDUE_CLASSES:
                residue.append((td, sym, round(ret, 6), cls))

        undoc = tuple(r for r in residue if (r[1], r[0]) not in documented)
        return VoidResult(
            window=(win_start, win_end), max_trade_date=max_td,
            n_screened=len(moves), n_true_moves=len(true_moves),
            residue_total=len(residue),
            residue_documented=len(residue) - len(undoc),
            residue_undocumented=len(undoc),
            undocumented_rows=undoc,
            passed=len(undoc) == 0,
        )
    finally:
        con.close()


def assert_void_clear(result: VoidResult) -> None:
    """Structural gate: raise if the screen found undocumented residue. The harness
    calls this BEFORE scoring; a VOID window yields no verdict."""
    if not result.passed:
        raise VoidPreconditionError(
            f"VOID: {result.residue_undocumented} undocumented residue move(s) in "
            f"{result.window[0]}..{result.window[1]} — window re-sealed pending a gate-(b) "
            f"fix; NO verdict rendered. Rows: {result.undocumented_rows}"
        )
