"""F1 Cash-Synthesized Feasibility Screen — GO/NO-GO on vendor data purchase.

Spec: docs/reports/F1_FEASIBILITY_SCREEN_SPEC.md
No sealed-window signal/return read. No promotion path.

Usage:
    python scripts/sfb/f1_feasibility_screen.py
"""

import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

import duckdb
import numpy as np
import pandas as pd

ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
REPORT_PATH = ROOT / "docs" / "reports" / "F1_FEASIBILITY_SCREEN_REPORT.md"

DEV_LO = date(2012, 1, 1)
DEV_HI = date(2022, 12, 31)
TRAIN_HI = date(2018, 12, 31)
HOLDOUT_LO = date(2019, 1, 1)
HOLDOUT_HI = date(2022, 12, 30)

MAX_NAMES = 10
MIN_NAMES = 3
LIQ_WINDOW = 63
LIQ_MIN_MEDIAN_TURNOVER = 50_000_000

SLIPPAGE_SWEEP = [
    ("optimistic", 0.0005),
    ("mid", 0.0010),
    ("pessimistic", 0.0020),
]

TRAIN_SLIPPAGE_MULT = 1.5
ATR_PERIOD = 21
BRACKET_N = [5, 10, 15, 20]
BRACKET_K_SL = [1.0, 1.5, 2.0, 2.5]
BRACKET_K_TP = [2.0, 3.0, 4.0, 5.0]

ROLL_ROUND_TRIPS_PER_FORMATION = 0.5
POSITION_NOTIONAL = 1_000_000


@dataclass
class FoldResult:
    label: str
    n_formations: int
    expectancy: float
    expectancy_ci: tuple
    max_dd: float
    days_held_mean: float
    turnover_drag_bp_yr: float
    gross_return_mean: float
    net_return_mean: float
    slippage_label: str
    bracket_params: tuple


@dataclass
class ScreenResult:
    train: list
    holdout: list
    best_bracket: tuple
    go: bool
    reason: str
    ci_violation: bool


def _is_month_end(cal, idx):
    return idx + 1 >= len(cal) or cal[idx].month != cal[idx + 1].month


# --- Lazy DataStore ---

class DataStore:
    def __init__(self, db_path, cutoff=DEV_HI):
        self.con = duckdb.connect(str(db_path), read_only=True)
        self.cutoff = cutoff
        self._cal = None
        self._cal_pos = None
        self._px_cache = {}
        self._op_cache = {}
        self._hi_cache = {}
        self._lo_cache = {}
        self._ent_dates_cache = defaultdict(set)
        self._neg_cache = set()

    @property
    def cal(self):
        if self._cal is None:
            self._cal = [r[0] for r in self.con.execute(
                "SELECT trade_date FROM trading_calendar WHERE n_symbols>=200 "
                "AND trade_date<=? ORDER BY trade_date", [self.cutoff]).fetchall()]
        return self._cal

    @property
    def cal_pos(self):
        if self._cal_pos is None:
            self._cal_pos = {d: i for i, d in enumerate(self.cal)}
        return self._cal_pos

    def _ensure_loaded(self, entities):
        needed = [e for e in entities if e not in self._ent_dates_cache
                  and e not in self._neg_cache]
        if not needed:
            return
        self._load_entities(needed)

    def _load_entities(self, needed):
        placeholders = ",".join("?" for _ in needed)
        rows = self.con.execute(f"""
            SELECT e.entity, a.trade_date, a.close, a.open, a.high, a.low
            FROM equity_bhavcopy_adjusted a
            JOIN universe_eligibility e ON e.symbol = a.symbol
            WHERE a.trade_date <= ?
              AND e.class IN ('equity_confirmed', 'equity_unidentified')
              AND e.entity IN ({placeholders})
              AND a.close > 0
        """, [self.cutoff] + needed).fetchall()
        seen = {e for e in needed}
        for ent, td, c, o, h, l in rows:
            if c is not None and c > 0:
                self._px_cache[(ent, td)] = float(c)
                self._ent_dates_cache[ent].add(td)
                seen.discard(ent)
            if h is not None and h > 0:
                self._hi_cache[(ent, td)] = float(h)
            if l is not None and l > 0:
                self._lo_cache[(ent, td)] = float(l)
            if o is not None:
                self._op_cache[(ent, td)] = float(o)
        for ent in seen:
            self._neg_cache.add(ent)

    def preload_universe(self, entities):
        """Preload OHLC for a batch of entities — call once before simulation."""
        all_ents = sorted(set(entities))
        chunk = 200
        for i in range(0, len(all_ents), chunk):
            batch = all_ents[i:i + chunk]
            self._load_entities(batch)

    def get_px(self, entity, d):
        if (entity, d) not in self._px_cache:
            self._ensure_loaded([entity])
        return self._px_cache.get((entity, d))

    def get_op(self, entity, d):
        if (entity, d) not in self._op_cache:
            self._ensure_loaded([entity])
        return self._op_cache.get((entity, d))

    def get_hi(self, entity, d):
        if (entity, d) not in self._hi_cache:
            self._ensure_loaded([entity])
        return self._hi_cache.get((entity, d))

    def get_lo(self, entity, d):
        if (entity, d) not in self._lo_cache:
            self._ensure_loaded([entity])
        return self._lo_cache.get((entity, d))

    def ent_dates(self, entity):
        if entity not in self._ent_dates_cache:
            self._ensure_loaded([entity])
        return sorted(self._ent_dates_cache.get(entity, []))

    def close(self):
        pass


