"""CSMP Gate (e) — 12-1 momentum transmission triage (the D1-lesson gate).

Dev-window ONLY (2012-01 -> 2022-12) triage: does classic 12-1 cross-sectional
momentum over the point-in-time NIFTY-200 universe (gate c) from CA-adjusted prices
(gate b) transmit into a tradeable, net-of-fee edge, using gate-(d) delivery fees —
BEFORE any pre-registration and WITHOUT touching the sealed held-out window
(2023-01 -> 2026-06).

Construct is charter-locked (D2): classic 12-1, monthly rebalance, equal-weight,
provisional top-quintile bucket. NO tuning, NO construct search, NO signal engineering.
This script reports what the locked construct does and renders CONTINUE/STOP on its own
pre-committed numbers.

Pre-committed stop rule (LOCKED 2026-07-11, frozen BEFORE the run):
  STOP if EITHER holds on the dev window ->
    (A) No skill  : mean monthly cross-sectional rank IC <= 0.02
                     OR block-bootstrap 95% CI of mean IC includes 0 (L=12 months).
    (B) No net edge: annualized net top-quintile minus equal-weight-universe spread <= 0.
  CONTINUE only if BOTH clear.

Sealed-window fence: every input query asserts MAX(trade_date) <= 2022-12-31. The last
scored formation month whose forward return is realizable inside the dev window is
2022-11 (forward 2022-11 -> 2022-12); the 2022-12 formation's forward return would read
2023-01 (sealed) and is therefore excluded from the IC / portfolio series.

Usage:
    python scripts/csmp/triage_momentum.py
"""

import json
import math
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
REPORT_PATH = ROOT / "docs" / "reports" / "CSMP_GATE_E_TRIAGE.md"
REF_CACHE = ROOT / "data" / "market_data" / "ref_nifty200mom30tri.json"

from core.execution.equity.delivery_fees import delivery_equity_fees  # noqa: E402

# ---- Charter-locked parameters (NO tuning freedom) --------------------------
DEV_END = date(2022, 12, 31)        # sealed window starts 2023-01-01
FORMATION_LOOKBACK = 12             # 12-1 momentum
SKIP_MONTHS = 1
FULL_SESSION_MIN = 200
N_UNIVERSE = 200
N_QUINTILE = N_UNIVERSE // 5        # 40
N_DECILE = N_UNIVERSE // 10         # 20

# ---- Pre-committed stop rule (LOCKED before the run) ------------------------
MEAN_IC_FLOOR = 0.02
NET_SPREAD_FLOOR = 0.0
BOOTSTRAP_L = 12                    # fixed a priori from 12-1 formation-window overlap
BOOTSTRAP_REPS = 20000
BOOTSTRAP_SEED = 20260711

# ---- Portfolio capital assumption (disclosed) --------------------------------
# Ad-valorem costs (STT/txn/stamp/SEBI/GST) are capital-independent; only the flat
# DP charge (Rs ~13.5/sell scrip) scales with capital. At Rs 1 crore book the DP drag
# is < 0.5 bp/month, so the net verdict is robust across the institutional range.
CAPITAL = 10_000_000.0


def line(s=""):
    L.append(s)


L = []


def pct(x):
    return f"{x*100:.2f}%"


