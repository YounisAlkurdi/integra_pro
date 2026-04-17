import os
from typing import Any, Optional
import time

def get_env_safe(key: str, default: Any = None) -> Any:
    """Safely retrieve environment variables."""
    val = os.getenv(key)
    if val is None:
        if default is not None:
            return default
        return ""
    return val

class NeuralCache:
    """Simple TTL-based cache for expensive operations."""
    def __init__(self):
        self._data = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._data:
            entry = self._data[key]
            if time.time() < entry["expiry"]:
                return entry["value"]
            else:
                del self._data[key]
        return None

    def set(self, key: str, value: Any, ttl: int = 300):
        self._data[key] = {
            "value": value,
            "expiry": time.time() + ttl
        }

    def clear(self):
        self._data = {}

# Global cache instance
cache = NeuralCache()