# --- PIT liquidity universe ---

def build_liquidity_universe(ds, cutoff=DEV_HI):
    """Build PIT F&O-eligibility proxy. Causal trailing-63-session median
    turnover computed per formation date from raw equity_bhavcopy."""
    cal = ds.cal
    form_dates = [d for i, d in enumerate(cal)
                  if _is_month_end(cal, i) and (cutoff is None or d <= cutoff)]

    # Get positions of formation dates for window slicing
    cal_pos = ds.cal_pos

    universe = {}
    for fd in form_dates:
        fd_pos = cal_pos.get(fd)
        if fd_pos is None or fd_pos < LIQ_WINDOW:
            continue
        lookback_start = cal[fd_pos - LIQ_WINDOW]
        rows = ds.con.execute("""
            WITH daily_t AS (
                SELECT symbol, trade_date, SUM(turnover) AS tot_t
                FROM equity_bhavcopy
                WHERE trade_date >= ? AND trade_date < ?
                  AND series IN ('EQ', 'BE') AND close > 0 AND turnover > 0
                GROUP BY symbol, trade_date
            )
            SELECT e.entity
            FROM daily_t d
            JOIN universe_eligibility e ON e.symbol = d.symbol
            WHERE e.class IN ('equity_confirmed', 'equity_unidentified')
            GROUP BY e.entity
            HAVING COUNT(*) >= 10 AND MEDIAN(tot_t) >= ?
        """, [lookback_start, fd, LIQ_MIN_MEDIAN_TURNOVER]).fetchall()
        eligible = sorted([r[0] for r in rows])
        if len(eligible) >= MIN_NAMES:
            universe[fd] = eligible

    return universe, form_dates


# --- Signal ---

def _day_back(ds, d, offset):
    cal = ds.cal
    cal_pos = ds.cal_pos
    idx = cal_pos.get(d)
    if idx is None or idx - offset < 0:
        return None
    return cal[idx - offset]


def score_momentum_12_1(ds, t, entities):
    t_12m = _day_back(ds, t, 252)
    t_1m = _day_back(ds, t, 21)
    if t_12m is None or t_1m is None:
        return {}
    scores = {}
    for ent in entities:
        p_start = ds.get_px(ent, t_12m)
        p_recent = ds.get_px(ent, t_1m)
        if p_start and p_recent and p_start > 0 and p_recent > 0:
            scores[ent] = p_recent / p_start - 1.0
    return scores


