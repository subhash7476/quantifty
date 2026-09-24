"""Trade-level short ATM straddles on single-stock monthly options.

For every monthly expiry E and entry offset (sessions before E), sell the ATM straddle
(nearest strike to the same-expiry future, both legs traded at entry) at the entry
close, buy back at the T-1 close (physical settlement => never marked to intrinsic).
Signals are computed from data known at the entry close only.
"""
import duckdb, pandas as pd, numpy as np

from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
SP = str(ROOT / "data" / "scratch" / "options_seller_edge")
Path(SP).mkdir(parents=True, exist_ok=True)
con = duckdb.connect()
con.execute(r"ATTACH 'data\market_data\stock_options_bhavcopy.duckdb' AS o (READ_ONLY)")
con.execute(r"ATTACH 'data\market_data\futures_bhavcopy.duckdb' AS f (READ_ONLY)")
con.execute(r"ATTACH 'data\market_data\options_bhavcopy.duckdb' AS i (READ_ONLY)")

days = [d for (d,) in con.execute("select distinct trade_date from f.futures_bhavcopy where inst_type in ('FUTSTK','FUTIDX') order by 1").fetchall()]
idx = {d: i for i, d in enumerate(days)}
exps = [e for (e,) in con.execute("""select expiry_dt from f.futures_bhavcopy where inst_type='FUTSTK'
    group by 1 having count(distinct underlying) > 50 order by 1""").fetchall()]
exps = [e for e in exps if e in idx]  # expired and observed
print("sessions", len(days), "monthly expiries", len(exps), exps[0], exps[-1])

OFFSETS = {"start": None, "m15": 15, "m10": 10, "m7": 7, "m5": 5, "m3": 3}
plan = []
for k in range(1, len(exps)):
    e, prev = exps[k], exps[k - 1]
    ie = idx[e]
    exit_d = days[ie - 1]
    for name, off in OFFSETS.items():
        ent = days[idx[prev] + 1] if off is None else days[ie - off]
        if idx[ent] >= ie - 1:
            continue
        plan.append((name, e, ent, exit_d, ie - idx[ent]))
plan = pd.DataFrame(plan, columns=["variant", "expiry_dt", "entry_date", "exit_date", "sess_to_exp"])
con.register("plan", plan)
con.execute("""create temp view allopt as
  select underlying, expiry_dt, strike, option_type, close, settle, contracts, val_in_lakh, open_int, trade_date from o.stock_options_bhavcopy
  union all
  select symbol, expiry_dt, strike, option_type, close, settle, contracts, val_in_lakh, open_int, trade_date from i.option_bhavcopy""")

# Front-future daily log returns, same contract, consecutive sessions.
con.execute("create temp table dtab as select * from (values " +
            ",".join(f"('{d}'::date,{i})" for d, i in idx.items()) + ") t(trade_date, di)")
con.execute("""
create temp table fret as
with c as (
  select b.underlying, b.expiry_dt, b.trade_date, d.di, b.close,
         lag(b.close) over w pc, lag(d.di) over w pdi
  from f.futures_bhavcopy b join dtab d using (trade_date)
  where b.inst_type in ('FUTSTK','FUTIDX') and b.close > 0
  window w as (partition by b.underlying, b.expiry_dt order by b.trade_date)
), front as (
  select underlying, trade_date, min(expiry_dt) fe from f.futures_bhavcopy
  where inst_type in ('FUTSTK','FUTIDX') and expiry_dt >= trade_date group by 1,2
)
select c.underlying, c.trade_date, c.di,
       case when pdi = di-1 and abs(ln(close/pc)) < 0.25 then ln(close/pc) end r,
       case when pdi = di-1 and abs(ln(close/pc)) >= 0.25 then 1 else 0 end ca_flag
from c join front on c.underlying=front.underlying and c.trade_date=front.trade_date and c.expiry_dt=front.fe
""")
con.execute("""
create temp table rv as
select underlying, trade_date, di,
  stddev_samp(r) over (partition by underlying order by di rows between 19 preceding and current row) * sqrt(252) rv20,
  count(r) over (partition by underlying order by di rows between 19 preceding and current row) n20,
  stddev_samp(r) over (partition by underlying order by di rows between 59 preceding and current row) * sqrt(252) rv60,
  count(r) over (partition by underlying order by di rows between 59 preceding and current row) n60,
  sum(r) over (partition by underlying order by di rows between 19 preceding and current row) mom20,
  sum(ca_flag) over (partition by underlying order by di rows between 59 preceding and 0 following) ca60
from fret
""")

con.execute("""
create temp table entry_legs as
select p.variant, p.expiry_dt, p.entry_date, p.exit_date, p.sess_to_exp, x.underlying, x.strike,
  max(case when option_type='CE' then close end) ce, max(case when option_type='PE' then close end) pe,
  max(case when option_type='CE' then contracts end) ce_n, max(case when option_type='PE' then contracts end) pe_n,
  sum(val_in_lakh) val_lakh, sum(open_int) oi
from plan p join allopt x on x.trade_date=p.entry_date and x.expiry_dt=p.expiry_dt
where x.contracts > 0 and x.close > 0
group by all having count(distinct option_type)=2
""")
con.execute("""
create temp table atm as
select * from (
  select l.*, fb.close fut_entry,
    row_number() over (partition by l.variant, l.expiry_dt, l.underlying order by abs(l.strike-fb.close), l.strike) rn,
    count(*) over (partition by l.variant, l.expiry_dt, l.underlying) n_strikes
  from entry_legs l join f.futures_bhavcopy fb
    on fb.inst_type in ('FUTSTK','FUTIDX') and fb.underlying=l.underlying and fb.expiry_dt=l.expiry_dt and fb.trade_date=l.entry_date
  where fb.close > 0 and (fb.inst_type='FUTSTK' or fb.underlying='NIFTY')
) where rn=1 and abs(strike/fut_entry-1) < 0.05
""")
df = con.execute("""
select a.*, fx.close fut_exit,
  max(case when x.option_type='CE' then case when x.contracts>0 then x.close else x.settle end end) ce_exit,
  max(case when x.option_type='PE' then case when x.contracts>0 then x.close else x.settle end end) pe_exit,
  max(case when x.option_type='CE' then x.contracts end) ce_exit_n,
  max(case when x.option_type='PE' then x.contracts end) pe_exit_n,
  r.rv20, r.n20, r.rv60, r.n60, r.mom20,
  (select sum(ca_flag) from fret q where q.underlying=a.underlying and q.trade_date > a.entry_date and q.trade_date <= a.exit_date) ca_in_hold
from atm a
left join allopt x on x.trade_date=a.exit_date and x.expiry_dt=a.expiry_dt and x.underlying=a.underlying and x.strike=a.strike
left join f.futures_bhavcopy fx on fx.inst_type in ('FUTSTK','FUTIDX') and fx.underlying=a.underlying and fx.expiry_dt=a.expiry_dt and fx.trade_date=a.exit_date
left join rv r on r.underlying=a.underlying and r.trade_date=a.entry_date
group by all
""").df()
print("rows", len(df))
df.to_parquet(SP + r"\stock_straddles.parquet")
print(df.groupby("variant").size())
