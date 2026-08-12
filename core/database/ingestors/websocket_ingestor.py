import asyncio
import json
import logging
import threading
import websockets
import pytz
from typing import List

logger = logging.getLogger(__name__)

IST = pytz.timezone('Asia/Kolkata')


class WebSocketIngestor:
    """
    Stateless WebSocket ingestor for Upstox V3.
    Enqueues raw frames to the LiveBufferWriter; never parses or writes on the loop.
    """

    WSS_URL = "wss://api.upstox.com/v3/feed/market-data-feed"
    
    def __init__(self, symbols: List[str], access_token: str, writer,
                 ping_interval: float = 10.0, ping_timeout: float = 30.0):
        self.symbols = symbols
        self.access_token = access_token
        self.writer = writer
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self._is_running = False
        self._loop = None
        self._thread = None
        
    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self):
        """Starts the ingestion in a background thread."""
        if self._is_running:
            return
        self._is_running = True
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()
        logger.info(f"WebSocketIngestor started for symbols: {self.symbols}")
        
    def stop(self):
        """Stops the ingestion."""
        self._is_running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("WebSocketIngestor stopped.")

    def _run_event_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connect_and_ingest())
        except Exception as e:
            logger.error(f"Ingestor loop failure: {e}", exc_info=True)
        finally:
            self._loop.close()

    async def _get_authorized_url(self):
        """Fetches the dynamic authorized WebSocket URL from Upstox."""
        import requests
        url = "https://api.upstox.com/v3/feed/market-data-feed/authorize"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.raise_for_status()
            data = res.json()
            return data['data']['authorized_redirect_uri']
        except Exception as e:
            logger.error(f"Failed to get authorized WS URL: {e}")
            return None

    async def _connect_and_ingest(self):
        backoff = 1.0
        while self._is_running:
            try:
                wss_url = await self._get_authorized_url()
                if not wss_url:
                    logger.error(f"Could not authorize WebSocket. Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                    backoff = min(60.0, backoff * 2)
                    continue

                async with websockets.connect(
                    wss_url, ping_interval=self.ping_interval, ping_timeout=self.ping_timeout
                ) as ws:
                    logger.info("Connected to Upstox Authorized WebSocket Feed.")
                    backoff = 1.0 
                    
                    subscribe_msg = {
                        "guid": "trading_bot_ingestor",
                        "method": "sub",
                        "data": {
                            "mode": "full",
                            "instrumentKeys": self.symbols
                        }
                    }
                    await ws.send(json.dumps(subscribe_msg).encode('utf-8'))
                    
                    async for message in ws:
                        if not self._is_running:
                            break
                        
                        if isinstance(message, bytes):
                            self._handle_message(message)
                        
            except Exception as e:
                if self._is_running:
                    logger.error(f"WebSocket connection error: {e}. Reconnecting in {backoff}s...")
                    await asyncio.sleep(backoff)
                    backoff = min(60.0, backoff * 2)
                else:
                    break

    def _handle_message(self, message: bytes):
        self.writer.enqueue_frame(message)
