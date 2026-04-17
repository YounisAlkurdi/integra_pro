import time
import os
import json
from typing import Any, Dict, Optional
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

class IntegraCache:
    """
    Hybrid Cache System for SaaS Performance.
    Uses Redis if available (production), falls back to In-Memory (development).
    """
    def __init__(self):
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self.redis_client = None
        
        # Initialize Redis if configured
        redis_url = os.getenv("REDIS_URL")
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis_client.ping()
                print("=> Cache: Redis Connection Established.")
            except Exception as e:
                print(f"=> Cache Warning: Redis connection failed, falling back to memory. Error: {e}")
                self.redis_client = None

    def set(self, key: str, value: Any, ttl: int = 300):
        """Sets a value in cache with a Time-To-Live (seconds)."""
        if self.redis_client:
            try:
                # Store as JSON for complex types
                serialized = json.dumps(value)
                self.redis_client.setex(key, ttl, serialized)
                return
            except Exception as e:
                print(f"=> Cache Error: Redis set failed: {e}")

        # Fallback to memory
        self._memory_cache[key] = {
            "value": value,
            "expiry": time.time() + ttl
        }

    def get(self, key: str) -> Optional[Any]:
        """Retrieves a value if it hasn't expired."""
        if self.redis_client:
            try:
                data = self.redis_client.get(key)
                if data:
                    return json.loads(data)
                return None
            except Exception as e:
                print(f"=> Cache Error: Redis get failed: {e}")

        # Fallback to memory
        data = self._memory_cache.get(key)
        if not data:
            return None
        
        if time.time() > data["expiry"]:
            del self._memory_cache[key]
            return None
            
        return data["value"]

    def delete(self, key: str):
        """Removes an item from cache."""
        if self.redis_client:
            try:
                self.redis_client.delete(key)
                return
            except Exception as e:
                print(f"=> Cache Error: Redis delete failed: {e}")

        if key in self._memory_cache:
            del self._memory_cache[key]

    def clear(self):
        """Clears all cached items."""
        if self.redis_client:
            try:
                self.redis_client.flushdb()
                return
            except Exception as e:
                print(f"=> Cache Error: Redis flush failed: {e}")

        self._memory_cache.clear()

# Global Cache instance
integra_cache = IntegraCache()
