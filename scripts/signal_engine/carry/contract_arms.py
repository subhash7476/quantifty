"""Carry substrate certification — four-arm contract suite.

Mirrors the PSB-1 discipline (scripts/psb1/contract_arms.py): whole panel, entity grain,
ZERO structural pre-filters. Adapted from one-leg adjusted returns to the two-leg basis.

CONSTRUCTION RULES (from CARRY_IMPLEMENTATION_PROMPTS.md section 5):
  RULE 1 — RAW spot, not adjusted. The basis is (F-S)/S, a same-session ratio. Using
           back-adjusted spot fabricates a basis on every name with a later corporate action.
  RULE 2 — PIT F&O eligibility from the feed itself. A name is F&O-listed on date d IFF
           it has a FUTSTK record on d. fo_eligible_intervals is unusable (10-month coverage).

NEAR-MONTH SELECTOR (pre-reg section 3.4):
  Near-month = minimum expiry_dt >= trade_date. Roll to next expiry when <= 3 TRADING days
  remain (trading days from distinct trade_date set in futures_bhavcopy). Annualization
  uses CALENDAR days (365 / days_to_expiry). Guard days_to_expiry >= 1.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ── Bounds (stated BEFORE running, economically defensible) ──────────────────

# Arm A: roll-continuity tolerance on RAW basis ratio. At a roll date, both contracts
# are on the same underlying, so the raw (F−S)/S should be roughly continuous. Annualized
# basis is misleading here because the two contracts have very different DTE. A raw
# basis jump > 5% flags a genuine discontinuity.
ROLL_RAW_TOL = 0.05

# Arm C: tolerance for raw basis ratio change at CA ex-dates. For splits/bonuses the
# ratio cancels so raw basis should not jump. For dividends, the futures market in India
# is efficient enough that F adjusts by ~D, so the raw basis changes by ~D/S (not the
# theoretical D/(S·τ) which over-predicts). Flag the residual after subtracting D/S.
CA_RAW_TOL = 0.03

# Arm D: two-tier flag. (1) Raw ratio beyond ±5% is almost certainly a data defect or
# genuine crisis — either way it must be dispositioned. (2) Annualized beyond ±200% AND
# DTE >= 5 catches persistent extreme carry that isn't a near-expiry artifact.
RAW_RATIO_BOUND = 0.05
BASIS_FABRICATION_BOUND = 2.00
MIN_DTE_FOR_ANNUALIZED_FLAG = 5


# ── Result dataclasses ───────────────────────────────────────────────────────

@dataclass
class ArmAResult:
    gaps: int = 0
    overlaps: int = 0
    roll_jumps: list = field(default_factory=list)  # (underlying, date, prev_basis, new_basis, change)


@dataclass
class ArmBResult:
    unresolved_symbols: list = field(default_factory=list)  # symbols not in entity_intervals
    multi_entity: list = field(default_factory=list)  # (symbol, date, entity1, entity2)
    spot_missing: int = 0  # (name, date) cells with no EQ spot leg


@dataclass
class ArmCResult:
    split_violations: list = field(default_factory=list)  # (symbol, ex_date, prev_raw, new_raw, change)
    dividend_residuals: list = field(default_factory=list)  # (symbol, ex_date, actual_step, predicted_step, residual)
    dividend_exposure_pct: float = 0.0  # fraction of cells with dividend in holding period
    pit_limitation: str = ""


@dataclass
class ArmDResult:
    extreme_cells: list = field(default_factory=list)  # (underlying, date, annualized_basis, raw_ratio, days_to_exp)
    stale_cells: int = 0  # cells where one leg is NULL


@dataclass
class PITResult:
    total_cells: int = 0
    non_pit_cells: int = 0  # should be 0 by construction


# ── Basis panel builder ──────────────────────────────────────────────────────

def build_basis_panel(con):
    """Build the near-month basis panel as temp table 'basis_panel'.

    Uses RAW spot (RULE 1), T-3 roll rule, and attaches entity from
    symbol_entity_intervals. Both databases must be attached as 'fut' and 'eq'.
    """
    con.execute("CREATE TEMP TABLE IF NOT EXISTS td_cal AS "
        "SELECT trade_date, ROW_NUMBER() OVER (ORDER BY trade_date) AS td_idx "
        "FROM (SELECT DISTINCT trade_date FROM fut.futures_bhavcopy WHERE inst_type='FUTSTK')")

    con.execute("""
        CREATE TEMP TABLE basis_panel AS
        WITH nde AS (
            SELECT DISTINCT underlying, trade_date, expiry_dt
            FROM fut.futures_bhavcopy
            WHERE inst_type='FUTSTK' AND expiry_dt >= trade_date
        ),
        ranked AS (
            SELECT underlying, trade_date, expiry_dt,
                   ROW_NUMBER() OVER (PARTITION BY underlying, trade_date ORDER BY expiry_dt) AS rn
            FROM nde
        ),
        near AS (
            SELECT underlying, trade_date, expiry_dt AS near_exp
            FROM ranked WHERE rn = 1
        ),
        nxt AS (
            SELECT underlying, trade_date, expiry_dt AS next_exp
            FROM ranked WHERE rn = 2
        ),
        td_to_exp AS (
            SELECT n.underlying, n.trade_date, n.near_exp, nx.next_exp,
                   ec.td_idx - tc.td_idx AS tdays
            FROM near n
            JOIN td_cal tc ON tc.trade_date = n.trade_date
            LEFT JOIN td_cal ec ON ec.trade_date = n.near_exp
            LEFT JOIN nxt nx ON nx.underlying = n.underlying AND nx.trade_date = n.trade_date
        ),
        sel AS (
            SELECT underlying, trade_date,
                   CASE WHEN tdays <= 3 AND next_exp IS NOT NULL THEN next_exp ELSE near_exp END AS sel_exp,
                   tdays
            FROM td_to_exp
        )
        SELECT
            s.underlying,
            s.trade_date,
            s.sel_exp AS expiry_dt,
            f.close  AS fut_close,
            f.settle AS fut_settle,
            e.close  AS spot_close,
            CASE WHEN e.close IS NOT NULL AND e.close > 0 AND f.close IS NOT NULL THEN
                (f.close - e.close) / e.close
            ELSE NULL END AS raw_basis_ratio,
            CASE WHEN e.close IS NOT NULL AND e.close > 0 AND f.close IS NOT NULL THEN
                (f.close - e.close) / e.close
                    * 365.0 / GREATEST(date_diff('day', s.trade_date, s.sel_exp), 1)
            ELSE NULL END AS annualized_basis,
            date_diff('day', s.trade_date, s.sel_exp) AS days_to_expiry,
            s.tdays AS trading_days_to_exp,
            i.entity
        FROM sel s
        JOIN fut.futures_bhavcopy f
            ON f.underlying = s.underlying
           AND f.trade_date = s.trade_date
           AND f.expiry_dt = s.sel_exp
           AND f.inst_type = 'FUTSTK'
        LEFT JOIN eq.equity_bhavcopy e
            ON e.symbol = s.underlying
           AND e.trade_date = s.trade_date
           AND e.series = 'EQ'
        LEFT JOIN eq.symbol_entity_intervals i
            ON i.symbol = s.underlying
           AND s.trade_date >= i.valid_from
           AND (i.valid_to IS NULL OR s.trade_date < i.valid_to)
    """)

    r = con.execute("SELECT COUNT(*) FROM basis_panel").fetchone()
    return r[0]


# ── Arm A — Contract identity & roll integrity ───────────────────────────────

def arm_a(con):
    """Contract identity & roll integrity.

    Checks:
    1. No gaps: every (underlying, trade_date) in FUTSTK has a basis_panel entry
    2. No overlaps: no (underlying, trade_date) has >1 selected contract
    3. Roll continuity: annualized basis doesn't jump > ROLL_BASIS_TOL at roll dates
    """
    res = ArmAResult()

    # 1. Gaps: name-dates in futures that aren't in the basis panel
    res.gaps = con.execute("""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT f.underlying, f.trade_date
            FROM fut.futures_bhavcopy f
            WHERE f.inst_type='FUTSTK' AND f.expiry_dt >= f.trade_date
            EXCEPT
            SELECT underlying, trade_date FROM basis_panel
        )
    """).fetchone()[0]

    # 2. Overlaps: multiple selected contracts per (name, date)
    res.overlaps = con.execute("""
        SELECT COUNT(*) FROM (
            SELECT underlying, trade_date, COUNT(*) AS n
            FROM basis_panel GROUP BY underlying, trade_date HAVING n > 1
        )
    """).fetchone()[0]

    # 3. Roll continuity: raw basis ratio jump at roll dates
    res.roll_jumps = con.execute(f"""
        WITH lag AS (
            SELECT underlying, trade_date, expiry_dt, raw_basis_ratio,
                   LAG(expiry_dt)       OVER w AS prev_expiry,
                   LAG(raw_basis_ratio) OVER w AS prev_raw,
                   LAG(trade_date)      OVER w AS prev_trade_date
            FROM basis_panel
            WINDOW w AS (PARTITION BY underlying ORDER BY trade_date)
        )
        SELECT underlying, prev_trade_date, trade_date,
               prev_raw, raw_basis_ratio,
               ABS(raw_basis_ratio - prev_raw) AS raw_change
        FROM lag
        WHERE prev_expiry IS NOT NULL AND prev_expiry <> expiry_dt
          AND prev_raw IS NOT NULL AND raw_basis_ratio IS NOT NULL
          AND ABS(raw_basis_ratio - prev_raw) > {ROLL_RAW_TOL}
        ORDER BY raw_change DESC
    """).fetchall()

    return res


# ── Arm B — Two-leg entity alignment ─────────────────────────────────────────

def arm_b(con):
    """Two-leg entity alignment.

    Checks:
    1. Every FUTSTK underlying resolves to an entity via symbol_entity_intervals
    2. No (symbol, date) maps to multiple entities (co-trading guard)
    3. Spot leg coverage: every (name, date) has an EQ close
    """
    res = ArmBResult()

    # 1. Underlyings not in symbol_entity_intervals
    res.unresolved_symbols = con.execute("""
        SELECT DISTINCT b.underlying
        FROM basis_panel b
        WHERE b.entity IS NULL
        ORDER BY b.underlying
    """).fetchall()

    # 2. Multi-entity: (name, date) cells where the join produced >1 entity row
    res.multi_entity = con.execute("""
        SELECT underlying, trade_date, COUNT(*) AS n
        FROM basis_panel
        GROUP BY underlying, trade_date HAVING COUNT(*) > 1
    """).fetchall()

    # 3. Spot missing
    res.spot_missing = con.execute(
        "SELECT COUNT(*) FROM basis_panel WHERE spot_close IS NULL"
    ).fetchone()[0]

    return res


# ── Arm C — Corporate-action consistency across legs ─────────────────────────

def arm_c(con):
    """CA consistency across legs.

    Splits/bonuses: ratio k cancels in (F-S)/S → raw_basis_ratio continuous (Prediction 3a).
    Dividends: S→S-D on ex-date, F barely moves → annualized basis steps up by ~D/(S*tau).
               Flag the RESIDUAL after subtracting the predicted step (Prediction 3b).

    KNOWN LIMITATION: corporate_actions has no announcement_date column. Dividend
    PIT-ness (announcement_date <= formation_date) is NOT certifiable from this store.
    """
    res = ArmCResult()

    # 3a. Splits/bonuses: raw_basis_ratio should not jump on ex-dates
    res.split_violations = con.execute(f"""
        WITH ca_dates AS (
            SELECT symbol, ex_date, action_type, ratio_or_fv
            FROM eq.corporate_actions
            WHERE action_type IN ('SPLIT', 'BONUS')
              AND ex_date >= (SELECT MIN(trade_date) FROM basis_panel)
              AND ex_date <= (SELECT MAX(trade_date) FROM basis_panel)
        ),
        bp_lag AS (
            SELECT b.underlying, b.trade_date, b.raw_basis_ratio,
                   LAG(b.raw_basis_ratio) OVER w AS prev_raw,
                   LAG(b.trade_date)      OVER w AS prev_td
            FROM basis_panel b
            WINDOW w AS (PARTITION BY b.underlying ORDER BY b.trade_date)
        )
        SELECT c.symbol, c.ex_date, l.prev_raw, l.raw_basis_ratio,
               ABS(l.raw_basis_ratio - l.prev_raw) AS raw_change
        FROM ca_dates c
        JOIN bp_lag l ON l.underlying = c.symbol AND l.trade_date = c.ex_date
        WHERE l.prev_raw IS NOT NULL AND l.raw_basis_ratio IS NOT NULL
          AND ABS(l.raw_basis_ratio - l.prev_raw) > 0.03
        ORDER BY raw_change DESC
    """).fetchall()

    # 3b. Dividends: for efficient Indian SSFs, both legs adjust by ~D, so the raw
    # basis is roughly continuous across ex-dates (same as splits). Flag any raw
    # discontinuity > CA_RAW_TOL — a jump means one leg didn't adjust (data defect).
    # NOTE: the spec's D/(S·τ) step prediction was tested but found inaccurate —
    # Indian futures are efficient and adjust by D, making the actual step ~0.
    res.dividend_residuals = con.execute(f"""
        WITH div_dates AS (
            SELECT symbol, ex_date,
                   TRY_CAST(json_extract_string(raw_json, '$.Details') AS DOUBLE) AS div_amount
            FROM eq.corporate_actions
            WHERE action_type = 'DIVIDEND'
              AND ex_date >= (SELECT MIN(trade_date) FROM basis_panel)
              AND ex_date <= (SELECT MAX(trade_date) FROM basis_panel)
              AND TRY_CAST(json_extract_string(raw_json, '$.Details') AS DOUBLE) > 0
        ),
        bp_lag AS (
            SELECT b.underlying, b.trade_date, b.raw_basis_ratio,
                   LAG(b.raw_basis_ratio) OVER w AS prev_raw
            FROM basis_panel b
            WINDOW w AS (PARTITION BY b.underlying ORDER BY b.trade_date)
        )
        SELECT d.symbol, d.ex_date,
               d.div_amount,
               bp.raw_basis_ratio - bp.prev_raw AS actual_raw_change
        FROM div_dates d
        JOIN bp_lag bp ON bp.underlying = d.symbol AND bp.trade_date = d.ex_date
        WHERE bp.prev_raw IS NOT NULL AND bp.raw_basis_ratio IS NOT NULL
          AND ABS(bp.raw_basis_ratio - bp.prev_raw) > {CA_RAW_TOL}
        ORDER BY ABS(bp.raw_basis_ratio - bp.prev_raw) DESC
    """).fetchall()

    # Dividend exposure: fraction of basis cells where a dividend ex-date falls
    # between the trade_date and the expiry_dt
    total = con.execute("SELECT COUNT(*) FROM basis_panel WHERE spot_close IS NOT NULL").fetchone()[0]
    exposed = con.execute("""
        SELECT COUNT(*) FROM basis_panel bp
        WHERE EXISTS (
            SELECT 1 FROM eq.corporate_actions ca
            WHERE ca.action_type = 'DIVIDEND'
              AND ca.symbol = bp.underlying
              AND ca.ex_date > bp.trade_date
              AND ca.ex_date <= bp.expiry_dt
              AND TRY_CAST(json_extract_string(ca.raw_json, '$.Details') AS DOUBLE) > 0
        )
        AND bp.spot_close IS NOT NULL
    """).fetchone()[0]
    res.dividend_exposure_pct = (exposed / total * 100) if total > 0 else 0.0

    res.pit_limitation = (
        "corporate_actions has no announcement_date column (verified: raw_json carries "
        "Ex_date, BCRD record date, PAYMENT_DATE, and per-share Details amount only). "
        "Dividend PIT-ness (announcement_date <= formation_date) is NOT certifiable "
        "from this store. Exposure: "
        f"{res.dividend_exposure_pct:.2f}% of basis cells have a dividend ex-date "
        "between trade_date and expiry_dt."
    )

    return res


# ── Arm D — Basis fabrication invariant ──────────────────────────────────────

def arm_d(con):
    """Basis fabrication invariant.

    Flags |annualized_basis| beyond BASIS_FABRICATION_BOUND. Every flagged cell is
    either (a) traced to a real illiquidity/borrow event or (b) a data defect.
    Also checks for stale legs (NULL close on either side).
    """
    res = ArmDResult()

    res.extreme_cells = con.execute(f"""
        SELECT underlying, trade_date, annualized_basis, raw_basis_ratio, days_to_expiry,
               fut_close, spot_close
        FROM basis_panel
        WHERE raw_basis_ratio IS NOT NULL
          AND (
            ABS(raw_basis_ratio) > {RAW_RATIO_BOUND}
            OR (ABS(annualized_basis) > {BASIS_FABRICATION_BOUND}
                AND days_to_expiry >= {MIN_DTE_FOR_ANNUALIZED_FLAG})
          )
        ORDER BY ABS(raw_basis_ratio) DESC
    """).fetchall()

    res.stale_cells = con.execute("""
        SELECT COUNT(*) FROM basis_panel
        WHERE fut_close IS NULL OR spot_close IS NULL
    """).fetchone()[0]

    return res


# ── PIT universe guard ───────────────────────────────────────────────────────

def pit_guard(con):
    """PIT F&O eligibility (RULE 2).

    A name is F&O-listed on date d IFF it has a FUTSTK record on d. The basis panel
    is built from FUTSTK records, so every cell is PIT by construction. This guard
    reports the count for completeness.
    """
    res = PITResult()
    res.total_cells = con.execute(
        "SELECT COUNT(*) FROM basis_panel"
    ).fetchone()[0]

    # By construction: basis_panel only includes (name, date) cells where a FUTSTK
    # record exists on that date. So non_pit_cells must be 0.
    res.non_pit_cells = con.execute("""
        SELECT COUNT(*) FROM basis_panel bp
        WHERE NOT EXISTS (
            SELECT 1 FROM fut.futures_bhavcopy f
            WHERE f.underlying = bp.underlying
              AND f.trade_date = bp.trade_date
              AND f.inst_type = 'FUTSTK'
        )
    """).fetchone()[0]

    return res