def select_top_n(scores, universe_at_t, n=MAX_NAMES):
    eligible = {e: s for e, s in scores.items() if e in universe_at_t}
    ranked = sorted(eligible.items(), key=lambda x: -x[1])
    return [e for e, _ in ranked[:n]]


# --- ATR and bracket ---

def _compute_atr(ds, ent, t):
    cal = ds.cal
    cal_pos = ds.cal_pos
    idx = cal_pos.get(t)
    if idx is None:
        return None
    start = max(0, idx - ATR_PERIOD)
    trues = []
    for i in range(start, idx):
        d = cal[i]
        high = ds.get_hi(ent, d)
        low = ds.get_lo(ent, d)
        prev_c = ds.get_px(ent, cal[i - 1]) if i > start else None
        if high and low and high > 0 and low > 0:
            hl = high - low
            hc = abs(high - (prev_c or low))
            lc = abs(low - (prev_c or low))
            trues.append(max(hl, hc, lc))
    if len(trues) >= 5:
        return sum(trues) / len(trues)
    return None


def _apply_bracket(entry_price, atr, max_hold, k_sl, k_tp, daily_bars):
    """Conservative bracket ladder per spec §3.

    1. Determine open-gap: price can gap through the stop at open.
       Model: open fill at worst-case (gap through SL = fill at gap-open price).
    2. Within-bar: SL checked before TP on same-bar reversal.
    3. High/Low intercept.
    4. Period-close fallback.

    Note: open-gap is approximated via the bar's low vs entry relationship
    since we use daily bars; a true intraday gap would require tick data.
    """
    if atr is None or atr <= 0:
        return entry_price, max_hold
    sl = entry_price - k_sl * atr
    tp = entry_price + k_tp * atr
    for i, (_d, high, low, open_p) in enumerate(daily_bars):
        if i >= max_hold:
            break
        if high is None or low is None:
            continue
        # Step 1: open-gap — gap open beyond SL or TP
        if open_p is not None and open_p > 0:
            if open_p <= sl:
                return open_p, i + 1
            if open_p >= tp:
                return open_p, i + 1
        # Step 2: worst-case whipsaw — SL before TP on same-bar reversal
        sl_hit = low <= sl
        tp_hit = high >= tp
        if sl_hit and tp_hit:
            return max(low, sl), i + 1
        if sl_hit:
            return max(low, sl), i + 1
        if tp_hit:
            return min(high, tp), i + 1
    return entry_price, max_hold


# --- Cost model ---

def formation_cost(trade_value, trade_date, side, slippage_bp):
    from core.execution.futures.futures_fees import futures_fees
    fees = futures_fees(side=side, trade_value=trade_value, trade_date=trade_date)
    slippage = trade_value * slippage_bp
    return (fees.total + slippage) / trade_value


# --- Simulation ---