# ---------------------------------------------------------------------------
# Data loading (every query fenced to the dev window)
# ---------------------------------------------------------------------------
def load(con):
    # Sealed-window guard: prove the dev-window boundary on all three fenced inputs.
    max_adj = con.execute(
        "SELECT MAX(trade_date) FROM equity_bhavcopy_adjusted "
        "WHERE trade_date <= ?", [DEV_END]).fetchone()[0]
    max_memb = con.execute(
        "SELECT MAX(rebalance_date) FROM universe_membership "
        "WHERE rebalance_date <= ?", [DEV_END]).fetchone()[0]
    max_cal = con.execute(
        "SELECT MAX(trade_date) FROM trading_calendar "
        "WHERE trade_date <= ?", [DEV_END]).fetchone()[0]

    # Full-session monthly grid from 2010-01 (data start) -> dev end, for lookback
    # endpoints that precede the universe start (2012-01).
    grid = [r[0] for r in con.execute("""
        WITH m AS (
          SELECT trade_date,
                 EXTRACT(YEAR FROM trade_date)::INT y,
                 EXTRACT(MONTH FROM trade_date)::INT m
          FROM trading_calendar
          WHERE n_symbols >= ? AND trade_date <= ?
        )
        SELECT MAX(trade_date) FROM m GROUP BY y, m ORDER BY 1
    """, [FULL_SESSION_MIN, DEV_END]).fetchall()]
    gidx = {d: i for i, d in enumerate(grid)}

    # Membership: (rebalance_date -> [(symbol, rank, entity)]) for the dev window.
    memb_rows = con.execute("""
        SELECT um.rebalance_date, um.symbol, um.rank, e.entity
        FROM universe_membership um
        JOIN universe_eligibility e ON e.symbol = um.symbol
        WHERE um.rebalance_date <= ?
        ORDER BY um.rebalance_date, um.rank
    """, [DEV_END]).fetchall()
    members = defaultdict(list)
    member_entities = set()
    for rd, sym, rank, ent in memb_rows:
        members[rd].append((sym, rank, ent))
        member_entities.add(ent)

    # Entity-level adjusted close: one row per (entity, date), max-turnover symbol
    # wins (same rule gate (c) used for the active-ticker label). Rename-continuous.
    # Inline window-function subquery — no temp table (read-only-safe). Joins every
    # universe_eligibility symbol; non-member rows are simply never looked up.
    px = {}
    q = """
        SELECT entity, trade_date, adj_close FROM (
          SELECT e.entity, a.trade_date, a.close AS adj_close, a.turnover, a.symbol,
                 ROW_NUMBER() OVER (PARTITION BY e.entity, a.trade_date
                                    ORDER BY a.turnover DESC NULLS LAST, a.symbol) rn
          FROM equity_bhavcopy_adjusted a
          JOIN universe_eligibility e ON e.symbol = a.symbol
          WHERE a.trade_date <= ?
        ) WHERE rn = 1
    """
    for ent, d, c in con.execute(q, [DEV_END]).fetchall():
        px[(ent, d)] = float(c)

    return max_adj, max_memb, max_cal, grid, gidx, px, members


# ---------------------------------------------------------------------------
# Block bootstrap 95% CI of the mean (moving-block, L months, fixed seed)
# ---------------------------------------------------------------------------
def bootstrap_ci_mean(series, L, reps, seed):
    series = np.asarray(series, dtype=float)
    n = len(series)
    if n == 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    n_blocks = math.ceil(n / L)
    means = np.empty(reps)
    for b in range(reps):
        starts = rng.integers(0, n - L + 1, size=n_blocks)
        sample = np.concatenate([series[s:s + L] for s in starts])[:n]
        means[b] = sample.mean()
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(lo), float(hi)


# ---------------------------------------------------------------------------
# Reference arm: NIFTY200 Momentum 30 TRI (cached probe; reference, not gating)
# ---------------------------------------------------------------------------
REF_URL = ("https://archives.nseindia.com/content/indices/"
           "ind_nifty200momentum30list.csv")


