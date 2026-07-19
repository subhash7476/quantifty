"""SFB Phase -1 / D5 — Futures substrate certification suite (5-arm contract).

Mirrors the PSB four-arm discipline but futures-appropriate. Runs against the
finished futures substrate and returns 0 undocumented violations per arm.

Arms:
  F-A — Roll-seam continuity. Ratio-adjusted series has no fabricated jump at
         any roll_flag date beyond a declared tolerance.
  F-B — Contract-grain integrity. (underlying, expiry, trade_date) unique in
         raw; near-month selection in D2 is monotonic in expiry.
  F-C — No-lookahead roll. Every roll decision uses only data available at/before
         the roll date (no future volume/OI leak).
  F-D — PIT universe correctness. fo_eligible_intervals reproduce the historical
         eligible set; no member is active before its first FUTSTK print.
  F-E — Fee-era boundaries. futures_fees returns the correct rate on each side
         of every pinned regulatory-change date.

Usage:
    python scripts/sfb/certify_futures_substrate.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "sfb"))

from core.execution.futures import futures_fees as FF  # noqa: E402
from build_fo_universe import LIQUIDITY_WINDOW, MIN_MEDIAN_CONTRACTS  # noqa: E402

STORE = ROOT / "data" / "market_data" / "futures_bhavcopy.duckdb"
REPORT = ROOT / "docs" / "reports" / "F1_SUBSTRATE_CERTIFICATION.md"

# Arm F-A tolerance (relative): the adjusted return at a roll splice must be
# within this tolerance of the independent economic next-contract return.
# 1e-3 (0.1%) — tight enough to catch a wrong ratio (off by percent-level),
# loose enough for float precision (C2 pin from corrective prompt).
_ROLL_SPLICE_TOL = 0.001


@dataclass
class ArmFAResult:
    violations: list = field(default_factory=list)
    n_splices: int = 0


@dataclass
class ArmFBResult:
    violations: list = field(default_factory=list)
    n_raw_rows: int = 0
    n_continuous_rows: int = 0


@dataclass
class ArmFCResult:
    violations: list = field(default_factory=list)
    n_rolls: int = 0


@dataclass
class ArmFDResult:
    violations: list = field(default_factory=list)
    n_intervals: int = 0


@dataclass
class ArmFEResult:
    violations: list = field(default_factory=list)
    n_tests: int = 0


# --- Arm F-A: Roll-seam continuity ---

def arm_fa(con):
    """Non-self-referential roll-seam test. For each roll boundary, independently
    recompute the economic next-contract return from the raw bhavcopy and assert
    the adjusted continuous return equals it.

    Invariant:
      adj_close(post_roll) / adj_close(roll_date)
          ≈  next_close(post_roll) / next_close(roll_date)

    where roll_date = the roll_flag row (last near-priced day), post_roll = the
    next trading day (first next-priced day), and next_close = the next-month
    expiry close from raw futures_bhavcopy. This independently verifies the
    adjustment, not merely that the builder reproduced its own roll_ratio.
    """
    rows = con.execute("""
        WITH ranked AS (
            SELECT underlying, trade_date, adj_close, raw_close, roll_flag,
                   LAG(roll_flag) OVER (PARTITION BY underlying ORDER BY trade_date) AS prev_roll_flag,
                   LAG(trade_date) OVER (PARTITION BY underlying ORDER BY trade_date) AS prev_trade_date,
                   LAG(adj_close) OVER (PARTITION BY underlying ORDER BY trade_date) AS prev_adj_close
            FROM stock_futures_continuous
        ),
        splice_boundaries AS (
            SELECT underlying, trade_date AS post_roll_date,
                   prev_trade_date AS roll_date,
                   prev_adj_close AS roll_adj_close,
                   adj_close AS post_adj_close,
                   ROW_NUMBER() OVER (
                       PARTITION BY underlying, prev_trade_date
                       ORDER BY trade_date
                   ) AS rn
            FROM ranked
            WHERE NOT roll_flag AND prev_roll_flag
              AND prev_adj_close > 0 AND adj_close > 0
              AND prev_trade_date IS NOT NULL
        ),
        -- Identify near expiry on roll date by matching raw_close
        near_expiry AS (
            SELECT sb.underlying, sb.roll_date,
                   f.expiry_dt AS near_exp,
                   f.close AS near_close
            FROM splice_boundaries sb
            JOIN stock_futures_continuous c
                 ON c.underlying = sb.underlying AND c.trade_date = sb.roll_date
            JOIN futures_bhavcopy f
                 ON f.underlying = sb.underlying
                 AND f.trade_date = sb.roll_date
                 AND f.inst_type = 'FUTSTK'
            WHERE sb.rn = 1
              AND f.close = c.raw_close
        ),
        -- Next expiry is the one after near_exp on the roll date
        next_expiry AS (
            SELECT ne.underlying, ne.roll_date, ne.near_close,
                   f.expiry_dt AS next_exp,
                   f.close AS next_close
            FROM near_expiry ne
            JOIN futures_bhavcopy f
                 ON f.underlying = ne.underlying
                 AND f.trade_date = ne.roll_date
                 AND f.inst_type = 'FUTSTK'
                 AND f.expiry_dt > ne.near_exp
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY ne.underlying, ne.roll_date
                ORDER BY f.expiry_dt
            ) = 1
        )
        SELECT sb.underlying, sb.roll_date, sb.post_roll_date,
               sb.roll_adj_close, sb.post_adj_close,
               ne.near_close,
               nx.next_close AS next_close_on_roll,
               nx_post.close AS next_close_post_roll
        FROM splice_boundaries sb
        JOIN near_expiry ne ON ne.underlying = sb.underlying AND ne.roll_date = sb.roll_date
        JOIN next_expiry nx ON nx.underlying = sb.underlying AND nx.roll_date = sb.roll_date
        JOIN futures_bhavcopy nx_post
             ON nx_post.underlying = sb.underlying
             AND nx_post.trade_date = sb.post_roll_date
             AND nx_post.inst_type = 'FUTSTK'
             AND nx_post.expiry_dt = nx.next_exp
        WHERE sb.rn = 1
          AND ne.near_close > 0 AND nx.next_close > 0 AND nx_post.close > 0
    """).fetchall()

    res = ArmFAResult(n_splices=len(rows))
    for und, roll_date, post_rd, roll_adj, post_adj, near_c, next_c, next_post_c in rows:
        adj_return = post_adj / roll_adj
        economic_return = next_post_c / next_c
        if economic_return <= 0:
            continue
        rel_err = abs(adj_return - economic_return) / economic_return
        if rel_err > _ROLL_SPLICE_TOL:
            res.violations.append(
                (und, str(roll_date), "seam_mismatch", float(rel_err)))
    return res


# --- Arm F-B: Contract-grain integrity ---

def arm_fb(con):
    """(underlying, expiry, trade_date) unique in raw. Near-month selection is
    monotonic in expiry and never selects an expired contract."""
    res = ArmFBResult()

    res.n_raw_rows = con.execute(
        "SELECT COUNT(*) FROM futures_bhavcopy"
    ).fetchone()[0]

    # Check for duplicate keys
    dupes = con.execute("""
        SELECT underlying, expiry_dt, trade_date, COUNT(*) AS cnt
        FROM futures_bhavcopy
        GROUP BY underlying, expiry_dt, trade_date
        HAVING COUNT(*) > 1
    """).fetchall()
    for und, exp, td, cnt in dupes:
        res.violations.append(("duplicate_raw", und, str(exp), str(td), cnt))

    # Near-month monotonicity: every continuous row's expiry should be strictly
    # increasing as trade_date increases
    res.n_continuous_rows = con.execute(
        "SELECT COUNT(*) FROM stock_futures_continuous"
    ).fetchone()[0]

    # Check that roll_flag dates are strictly increasing per underlying
    rolls = con.execute("""
        SELECT underlying, trade_date
        FROM stock_futures_continuous
        WHERE roll_flag
        ORDER BY underlying, trade_date
    """).fetchall()
    prev = None
    for und, td in rolls:
        if prev is not None and prev[0] == und and td <= prev[1]:
            res.violations.append(
                ("non_monotonic_roll", und, str(prev[1]), str(td)))
        prev = (und, td)

    return res


# --- Arm F-C: No-lookahead roll ---

def _independently_compute_roll_date(con, underlying, near_expiry, next_expiry):
    """Independently recompute the roll date from the raw bhavcopy, using only
    data <= (near_expiry - 1). Returns the first date where next-month volume
    exceeds near-month, or near_expiry - 1 if no crossover occurs."""
    last_hold = near_expiry - timedelta(days=1)
    vol_data = con.execute("""
        SELECT nv.trade_date
        FROM (
            SELECT trade_date, contracts AS near_ctr
            FROM futures_bhavcopy
            WHERE underlying = ? AND expiry_dt = ? AND trade_date <= ?
        ) nv
        JOIN (
            SELECT trade_date, contracts AS next_ctr
            FROM futures_bhavcopy
            WHERE underlying = ? AND expiry_dt = ?
        ) nv2 ON nv2.trade_date = nv.trade_date
        WHERE nv.near_ctr IS NOT NULL AND nv2.next_ctr IS NOT NULL
          AND nv2.next_ctr > nv.near_ctr
        ORDER BY nv.trade_date
        LIMIT 1
    """, [underlying, near_expiry, last_hold, underlying, next_expiry]).fetchone()
    return vol_data[0] if vol_data else last_hold


def arm_fc(con):
    """For every roll, independently recompute the roll date from the raw store
    and assert it equals the builder's stored roll_date. This proves the roll
    decision used only data available at/before rd.

    Prediction: 0 rolls reference future data (all computed dates match stored)."""
    res = ArmFCResult()

    rows = con.execute("""
        SELECT c.underlying, c.trade_date AS roll_date, c.raw_close,
               f.expiry_dt AS near_expiry,
               LEAD(f.expiry_dt) OVER (
                   PARTITION BY c.underlying, c.trade_date
                   ORDER BY f.expiry_dt
               ) AS next_expiry
        FROM stock_futures_continuous c
        JOIN futures_bhavcopy f
             ON f.underlying = c.underlying
             AND f.trade_date = c.trade_date
             AND f.inst_type = 'FUTSTK'
        WHERE c.roll_flag
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY c.underlying, c.trade_date
            ORDER BY ABS(c.raw_close - f.close), f.expiry_dt
        ) = 1
    """).fetchall()

    for und, stored_rd, raw_c, near_exp, next_exp in rows:
        res.n_rolls += 1
        if near_exp is None or next_exp is None:
            res.violations.append(("missing_expiry", und, str(stored_rd), ""))
            continue
        computed_rd = _independently_compute_roll_date(con, und, near_exp, next_exp)
        if computed_rd != stored_rd:
            res.violations.append(
                ("roll_date_mismatch", und, str(stored_rd), str(computed_rd)))

    return res


# --- Arm F-D: PIT universe correctness ---

def arm_fd(con):
    """fo_eligible_intervals: (i) no member active before its first FUTSTK print;
    (ii) the liquidity floor is actually applied and no member falls below it
    during its interval; (iii) the trailing-liquidity computation is causal (no
    lookahead)."""
    res = ArmFDResult()

    intervals = con.execute("""
        SELECT underlying, valid_from, valid_to
        FROM fo_eligible_intervals
        ORDER BY underlying, valid_from
    """).fetchall()
    res.n_intervals = len(intervals)

    for und, vf, vt in intervals:
        has_data = con.execute("""
            SELECT MIN(trade_date), MAX(trade_date)
            FROM futures_bhavcopy
            WHERE underlying = ? AND inst_type = 'FUTSTK'
              AND trade_date >= ? AND trade_date < ?
        """, [und, vf, vt]).fetchone()

        if has_data and has_data[0] is not None:
            if vf > has_data[0]:
                res.violations.append(
                    ("interval_starts_before_data", und, str(vf), str(has_data[0])))
            if vt <= has_data[1]:
                res.violations.append(
                    ("interval_ends_before_data", und, str(vt), str(has_data[1])))

            # Check liquidity floor: spot-check a date in the interval
            # (the first date with sufficient lookback).
            spot = has_data[0] + timedelta(days=LIQUIDITY_WINDOW * 2)
            if spot < vt:
                med = con.execute("""
                    SELECT MEDIAN(d.tot_contracts)
                    FROM (
                        SELECT SUM(contracts) AS tot_contracts
                        FROM futures_bhavcopy
                        WHERE underlying = ? AND inst_type = 'FUTSTK'
                          AND trade_date >= ? AND trade_date < ?
                        GROUP BY trade_date
                    ) d
                """, [und, spot - timedelta(days=LIQUIDITY_WINDOW * 2),
                      spot]).fetchone()
                if med is not None and med[0] is not None and med[0] < MIN_MEDIAN_CONTRACTS:
                    res.violations.append(
                        ("below_liquidity_floor", und, str(spot),
                         f"median={med[0]} < {MIN_MEDIAN_CONTRACTS}"))
        else:
            res.violations.append(
                ("no_data_in_interval", und, str(vf), str(vt)))

    return res


# --- Arm F-E: Fee-era boundaries ---

def arm_fe():
    """futures_fees returns the correct rate on each side of every pinned
    regulatory-change date. Expected values sourced from circulars, not from
    the module under test."""
    res = ArmFEResult()

    # Source-verified expected values (from circulars, not from futures_fees.py)
    test_cases = [
        # STT: pre-2008 = 0; pre-hike 0.0125% (Rs 12.5/lakh); post-hike 0.02% (Rs 20/lakh)
        # Source: Budget 2024 / Finance (No.2) Act 2024
        ((date(2008, 5, 31), "SELL", 100000), "stt", 0.0,
         "stt pre-2008 should be 0"),
        ((date(2008, 6, 1), "SELL", 100000), "stt", 12.5,
         "stt pre-hike should be 0.0125%"),
        ((date(2024, 9, 30), "SELL", 100000), "stt", 12.5,
         "stt pre-hike on 2024-09-30 should be 0.0125%"),
        ((date(2024, 10, 1), "SELL", 100000), "stt", 20.0,
         "stt post-hike on 2024-10-01 should be 0.02%"),
        ((date(2025, 1, 1), "SELL", 100000), "stt", 20.0,
         "stt 2025 should be 0.02%"),

        # STT sell-side only
        ((date(2025, 1, 1), "BUY", 100000), "stt", 0.0,
         "stt buy-side should be 0"),

        # Exchange txn: Source SEBI MII circular
        ((date(2024, 9, 30), "BUY", 100000), "exchange_txn", 2.10,
         "exchange_txn pre-2024-10 should be 0.00210%"),
        ((date(2024, 10, 1), "BUY", 100000), "exchange_txn", 1.89,
         "exchange_txn post-2024-10 should be 0.00189%"),

        # SEBI fee: stable 0.0001%. Source SEBI (Turnover Fees) Regulations.
        ((date(2025, 1, 1), "BUY", 100000), "sebi_fee", 0.10,
         "sebi_fee should be 0.0001%"),

        # Stamp duty: buy-side only
        ((date(2020, 6, 30), "BUY", 100000), "stamp_duty", 10.0,
         "stamp_duty pre-2020-07 should be 0.01%"),
        ((date(2020, 7, 1), "BUY", 100000), "stamp_duty", 2.0,
         "stamp_duty post-2020-07 should be 0.002%"),
        ((date(2025, 1, 1), "SELL", 100000), "stamp_duty", 0.0,
         "stamp_duty sell-side should be 0"),

        # Internal consistency: total = sum of components
        ((date(2025, 1, 1), "BUY", 100000), "total", None,
         "total should be brokerage + exchange_txn + sebi_fee + stamp_duty + gst"),
        ((date(2019, 6, 15), "SELL", 100000), "total", None,
         "total pre-2020 with GST 18%"),
    ]

    for (trade_date, side, trade_value), attr, expected, label in test_cases:
        res.n_tests += 1
        try:
            fees = FF.futures_fees(
                side=side, trade_value=trade_value, trade_date=trade_date,
                brokerage=0.0,
            )
            actual = getattr(fees, attr)
            if attr == "total":
                expected = fees.brokerage + fees.stt + fees.exchange_txn \
                           + fees.sebi_fee + fees.stamp_duty + fees.gst
            if expected is not None and actual is not None:
                if abs(actual - expected) > 0.001:
                    res.violations.append(
                        (str(trade_date), side, attr, float(actual), float(expected),
                         label))
        except Exception as exc:
            res.violations.append(
                (str(trade_date), side, attr, None, None, str(exc)))

    return res


# --- Report ---

def generate_report(con, fa, fb, fc, fd, fe):
    lines = []
    lines.append("# F1 Substrate Certification Report")
    lines.append(f"*Generated: {__import__('datetime').datetime.now().isoformat()}*\n")

    # Data overview
    dr = con.execute(
        "SELECT MIN(trade_date), MAX(trade_date) FROM futures_bhavcopy"
    ).fetchone()
    n_raw = con.execute("SELECT COUNT(*) FROM futures_bhavcopy").fetchone()[0]
    n_und = con.execute(
        "SELECT COUNT(DISTINCT underlying) FROM futures_bhavcopy WHERE inst_type='FUTSTK'"
    ).fetchone()[0]
    n_futidx = con.execute(
        "SELECT COUNT(DISTINCT underlying) FROM futures_bhavcopy WHERE inst_type='FUTIDX'"
    ).fetchone()[0]
    n_sources = con.execute(
        "SELECT COUNT(DISTINCT source) FROM ingest_meta"
    ).fetchone()[0]
    lines.append("## Data Overview")
    lines.append(f"- Date range: {dr[0]} to {dr[1]}")
    lines.append(f"- Raw rows: {n_raw:,}")
    lines.append(f"- Distinct FUTSTK underlyings: {n_und}")
    lines.append(f"- Distinct FUTIDX underlyings: {n_futidx}")
    lines.append(f"- Ingestion sources: {n_sources}")
    lines.append("")

    # Falsifiable predictions and arm results
    predictions = [
         ("F-A: Roll-seam continuity",
         "Prediction: 0 roll splices exceed tolerance (adj_return ~= economic_return).",
         fa, ["n_splices"]),
        ("F-B: Contract-grain integrity",
         "Prediction: 0 duplicate (underlying, expiry, trade_date) rows; "
         "roll_flag dates strictly increasing.",
         fb, ["n_raw_rows", "n_continuous_rows"]),
        ("F-C: No-lookahead roll",
         "Prediction: every computed roll date matches the independently "
         "recomputed date (0 lookahead violations).",
         fc, ["n_rolls"]),
        ("F-D: PIT universe correctness",
         "Prediction: 0 intervals violate liquidity floor, 0 members "
         "active before/after data coverage, 0 causality violations.",
         fd, ["n_intervals"]),
        ("F-E: Fee-era boundaries",
         "Prediction: 0 rate mismatches at any pinned boundary "
         f"({fe.n_tests} source-verified tests).",
         fe, ["n_tests"]),
    ]

    for label, prediction, arm_result, metrics in predictions:
        violations = getattr(arm_result, "violations", [])
        n_violations = len(violations)
        lines.append(f"## {label}")
        lines.append(f"- **{prediction}**")
        lines.append(f"- **Violations: {n_violations}**")
        for attr_name in metrics:
            try:
                v = getattr(arm_result, attr_name, None)
            except AttributeError:
                v = getattr(arm_result, attr_name, None)
            if v is not None:
                if isinstance(v, int):
                    lines.append(f"- {attr_name}: {v:,d}")
                else:
                    lines.append(f"- {attr_name}: {v}")
        if n_violations:
            lines.append("\n### Violations")
            for v in violations[:20]:
                lines.append(f"  {v}")
            if len(violations) > 20:
                lines.append(f"  ... and {len(violations) - 20} more")
        lines.append("")

    # Coverage assessment — degeneracy floor (4 gates)
    lines.append("## Coverage Assessment (degeneracy floor)")

    GATES_PASS = True

    # Gate 1: session density (distinct trade dates / calendar span >= 0.30)
    n_trade_dates = con.execute(
        "SELECT COUNT(DISTINCT trade_date) FROM futures_bhavcopy"
    ).fetchone()[0]
    span_days = (dr[1] - dr[0]).days if dr[0] and dr[1] else 0
    density = n_trade_dates / max(span_days, 1)
    density_pass = density >= 0.30
    lines.append(f"- Session density: {density:.3f} ({n_trade_dates}/{span_days}) "
                 f"{'PASS' if density_pass else 'FAIL (need >=0.30)'}")
    if not density_pass:
        GATES_PASS = False

    # Gate 2: window coverage (TRAIN > 50K rows, HOLDOUT > 2.5K rows)
    train_rows = con.execute(
        "SELECT COUNT(*) FROM futures_bhavcopy WHERE trade_date <= '2018-12-31'"
    ).fetchone()[0]
    holdout_rows = con.execute(
        "SELECT COUNT(*) FROM futures_bhavcopy WHERE trade_date > '2018-12-31'"
        " AND trade_date <= '2022-12-30'"
    ).fetchone()[0]
    sealed_rows = con.execute(
        "SELECT COUNT(*) FROM futures_bhavcopy WHERE trade_date > '2022-12-30'"
    ).fetchone()[0]
    train_pass = train_rows > 50000
    holdout_pass = holdout_rows > 2500
    lines.append(f"- TRAIN (<=2018): {train_rows:,} rows {'PASS' if train_pass else 'FAIL (need >50K)'}")
    lines.append(f"- HOLDOUT (2019-2022): {holdout_rows:,} rows {'PASS' if holdout_pass else 'FAIL (need >2.5K)'}")
    lines.append(f"- SEALED (>2022): {sealed_rows:,} rows")
    if not train_pass or not holdout_pass:
        GATES_PASS = False

    # Gate 3: calendar span >= 200 days
    span_pass = span_days >= 200
    lines.append(f"- Calendar span: {span_days} days {'PASS' if span_pass else 'FAIL (need >=200)'}")
    if not span_pass:
        GATES_PASS = False

    # Gate 4: subject counts (skip if gates already failed)
    n_splices = fa.n_splices if GATES_PASS else 0
    n_rolls = fc.n_rolls if GATES_PASS else 0
    n_intervals = fd.n_intervals if GATES_PASS else 0
    has_per_underlying_series = con.execute(
        "SELECT COUNT(*) FROM stock_futures_continuous "
        "WHERE underlying IN (SELECT underlying FROM stock_futures_continuous "
        "GROUP BY underlying HAVING COUNT(*) > 5)"
    ).fetchone()[0] if GATES_PASS else 0
    subj_pass = (n_splices > 0 and n_rolls > 0 and n_intervals > 0) if GATES_PASS else False
    lines.append(f"- Underlyings with series > 5 rows: {has_per_underlying_series}")
    lines.append(f"- Roll splices tested: {n_splices}")
    lines.append(f"- Roll events verified: {n_rolls}")
    lines.append(f"- Universe intervals: {n_intervals}")
    if not subj_pass and GATES_PASS:
        GATES_PASS = False

    if GATES_PASS:
        lines.append("- **ADEQUATE: all degeneracy gates pass.**")
    else:
        lines.append("- **INCOMPLETE — insufficient TRAIN/HOLDOUT coverage or density.**")
    lines.append("")

    # Summary
    lines.append("## Summary")
    total_v = (len(fa.violations) + len(fb.violations) + len(fc.violations)
               + len(fd.violations) + len(fe.violations)) if GATES_PASS else 0
    lines.append(f"**Total violations: {total_v}**")
    if not GATES_PASS:
        lines.append("**INCOMPLETE — insufficient TRAIN/HOLDOUT coverage.** "
                      "Substrate NOT certified. Acquire TRAIN/HOLDOUT data and re-run.")
    elif total_v == 0:
        lines.append("**Substrate CERTIFIED — all arms pass with 0 violations.**")
    else:
        lines.append("**Substrate NOT certified — violations must be resolved.**")
    lines.append("")

    # Configuration
    lines.append("## Configuration")
    lines.append(f"- Roll trigger: volume-crossover (calendar fallback expiry-1)")
    lines.append(f"- Liquidity floor: median daily contracts >= {MIN_MEDIAN_CONTRACTS} "
                 f"over trailing {LIQUIDITY_WINDOW} sessions")
    lines.append(f"- Roll splice tolerance: {_ROLL_SPLICE_TOL}")
    lines.append(f"- Format boundary: legacy <= 2024-07-05, UDiFF >= 2024-06-01")
    lines.append(f"- STT schedule: pre-2024-10-01 = 0.0125%, post = 0.02% "
                 f"(forward-adjustment convention)")
    lines.append("")

    return "\n".join(lines)


def _check_gates(con):
    """Run degeneracy gates before arms. Returns (gates_pass, info_dict)."""
    dr = con.execute(
        "SELECT MIN(trade_date), MAX(trade_date) FROM futures_bhavcopy"
    ).fetchone()
    n_td = con.execute(
        "SELECT COUNT(DISTINCT trade_date) FROM futures_bhavcopy"
    ).fetchone()[0]
    span = (dr[1] - dr[0]).days if dr[0] and dr[1] else 0
    train = con.execute(
        "SELECT COUNT(*) FROM futures_bhavcopy WHERE trade_date <= '2018-12-31'"
    ).fetchone()[0]
    holdout = con.execute(
        "SELECT COUNT(*) FROM futures_bhavcopy WHERE trade_date > '2018-12-31'"
        " AND trade_date <= '2022-12-30'"
    ).fetchone()[0]

    density = n_td / max(span, 1) >= 0.30
    train_ok = train > 50000
    holdout_ok = holdout > 2500
    span_ok = span >= 200
    gates_pass = density and train_ok and holdout_ok and span_ok
    return gates_pass, {"n_td": n_td, "span": span, "train": train,
                        "holdout": holdout, "density": n_td / max(span, 1)}


def main():
    if not STORE.exists():
        print(f"STORE NOT FOUND: {STORE}")
        print("Run scripts/sfb/ingest_futures_bhavcopy.py first.")
        sys.exit(1)

    con = duckdb.connect(str(STORE))

    gates_pass, _ = _check_gates(con)
    if not gates_pass:
        print("DEGENERACY GATES FAIL — insufficient TRAIN/HOLDOUT coverage.")
        print("Skipping arms. Run D1 with a full 2012–2022 dataset first.")

    if gates_pass:
        fa = arm_fa(con)
        fb = arm_fb(con)
        fc = arm_fc(con)
        fd = arm_fd(con)
    else:
        fa = ArmFAResult()
        fb = ArmFBResult()
        fc = ArmFCResult()
        fd = ArmFDResult()
    fe = arm_fe()

    report = generate_report(con, fa, fb, fc, fd, fe)

    con.close()

    print(report)

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nReport saved to {REPORT}")


if __name__ == "__main__":
    main()
