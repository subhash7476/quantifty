import duckdb
con = duckdb.connect('data/market_data/equity_bhavcopy.duckdb', read_only=True)
r = con.execute('SELECT MIN(trade_date), MAX(trade_date) FROM equity_bhavcopy_adjusted').fetchone()
print('Equity adjusted range: {} to {}'.format(r[0], r[1]))
train = con.execute("SELECT COUNT(*) FROM equity_bhavcopy_adjusted WHERE trade_date <= '2018-12-31'").fetchone()[0]
holdout = con.execute("SELECT COUNT(*) FROM equity_bhavcopy_adjusted WHERE trade_date > '2018-12-31' AND trade_date <= '2022-12-30'").fetchone()[0]
print('TRAIN rows: {:,}'.format(train))
print('HOLDOUT rows: {:,}'.format(holdout))
n_td = con.execute("SELECT COUNT(DISTINCT trade_date) FROM equity_bhavcopy_adjusted WHERE trade_date <= '2018-12-31'").fetchone()[0]
print('TRAIN trade dates: {}'.format(n_td))
n_td2 = con.execute("SELECT COUNT(DISTINCT trade_date) FROM equity_bhavcopy_adjusted WHERE trade_date > '2018-12-31' AND trade_date <= '2022-12-30'").fetchone()[0]
print('HOLDOUT trade dates: {}'.format(n_td2))
con.close()
