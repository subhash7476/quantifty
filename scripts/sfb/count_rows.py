import duckdb
con = duckdb.connect('data/market_data/equity_bhavcopy.duckdb', read_only=True)
r = con.execute("SELECT COUNT(*) FROM equity_bhavcopy_adjusted a JOIN universe_eligibility e ON e.symbol=a.symbol WHERE a.trade_date <= '2022-12-31' AND e.class IN ('equity_confirmed', 'equity_unidentified')").fetchone()
print('Row count:', r[0])
# Also count per-entity
r2 = con.execute("SELECT COUNT(DISTINCT e.entity) FROM equity_bhavcopy_adjusted a JOIN universe_eligibility e ON e.symbol=a.symbol WHERE a.trade_date <= '2022-12-31' AND e.class IN ('equity_confirmed', 'equity_unidentified')").fetchone()
print('Entities:', r2[0])
con.close()