def simulate_portfolio(ds, universe, form_dates, bracket_params,
                       slippage_bp, label, cutoff, is_train=False):
    n_max, k_sl, k_tp = bracket_params
    cal = ds.cal
    cal_pos = ds.cal_pos
    effective_slip = slippage_bp * (TRAIN_SLIPPAGE_MULT if is_train else 1.0)

    all_net = []
    all_gross = []
    all_days_list = []
    equity = [1.0]

    for t in form_dates:
        if t > cutoff:
            break
        universe_at_t = set(universe.get(t, []))
        scores = score_momentum_12_1(ds, t, universe_at_t)
        picks = select_top_n(scores, universe_at_t)
        if len(picks) < MIN_NAMES:
            continue

        idx = cal_pos.get(t)
        next_fd = None
        for j in range(idx + 1, len(cal)):
            if _is_month_end(cal, j) and cal[j] <= cutoff:
                next_fd = cal[j]
                break
        if next_fd is None or next_fd <= t:
            continue

        w = 1.0 / len(picks)
        port_gross = 0.0
        port_net = 0.0
        days_this_form = []

        for ent in picks:
            p0 = ds.get_px(ent, t)
            if not p0 or p0 <= 0:
                continue

            bars = []
            for j in range(idx + 1, len(cal)):
                d = cal[j]
                if d > next_fd:
                    break
                h = ds.get_hi(ent, d)
                lv = ds.get_lo(ent, d)
                op = ds.get_op(ent, d)
                bars.append((d, h, lv, op))
            if not bars:
                continue

            atr = _compute_atr(ds, ent, t)
            exit_price, days_held = _apply_bracket(p0, atr, n_max, k_sl, k_tp, bars)

            if exit_price == p0:
                p1 = ds.get_px(ent, next_fd)
                if p1 and p1 > 0:
                    exit_price = p1
                    days_held = len(bars)

            if exit_price <= 0:
                continue

            gross_ret = exit_price / p0 - 1.0
            buy_cost = formation_cost(POSITION_NOTIONAL, t, "BUY", effective_slip)
            sell_cost = formation_cost(POSITION_NOTIONAL, next_fd, "SELL", effective_slip)
            roll_cost = ROLL_ROUND_TRIPS_PER_FORMATION * (
                formation_cost(POSITION_NOTIONAL, t, "SELL", effective_slip)
                + formation_cost(POSITION_NOTIONAL, t, "BUY", effective_slip))
            net_ret = gross_ret - buy_cost - sell_cost - roll_cost

            port_gross += w * gross_ret
            port_net += w * net_ret
            days_this_form.append(days_held)

        if not days_this_form:
            continue
        all_gross.append(port_gross)
        all_net.append(port_net)
        all_days_list.append(days_this_form)
        equity.append(equity[-1] * (1 + port_net))

    if len(all_net) < 5:
        return FoldResult(label, len(all_net), 0.0, (0, 0), 0.0, 0.0, 0.0,
                          0.0, 0.0, label, bracket_params)

    expectancy = float(np.mean(all_net))
    gross_mean = float(np.mean(all_gross))
    net_mean = float(np.mean(all_net))
    ec = np.array(equity)
    peak = np.maximum.accumulate(ec)
    dd = (ec - peak) / peak
    max_dd = float(np.min(dd))
    all_days = [d for sub in all_days_list for d in sub]
    days_held_mean = float(np.mean(all_days)) if all_days else 0.0
    yr_span = max(1, (form_dates[-1].year - form_dates[0].year)
                  + (form_dates[-1].month - form_dates[0].month) / 12)
    n_yr = len(all_net) / yr_span
    turnover_drag_bp_yr = (gross_mean - net_mean) * n_yr * 10000

    np.random.seed(42)
    n_boot = 1000
    arr = np.array(all_net)
    block_size = max(4, len(arr) // 20)
    boot_means = []
    for _ in range(n_boot):
        n_full = int(np.floor(len(arr) / block_size))
        blocks = []
        for _ in range(n_full):
            start = np.random.randint(0, max(1, len(arr) - block_size + 1))
            blocks.extend(arr[start:start + block_size])
        boot_means.append(np.mean(blocks[:len(arr)]))
    ci_lower = float(np.percentile(boot_means, 5))
    ci_upper = float(np.percentile(boot_means, 95))

    return FoldResult(label, len(all_net), expectancy, (ci_lower, ci_upper),
                      max_dd, days_held_mean, turnover_drag_bp_yr,
                      gross_mean, net_mean, label, bracket_params)


def select_bracket(ds, universe, train_fd, slippage_bp):
    best_exp = -float("inf")
    best_params = (BRACKET_N[0], BRACKET_K_SL[0], BRACKET_K_TP[0])
    total = len(BRACKET_N) * len(BRACKET_K_SL) * len(BRACKET_K_TP)
    count = 0
    for n in BRACKET_N:
        for k_sl in BRACKET_K_SL:
            for k_tp in BRACKET_K_TP:
                count += 1
                if count % 16 == 0:
                    print(f"    grid {count}/{total}...", flush=True)
                r = simulate_portfolio(ds, universe, train_fd,
                                       (n, k_sl, k_tp), slippage_bp,
                                       "sel", TRAIN_HI, is_train=True)
                if r.expectancy > best_exp:
                    best_exp = r.expectancy
                    best_params = (n, k_sl, k_tp)
    return best_params


# --- Decision rule (spec §6) ---

def decide(train_results, holdout_results):
    ci_violation = False
    for r in train_results:
        if r.net_return_mean <= 0:
            return False, (
                f"NO-GO: net expectancy <= 0 at '{r.slippage_label}' "
                f"on TRAIN (net={r.net_return_mean:.4f})."), ci_violation
        if r.slippage_label == "pessimistic" and r.expectancy_ci[0] <= 0:
            ci_violation = True
    for r in holdout_results:
        if r.net_return_mean <= 0:
            return False, (
                f"NO-GO: net expectancy <= 0 at '{r.slippage_label}' "
                f"on HOLDOUT (net={r.net_return_mean:.4f})."), ci_violation
        if r.slippage_label == "pessimistic" and r.expectancy_ci[0] <= 0:
            ci_violation = True
    for train_r, hold_r in zip(train_results, holdout_results):
        if train_r.gross_return_mean > 0 and train_r.net_return_mean <= 0:
            return False, (
                f"NO-GO: fees consume all gross edge on TRAIN at "
                f"'{train_r.slippage_label}'."), ci_violation
        if hold_r.gross_return_mean > 0 and hold_r.net_return_mean <= 0:
            return False, (
                f"NO-GO: fees consume all gross edge on HOLDOUT at "
                f"'{hold_r.slippage_label}'."), ci_violation
    go_text = (
        "GO: net expectancy positive across full slippage band on "
        "both TRAIN and HOLDOUT. Recommend purchasing vendor futures data.")
    if ci_violation:
        go_text += (
            " CAVEAT: CI lower bound <= 0 at pessimistic slippage \u2014 "
            "net expectancy is not robustly positive at the conservative end.")
    return True, go_text, ci_violation


# --- Report ---

def _grid_boundary_note(params):
    """Return note if winner sits at grid boundary."""
    n, k_sl, k_tp = params
    boundaries = []
    if n in (BRACKET_N[0], BRACKET_N[-1]):
        boundaries.append(f"n={'min' if n==BRACKET_N[0] else 'max'}")
    if k_sl in (BRACKET_K_SL[0], BRACKET_K_SL[-1]):
        boundaries.append(f"k_sl={'min' if k_sl==BRACKET_K_SL[0] else 'max'}")
    if k_tp in (BRACKET_K_TP[0], BRACKET_K_TP[-1]):
        boundaries.append(f"k_tp={'min' if k_tp==BRACKET_K_TP[0] else 'max'}")
    if boundaries:
        return f"  **Note:** winner at grid boundary ({', '.join(boundaries)}). True optimum may lie outside."
    return ""


def generate_report(screen_result):
    lines = []
    lines.append("# F1 Feasibility Screen Report")
    lines.append(f"*Generated: {pd.Timestamp.now().isoformat()}*")
    lines.append("")
    lines.append("## Caveats (read before interpreting)")
    lines.append("")
    lines.append("1. **Signal prior-exposed.** 12-1 momentum on this panel ran as PSB-2 C4")
    lines.append("   (dropped on power 0.4110). TRAIN is not a clean fold.")
    lines.append("2. **Cost assumed, not measured.** Roll cost, bid-ask, and impact are modeled,")
    lines.append("   not observed. Roll frequency is an uncalibrated assumption \u2014 the")
    lines.append("   spec-required 2023+ futures panel was inaccessible (NSE blocks).")
    lines.append("3. **Basis/carry ignored.** Futures-to-cash basis convergence over the ~monthly")
    lines.append("   hold is small vs. momentum dispersion but adds unmodeled noise.")
    lines.append("4. **Not a promote path.** A GO means worth buying vendor data for a proper")
    lines.append("   pre-registered battery. It does not bless the construct for live trading.")
    lines.append("5. **No sealed-window signal read.** Returns computed only up to 2022-12-31.")
    lines.append("6. **Bracket fills modeled on daily OHLC.** Open-gap approximated via daily")
    lines.append("   low/entry; intraday fills assume execution at level (conservative SL-first).")
    lines.append("")

    verdict_line = "**GO**" if screen_result.go else "**NO-GO**"
    lines.append(f"## Verdict: {verdict_line}")
    lines.append("")
    lines.append(screen_result.reason)
    if screen_result.ci_violation and screen_result.go:
        lines.append("")
        lines.append("**Note:** the GO is conditional \u2014 net expectancy CI spans zero at the")
        lines.append("conservative end of the slippage band. A vendor-data battery would need")
        lines.append("to resolve this with real futures prices.")
    lines.append("")

    n, k_sl, k_tp = screen_result.best_bracket
    lines.append(f"## Best Bracket Params (TRAIN-selected)")
    lines.append(f"- ATR period: {ATR_PERIOD}d, n={n}, k_sl={k_sl}, k_tp={k_tp}")
    lines.append(f"- Grid searched: {len(BRACKET_N)}x{len(BRACKET_K_SL)}x"
                 f"{len(BRACKET_K_TP)} = {len(BRACKET_N)*len(BRACKET_K_SL)*len(BRACKET_K_TP)} "
                 f"combinations")
    bn = _grid_boundary_note(screen_result.best_bracket)
    if bn:
        lines.append(bn)
    lines.append("")

    for fold_label, results in [("TRAIN (2012-2018)", screen_result.train),
                                 ("HOLDOUT (2019-2022)", screen_result.holdout)]:
        lines.append(f"## {fold_label}")
        hdr = ("| Slippage     |  n  |   Exp    | CI_low   | CI_high  |"
               " MaxDD    | DaysH | TD_bp/yr | Gross    | Net      |")
        lines.append(hdr)
        lines.append("|" + "-" * (len(hdr) - 2) + "|")
        for r in results:
            ci_flag = " *" if r.expectancy_ci[0] <= 0 else "  "
            lines.append(
                f"| {r.slippage_label:<12s} | {r.n_formations:>3d} |"
                f" {r.expectancy:>+8.4f} | {r.expectancy_ci[0]:>+8.4f}{ci_flag}|"
                f" {r.expectancy_ci[1]:>+8.4f} | {r.max_dd:>8.4f} |"
                f" {r.days_held_mean:>5.1f} | {r.turnover_drag_bp_yr:>8.0f} |"
                f" {r.gross_return_mean:>+8.4f} | {r.net_return_mean:>+8.4f} |")
        lines.append("  * CI lower bound <= 0 at this point")
        lines.append("")

    lines.append("## Configuration")
    lines.append(f"- Signal: 12-1 cross-sectional momentum, skip most-recent month")
    lines.append(f"- Portfolio: <={MAX_NAMES} names, equal-weight, monthly formation")
    lines.append(f"- Bracket: ATR-{ATR_PERIOD}d, SL before TP (conservative), "
                 f"open-gap approximated via daily bar low")
    lines.append(f"- Universe: cash liquidity proxy (>=Rs{LIQ_MIN_MEDIAN_TURNOVER/1e7:.0f}cr "
                 f"median daily turnover over trailing {LIQ_WINDOW}d, "
                 f"causal per-formation-date computation)")
    lines.append(f"- Slippage sweep: "
                 + ", ".join(f"{l} {b*10000:.0f}bp" for l, b in SLIPPAGE_SWEEP))
    lines.append(f"- TRAIN slippage multiplier: {TRAIN_SLIPPAGE_MULT}x")
    lines.append(f"- Roll cost assumption: {ROLL_ROUND_TRIPS_PER_FORMATION} extra round-trips/formation")
    lines.append(f"- Position notional: Rs{POSITION_NOTIONAL/1e5:.0f}L")
    lines.append(f"- TRAIN window: {DEV_LO} to {TRAIN_HI}")
    lines.append(f"- HOLDOUT window: {HOLDOUT_LO} to {HOLDOUT_HI}")
    lines.append("")

    return "\n".join(lines)


def main():
    print("Initializing data store...", flush=True)
    ds = DataStore(DB_PATH, cutoff=DEV_HI)
    print(f"  Calendar: {len(ds.cal)} days", flush=True)

    print("Building causal PIT liquidity universe (trailing 63d per formation)...", flush=True)
    universe, form_dates = build_liquidity_universe(ds, cutoff=DEV_HI)
    active = {d: ents for d, ents in universe.items() if len(ents) >= MIN_NAMES}
    print(f"  Formation dates with >= {MIN_NAMES} eligible names: {len(active)}", flush=True)

    if not active:
        result = ScreenResult(
            [], [], (BRACKET_N[0], BRACKET_K_SL[0], BRACKET_K_TP[0]),
            False, "No formation dates with eligible names.", False)
        report_text = generate_report(result)
        print(report_text)
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            f.write(report_text)
        return

    train_fd = sorted([d for d in active if DEV_LO <= d <= TRAIN_HI])
    holdout_fd = sorted([d for d in active if HOLDOUT_LO <= d <= HOLDOUT_HI])
    print(f"  TRAIN ({DEV_LO}..{TRAIN_HI}): {len(train_fd)} formations", flush=True)
    print(f"  HOLDOUT ({HOLDOUT_LO}..{HOLDOUT_HI}): {len(holdout_fd)} formations", flush=True)

    # Preload all entity OHLC data upfront to avoid per-entity DB round-trips
    all_entities = set()
    for ents in active.values():
        all_entities.update(ents)
    print(f"  Preloading OHLC for {len(all_entities)} entities...", flush=True)
    import time as _time
    _t0 = _time.time()
    ds.preload_universe(list(all_entities))
    print(f"  Preload done ({_time.time()-_t0:.0f}s)", flush=True)

    if len(train_fd) < 5:
        result = ScreenResult(
            [], [], (BRACKET_N[0], BRACKET_K_SL[0], BRACKET_K_TP[0]),
            False, f"Too few TRAIN formations: {len(train_fd)}", False)
        report_text = generate_report(result)
        print(report_text)
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            f.write(report_text)
        return

    print("Selecting bracket params on TRAIN (mid slippage, 10bp)...", flush=True)
    import time as _time
    _t0 = _time.time()
    best_bracket = select_bracket(ds, active, train_fd, 0.0010)
    print(f"  Best: n={best_bracket[0]}, k_sl={best_bracket[1]}, "
          f"k_tp={best_bracket[2]} ({_time.time()-_t0:.0f}s)", flush=True)

    train_results = []
    holdout_results = []

    for sl_label, sl_bp in SLIPPAGE_SWEEP:
        print(f"  Slippage: {sl_label} ({sl_bp*10000:.0f} bp/side)", flush=True)
        tr = simulate_portfolio(ds, active, train_fd, best_bracket,
                                sl_bp, sl_label, TRAIN_HI, is_train=True)
        train_results.append(tr)
        print(f"    TRAIN: exp={tr.expectancy:.4f}, net={tr.net_return_mean:.4f}, "
              f"maxdd={tr.max_dd:.4f}, drag={tr.turnover_drag_bp_yr:.0f}bp/yr", flush=True)

        if holdout_fd:
            hr = simulate_portfolio(ds, active, holdout_fd, best_bracket,
                                    sl_bp, sl_label, HOLDOUT_HI, is_train=False)
            holdout_results.append(hr)
            print(f"    HOLDOUT: exp={hr.expectancy:.4f}, net={hr.net_return_mean:.4f}, "
                  f"maxdd={hr.max_dd:.4f}, drag={hr.turnover_drag_bp_yr:.0f}bp/yr", flush=True)

    go, reason, ci_viol = decide(
        train_results, holdout_results if holdout_fd else [])

    screen_result = ScreenResult(
        train=train_results, holdout=holdout_results,
        best_bracket=best_bracket, go=go, reason=reason,
        ci_violation=ci_viol)

    ds.con.close()
    report_text = generate_report(screen_result)
    print()
    print(report_text, flush=True)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"\nReport saved to {REPORT_PATH}")


if __name__ == "__main__":
    main()
