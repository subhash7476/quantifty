from typing import Dict, Optional, List
from datetime import datetime, timedelta
from core.events import OHLCVBar

class TickAggregator:
    """
    Aggregates ticks into 1-minute OHLCV bars.
    
    GUARANTEES:
    - Deterministic aggregation.
    - Explicit bar-close detection based on tick timestamps.
    - Preserves OHLCV integrity.
    """
    
    def __init__(self):
        # symbol -> current open bar data
        self._current_bars: Dict[str, Dict] = {}
        
    def add_tick(self, symbol: str, timestamp: datetime, price: float, volume: float) -> Optional[OHLCVBar]:
        """
        Adds a tick and returns a completed bar if the minute has rolled over.
        """
        bar_start_time = timestamp.replace(second=0, microsecond=0)
        
        completed_bar = None
        
        if symbol in self._current_bars:
            current = self._current_bars[symbol]
            
            if bar_start_time > current['timestamp']:
                # Minute rolled over, complete the previous bar
                completed_bar = OHLCVBar(
                    symbol=symbol,
                    timestamp=current['timestamp'],
                    open=current['open'],
                    high=current['high'],
                    low=current['low'],
                    close=current['close'],
                    volume=current['volume']
                )
                # Start new bar
                self._current_bars[symbol] = {
                    'timestamp': bar_start_time,
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': volume
                }
            else:
                # Update current bar
                current['high'] = max(current['high'], price)
                current['low'] = min(current['low'], price)
                current['close'] = price
                current['volume'] += volume
        else:
            # First tick for this symbol
            self._current_bars[symbol] = {
                'timestamp': bar_start_time,
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': volume
            }
            
        return completed_bar

    def force_close_all(self) -> List[OHLCVBar]:
        """Closes all currently open bars (e.g. at market close)."""
        bars = []
        for symbol, current in self._current_bars.items():
            bars.append(OHLCVBar(
                symbol=symbol,
                timestamp=current['timestamp'],
                open=current['open'],
                high=current['high'],
                low=current['low'],
                close=current['close'],
                volume=current['volume']
            ))
        self._current_bars.clear()
        return bars
