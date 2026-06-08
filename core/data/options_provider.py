"""
Options Provider
----------------
Fetches and caches option chain data from Upstox V2 API.

Uses instrument master database for strike/expiry resolution.

Usage:
    provider = OptionsProvider()
    chain = provider.fetch_option_chain("NSE_INDEX|Nifty 50", "2026-03-04")
"""

from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import requests
import logging
import duckdb

from core.logging import setup_logger

logger = setup_logger("options_provider")


# Path to instrument master database
INSTRUMENT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "instruments" / "nse_fo_instruments.duckdb"


@dataclass
class OptionChainRow:
    """Single option contract data."""
    strike: float
    option_type: str  # 'CE' or 'PE'
    instrument_key: str
    tradingsymbol: str
    expiry: str
    
    # Price data
    ltp: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    
    # OI data
    oi: int = 0
    oi_change: int = 0
    oi_change_pct: float = 0.0
    volume: int = 0
    
    # Greeks (from API or calculated)
    iv: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None
    
    # Metadata
    lot_size: int = 75
    underlying_ltp: Optional[float] = None


@dataclass
class UnderlyingData:
    """Underlying index data."""
    instrument_key: str
    ltp: float
    change: float
    change_pct: float


class OptionsProvider:
    """
    Fetches and caches option chain data from Upstox V2 API.
    
    Architecture:
    - Single backend fetcher (5s cycle) → cache in DuckDB → consumers read from cache
    - Avoids per-client API calls
    - Supports Nifty and Banknifty indices
    """
    
    # Upstox V2 Option Chain endpoint
    OPTION_CHAIN_URL = "https://api.upstox.com/v2/option/chain"
    MARKET_QUOTE_URL = "https://api.upstox.com/v2/market-quote/quotes"
    
    # Underlying symbol mapping
    UNDERLYING_MAP = {
        "NIFTY": "NSE_INDEX|Nifty 50",
        "BANKNIFTY": "NSE_INDEX|Nifty Bank",
    }
    
    # Expiry weekday mapping (Nifty: Tuesday, Banknifty: Wednesday)
    EXPIRY_WEEKDAY = {
        "NSE_INDEX|Nifty 50": 1,      # Tuesday
        "NSE_INDEX|Nifty Bank": 2,    # Wednesday
    }
    
    def __init__(self, db_path: Optional[Path] = None, read_only: bool = False):
        """
        Initialize OptionsProvider.

        Args:
            db_path: Path to DuckDB for caching. Defaults to data/market_data/options_poller.duckdb
            read_only: If True, skip schema init and never write (for Flask readers)
        """
        self._db_path = db_path or Path("data/market_data/options_poller.duckdb")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._read_only = read_only

        # In-memory cache: key = "underlying:expiry"
        self._cache: Dict[str, List[OptionChainRow]] = {}
        self._last_fetch_time: Dict[str, datetime] = {}
        self._underlying_cache: Dict[str, UnderlyingData] = {}

        # Initialize database schema (writer only)
        if not read_only:
            self._init_db()
    
    def _init_db(self):
        """Initialize DuckDB schema for options caching."""
        # Use WAL mode for better concurrent access
        conn = duckdb.connect(str(self._db_path))
        try:
            # Create sequence first
            conn.execute("CREATE SEQUENCE IF NOT EXISTS snapshot_id_seq START 1")
            
            # Then create table with auto-increment
            conn.execute("""
                CREATE TABLE IF NOT EXISTS option_chain_snapshot (
                    snapshot_id       INTEGER DEFAULT nextval('snapshot_id_seq'),
                    snapshot_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    underlying_symbol  VARCHAR NOT NULL,
                    expiry_date        VARCHAR NOT NULL,
                    strike_price       DOUBLE NOT NULL,
                    option_type        VARCHAR NOT NULL,
                    instrument_key     VARCHAR NOT NULL,
                    tradingsymbol      VARCHAR NOT NULL,
                    ltp                DOUBLE,
                    open               DOUBLE,
                    high               DOUBLE,
                    low                DOUBLE,
                    close              DOUBLE,
                    oi                 BIGINT DEFAULT 0,
                    oi_change          BIGINT DEFAULT 0,
                    oi_change_pct      DOUBLE DEFAULT 0.0,
                    volume             BIGINT DEFAULT 0,
                    iv                 DOUBLE,
                    delta              DOUBLE,
                    gamma              DOUBLE,
                    theta              DOUBLE,
                    vega               DOUBLE,
                    rho                DOUBLE,
                    lot_size           INTEGER DEFAULT 75,
                    underlying_ltp     DOUBLE,
                    PRIMARY KEY (snapshot_id)
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_oc_underlying ON option_chain_snapshot(underlying_symbol)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_oc_expiry ON option_chain_snapshot(expiry_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_oc_strike ON option_chain_snapshot(strike_price)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_oc_timestamp ON option_chain_snapshot(snapshot_timestamp)")
            
            conn.commit()
        finally:
            conn.close()
    
    def _get_db_connection(self):
        """Get a new database connection (caller must close)."""
        return duckdb.connect(str(self._db_path), read_only=self._read_only)
    
    def fetch_option_chain(
        self,
        underlying: str,
        expiry: str,
        force_refresh: bool = False
    ) -> List[OptionChainRow]:
        """
        Fetch full option chain for given underlying and expiry.
        
        Args:
            underlying: "NSE_INDEX|Nifty 50" or "NSE_INDEX|Nifty Bank"
            expiry: YYYY-MM-DD format
            force_refresh: If True, bypass cache and fetch from API
            
        Returns:
            List of OptionChainRow dataclasses
        """
        cache_key = f"{underlying}:{expiry}"
        
        # Return cached if < 5 seconds old (unless force_refresh)
        if not force_refresh and cache_key in self._last_fetch_time:
            age = (datetime.now() - self._last_fetch_time[cache_key]).total_seconds()
            if age < 5:
                return self._cache.get(cache_key, [])
        
        # Try to fetch from API
        chain_data, underlying_data = self._fetch_from_upstox(underlying, expiry)
        
        if chain_data:
            # Update underlying cache
            if underlying_data:
                self._underlying_cache[underlying] = underlying_data
                # Attach underlying LTP to each row
                for row in chain_data:
                    row.underlying_ltp = underlying_data.ltp
            
            # Cache and persist
            self._cache[cache_key] = chain_data
            self._last_fetch_time[cache_key] = datetime.now()
            self._persist_to_duckdb(chain_data, underlying)
        else:
            # Fallback: try to load from cache (DuckDB)
            logger.warning(f"[OptionsProvider] API fetch failed, trying cache for {underlying} {expiry}")
            chain_data = self.get_cached_option_chain(underlying, expiry)
            if chain_data:
                self._cache[cache_key] = chain_data
                self._last_fetch_time[cache_key] = datetime.now()
        
        return chain_data if chain_data else []
    
    def _fetch_from_upstox(
        self, 
        underlying: str, 
        expiry: str
    ) -> Tuple[List[OptionChainRow], Optional[UnderlyingData]]:
        """
        Fetch option chain from Upstox V2 API.
        
        GET https://api.upstox.com/v2/option/chain?instrument_key={underlying}&expiry_date={expiry}
        
        Returns:
            Tuple of (option_chain_list, underlying_data)
        """
        from core.auth.credentials import credentials
        
        token = credentials.get("access_token")
        if not token:
            logger.error("[OptionsProvider] No access token found")
            return [], None
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        params = {
            "instrument_key": underlying,
            "expiry_date": expiry
        }
        
        logger.info(f"[OptionsProvider] Fetching option chain: {underlying} {expiry}")
        
        try:
            resp = requests.get(
                self.OPTION_CHAIN_URL,
                headers=headers,
                params=params,
                timeout=15
            )
            
            if resp.status_code != 200:
                logger.error(f"[OptionsProvider] API Error {resp.status_code}: {resp.text[:300]}")
                return [], None
            
            data = resp.json().get("data", {})
            return self._parse_option_chain_response(data, expiry)
            
        except requests.RequestException as e:
            logger.error(f"[OptionsProvider] Request failed: {e}")
            return [], None
    
    def _parse_option_chain_response(
        self, 
        data: dict, 
        expiry: str
    ) -> Tuple[List[OptionChainRow], Optional[UnderlyingData]]:
        """
        Parse Upstox V2 option chain response.
        
        V2 API returns data as a list directly:
        [
            {
                "expiry": "2026-03-10",
                "strike_price": 22400,
                "underlying_key": "NSE_INDEX|Nifty 50",
                "underlying_spot_price": 22450.30,
                "call_options": {...},
                "put_options": {...}
            },
            ...
        ]
        """
        # V2 API returns list directly in data field
        option_chain = data if isinstance(data, list) else data.get("data", [])
        
        # Parse underlying data from first item
        underlying_data = None
        
        if option_chain and len(option_chain) > 0:
            first = option_chain[0]
            underlying_data = UnderlyingData(
                instrument_key=first.get("underlying_key", ""),
                ltp=float(first.get("underlying_spot_price", 0)),
                change=0,
                change_pct=0
            )
        
        # Parse option chain
        chain_rows = []
        
        for strike_data in option_chain:
            strike = strike_data.get("strike_price", 0)
            underlying_ltp = strike_data.get("underlying_spot_price")
            
            # Parse CE (call_options in V2)
            call_data = strike_data.get("call_options", {})
            if call_data:
                # V2 API nests data in market_data and option_greeks
                market_data = call_data.get("market_data", {})
                option_greeks = call_data.get("option_greeks", {})
                
                ce_row = OptionChainRow(
                    strike=strike,
                    option_type="CE",
                    instrument_key=call_data.get("instrument_key", ""),
                    tradingsymbol=call_data.get("tradingsymbol", ""),
                    expiry=strike_data.get("expiry", expiry),
                    ltp=market_data.get("ltp"),
                    open=market_data.get("open"),
                    high=market_data.get("high"),
                    low=market_data.get("low"),
                    close=market_data.get("close_price"),
                    oi=int(market_data.get("oi", 0) or 0),
                    oi_change=int((market_data.get("oi", 0) or 0) - (market_data.get("prev_oi", 0) or 0)),
                    oi_change_pct=0.0,  # Calculate if needed
                    volume=market_data.get("volume", 0),
                    iv=option_greeks.get("iv"),
                    delta=option_greeks.get("delta"),
                    gamma=option_greeks.get("gamma"),
                    theta=option_greeks.get("theta"),
                    vega=option_greeks.get("vega"),
                    rho=None,  # Not provided by Upstox
                    lot_size=call_data.get("lot_size", 75),
                    underlying_ltp=underlying_ltp
                )
                chain_rows.append(ce_row)
            
            # Parse PE (put_options in V2)
            put_data = strike_data.get("put_options", {})
            if put_data:
                market_data = put_data.get("market_data", {})
                option_greeks = put_data.get("option_greeks", {})
                
                pe_row = OptionChainRow(
                    strike=strike,
                    option_type="PE",
                    instrument_key=put_data.get("instrument_key", ""),
                    tradingsymbol=put_data.get("tradingsymbol", ""),
                    expiry=strike_data.get("expiry", expiry),
                    ltp=market_data.get("ltp"),
                    open=market_data.get("open"),
                    high=market_data.get("high"),
                    low=market_data.get("low"),
                    close=market_data.get("close_price"),
                    oi=int(market_data.get("oi", 0) or 0),
                    oi_change=int((market_data.get("oi", 0) or 0) - (market_data.get("prev_oi", 0) or 0)),
                    oi_change_pct=0.0,
                    volume=market_data.get("volume", 0),
                    iv=option_greeks.get("iv"),
                    delta=option_greeks.get("delta"),
                    gamma=option_greeks.get("gamma"),
                    theta=option_greeks.get("theta"),
                    vega=option_greeks.get("vega"),
                    rho=None,
                    lot_size=put_data.get("lot_size", 75),
                    underlying_ltp=underlying_ltp
                )
                chain_rows.append(pe_row)
        
        return chain_rows, underlying_data
    
    def _persist_to_duckdb(self, chain: List[OptionChainRow], underlying: str = ""):
        """Persist option chain to DuckDB cache."""
        if not chain or self._read_only:
            return

        conn = self._get_db_connection()
        try:
            for row in chain:
                conn.execute("""
                    INSERT INTO option_chain_snapshot (
                        underlying_symbol, expiry_date, strike_price, option_type,
                        instrument_key, tradingsymbol, ltp, open, high, low, close,
                        oi, oi_change, oi_change_pct, volume,
                        iv, delta, gamma, theta, vega, rho,
                        lot_size, underlying_ltp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    underlying,
                    row.expiry,
                    row.strike,
                    row.option_type,
                    row.instrument_key,
                    row.tradingsymbol,
                    row.ltp,
                    row.open,
                    row.high,
                    row.low,
                    row.close,
                    row.oi if row.oi else 0,
                    row.oi_change if row.oi_change else 0,
                    row.oi_change_pct if row.oi_change_pct else 0.0,
                    row.volume if row.volume else 0,
                    row.iv,
                    row.delta,
                    row.gamma,
                    row.theta,
                    row.vega,
                    row.rho,
                    row.lot_size,
                    row.underlying_ltp
                ])
            
            conn.commit()
        except Exception as e:
            logger.error(f"[OptionsProvider] Failed to persist to DuckDB: {e}")
        finally:
            conn.close()
    
    def get_cached_option_chain(
        self,
        underlying: str,
        expiry: str
    ) -> List[OptionChainRow]:
        """
        Get cached option chain from memory or DuckDB.
        Uses URI mode for better concurrent access.
        """
        cache_key = f"{underlying}:{expiry}"
        
        # Check memory cache first
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Fall back to DuckDB
        conn = None
        try:
            conn = self._get_db_connection()
            result = conn.execute("""
                SELECT
                    strike_price, option_type, instrument_key, tradingsymbol, expiry_date,
                    ltp, open, high, low, close,
                    oi, oi_change, oi_change_pct, volume,
                    iv, delta, gamma, theta, vega, rho,
                    lot_size, underlying_ltp
                FROM option_chain_snapshot
                WHERE underlying_symbol = ? AND expiry_date = ?
                ORDER BY strike_price, option_type
            """, [underlying, expiry]).fetchall()

            chain = []
            for row in result:
                chain.append(OptionChainRow(
                    strike=row[0],
                    option_type=row[1],
                    instrument_key=row[2],
                    tradingsymbol=row[3],
                    expiry=row[4],
                    ltp=row[5],
                    open=row[6],
                    high=row[7],
                    low=row[8],
                    close=row[9],
                    oi=row[10],
                    oi_change=row[11],
                    oi_change_pct=row[12],
                    volume=row[13],
                    iv=row[14],
                    delta=row[15],
                    gamma=row[16],
                    theta=row[17],
                    vega=row[18],
                    rho=row[19],
                    lot_size=row[20],
                    underlying_ltp=row[21]
                ))

            # Cache in memory
            if chain:
                self._cache[cache_key] = chain

            return chain
        except Exception as e:
            logger.warning(f"[OptionsProvider] Failed to read cache from DuckDB: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_weekly_expiry(
        self, 
        underlying: str, 
        as_of_date: Optional[date] = None
    ) -> str:
        """
        Get the nearest weekly expiry date for given index.
        Uses instrument master if available, otherwise calculates.
        """
        # Map underlying to index name
        index_map = {
            "NSE_INDEX|Nifty 50": "NIFTY",
            "NSE_INDEX|Nifty Bank": "BANKNIFTY",
        }
        index_name = index_map.get(underlying)
        
        if index_name and INSTRUMENT_DB_PATH.exists():
            # Get actual expiries from instrument master
            try:
                conn = duckdb.connect(str(INSTRUMENT_DB_PATH), read_only=True)
                result = conn.execute("""
                    SELECT DISTINCT expiry FROM instruments
                    WHERE name = ? AND instrument_type = 'CE' AND expiry >= ?
                      AND snapshot_date = (SELECT MAX(snapshot_date) FROM instruments)
                    ORDER BY expiry LIMIT 1
                """, [index_name, (as_of_date or date.today()).isoformat()]).fetchone()
                conn.close()
                if result and result[0]:
                    return result[0]
            except Exception:
                pass
        
        # Fallback to calculated expiry
        as_of = as_of_date or date.today()
        expiry_weekday = self.EXPIRY_WEEKDAY.get(underlying, 1)
        target = as_of + timedelta(days=1)
        days_ahead = (expiry_weekday - target.weekday()) % 7
        expiry = target + timedelta(days=days_ahead)
        return expiry.strftime("%Y-%m-%d")
    
    def get_available_expiries(
        self,
        underlying: str,
        count: int = 4
    ) -> List[str]:
        """Get list of available weekly expiry dates."""
        expiries = []
        current = date.today()
        for _ in range(count):
            expiry = self.get_weekly_expiry(underlying, current)
            expiries.append(expiry)
            current = datetime.strptime(expiry, "%Y-%m-%d").date() + timedelta(days=7)
        return expiries
    
    def get_underlying_ltp(self, underlying: str) -> Optional[float]:
        """Get cached underlying LTP."""
        if underlying in self._underlying_cache:
            return self._underlying_cache[underlying].ltp
        return None
    
    def get_index(self, index_name: str) -> str:
        """Map index name to underlying symbol."""
        return self.UNDERLYING_MAP.get(index_name.upper(), "")

    def get_available_strikes(
        self,
        index_name: str,
        expiry: str
    ) -> List[float]:
        """Get available strikes for an index and expiry from instrument master."""
        name_map = {"NIFTY": "NIFTY", "BANKNIFTY": "BANKNIFTY"}
        name = name_map.get(index_name.upper())
        if not name:
            return []

        if not INSTRUMENT_DB_PATH.exists():
            return []

        try:
            conn = duckdb.connect(str(INSTRUMENT_DB_PATH), read_only=True)
            result = conn.execute("""
                SELECT DISTINCT strike FROM instruments
                WHERE name = ? AND expiry = ? AND instrument_type = 'CE'
                  AND snapshot_date = (SELECT MAX(snapshot_date) FROM instruments)
                ORDER BY strike
            """, [name, expiry]).fetchall()
            conn.close()
            return [row[0] for row in result]
        except Exception as e:
            logger.error(f"[OptionsProvider] Failed to get strikes: {e}")
            return []

    def get_lot_size(self, index_name: str) -> int:
        """Get lot size for an index from instrument master."""
        name_map = {"NIFTY": "NIFTY", "BANKNIFTY": "BANKNIFTY"}
        name = name_map.get(index_name.upper())
        if not name:
            return 75

        if not INSTRUMENT_DB_PATH.exists():
            return 75

        try:
            conn = duckdb.connect(str(INSTRUMENT_DB_PATH), read_only=True)
            result = conn.execute("""
                SELECT DISTINCT lot_size FROM instruments
                WHERE name = ? AND instrument_type = 'CE'
                  AND snapshot_date = (SELECT MAX(snapshot_date) FROM instruments)
                LIMIT 1
            """, [name]).fetchone()
            conn.close()
            return result[0] if result else 75
        except Exception:
            return 75

    def get_expiry_list(
        self,
        index_name: str,
        count: int = 4
    ) -> List[str]:
        """Get available expiries from instrument master."""
        name_map = {"NIFTY": "NIFTY", "BANKNIFTY": "BANKNIFTY"}
        name = name_map.get(index_name.upper())
        if not name:
            return []

        if not INSTRUMENT_DB_PATH.exists():
            return self.get_available_expiries(self.UNDERLYING_MAP.get(index_name, ""), count)

        try:
            conn = duckdb.connect(str(INSTRUMENT_DB_PATH), read_only=True)
            result = conn.execute("""
                SELECT DISTINCT expiry FROM instruments
                WHERE name = ? AND instrument_type = 'CE'
                  AND snapshot_date = (SELECT MAX(snapshot_date) FROM instruments)
                ORDER BY expiry LIMIT ?
            """, [name, count]).fetchall()
            conn.close()
            return [row[0] for row in result]
        except Exception:
            return self.get_available_expiries(self.UNDERLYING_MAP.get(index_name, ""), count)
