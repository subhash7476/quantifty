"""
Database Schema Definitions for Refactored Architecture
Matches monolithic schemas for smooth migration.
"""

# ─────────────────────────────────────────────────────────────
# MARKET DATA (DuckDB)
# ─────────────────────────────────────────────────────────────

MARKET_TICKS_SCHEMA = """
CREATE TABLE IF NOT EXISTS ticks (
    symbol VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    price DOUBLE NOT NULL,
    volume BIGINT NOT NULL,
    bid DOUBLE,
    ask DOUBLE,
    PRIMARY KEY (symbol, timestamp)
);
"""

MARKET_CANDLES_SCHEMA = """
CREATE TABLE IF NOT EXISTS candles (
    symbol VARCHAR DEFAULT '',
    instrument_key VARCHAR DEFAULT '',
    timeframe VARCHAR DEFAULT '1m',
    timestamp TIMESTAMP NOT NULL,
    open DOUBLE NOT NULL,
    high DOUBLE NOT NULL,
    low DOUBLE NOT NULL,
    close DOUBLE NOT NULL,
    volume BIGINT NOT NULL,
    is_synthetic BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (symbol, timeframe, timestamp)
);
"""

MARKET_OHLCV_RESAMPLED_SCHEMA = """
CREATE TABLE IF NOT EXISTS ohlcv_resampled (
    symbol VARCHAR NOT NULL,
    timeframe VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open DOUBLE NOT NULL,
    high DOUBLE NOT NULL,
    low DOUBLE NOT NULL,
    close DOUBLE NOT NULL,
    volume BIGINT NOT NULL,
    PRIMARY KEY (symbol, timeframe, timestamp)
);
"""

# ─────────────────────────────────────────────────────────────
# TRADING (SQLite)
# ─────────────────────────────────────────────────────────────

TRADING_TRADES_SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    trade_id TEXT PRIMARY KEY,
    signal_id TEXT UNIQUE,
    strategy_id TEXT,
    symbol TEXT,
    timestamp DATETIME,
    side TEXT,
    direction TEXT,
    entry_price DOUBLE,
    price DOUBLE,
    exit_price DOUBLE,
    quantity INTEGER,
    pnl DOUBLE,
    fees DOUBLE,
    status TEXT,
    metadata TEXT
);
"""

# ─────────────────────────────────────────────────────────────
# SIGNALS & SCANNERS (SQLite)
# ─────────────────────────────────────────────────────────────



SIGNALS_STRATEGY_SIGNALS_SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    signal_id TEXT PRIMARY KEY,
    strategy_id TEXT,
    symbol TEXT,
    signal_type TEXT,
    confidence DOUBLE,
    bar_ts DATETIME,
    status TEXT, -- 'PENDING', 'EXECUTED', 'REJECTED'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# ─────────────────────────────────────────────────────────────
# USER & CONFIG (SQLite)
# ─────────────────────────────────────────────────────────────

CONFIG_USERS_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password_hash TEXT,
    roles TEXT, -- Comma-separated
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CONFIG_ROLES_SCHEMA = """
CREATE TABLE IF NOT EXISTS roles (
    role_name TEXT PRIMARY KEY,
    permissions TEXT -- Comma-separated
);
"""

CONFIG_ROLES_SEED = """
INSERT INTO roles (role_name, permissions)
VALUES
    ('admin', 'all'),
    ('viewer', 'read')
ON CONFLICT(role_name) DO NOTHING;
"""

CONFIG_WATCHLIST_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_watchlist (
    username TEXT DEFAULT 'default',
    instrument_key TEXT NOT NULL,
    trading_symbol TEXT,
    exchange TEXT,
    market_type TEXT,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (username, instrument_key)
);
"""

CONFIG_INSTRUMENT_META_SCHEMA = """
CREATE TABLE IF NOT EXISTS instrument_meta (
    symbol TEXT PRIMARY KEY,
    trading_symbol TEXT,
    instrument_key TEXT,
    exchange TEXT,
    market_type TEXT,
    lot_size INTEGER DEFAULT 1,
    tick_size DOUBLE DEFAULT 0.05,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CONFIG_RUNNER_STATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS runner_state (
    symbol TEXT,
    strategy_id TEXT,
    timeframe TEXT DEFAULT '1m',
    current_bias TEXT,
    signal_state TEXT,
    confidence REAL,
    last_bar_ts DATETIME,
    status TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, strategy_id)
);
"""

CONFIG_WEBSOCKET_STATUS_SCHEMA = """
CREATE TABLE IF NOT EXISTS websocket_status (
    key TEXT PRIMARY KEY DEFAULT 'singleton',
    status TEXT NOT NULL,
    updated_at DATETIME NOT NULL,
    pid INTEGER
);
"""

