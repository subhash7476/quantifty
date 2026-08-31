import duckdb
import pandas as pd

bt = pd.read_csv(r"data/mrlc_test/trades_live_196.csv")
con = duckdb.connect(r"data/mrlc_test/paper/paper.duckdb", read_only=True)
p = con.execute(
    "SELECT symbol, signal_date, entry_date, entry_price, sl, tp, reason1, reason2, round(r_net, 4) AS r_net FROM trades ORDER BY signal_date"
).fetchdf()
con.close()
bt["signal_date"] = pd.to_datetime(bt["signal_date"]).dt.date
p["signal_date"] = pd.to_datetime(p["signal_date"]).dt.date
m = p.merge(bt[["symbol", "signal_date", "entry", "sl", "tp", "r_net", "reason1", "reason2"]],
            on=["symbol", "signal_date"], how="left", suffixes=("_paper", "_bt"))
m["entry_ok"] = (abs(m["entry_price"] - m["entry"]) / m["entry"] < 0.001)
m["sl_ok"] = (abs(m["sl_paper"] - m["sl_bt"]) / m["sl_bt"] < 0.01)
m["r_ok"] = (abs(m["r_net_paper"] - m["r_net_bt"]) / m["r_net_bt"].abs() < 0.10)
print(m[["symbol", "signal_date", "entry_price", "entry", "sl_paper", "sl_bt",
         "r_net_paper", "r_net_bt", "entry_ok", "sl_ok", "r_ok"]].to_string(index=False))
print("checks:", "ALL OK" if m["entry_ok"].all() and m["sl_ok"].all() and m["r_ok"].all() else "MISMATCHES")