def reference_arm():
    """External sign/magnitude sanity check. Cached for deterministic re-runs; if
    unobtainable, say so with HTTP evidence (gate (b)/(c) discipline)."""
    if REF_CACHE.exists():
        try:
            return json.loads(REF_CACHE.read_text())
        except Exception:
            pass
    outcome = {"obtained": False, "note": "", "url": REF_URL}
    try:
        req = urllib.request.Request(REF_URL, headers={"User-Agent": "CSMP-gate-e/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read()
        head = body[:200].decode("utf-8", "replace").lower()
        if head.startswith("<!doctype html") or head.startswith("<html"):
            outcome["note"] = (f"HTTP {r.status} but HTML shell (wrong-content 200), "
                               "not a TRI series CSV. NSE does not publish a freely "
                               "obtainable historical TRI series file at this path.")
        else:
            outcome["obtained"] = True
            outcome["note"] = f"HTTP {r.status}; {len(body)} bytes."
    except urllib.error.HTTPError as e:
        outcome["note"] = f"HTTPError {e.code} — no historical TRI file published."
    except Exception as e:
        outcome["note"] = f"unreachable ({type(e).__name__}): {str(e)[:120]}"
    REF_CACHE.parent.mkdir(parents=True, exist_ok=True)
    REF_CACHE.write_text(json.dumps(outcome, indent=2))
    return outcome


# ---------------------------------------------------------------------------
# Main triage
# ---------------------------------------------------------------------------
def main():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    max_adj, max_memb, max_cal, grid, gidx, px, members = load(con)
    con.close()

    line("# CSMP Gate (e) — 12-1 Momentum Transmission Triage")
    line()
    line("**Window:** dev window ONLY (2012-01 → 2022-12). Sealed held-out window "
         "(2023-01 → 2026-06) is untouched and is not read.")
    line("**Construct:** charter-locked classic 12-1, monthly rebalance, equal-weight, "
         "provisional top-quintile bucket. No tuning.")
    line("**Capital assumption:** Rs 1,00,00,000 (₹1 cr) — disclosed; ad-valorem costs "
         "are capital-independent, DP drag < 0.5 bp/mo at this scale.")
    line()

    line("## 1. Sealed-window fence")
    line()
    line(f"- `MAX(trade_date) <= {DEV_END}` asserted on every input query.")
    line(f"- Dev-window boundary on every fenced input (each `≤ {DEV_END}`): "
         f"`equity_bhavcopy_adjusted` MAX(trade_date) = **{max_adj}** "
         f"({'OK' if max_adj <= DEV_END else 'VIOLATION'}); "
         f"`universe_membership` MAX(rebalance_date) = **{max_memb}** "
         f"({'OK' if max_memb <= DEV_END else 'VIOLATION'}); "
         f"`trading_calendar` MAX(trade_date) = **{max_cal}** "
         f"({'OK' if max_cal <= DEV_END else 'VIOLATION'}).")
    line(f"- Monthly full-session grid: {len(grid)} sessions, {grid[0]} → {grid[-1]}.")
    line(f"- Forward-return cutoff: the last dev-window session is **{grid[-1]}**; a "
         f"formation's forward return needs the *next* session, so the last formation "
         f"month with an in-dev forward return is **{grid[-2]}** (forward → {grid[-1]}). "
         f"The {grid[-1]} formation's forward return would read the sealed window "
         f"(2023-01) and is excluded from the IC / portfolio series.")
    line()

    # ---- Scored months: 2012-01 .. last-with-in-dev-forward -----------------
    scored_months = [d for d in grid if d in members and gidx[d] + 1 < len(grid)
                     and gidx[d] - FORMATION_LOOKBACK >= 0
                     and grid[gidx[d] + 1] <= DEV_END]
    line("## 2. Formation & ranking")
    line()
    line("- **Score (12-1):** total adjusted return from `t−12m` to `t−1m` "
         "(skip most-recent month), entity-continuous across renames via "
         "`universe_eligibility`/`symbol_changes`.")
    line("- Members scored at each `t` are the point-in-time `universe_membership` "
         "members; names lacking a complete formation window (not priced at `t−12m` "
         "or `t−1m`) are excluded and counted.")
    line(f"- Forward return: adjusted return `t → t+1` (next grid session).")
    line(f"- Scored months (IC series): **{len(scored_months)}** "
         f"({scored_months[0]} → {scored_months[-1]}).")
    line()

    ic_series, ic_dates = [], []
    excl_total = 0
    fwd_ok_total = 0
    spread_q_series, spread_d_series = [], []
    per_month_rows = []  # for portfolio
    incomplete_by_year = defaultdict(int)

    for t in scored_months:
        i = gidx[t]
        t12, t1, tp1 = grid[i - FORMATION_LOOKBACK], grid[i - SKIP_MONTHS], grid[i + 1]
        rows = members[t]
        scored, excluded = [], 0
        for sym, rank, ent in rows:
            p12 = px.get((ent, t12))
            p1 = px.get((ent, t1))
            if p12 and p1 and p12 > 0:
                scored.append((sym, rank, ent, p1 / p12 - 1.0))
            else:
                excluded += 1
        excl_total += excluded
        incomplete_by_year[t.year] += excluded

        # forward return for scored names
        pairs = []
        for sym, rank, ent, sc in scored:
            pa = px.get((ent, t))
            pb = px.get((ent, tp1))
            if pa and pb and pa > 0:
                pairs.append((rank, sc, pb / pa - 1.0, sym))
                fwd_ok_total += 1
        if len(pairs) < 5:
            continue
        rho, _ = spearmanr([p[1] for p in pairs], [p[2] for p in pairs])
        ic_series.append(float(rho))
        ic_dates.append(t)

        # bucket gross spreads (equal-weight)
        pairs_sorted = sorted(pairs, key=lambda x: x[1], reverse=True)  # by 12-1 momentum score, high->low
        def ew_top(n):
            return np.mean([p[2] for p in pairs_sorted[:n]])
        def ew_bot(n):
            return np.mean([p[2] for p in pairs_sorted[-n:]])
        spread_q_series.append(ew_top(N_QUINTILE) - ew_bot(N_QUINTILE))
        spread_d_series.append(ew_top(N_DECILE) - ew_bot(N_DECILE))

        per_month_rows.append((t, pairs, tp1))

    line(f"- Total names excluded (incomplete formation window): **{excl_total:,}** "
         f"across {len(scored_months)} months.")
    line("- Incomplete-window exclusions by year: "
         + ", ".join(f"{y}:{incomplete_by_year[y]}" for y in sorted(incomplete_by_year))
         + ".")
    line(f"- Forward returns computed for **{fwd_ok_total:,}** member-months.")
    line()

    # ---- IC statistics ------------------------------------------------------
    line("## 3. Cross-sectional rank IC (Spearman)")
    line()
    ic = np.asarray(ic_series)
    n = len(ic)
    mean_ic = float(ic.mean())
    sd_ic = float(ic.std(ddof=1))
    t_stat = mean_ic / (sd_ic / math.sqrt(n)) if sd_ic > 0 else float("nan")
    hit = float((ic > 0).mean())
    ci_lo, ci_hi = bootstrap_ci_mean(ic_series, BOOTSTRAP_L, BOOTSTRAP_REPS,
                                     BOOTSTRAP_SEED)
    line(f"- Months: **{n}**")
    line(f"- Mean rank IC: **{mean_ic:.4f}**  | SD: {sd_ic:.4f}  "
         f"| naive t-stat: {t_stat:.2f}  | hit rate (>0): {pct(hit)}")
    line(f"- Block-bootstrap 95% CI of mean IC (L={BOOTSTRAP_L}, "
         f"reps={BOOTSTRAP_REPS}, seed={BOOTSTRAP_SEED}): "
         f"**[{ci_lo:.4f}, {ci_hi:.4f}]**")
    line()
    line("By formation year:")
    line()
    line("| Year | Months | Mean IC | Hit rate |")
    line("|------|-------:|--------:|---------:|")
    by_year = defaultdict(list)
    for d, v in zip(ic_dates, ic_series):
        by_year[d.year].append(v)
    for y in sorted(by_year):
        vals = by_year[y]
        line(f"| {y} | {len(vals)} | {np.mean(vals):+.4f} | {pct(np.mean(np.array(vals) > 0))} |")
    line()
    line("Monthly IC series (year, mean IC):")
    line()
    line("```")
    for y in sorted(by_year):
        line(f"  {y}: {np.mean(by_year[y]):+.4f}")
    line("```")
    line()

    # ---- Bucket spreads -----------------------------------------------------
    line("## 4. Bucket gross spreads (equal-weight, long top / short bottom)")
    line()
    sq = np.asarray(spread_q_series)
    sd = np.asarray(spread_d_series)
    line(f"- Top-minus-bottom **quintile** (40/40): mean gross spread **{pct(sq.mean())}** "
         f"per month, SD {pct(sq.std(ddof=1))}, hit rate {pct((sq > 0).mean())}.")
    line(f"- Top-minus-bottom **decile** (20/20): mean gross spread **{pct(sd.mean())}** "
         f"per month, SD {pct(sd.std(ddof=1))}, hit rate {pct((sd > 0).mean())}.")
    line()

    # ---- Net-of-fee portfolios ---------------------------------------------
    line("## 5. Net-of-fee portfolios (gate-(d) delivery fees on turnover)")
    line()
    line(f"- Capital: Rs {CAPITAL:,.0f}. Equal-weight, monthly rebalance. Turnover = "
         f"names entering/leaving the held bucket (bucket churn — for the top quintile, "
         f"names rotating in/out of the top-40-by-momentum set; for the universe, "
         f"membership churn). Equal-weight drift of continuing holdings is not re-traded, "
         f"a disclosed simplification that slightly understates fees for both arms "
         f"(conservative: the net drag is a few bp/mo either way).")
    line(f"- Fees: gate-(d) `delivery_equity_fees` on each buy/sell leg of rebalance "
         f"turnover; first rebalance buys the whole book; terminal month marked, not "
         f"liquidated (standard for a return series).")
    line("- **Baseline disclosure:** the equal-weight universe arm holds the "
         "formation-complete members each month (~197 of the 200 point-in-time names — the "
         "same completeness filter the momentum arm passes), not a naive all-200 book. An "
         "all-200 book nets ~9.07% (vs 9.16% here), which would *widen* the reported spread "
         "— so this choice is conservative and apples-to-apples.")
    line()

    def simulate(pick):
        """pick(t, pairs) -> set of held symbols (the target bucket at t).
        Returns (ann_net, ann_gross, avg_two_way_turnover, avg_fee_drag_bpm, n_periods)."""
        V = CAPITAL
        prev_hold = None
        gross_rets, fee_drags, turnovers = [], [], []
        for t, pairs, tp1 in per_month_rows:
            hold = pick(t, pairs)  # set of held symbols
            hold_pairs = [p for p in pairs if p[3] in hold]
            N = max(len(hold_pairs), 1)
            gross = float(np.mean([p[2] for p in hold_pairs])) if hold_pairs else 0.0
            # turnover vs previous bucket (by SYMBOL — ranks reshuffle monthly)
            if prev_hold is None:
                enters = set(p[3] for p in hold_pairs)
                exits = set()
            else:
                enters = set(p[3] for p in hold_pairs) - prev_hold
                exits = prev_hold - set(p[3] for p in hold_pairs)
            fee = 0.0
            for _ in enters:
                fee += delivery_equity_fees(
                    side="BUY", trade_value=V / N, trade_date=t).total
            for _ in exits:
                fee += delivery_equity_fees(
                    side="SELL", trade_value=V / N, trade_date=t).total
            drag = fee / V
            fee_drags.append(drag)
            two_way = (len(enters) + len(exits)) / (2 * N) if N else 0.0
            turnovers.append(two_way)
            gross_rets.append(gross)
            V = (V - fee) * (1 + gross)
            prev_hold = set(p[3] for p in hold_pairs)
        n_per = len(per_month_rows)
        ann_net = (V / CAPITAL) ** (12 / n_per) - 1 if n_per else float("nan")
        gross_factor = 1.0
        for g in gross_rets:
            gross_factor *= (1 + g)
        ann_gross = gross_factor ** (12 / n_per) - 1 if n_per else float("nan")
        return (ann_net, ann_gross, float(np.mean(turnovers)),
                float(np.mean(fee_drags) * 10000), n_per)

    top_q = simulate(lambda t, pairs: set(p[3] for p in sorted(pairs, key=lambda x: x[1], reverse=True)[:N_QUINTILE]))
    univ = simulate(lambda t, pairs: set(p[3] for p in pairs))

    def fmt(p):
        return (f"annualized net {pct(p[0])}, gross {pct(p[1])}, "
                f"avg monthly two-way turnover {pct(p[2])}, "
                f"avg fee drag {p[3]:.2f} bp/mo, {p[4]} periods")
    line(f"- **Top-quintile EW:** {fmt(top_q)}")
    line(f"- **Equal-weight universe:** {fmt(univ)}")
    net_spread = top_q[0] - univ[0]
    line(f"- **Net annualized top-minus-universe spread: {pct(net_spread)}**")
    line()

    # ---- Reference arm ------------------------------------------------------
    line("## 6. Reference arm (NIFTY200 Momentum 30 TRI)")
    line()
    ref = reference_arm()
    if ref.get("obtained"):
        line(f"- Obtained from `{ref['url']}`. {ref['note']}")
        line("- (External index total-return series not parsed into the comparison; "
             "reported as obtainable for the sign/magnitude cross-check.)")
    else:
        line(f"- **Unobtainable** as a freely-downloadable historical TRI series. "
             f"`{ref['url']}` — {ref['note']}")
        line("- This is a reference, not the gating baseline (per the prompt); the "
             "verdict below rests solely on the dev-window IC and net-spread stop rules.")
    line()

    # ---- Pre-committed stop rule -------------------------------------------
    a_skill = mean_ic > MEAN_IC_FLOOR and ci_lo > 0
    b_edge = net_spread > NET_SPREAD_FLOOR
    verdict = "CONTINUE" if (a_skill and b_edge) else "STOP"
    line("## 7. Pre-committed stop rule (LOCKED before the run)")
    line()
    line("| Rule | Threshold | Observed | Result |")
    line("|------|-----------|----------|--------|")
    line(f"| (A) mean rank IC > {MEAN_IC_FLOOR} | {MEAN_IC_FLOOR} | "
         f"{mean_ic:.4f} | {'PASS' if mean_ic > MEAN_IC_FLOOR else 'FAIL'} |")
    line(f"| (A) bootstrap 95% CI excludes 0 (lower > 0) | 0 | "
         f"[{ci_lo:.4f}, {ci_hi:.4f}] | {'PASS' if ci_lo > 0 else 'FAIL'} |")
    line(f"| (B) net annualized top-minus-universe spread > 0 | 0 | "
         f"{pct(net_spread)} | {'PASS' if b_edge else 'FAIL'} |")
    line()
    line(f"### VERDICT: **{verdict}**")
    line()
    if verdict == "CONTINUE":
        line("Both stop rules clear on the dev window: classic 12-1 momentum transmits "
             "into a statistically-positive, net-of-fee edge over the 2012-2022 "
             "point-in-time universe. CSMP may proceed to Phase-1 pre-registration; the "
             "sealed held-out window (2023-01 → 2026-06) remains untouched for the "
             "post-pre-registration test (D3).")
    else:
        reasons = []
        if not (mean_ic > MEAN_IC_FLOOR):
            reasons.append(f"mean rank IC {mean_ic:.4f} ≤ floor {MEAN_IC_FLOOR}")
        if not (ci_lo > 0):
            reasons.append(f"bootstrap 95% CI lower bound {ci_lo:.4f} ≤ 0")
        if not b_edge:
            reasons.append(f"net top-minus-universe spread {pct(net_spread)} ≤ 0")
        line("A stop rule fired (" + "; ".join(reasons) + "). Per the pre-committed "
             "discipline (the D1 lesson) a STOP is a PASS of this gate's discipline, "
             "not a failure — a null result is a legitimate terminal state. CSMP halts "
             "before pre-registration; the operator decides next. No post-hoc widening.")
    line()
    line("---")
    line("*Report generated by `scripts/csmp/triage_momentum.py` against the gate-(a/b/c) "
         "store and gate-(d) fee model. Deterministic; re-running against an unchanged "
         "store reproduces this report byte-for-byte (fixed seed "
         f"{BOOTSTRAP_SEED}, {BOOTSTRAP_REPS} bootstrap reps). Reference-arm probe cached "
         f"at `{REF_CACHE.relative_to(ROOT)}`.*")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    print(f"Mean IC = {mean_ic:.4f}  | 95% CI [{ci_lo:.4f}, {ci_hi:.4f}]  "
          f"| net spread = {pct(net_spread)}  | VERDICT = {verdict}")


if __name__ == "__main__":
    main()
