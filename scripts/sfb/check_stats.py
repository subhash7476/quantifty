import duckdb
con = duckdb.connect('data/market_data/futures_bhavcopy.duckdb')
r = con.execute('SELECT COUNT(*), MIN(trade_date), MAX(trade_date) FROM futures_bhavcopy').fetchone()
print('Rows: {:,}'.format(r[0]))
print('Range: {} to {}'.format(r[1], r[2]))
n_td = con.execute('SELECT COUNT(DISTINCT trade_date) FROM futures_bhavcopy').fetchone()[0]
print('Distinct trade dates: {}'.format(n_td))
n_stk = con.execute("SELECT COUNT(DISTINCT underlying) FROM futures_bhavcopy WHERE inst_type='FUTSTK'").fetchone()[0]
n_idx = con.execute("SELECT COUNT(DISTINCT underlying) FROM futures_bhavcopy WHERE inst_type='FUTIDX'").fetchone()[0]
print('FUTSTK underlyings: {}'.format(n_stk))
print('FUTIDX underlyings: {}'.format(n_idx))
con.close()
