"""ISD battery unit tests — synthetic fixtures only, no stores, no network."""
import numpy as np
import pytest

from scripts.isd.battery_features import MIN_NAMES


def _noise_feat_label(n_s, n_c, seed=7, rho=0.0):
    rng = np.random.default_rng(seed)
    f = rng.standard_normal((n_s, n_c))
    l = rng.standard_normal((n_s, n_c))
    if rho > 0:
        l = rho * f + np.sqrt(1 - rho**2) * l
    return f, l


def test_series_stats_nw_t_less_than_plain_under_ar1():
    from scripts.isd.battery_stats import series_stats
    rng = np.random.default_rng(3)
    x = np.zeros(400)
    e = rng.standard_normal(400)
    for i in range(1, 400):
        x[i] = 0.6 * x[i - 1] + 0.02 + e[i]          # positive drift + AR1
    st = series_stats(x)
    assert st["ac1"] > 0.3
    assert st["t_nw"] < st["t_plain"]                  # NW corrects inflation


def test_random_entry_null_zero_mean_under_pure_noise():
    from scripts.isd.battery_stats import random_entry_null
    f, l = _noise_feat_label(200, 80)
    rng = np.random.default_rng(11)
    nulls = random_entry_null(f, l, rng, iters=500)
    assert abs(nulls.mean()) < 0.01                     # null centered at zero
    assert nulls.std() > 1e-4


def test_random_entry_null_detects_signal():
    from scripts.isd.battery_stats import empirical_p, random_entry_null
    f, l = _noise_feat_label(200, 80, rho=0.15)         # planted correlation
    rng = np.random.default_rng(12)
    ic = np.array([np.corrcoef(f[i], l[i])[0, 1] for i in range(200)])
    nulls = random_entry_null(f, l, rng, iters=500)
    assert empirical_p(float(ic.mean()), nulls, +1) < 0.05


def test_per_session_ic_respects_min_names():
    from scripts.isd.battery_stats import per_session_ic
    f, l = _noise_feat_label(10, 50)
    f[3, 19:] = np.nan                                  # session 3 too thin (19 < 20)
    ic = per_session_ic(f, l)
    assert np.isnan(ic[3])
    assert not np.isnan(ic[0])


def test_net_spread_arithmetic():
    from scripts.isd.battery_stats import net_spread_series
    gross = np.array([100.0, -50.0])
    net = net_spread_series(gross, np.array([2.7, 2.7]), np.array([4.5, 4.5]))
    assert net[0] == pytest.approx(100 - 2 * 2.7 - 4.5)
    assert net[1] == pytest.approx(-50 - 2 * 2.7 - 4.5)


def test_f1_feature_nonzero_and_label_no_overlap():
    import pandas as pd
    from scripts.isd.battery_features import session_frame
    rows = [
        ("NSE_EQ|INE000AAA", "2024-01-05 09:15:00", 100.0, 101.0, 99.0, 100.0, 10),
        ("NSE_EQ|INE000AAA", "2024-01-05 09:45:00", 102.0, 102.5, 101.5, 102.0, 10),
        ("NSE_EQ|INE000AAA", "2024-01-05 09:46:00", 102.0, 103.0, 101.0, 102.5, 10),
        ("NSE_EQ|INE000AAA", "2024-01-05 10:00:00", 104.0, 104.5, 103.5, 104.0, 10),
        ("NSE_EQ|INE000AAA", "2024-01-05 10:01:00", 104.0, 105.0, 103.0, 104.5, 10),
        ("NSE_EQ|INE000AAA", "2024-01-05 15:29:00", 106.0, 107.0, 105.0, 106.0, 10),
    ]
    import duckdb
    p = tmp_db(rows)
    fr = session_frame(str(p))
    row = fr.loc["NSE_EQ|INE000AAA"]
    feat_w1000 = (row["close1000"] - row["open0915"]) / row["open0915"]
    assert feat_w1000 == pytest.approx(0.04)             # (104-100)/100
    label = (row["close1529"] - row["open1001"]) / row["open1001"]
    assert label == pytest.approx((106 - 104) / 104)     # entry 10:01, no overlap


def tmp_db(rows):
    import tempfile
    from pathlib import Path
    import duckdb
    d = Path(tempfile.mkdtemp())
    p = d / "day.duckdb"
    con = duckdb.connect(str(p))
    con.execute("create table candles (symbol VARCHAR, instrument_key VARCHAR,"
                " timeframe VARCHAR, timestamp TIMESTAMP, open DOUBLE,"
                " high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT,"
                " is_synthetic BOOLEAN)")
    for r in rows:
        con.execute("insert into candles values (?, '', '1m', ?, ?, ?, ?, ?, ?,"
                    " false)", list(r))
    con.close()
    return p
