import duckdb
from datetime import datetime

con = duckdb.connect('data/market_data/equity_bhavcopy.duckdb', read_only=True)
cal = con.execute("SELECT trade_date FROM trading_calendar WHERE n_symbols >= 200 ORDER BY trade_date").fetchall()
dates = [r[0] for r in cal]

start_dt = datetime(2020, 9, 4).date()
end_dt = datetime(2022, 12, 31).date()
sealed_start = datetime(2023, 1, 1).date()
sealed_end = datetime(2026, 6, 30).date()

def count_grid(dates, start, end, rule):
    grid = []
    for idx, d in enumerate(dates):
        if d < start or d > end:
            continue
        if rule == 'fortnightly':
            is_mid = d.day <= 15
            is_eom = False
            if idx + 1 >= len(dates) or dates[idx+1].month != d.month:
                is_eom = True
            if is_mid:
                next_idx = idx + 1
                is_last_mid = True
                if next_idx < len(dates) and dates[next_idx].month == d.month and dates[next_idx].day <= 15:
                    is_last_mid = False
                if is_last_mid:
                    grid.append(d)
            if is_eom:
                grid.append(d)
        elif rule == 'monthly':
            is_eom = False
            if idx + 1 >= len(dates) or dates[idx+1].month != d.month:
                is_eom = True
            if is_eom:
                grid.append(d)
    return grid

# C2/C3 dev window
fg = count_grid(dates, start_dt, end_dt, 'fortnightly')
mid = [d for d in fg if d.day <= 15]
eom = [d for d in fg if d.day > 15]
print(f"C2/C3 dev fortnightly grid dates (2020-09-04 to 2022-12-31): {len(fg)}")
print(f"  Mid-month: {len(mid)}, Month-end: {len(eom)}")
print(f"  First: {fg[0]}, Last: {fg[-1]}")

# Sealed window n*
sealed_fg = count_grid(dates, sealed_start, sealed_end, 'fortnightly')
print(f"\nC2/C3 sealed n* (fortnightly, 2023-01-01 to 2026-06-30): {len(sealed_fg)}")
sealed_mg = count_grid(dates, sealed_start, sealed_end, 'monthly')
print(f"C4 sealed n* (monthly, 2023-01-01 to 2026-06-30): {len(sealed_mg)}")

# Also count C4 dev window monthly grid dates
dev_mg = count_grid(dates, start_dt, end_dt, 'monthly')
print(f"\nC4 dev monthly grid dates (2020-09-04 to 2022-12-31): {len(dev_mg)}")
full_dev_mg = count_grid(dates, datetime(2012, 1, 1).date(), end_dt, 'monthly')
print(f"C4 dev monthly grid dates (2012-01-01 to 2022-12-31): {len(full_dev_mg)}")

con.close()