CONFIG_FO_STOCKS_SCHEMA = """
CREATE TABLE IF NOT EXISTS fo_stocks (
    trading_symbol TEXT PRIMARY KEY,
    instrument_key TEXT NOT NULL,
    name TEXT,
    lot_size INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT 1,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# ─────────────────────────────────────────────────────────────
# BACKGROUND JOBS (SQLite)
# ─────────────────────────────────────────────────────────────

CONFIG_DOWNLOAD_JOBS_SCHEMA = """
CREATE TABLE IF NOT EXISTS download_jobs (
    job_id TEXT PRIMARY KEY,
    symbols TEXT, -- Comma-separated or 'ALL'
    unit TEXT,
    interval INTEGER,
    from_date DATE,
    to_date DATE,
    status TEXT DEFAULT 'PENDING', -- 'PENDING', 'RUNNING', 'COMPLETED', 'FAILED'
    progress TEXT, -- e.g. "5/100" or "50%"
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""





# ─────────────────────────────────────────────────────────────
# TRADE LEARNING PROTOCOL V1 (SQLite — trading.db / signals.db)
# ─────────────────────────────────────────────────────────────

TRADING_TRADE_CONTEXT_SCHEMA = """
CREATE TABLE IF NOT EXISTS trade_context (
    trade_id            TEXT PRIMARY KEY,
    model_version       TEXT DEFAULT 'TLP_V1_CORE',
    universe_version    TEXT DEFAULT 'NIFTY_UNIVERSE_V1',
    regime_state        TEXT,
    regime_confidence   REAL,
    session_type        TEXT,
    dispersion_value    REAL,
    dispersion_pct      REAL,
    volatility_value    REAL,
    volatility_pct      REAL,
    breadth_ratio       REAL,
    sl_distance         REAL,
    risk_r              REAL,
    pnl_rs              REAL,
    mae_points          REAL,
    mfe_points          REAL,
    mae_r               REAL,
    mfe_r               REAL,
    theoretical_max_pnl REAL,
    exit_efficiency     REAL,
    signal_timestamp    TEXT,
    entry_timestamp     TEXT,
    exit_timestamp      TEXT,
    created_at          TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(trade_id) REFERENCES trades(trade_id)
);
"""



# ─────────────────────────────────────────────────────────────
# OPTIONS STRUCTURAL ENGINE (DuckDB)
# ─────────────────────────────────────────────────────────────

OPTIONS_CHAIN_SNAPSHOT_SCHEMA = """
CREATE TABLE IF NOT EXISTS option_chain_snapshot (
    snapshot_id       BIGINT PRIMARY KEY,
    snapshot_timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    underlying_symbol  TEXT NOT NULL,  -- "NSE_INDEX|Nifty 50" or "NSE_INDEX|Nifty Bank"
    expiry_date        TEXT NOT NULL,  -- YYYY-MM-DD format
    strike_price       REAL NOT NULL,
    option_type        TEXT NOT NULL,  -- 'CE' or 'PE'
    instrument_key     TEXT NOT NULL,  -- Upstox key: "NSE_FO|54710"
    tradingsymbol      TEXT NOT NULL,  -- Human-readable: "NIFTY04MAR2622500CE"

    -- Price data
    ltp                REAL,           -- Last traded price
    open               REAL,
    high               REAL,
    low                REAL,
    close              REAL,

    -- OI data
    oi                 INTEGER DEFAULT 0,
    oi_change          INTEGER DEFAULT 0,
    oi_change_pct      REAL DEFAULT 0.0,
    volume             INTEGER DEFAULT 0,

    -- Greeks (from API or calculated)
    iv                 REAL,           -- Implied volatility (decimal: 0.14 = 14%)
    delta              REAL,
    gamma              REAL,
    theta              REAL,
    vega               REAL,
    rho                REAL,

    -- Metadata
    lot_size           INTEGER DEFAULT 75,
    underlying_ltp     REAL            -- Spot price at snapshot time
);
"""

OPTIONS_INDEXES_SCHEMA = """
CREATE INDEX IF NOT EXISTS idx_option_chain_underlying ON option_chain_snapshot(underlying_symbol);
CREATE INDEX IF NOT EXISTS idx_option_chain_expiry ON option_chain_snapshot(expiry_date);
CREATE INDEX IF NOT EXISTS idx_option_chain_strike ON option_chain_snapshot(strike_price);
CREATE INDEX IF NOT EXISTS idx_option_chain_timestamp ON option_chain_snapshot(snapshot_timestamp);
"""

# ─────────────────────────────────────────────────────────────
# BOOTSTRAP STATEMENTS (Combined Schema)
# ─────────────────────────────────────────────────────────────

BOOTSTRAP_STATEMENTS = [
    # Market Data (DuckDB)
    MARKET_TICKS_SCHEMA,
    MARKET_CANDLES_SCHEMA,
    MARKET_OHLCV_RESAMPLED_SCHEMA,

    # Trading (SQLite)
    TRADING_TRADES_SCHEMA,

    # Signals (SQLite)
    SIGNALS_STRATEGY_SIGNALS_SCHEMA,

    # User & Config (SQLite)
    CONFIG_USERS_SCHEMA,
    CONFIG_ROLES_SCHEMA,
    CONFIG_ROLES_SEED,
    CONFIG_WATCHLIST_SCHEMA,
    CONFIG_INSTRUMENT_META_SCHEMA,
    CONFIG_RUNNER_STATE_SCHEMA,
    CONFIG_WEBSOCKET_STATUS_SCHEMA,
    CONFIG_FO_STOCKS_SCHEMA,
    CONFIG_DOWNLOAD_JOBS_SCHEMA,

    # Trade Learning Protocol V1
    TRADING_TRADE_CONTEXT_SCHEMA,

    # Options Structural Engine
    OPTIONS_CHAIN_SNAPSHOT_SCHEMA,
]

INDEX_STATEMENTS = [
    OPTIONS_INDEXES_SCHEMA,
]
