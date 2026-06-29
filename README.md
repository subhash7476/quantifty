# Nifty Market Data Repository

**Single source of truth** for all market data, reference data, and research datasets used by the Nifty trading platform.

---

## Directory Layout

```
F:\nifty
├── reference/                  # Static reference data (immutable)
│   ├── instrument_master/      # NSE F&O instrument master (DuckDB)
│   │   ├── latest/             # Most recent snapshot
│   │   └── archive/            # Historical snapshots
│   ├── span/                   # SPAN margin parameter files
│   │   ├── latest/             # Current trading day
│   │   └── archive/            # Historical SPAN files
│   ├── contract_specs/         # Contract specifications
│   ├── lot_sizes/              # Lot size reference
│   ├── expiries/               # Expiry calendars (weekly, monthly)
│   ├── holidays/               # NSE holiday calendars
│   └── metadata/               # Symbol lists, corporate actions, etc.
│
├── historical/                 # Historical market data (append-only)
│   ├── equity/                 # Equity cash market candles
│   ├── futures/                # Futures candles
│   ├── options/                # Options data (chain snapshots, Greeks)
│   ├── index/                  # Index candles (1d, 1m)
│   │   ├── 1d/                 # Daily NSE candles (2023–2026)
│   │   └── 1m/                 # 1-minute NSE candles (2024–2026)
│   └── mcx/                    # MCX commodity candles
│
├── tick/                       # Tick-by-tick data
│   ├── 2022/                   # 2022 ticks
│   ├── 2023/                   # 2023 ticks
│   ├── 2024/                   # 2024 ticks
│   ├── 2025/                   # 2025 ticks
│   └── 2026/                   # 2026 ticks
│
├── research/                   # Research and feature datasets
│   ├── trading/                # Trading research (day features, FTMO)
│   ├── experiments/            # Experimental data
│   ├── weather/                # Weather data (if applicable)
│   └── exports/                # Exported analysis results
│
├── examples/                   # Representative samples for AI inspection
│   ├── instrument_master/      # Instrument master sample
│   ├── option_chain/           # Option chain sample
│   ├── futures/                # Futures data sample
│   ├── tick/                   # Tick data sample
│   └── span/                   # SPAN parameter sample
│
├── cache/                      # Derived/temporary caches (ephemeral)
├── logs/                       # Processing logs
└── backups/                    # Data backups
```

---

## Naming Conventions

| Dataset | Format | Naming Pattern |
|---------|--------|----------------|
| Candle files (1d) | `{YYYY-MM-DD}.duckdb` | Date-keyed DuckDB files |
| Candle files (1m) | `{YYYY-MM-DD}.duckdb` | Same pattern, one file per day |
| Instrument master | `nse_fo_instruments.duckdb` | Single DuckDB database |
| Option chain | `options_poller.duckdb` | Polled option chain |
| SPAN files | `nse_fo_span_{YYYY-MM-DD}.parquet` | ISO-date versioned |
| Features | `{context}_{descriptor}_{year}.csv` | Descriptive names |
| FTMO/cache | `cache_{symbol}_{timeframe}.parquet` | Instrument + timeframe |

---

## Ownership

- **Instrument master**: Updated daily via `scripts/fetch_instrument_master.py`
- **SPAN parameters**: Updated daily via `scripts/fetch_span_params.py`
- **Historical candles**: Populated via `scripts/fetch_intermarket_data.py`
- **All other data**: Appended by the respective platform data pipeline

---

## Update Procedure

1. **Instrument master**: Run `python scripts/fetch_instrument_master.py` daily (validated before published).
2. **SPAN data**: Run `python scripts/fetch_span_params.py` daily during market hours.
3. **Candles**: Run `python scripts/fetch_intermarket_data.py` for incremental backfill.
4. **Manual data**: Place new datasets in the appropriate `historical/` subdirectory with ISO-date naming.

---

## Archive Policy

- **Instrument master snapshots**: Retain last 5 trading days in `reference/instrument_master/archive/`
- **SPAN files**: Retain last 90 trading days in `reference/span/archive/`
- **Historical candles**: Permanent (append-only, never deleted)
- **Tick data**: Permanent (append-only)
- **Research datasets**: Retain indefinitely in `research/trading/`

---

## Source

All data was migrated from `D:\bot\root` on 2026-06-28. The original source is preserved in place until the migration is verified.

---

## Adding New Datasets

Place new datasets in the appropriate subdirectory:

1. **Reference data** → `reference/<category>/`
2. **Historical prices** → `historical/<asset_class>/`
3. **Tick data** → `tick/<year>/`
4. **Research** → `research/<domain>/`
5. **Examples** → `examples/<category>/` (small, representative samples only)
