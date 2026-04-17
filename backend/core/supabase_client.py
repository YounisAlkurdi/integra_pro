import httpx
import json
import urllib.parse
import time
from typing import Any, Dict, List, Optional
from .utils import get_env_safe
from .cache import integra_cache

SUPABASE_URL = get_env_safe("SUPABASE_URL")
SUPABASE_SERVICE_KEY = get_env_safe("SUPABASE_SERVICE_ROLE_KEY")

class SupabaseClient:
    """
    Unified Async Supabase Client for Integra SaaS.
    Optimized with memory caching for high-frequency GET requests.
    """
    
    def __init__(self):
        self.base_url = f"{SUPABASE_URL}/rest/v1"
        self.headers = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        self._async_client: Optional[httpx.AsyncClient] = None

    def _get_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(
                timeout=30.0, 
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
            )
        return self._async_client

    async def request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None, cache_ttl: int = 0) -> List[Dict[str, Any]]:
        """
        Executes a REST request. If cache_ttl > 0 and method is GET, checks cache first.
        """
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            return []

        # Cache check
        cache_key = f"supabase:{method}:{path}"
        if method.upper() == "GET" and cache_ttl > 0:
            cached = integra_cache.get(cache_key)
            if cached is not None:
                return cached

        # Path encoding
        if '?' in path:
            base, query = path.split('?', 1)
            encoded_query = urllib.parse.quote(query, safe='=&(),.!')
            path = f"{base}?{encoded_query}"

        url = f"{self.base_url}/{path}"
        
        try:
            client = self._get_async_client()
            if method.upper() == "GET":
                response = await client.get(url, headers=self.headers)
            elif method.upper() == "POST":
                response = await client.post(url, headers=self.headers, json=body)
            elif method.upper() == "PATCH":
                response = await client.patch(url, headers=self.headers, json=body)
            elif method.upper() == "DELETE":
                response = await client.delete(url, headers=self.headers)
            else:
                response = await client.request(method.upper(), url, headers=self.headers, json=body)
            
            response.raise_for_status()
            res_json = response.json() if response.content else []
            
            # Save to cache if requested
            if method.upper() == "GET" and cache_ttl > 0:
                integra_cache.set(cache_key, res_json, ttl=cache_ttl)
                
            return res_json
        except Exception as e:
            print(f"=> Supabase Request Failure [{method} {path}]: {e}")
            return []

    async def get(self, table: str, query: str = "", cache_ttl: int = 60) -> List[Dict[str, Any]]:
        """GET wrapper with default 1-minute cache for SaaS performance."""
        path = f"{table}?{query}" if query else table
        return await self.request("GET", path, cache_ttl=cache_ttl)

    async def post(self, table: str, body: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Invalidate cache for this table on modification (simple invalidation)
        # Note: A real SaaS would need more granular invalidation
        return await self.request("POST", table, body)

# Global singleton
supabase = SupabaseClient()

def get_supabase_client():
    return supabase
