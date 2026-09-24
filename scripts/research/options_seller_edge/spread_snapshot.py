"""Live stock-option bid/ask snapshot — calibrates the spread assumption for the
bhavcopy (no bid/ask) seller study. Read-only market-data calls only."""
import sys, time, json
from datetime import datetime
sys.path.insert(0, ".")
import duckdb, pandas as pd
from core.brokers.upstox_market_data import UpstoxMarketData
import requests
from core.auth.credentials import credentials

from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
OUT = str(ROOT / "data" / "scratch" / "options_seller_edge" / "stock_opt_spreads.parquet")
Path(OUT).parent.mkdir(parents=True, exist_ok=True)
inst = duckdb.connect(r"data\instruments\nse_fo_instruments.duckdb", read_only=True)
fut = duckdb.connect(r"data\market_data\futures_bhavcopy.duckdb", read_only=True)
snap = inst.execute("select max(snapshot_date) from instruments").fetchone()[0]
futs = inst.execute("""select instrument_key, tradingsymbol, name, expiry, lot_size from instruments
    where snapshot_date=? and instrument_type='FUT' and instrument_key like 'NSE_FO%'""", [snap]).df()
futs["underlying"] = futs.tradingsymbol.str.split(" ").str[0]
fclose = fut.execute("""select underlying, expiry_dt, close from futures_bhavcopy
    where trade_date=(select max(trade_date) from futures_bhavcopy) and inst_type='FUTSTK'""").df()
fclose["expiry"] = fclose.expiry_dt.astype(str)
futs = futs.merge(fclose[["underlying", "expiry", "close"]], on=["underlying", "expiry"])
futs = futs[futs.expiry.isin(["2026-09-29", "2026-10-27"])]
opts = inst.execute("""select instrument_key, name, expiry, strike, instrument_type as opt_type, lot_size
    from instruments where snapshot_date=? and instrument_type in ('CE','PE')
    and expiry in ('2026-09-29','2026-10-27')""", [snap]).df()
opts = opts.merge(futs[["name", "expiry", "underlying", "close"]], on=["name", "expiry"])
opts = opts[(opts.strike / opts.close - 1).abs() <= 0.15]
print("futures", len(futs), "options", len(opts))

token = credentials.get("access_token")
def quotes(keys):
    r = requests.get("https://api.upstox.com/v2/market-quote/quotes",
                     headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                     params={"instrument_key": ",".join(keys)}, timeout=20)
    r.raise_for_status()
    out = {}
    for e in r.json().get("data", {}).values():
        d = (e.get("depth") or {})
        b = (d.get("buy") or [{}])[0]; a = (d.get("sell") or [{}])[0]
        out[e["instrument_token"]] = dict(ltp=e.get("last_price"), bid=b.get("price"), ask=a.get("price"),
                                           bid_qty=b.get("quantity"), ask_qty=a.get("quantity"),
                                           volume=e.get("volume"), oi=e.get("oi"))
    return out

ts = datetime.now()
allq = {}
keys = list(opts.instrument_key) + list(futs.instrument_key)
for i in range(0, len(keys), 450):
    allq.update(quotes(keys[i:i + 450]))
    time.sleep(0.3)
q = pd.DataFrame.from_dict(allq, orient="index").rename_axis("instrument_key").reset_index()
fq = futs.merge(q, on="instrument_key")[["underlying", "expiry", "ltp"]].rename(columns={"ltp": "fut_ltp"})
df = opts.merge(q, on="instrument_key").merge(fq, on=["underlying", "expiry"], how="left")
df["snapshot_ts"] = ts
df.to_parquet(OUT)
print("saved", len(df), "rows at", ts, "two-sided:", ((df.bid > 0) & (df.ask > 0)).mean())
