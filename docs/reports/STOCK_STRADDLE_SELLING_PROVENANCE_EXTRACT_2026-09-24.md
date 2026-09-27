# Seller-edge provenance extract (from session bfb195bb, SHA-256 326eb5eb0a068f48667bb3d14fc28914e63ad6849a3689ba03591726316bd3ae)

Tool calls touching the straddle build, 2023+ reads, or the study report, 2026-09-11 (UTC). Commands truncated to 400 chars. No market data is reproduced.

- `2026-09-11T07:18:06` PowerShell: `@' | import duckdb | c = duckdb.connect("data/market_data/options_bhavcopy.duckdb", read_only=True) | print(c.execute("select symbol, min(trade_date), max(trade_date), count(*), count(distinct expiry_dt) from option_bhavcopy group by 1").fetchall()) | c.close() | c = duckdb.connect("data/market_data/stock_options_bhavcopy.duckdb", read_only=True) | print(c.execute("select min(trade_date), max(trade_date), cou`
- `2026-09-11T07:18:44` Bash: `cd /f/Nifty && ls -la data/market_data/bhavcopy_raw | grep -E "foudiff|udiff_"; grep -rn "def \|BASE_URL\|url" scripts/sfb/ingest_stock_options_bhavcopy.py | head -40`
- `2026-09-11T07:25:30` PowerShell: `@' | import pandas as pd, numpy as np | df = pd.read_parquet(r"C:\Users\devou\AppData\Local\Temp\claude\F--Nifty\bfb195bb-d6ce-4b94-9fc4-c7d325e3a3c7\scratchpad\stock_opt_spreads.parquet") | df = df[(df.bid>0)&(df.ask>0)&df.fut_ltp.notna()].copy() | df["mid"]=(df.bid+df.ask)/2; df["rs"]=(df.ask-df.bid)/df.mid | df["mny"]=np.where(df.opt_type=="CE", df.strike/df.fut_ltp-1, 1-df.strike/df.fut_ltp)  # + = OTM | `
- `2026-09-11T07:26:21` PowerShell: `@' | import duckdb | c = duckdb.connect("data/market_data/stock_options_bhavcopy.duckdb", read_only=True) | print(c.execute("""select underlying, expiry_dt, strike, option_type, open, high, low, close, settle, contracts, open_int, trade_date |  from stock_options_bhavcopy where underlying='RELIANCE' and trade_date in ('2019-03-05','2025-03-05') and expiry_dt=(select min(expiry_dt) from stock_options_bhavc`
- `2026-09-11T07:26:39` PowerShell: `@' | import duckdb | c = duckdb.connect("data/market_data/stock_options_bhavcopy.duckdb", read_only=True) | print(c.execute("""select trade_date>='2024-07-08' u, avg((close=0)::int), avg((settle=0)::int), avg((open=0)::int) from stock_options_bhavcopy where contracts=0 and trade_date between '2019-01-01' and '2026-09-10' group by 1""").fetchall()) | print(c.execute("""select * from stock_options_bhavcopy `
- `2026-09-11T07:27:42` PowerShell: `cd F:\Nifty; Measure-Command { python "C:\Users\devou\AppData\Local\Temp\claude\F--Nifty\bfb195bb-d6ce-4b94-9fc4-c7d325e3a3c7\scratchpad\build_stock_straddles.py" | Out-Host } | Select-Object TotalSeconds`
- `2026-09-11T07:28:53` PowerShell: `cd F:\Nifty; python "C:\Users\devou\AppData\Local\Temp\claude\F--Nifty\bfb195bb-d6ce-4b94-9fc4-c7d325e3a3c7\scratchpad\analyze_stock_straddles.py" 2016-01-01 2022-12-31 2>&1 | Select-String -NotMatch "DeprecationWarning|FutureWarning|apply\(|groupby"`
- `2026-09-11T07:30:39` Bash: `cd "C:/Users/devou/AppData/Local/Temp/claude/F--Nifty/bfb195bb-d6ce-4b94-9fc4-c7d325e3a3c7/scratchpad" && python - <<'EOF' | s = open("build_stock_straddles.py").read() | s = s.replace('OFFSETS = {"start": None, "m10": 10, "m5": 5}', 'OFFSETS = {"start": None, "m15": 15, "m10": 10, "m7": 7, "m5": 5, "m3": 3}') | s = s.replace("inst_type='FUTSTK'", "inst_type in ('FUTSTK','FUTIDX')") | # restrict monthly-e`
- `2026-09-11T07:30:53` PowerShell: `cd F:\Nifty; python "C:\Users\devou\AppData\Local\Temp\claude\F--Nifty\bfb195bb-d6ce-4b94-9fc4-c7d325e3a3c7\scratchpad\build_stock_straddles.py"`
- `2026-09-11T07:32:37` PowerShell: `cd F:\Nifty; python "C:\Users\devou\AppData\Local\Temp\claude\F--Nifty\bfb195bb-d6ce-4b94-9fc4-c7d325e3a3c7\scratchpad\cycle_study.py" 2016-01-01 2022-12-31 m10 2>&1 | Select-String -NotMatch "Warning"`
- `2026-09-11T07:35:21` Write report (10613 chars)

  §4–§5 as first written at this timestamp (verbatim):

