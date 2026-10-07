# Structural census: per phase-0 formation, names with valid GEX + ATM IV under the frozen rule.
# Option + futures data only. No equity bars, no outcomes, no results calendar.
import duckdb, pandas as pd
from datetime import date
from core.analytics.gex_history import select_strikes
from scripts.gex_xs_5d import panel as P
from scripts.gex_xs_5d.run_stage import STAGES
D = "F:/Nifty/data/market_data/"   # run from the worktree; data lives in the main checkout
o = duckdb.connect(D + "stock_options_bhavcopy.duckdb", read_only=True)
f = duckdb.connect(D + "futures_bhavcopy.duckdb", read_only=True)
for stage in ("dev", "sealed"):
    a, b = STAGES[stage]
    s = P.session_grid([r[0] for r in o.execute("SELECT DISTINCT trade_date FROM stock_options_bhavcopy WHERE trade_date BETWEEN ? AND ?", [a, b]).fetchall()], a, b)
    rows = []
    for i in P.formation_indices(len(s), 0):
        t, t5 = s[i], s[i + 5]
        ch = o.execute("""SELECT underlying, expiry_dt, strike, option_type, close, contracts, open_int FROM stock_options_bhavcopy
            WHERE trade_date = ? AND expiry_dt > trade_date AND (contracts > 0 OR open_int > 0)""", [t]).df()
        ch["expiry_dt"] = pd.to_datetime(ch["expiry_dt"]).dt.date
        fut = {(u, e): c for u, e, c in f.execute("SELECT underlying, expiry_dt, close FROM futures_bhavcopy WHERE inst_type='FUTSTK' AND trade_date = ?", [t]).fetchall()}
        valid = ok = 0
        for und, c in ch.groupby("underlying"):
            exps = sorted(c["expiry_dt"].unique()); by = {}
            for e in exps:
                F = fut.get((und, e))
                if F is not None:
                    by[e] = select_strikes(c[c["expiry_dt"] == e], F, (e - t).days / 365)
            es = [x for x in by.values() if len(x.strikes)]
            if P.name_valid(es):
                valid += 1
                ive = P.iv_expiry(exps, t5)
                ok += ive in by and len(by[ive].strikes) > 0 and P.atm_iv(by[ive]) is not None
        near = min(ch["expiry_dt"]) if len(ch) else None
        rows.append((stage, t, near is not None and near <= t5, valid, ok))
        print(stage, t, valid, ok, flush=True)
    df = pd.DataFrame(rows, columns=["stage", "t", "expiry_in_window", "valid", "with_iv"])
    df.to_csv(f"F:/Nifty/data/research/gex_xs_5d/xs_census_{stage}.csv", index=False)
