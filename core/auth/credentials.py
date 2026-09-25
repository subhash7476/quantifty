import json
import os
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Anchored to the repo so a process started from another cwd (e.g. the token
# webhook) reads and writes the same file as everything else.
DEFAULT_PATH = Path(__file__).resolve().parents[2] / "config" / "credentials.json"

# Upstox access tokens die at 03:30 local time following issue, whatever their age.
TOKEN_CUTOFF_HOUR, TOKEN_CUTOFF_MINUTE = 3, 30


def _token_expiry(saved_at: float) -> float:
    issued = datetime.fromtimestamp(saved_at)
    cutoff = issued.replace(hour=TOKEN_CUTOFF_HOUR, minute=TOKEN_CUTOFF_MINUTE,
                            second=0, microsecond=0)
    if issued >= cutoff:
        cutoff += timedelta(days=1)
    return cutoff.timestamp()

class CredentialManager:
    """
    Manages sensitive API credentials and tokens.

    GUARANTEES:
    - Centralized access to Upstox API keys and tokens.
    - Thread-safe (process-level) filesystem storage.
    - No credentials stored in version control.
    - Token expiry detection for Upstox access tokens.
    """

    def __init__(self, config_path: str = str(DEFAULT_PATH)):
        self.path = Path(config_path)
        self._cache: Dict[str, Any] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                with open(self.path, "r") as f:
                    self._cache = json.load(f)
            except Exception:
                self._cache = {}

    def save(self, data: Dict[str, Any]):
        """Persists credential data to disk. Records token_saved_at and last_refresh_date.

        Re-reads the file first: several processes hold their own instance, and
        writing a cache loaded hours ago would roll back a token another process
        saved since. The write is atomic so a concurrent reader never sees a
        half-written file.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Track when token was saved for expiry detection
        if "access_token" in data:
            now = time.time()
            data["token_saved_at"] = now
            data["last_refresh_date"] = time.strftime("%Y-%m-%d", time.localtime(now))
        self._load()
        self._cache.update(data)
        tmp = self.path.with_name(self.path.name + ".tmp")
        with open(tmp, "w") as f:
            json.dump(self._cache, f, indent=4)
        os.replace(tmp, self.path)

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a credential value."""
        return self._cache.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        return self._cache.copy()

    @property
    def has_upstox_token(self) -> bool:
        return bool(self.get("access_token"))

    @property
    def is_token_expired(self) -> bool:
        """True once the 03:30 cutoff after the token was saved has passed.

        An age rule (the old 22 h) called a 14:00 token fresh at 09:10 the next
        day, 6 h after Upstox had already killed it.
        """
        saved_at = self.get("token_saved_at")
        if not saved_at:
            # No timestamp recorded — treat as expired if token exists
            return self.has_upstox_token
        return time.time() >= _token_expiry(saved_at)

    @property
    def token_age_hours(self) -> Optional[float]:
        """Returns how many hours old the current token is, or None."""
        saved_at = self.get("token_saved_at")
        if not saved_at:
            return None
        return (time.time() - saved_at) / 3600

    @property
    def needs_daily_refresh(self) -> bool:
        """
        Check if the Upstox token needs a daily refresh.
        """
        if not self.has_upstox_token:
            return True
            
        last_date = self.get("last_refresh_date")
        current_date = time.strftime("%Y-%m-%d", time.localtime(time.time()))
        
        if last_date != current_date:
            return True
            
        return self.is_token_expired

# Singleton instance
credentials = CredentialManager()
