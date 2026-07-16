"""PSB-1 Prompt 5-C — the four-arm contract suite.

Replaces the bug-shaped certification invariants with a test of the ONE contract:

    The entity-grain adjusted series is continuous. Every consecutive-print return is
    explained by a documented factor of the matching ratio, or is a normal move; and
    adj_prev_close(t) == adj_close(t-1).

Four arms share one discipline — run over the finished substrate, entity grain, EQ+BE
union, rn=1 turnover-primary dedup, every entity / every handoff / every factor, ZERO
structural filters (no sample, no alag>0, no symbol-partition, no MAX_GAP_DAYS, no
merge-gate mount, no NOT IN symbol_changes, no f>=0.75 suspect cut). The ONLY permitted
exclusion is membership in a committed disposition register (applied by the caller, not
here — the arms enumerate ALL residue).

  Arm A  intra-symbol CA-shape.  For every intra-symbol move whose survived ratio is
         CA-shaped (open or close, gate-(b)'s is_ca_shaped), assert a documented factor
         of the matching ratio spans it. Shape-gating IS the definition of the question.
         Non-CA-shaped large moves are enumerated into large_genuine for disposition,
         never silently blessed. -> catches PHILIPCARB, the DTIL missing-factor side.

  Arm B  cross-symbol handoff, SHAPE-FREE.  For every multi-ticker entity, every
         consecutive-symbol handoff (rename-path and ISIN-merge alike, ANY gap), assert
         |adjusted return| < 20%. A continuously-graded entity has no normal 16,406%
         overnight. -> catches INDOSOLAR, the ISIN-merge splices, the DTIL/DVL splice.

  Arm C  prev_close identity.  adj_prev_close(t) == adj_close(t-1) at entity grain, NO
         alag>0 filter (that filter hid F-7). First sessions are checked separately:
         if the first session is an ex-date, prev_close must carry the factor.

  Arm D  factor evidence (the quadrant A-C do not cover).  Arms A-C trust the factor
         register; a factor that exists but corresponds to NO real reprice passes all
         three silently. Import gate-(b)'s fetch_evidence and the absolute-and-relative
         test (no_reprice / wrong_ratio), over the ENTIRE adjustment_factors register,
         unfiltered (not the Prompt-4 f>=0.75 x membership suspect cut). -> catches the
         DVL +40.2% spurious/mis-key class, AHLEAST wrong-ratio.

Governing analysis: PSB1_CERTIFICATION_METHODOLOGY.md (operator-endorsed 2026-07-15).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "csmp"))
sys.path.insert(0, str(ROOT / "scripts" / "psb1"))

from audit_corporate_actions import (  # noqa: E402  — frozen; imported, never edited
    CA_RATIOS, CA_RATIO_TOLERANCE, CA_RATIO_MIN_PRICE, EVIDENCE_TOLERANCE,
    fetch_evidence, is_ca_shaped,
)
from ingest_corporate_actions import NO_REPRICE_TOLERANCE  # noqa: E402  — frozen; constant only
from screening_harness import classify_move, RESIDUE  # noqa: E402

# Slightly wider than CA_RATIO_TOLERANCE / the large_genuine threshold so the SQL
# pre-filter is a guaranteed superset; classify_move / is_ca_shaped make the exact call.
_SHAPE_PREFILTER_TOL = CA_RATIO_TOLERANCE + 0.005      # 0.025
_LARGE_GENUINE_THRESHOLD = 0.30  # surfaces bonus-shaped moves (factor > 0.5, ret ~ -33%) that
                                  # CA_RATIOS (capped at 0.5) is structurally blind to — the
                                  # methodology mandates "never silently passed"
_LARGE_PREFILTER = _LARGE_GENUINE_THRESHOLD - 0.02
_SPLICE_BOUND = 0.20          # Arm B handoff bound (shape-free)
_CONTINUITY_TOL = 1e-6        # adj_prev_close == adj_close(t-1) tolerance (relative)


def _ca_ratios_sql():
    """SQL VALUES list of canonical CA ratios for an EXISTS membership test."""
    return "(VALUES " + ", ".join(f"({r})" for r in CA_RATIOS) + ")"


# ──────────────────────────────────────────────────────────────────────────────
# Shared CTE: entity-grain consecutive prints (rn=1 turnover-primary, EQ+BE union)
# ──────────────────────────────────────────────────────────────────────────────
_LAGGED_CTE = """
WITH eqbe AS (
    SELECT i.entity, a.symbol, a.series, a.trade_date, a.close, a.open, a.prev_close, a.turnover,
           ROW_NUMBER() OVER (PARTITION BY i.entity, a.trade_date
               ORDER BY a.turnover DESC NULLS LAST, a.symbol) rn
    FROM equity_bhavcopy_adjusted a
    JOIN symbol_entity_intervals i ON i.symbol = a.symbol
         AND a.trade_date >= i.valid_from AND a.trade_date < i.valid_to
    WHERE a.series IN ('EQ','BE')
),
dedup AS (
    SELECT entity, symbol, series, trade_date, close, open, prev_close FROM eqbe WHERE rn = 1
),
lagged AS (
    SELECT entity, symbol, series, trade_date, close, open, prev_close,
           LAG(symbol)     OVER w AS prev_sym,
           LAG(trade_date) OVER w AS prev_td,
           LAG(close)      OVER w AS prev_close_lag
    FROM dedup
    WINDOW w AS (PARTITION BY entity ORDER BY trade_date)
)
SELECT entity, symbol, series, trade_date, close, open, prev_close,
       prev_sym, prev_td, prev_close_lag