```
## 4. Pre-stated predictions for the confirmation window (written before reading 2023+)

Confirmation window: entries 2023-01-01 → 2026-08-24 (expiries through 2026-08-25). The code is
`cycle_study.py`, unchanged. Split at 2024-11-20, the SEBI F&O reform (weekly-expiry
rationalisation, higher contract sizes, expiry-day ELM). Prior exposure: none of this study's
authors has read 2023+ single-stock option returns. MSRP Phase 7 read 2023–2025 **Nifty** daily
straddles (index side only). The Skew sleeve read stock options on TRAIN only.

| # | Prediction | Pass condition |
|---|---|---|
| P1 | 10-before stock basket earns positive gross seller return | per-expiry mean > 0, t > 1.68 |
| P2 | It survives costs | net @2 % spread per-expiry mean > 0, t > 1.68 |
| P3 | The edge is late-cycle | mean gross/session of {10,7,5,3 before} > mean of {start, 15 before} |
| P4 | Positive in both regulatory sub-windows | net @2 % mean > 0 in 2023-01→2024-10 **and** in 2024-11→2026-08 (no t hurdle; n ≈ 22 each) |
| P5 | vrp60 tilts the right way | rank IC mean > 0 (t hurdle 1.68 stated, but power is only ~0.80 even at full effect) |
| P6 | Expected shrinkage | 10-before net @2 % mean lands in **+3 % to +12 %** of premium; below +3 % counts as "decayed" even if P2 passes |
| — | Stock − NIFTY gap | **no prediction** (not significant in discovery; NIFTY store ends 2026-07-17) |

A pass on P1, P2 and P4 makes this a candidate for a proper pre-registration. It does **not**
authorise trading. A fail on P2 or P4 retires it.

---

## 5. Confirmation results (2023-01 → 2026-08)

_Pending — run after §4 was saved._
```

- `2026-09-11T07:35:35` PowerShell: `cd F:\Nifty; $s="C:\Users\devou\AppData\Local\Temp\claude\F--Nifty\bfb195bb-d6ce-4b94-9fc4-c7d325e3a3c7\scratchpad\cycle_study.py"; foreach ($w in @(@("2023-01-01","2026-08-24"),@("2023-01-01","2024-11-19"),@("2024-11-20","2026-08-24"))) { Write-Output "############ $($w[0]) .. $($w[1])"; python $s $w[0] $w[1] m10 2>&1 | Select-String -NotMatch "Warning" }`
- `2026-09-11T07:37:04` Bash: `date; cd "C:/Users/devou/AppData/Local/Temp/claude/F--Nifty/bfb195bb-d6ce-4b94-9fc4-c7d325e3a3c7/scratchpad" && python - <<'EOF' | s = open("spread_snapshot.py").read() | s = s.replace('OUT = r"', 'import os\nTAG = os.environ.get("SNAP_TAG", "")\nOUT = r"').replace('stock_opt_spreads.parquet"', 'stock_opt_spreads" + TAG + ".parquet"') | s = s.replace('futs = futs[futs.expiry.isin(["2026-09-29", "2026-10`
- `2026-09-11T07:37:57` Edit report (2978 chars)
- `2026-09-11T07:40:35` Bash: `cd "C:/Users/devou/AppData/Local/Temp/claude/F--Nifty/bfb195bb-d6ce-4b94-9fc4-c7d325e3a3c7/scratchpad" && python - <<'EOF' | s = open("nifty_weekly.py").read() | old = """    s = straddle(e, e)  # DTE-0: strike chosen off prior close forward is unavailable -> use expiry-day open prices at close-nearest strike |     if s is not None and s[3] > 0 and s[4] > 0: |         K = s[0]; o = s[3] + s[4] |         row`
- `2026-09-11T07:41:07` Bash: `cd "C:/Users/devou/AppData/Local/Temp/claude/F--Nifty/bfb195bb-d6ce-4b94-9fc4-c7d325e3a3c7/scratchpad" && python - <<'EOF' | s = open("nifty_weekly.py").read() | s = s.replace('    o = on[(on.date >= lo) & (on.date <= hi)]\n', '    if on.empty: return\n    o = on[(on.date >= lo) & (on.date <= hi)]\n') | s = s.replace('cyc.to_parquet(SP + r"\\nifty_weekly_cycle.parquet"); on.to_parquet(SP + r"\\nifty_ove`
- `2026-09-11T07:44:06` PowerShell: `@' | import pandas as pd, numpy as np | SP = r"C:\Users\devou\AppData\Local\Temp\claude\F--Nifty\bfb195bb-d6ce-4b94-9fc4-c7d325e3a3c7\scratchpad" | df = pd.read_parquet(SP + r"\stock_straddles.parquet") | df["entry_date"] = pd.to_datetime(df.entry_date) | df = df[(df.underlying!="NIFTY") & (df.variant=="m10") & (df.ca_in_hold.fillna(0)==0) & df.ce_exit.notna() & df.pe_exit.notna() & (df.n60>=40)].copy() | df[`
- `2026-09-11T07:45:12` Edit report (6394 chars)
- `2026-09-11T07:46:41` Edit report (5918 chars)
- `2026-09-11T07:46:56` Edit report (206 chars)
- `2026-09-11T07:47:06` Bash: `mkdir -p scripts/research/options_seller_edge && SPD="C:/Users/devou/AppData/Local/Temp/claude/F--Nifty/bfb195bb-d6ce-4b94-9fc4-c7d325e3a3c7/scratchpad" && python - "$SPD" <<'EOF' | import sys, re, pathlib | spd = pathlib.Path(sys.argv[1]); dst = pathlib.Path("scripts/research/options_seller_edge") | old_sp = r'SP = r"C:\Users\devou\AppData\Local\Temp\claude\F--Nifty\bfb195bb-d6ce-4b94-9fc4-c7d325e3a3c7`
- `2026-09-11T07:47:52` PowerShell: `cd F:\Nifty; python scripts\research\options_seller_edge\build_stock_straddles.py; python scripts\research\options_seller_edge\cycle_study.py 2023-01-01 2026-08-24 m10 2>&1 | Select-String "m10  |  all  |break-even"`
