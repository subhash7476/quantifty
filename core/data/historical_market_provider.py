"""
Historical Market Data Provider
-----------------------------
Reads historical OHLCV data from DuckDB for backtesting.
"""
from typing import List, Optional, Tuple
from datetime import datetime
from core.data.market_data_provider import MarketDataProvider
from core.data.duckdb_market_data_provider import DuckDBMarketDataProvider
from core.events import OHLCVBar

class HistoricalMarketProvider(DuckDBMarketDataProvider):
    """
    Standard historical data provider. 
    Inherits from DuckDBMarketDataProvider for the heavy lifting.
    """
    def __init__(
        self, 
        symbols: List[str], 
        start_time: datetime, 
        end_time: datetime,
        db_path: str = "data/trading_bot.duckdb"
    ):
        super().__init__(
            symbols=symbols,
            db_path=db_path,
            start_time=start_time,
            end_time=end_time
        )