FROM lagged
"""


@dataclass
class ArmAResult:
    violations: list = field(default_factory=list)      # RESIDUE: (entity, symbol, move_date, ret, cls)
    large_genuine: list = field(default_factory=list)   # (entity, symbol, move_date, ret, survived)


@dataclass
class ArmBResult:
    splices: list = field(default_factory=list)         # (entity, prev_sym, sym, handoff_date, ret, prev_close, close)


@dataclass
class ArmCResult:
    violations: list = field(default_factory=list)      # (entity, symbol, move_date, adj_prev_close, adj_close_prev, kind)


@dataclass
class ArmDResult:
    n_tested: int = 0
    violations: list = field(default_factory=list)      # (symbol, ex_date, factor, implied_open, implied_close, failure_type, deviation)


# ──────────────────────────────────────────────────────────────────────────────
# Arm A — intra-symbol CA-shape
# ──────────────────────────────────────────────────────────────────────────────
def arm_a(con, factors_by_entity):
    """Every intra-symbol CA-shaped move needs a documented matching factor.

    No MAX_GAP_DAYS, no -20%/+25% screen: the CA-shape test IS the definition of the
    question (is_ca_shaped rejects tiny moves — 1+ret must sit on a canonical ratio).
    classify_move (gate-(b)'s classifier, F-10 open+close) makes the exact call; the SQL
    pre-filter only narrows for performance. Non-CA-shaped moves with |ret| >= 0.40 are
    enumerated into large_genuine, never silently blessed as "genuine by convention."
    """
    ratios = _ca_ratios_sql()
    tol = _SHAPE_PREFILTER_TOL
    minpx = CA_RATIO_MIN_PRICE
    rows = con.execute(f"""
        {_LAGGED_CTE}
        WHERE prev_sym IS NOT NULL
          AND prev_sym = symbol
          AND prev_close_lag > 0
          AND (
            (prev_close_lag >= {minpx} AND (
               EXISTS (SELECT 1 FROM {ratios} AS t(r)
                        WHERE ABS(close / prev_close_lag - t.r) / t.r <= {tol})
               OR (open IS NOT NULL AND open > 0 AND
                   EXISTS (SELECT 1 FROM {ratios} AS t(r)
                            WHERE ABS(open / prev_close_lag - t.r) / t.r <= {tol}))))
            OR ABS(close / prev_close_lag - 1.0) >= {_LARGE_PREFILTER}
          )
    """).fetchall()

    res = ArmAResult()
    for ent, sym, _ser, td, close, opn, _pc, prev_sym, prev_td, prev_close in rows:
        if prev_close is None or prev_close <= 0 or prev_td is None:
            continue
        ret = close / prev_close - 1.0
        facs = factors_by_entity.get(ent, [])
        cls = classify_move(ret, prev_close, prev_td, td, facs, open_price=opn)
        if cls in RESIDUE:
            res.violations.append((ent, sym, td, ret, cls))
        elif cls == "genuine" and abs(ret) >= _LARGE_GENUINE_THRESHOLD:
            res.large_genuine.append((ent, sym, td, ret, 1.0 + ret))
    return res


# ──────────────────────────────────────────────────────────────────────────────
# Arm B — cross-symbol handoff (shape-free)
# ──────────────────────────────────────────────────────────────────────────────
def arm_b(con):
    """Every multi-ticker entity's adjusted return across each symbol handoff < |20%|.

    Shape-free is load-bearing: a continuously-graded entity has no "normal" 16,406%
    overnight, so a handoff jump is always a capital event or a fabrication regardless
    of ratio. Any gap (no MAX_GAP_DAYS). Rename-path and ISIN-merge alike.
    """
    rows = con.execute(f"""
        {_LAGGED_CTE}
        WHERE prev_sym IS NOT NULL
          AND prev_sym <> symbol
          AND prev_close_lag > 0
          AND ABS(close / prev_close_lag - 1.0) >= {_SPLICE_BOUND}
        ORDER BY ABS(close / prev_close_lag - 1.0) DESC
    """).fetchall()
    res = ArmBResult()
    for ent, sym, _ser, td, close, _opn, _pc, prev_sym, prev_td, prev_close in rows:
        ret = close / prev_close - 1.0
        res.splices.append((ent, prev_sym, sym, td, ret, prev_close, close))
    return res


# ──────────────────────────────────────────────────────────────────────────────
# Arm C — prev_close identity (no alag>0 filter)
# ──────────────────────────────────────────────────────────────────────────────
def arm_c(con, factors_by_entity):
    """adj_prev_close(t) == adj_close(t-1) at entity grain, over ALL sessions.

    The old WHERE alag > 0 filter structurally excluded every first session — exactly
    what hid F-7 (LITL). Two complementary predicates:

      (1) consecutive sessions: the adjustment ratio for prev_close must equal the
          adjustment ratio for close(t-1). I.e. adj_prev_close(t)/adj_close(t-1) ==
          raw_prev_close(t)/raw_close(t-1). The cum factor must be the same for both;
          if the view's LAG reaches across a series seam or a co-trading entity to a
          different cum (the Prompt 3-B / DVL +50% defects), this ratio diverges. It
          is 0 on a correct view, but is NOT structurally unfalsifiable — a
          series-partitioned LAG makes it fail. NO alag>0 filter: every session with a
          previous is tested.

      (2) first session that is an ex-date: prev_close must carry the factor (the F-7
          case — the view's COALESCE fallback substituting cum(t) instead of
          cum(t)*factor(ex on t)). A first session has no t-1, so (1) cannot reach it;
          (2) checks it independently. Expected = raw_prev_close x cum_all (product of
          ALL entity price factors) — which is what the fallback computes when it
          correctly includes the factor on t.
    """
    # (1) ratio-identity over ALL consecutive sessions (no alag>0 filter)
    rows = con.execute(f"""
        WITH eqbe AS (
            SELECT i.entity, a.symbol, a.trade_date, a.prev_close adj_pc, a.close adj_close,
                   ROW_NUMBER() OVER (PARTITION BY i.entity, a.trade_date
                       ORDER BY a.turnover DESC NULLS LAST, a.symbol) rn
            FROM equity_bhavcopy_adjusted a
            JOIN symbol_entity_intervals i ON i.symbol = a.symbol
                 AND a.trade_date >= i.valid_from AND a.trade_date < i.valid_to
            WHERE a.series IN ('EQ','BE')
        ),
        adj_dedup AS (SELECT entity, symbol, trade_date, adj_pc, adj_close FROM eqbe WHERE rn=1),
        eqbe_raw AS (
            SELECT i.entity, r.trade_date, r.prev_close raw_pc, r.close raw_close,
                   ROW_NUMBER() OVER (PARTITION BY i.entity, r.trade_date
                       ORDER BY r.turnover DESC NULLS LAST, r.symbol) rn
            FROM equity_bhavcopy r
            JOIN symbol_entity_intervals i ON i.symbol = r.symbol
                 AND r.trade_date >= i.valid_from AND r.trade_date < i.valid_to
            WHERE r.series IN ('EQ','BE')
        ),
        raw_dedup AS (SELECT entity, trade_date, raw_pc, raw_close FROM eqbe_raw WHERE rn=1),
        combined AS (
            SELECT a.entity, a.symbol, a.trade_date, a.adj_pc,
                   LAG(a.adj_close) OVER w AS adj_close_prev,
                   rw.raw_pc, LAG(rw.raw_close) OVER w AS raw_close_prev
            FROM adj_dedup a
            JOIN raw_dedup rw ON rw.entity = a.entity AND rw.trade_date = a.trade_date
            WINDOW w AS (PARTITION BY a.entity ORDER BY a.trade_date)
        )
        SELECT entity, symbol, trade_date, adj_pc, adj_close_prev, raw_pc, raw_close_prev
        FROM combined
        WHERE adj_close_prev > 0 AND raw_close_prev > 0 AND raw_pc > 0
          AND ABS(adj_pc / adj_close_prev - raw_pc / raw_close_prev) > {_CONTINUITY_TOL}
    """).fetchall()
    res = ArmCResult()
    for ent, sym, td, adj_pc, adj_cp, raw_pc, raw_cp in rows:
        res.violations.append((ent, sym, td, adj_pc, adj_cp, "ratio_identity"))

    # (2) first-session ex-date: cum_all per entity = product of ALL compounded factors
    cum_all = {}
    for ent, facs in factors_by_entity.items():
        c = 1.0
        for _exd, f in facs:
            c *= f
        if c != 1.0:
            cum_all[ent] = c
    fs_rows = con.execute("""
        WITH fs AS (
            SELECT i.entity, MIN(a.trade_date) first_td
            FROM equity_bhavcopy_adjusted a
            JOIN symbol_entity_intervals i ON i.symbol = a.symbol
                 AND a.trade_date >= i.valid_from AND a.trade_date < i.valid_to
            WHERE a.series IN ('EQ','BE')
            GROUP BY i.entity
        ),
        ca_t AS (
            SELECT i.entity,
                   COALESCE(EXP(SUM(LN(af.factor)) FILTER (
                       WHERE af.action_type IN ('BONUS','SPLIT','SPECIAL_DIVIDEND'))), 1.0) AS cum_all_v
            FROM adjustment_factors af
            JOIN symbol_entity_intervals i ON i.symbol = af.symbol
                 AND af.ex_date >= i.valid_from AND af.ex_date < i.valid_to
            GROUP BY i.entity
        ),
        fac_on_fs AS (
            SELECT i.entity, af.ex_date, af.factor
            FROM adjustment_factors af
            JOIN symbol_entity_intervals i ON i.symbol = af.symbol
                 AND af.ex_date >= i.valid_from AND af.ex_date < i.valid_to
            WHERE af.action_type IN ('BONUS','SPLIT','SPECIAL_DIVIDEND')
        )
        SELECT fs.entity, fs.first_td, ca.cum_all_v
        FROM fs
        JOIN ca_t ca ON ca.entity = fs.entity AND ca.cum_all_v <> 1.0
        JOIN fac_on_fs f ON f.entity = fs.entity AND f.ex_date = fs.first_td AND f.factor <> 1.0
    """).fetchall()
    for ent, first_td, cum_all_val in fs_rows:
        adj = con.execute("""
            SELECT a.prev_close, a.symbol FROM equity_bhavcopy_adjusted a
            JOIN symbol_entity_intervals i ON i.symbol=a.symbol
                 AND a.trade_date>=i.valid_from AND a.trade_date<i.valid_to
            WHERE i.entity=? AND a.trade_date=? AND a.series IN ('EQ','BE')
            ORDER BY a.turnover DESC NULLS LAST, a.symbol LIMIT 1
        """, [ent, first_td]).fetchone()
        raw = con.execute("""
            SELECT r.prev_close FROM equity_bhavcopy r
            JOIN symbol_entity_intervals i ON i.symbol=r.symbol
                 AND r.trade_date>=i.valid_from AND r.trade_date<i.valid_to
            WHERE i.entity=? AND r.trade_date=? AND r.series IN ('EQ','BE')
            ORDER BY r.turnover DESC NULLS LAST, r.symbol LIMIT 1
        """, [ent, first_td]).fetchone()
        if not adj or not raw or not raw[0] or raw[0] <= 0:
            continue
        expected = raw[0] * cum_all_val
        if expected > 0 and abs(adj[0] - expected) / expected > _CONTINUITY_TOL:
            res.violations.append((ent, adj[1], first_td, adj[0], expected, "first_session_exdate"))
    return res


# ──────────────────────────────────────────────────────────────────────────────
# Arm D — factor evidence over the entire register (unfiltered)
# ──────────────────────────────────────────────────────────────────────────────
def arm_d(con):
    """Every recorded factor must correspond to a real reprice.

    Arms A-C trust the factor register; a spurious factor (DVL +40.2%: factor 0.6667 but
    the stock never repriced) passes all three. Import gate-(b)'s frozen fetch_evidence
    (implied_open = open(ex)/close(ex-1)) and reuse the absolute-AND-relative test:
      no_reprice:  implied_open closer to 1.0 than to f (the CA never happened)
      wrong_ratio: min|f - implied|/implied > EVIDENCE_TOLERANCE (the ratio is wrong)
    Over the ENTIRE adjustment_factors register, unfiltered (not the Prompt-4 f>=0.75 x
    membership suspect cut).
    """
    evidence = fetch_evidence(con)
    res = ArmDResult(n_tested=len(evidence))
    for sym, ex, legs, f, imp_open, imp_close in evidence:
        devs = [abs(f - i) / i for i in (imp_open, imp_close) if i is not None and i > 0]
        if not devs:
            continue
        dev = min(devs)
        no_reprice = (imp_open is not None and imp_open > 0
                      and abs(imp_open - 1.0) < abs(imp_open - f)
                      and abs(imp_open - 1.0) <= NO_REPRICE_TOLERANCE
                      and abs(f - 1.0) > NO_REPRICE_TOLERANCE)
        relative = dev > EVIDENCE_TOLERANCE
        if not (relative or no_reprice):
            continue
        ftype = ("no_reprice" if no_reprice and not relative
                 else "wrong_ratio" if relative and not no_reprice
                 else "no_reprice+wrong_ratio")
        res.violations.append((sym, ex, f, imp_open, imp_close, ftype, dev))
    res.violations.sort(key=lambda r: (r[0], r[1]))
    return res
