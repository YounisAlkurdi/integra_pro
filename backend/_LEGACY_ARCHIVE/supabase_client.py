import httpx
import json
import urllib.parse
from typing import Any, Dict, List, Optional
from .utils import get_env_safe, cache

SUPABASE_URL = get_env_safe("SUPABASE_URL")
SUPABASE_SERVICE_KEY = get_env_safe("SUPABASE_SERVICE_ROLE_KEY")

class SupabaseClient:
    """
    Unified Async Supabase Client for Integra with Caching.
    Handles REST API calls with httpx and automatic query encoding.
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

    async def request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None, use_cache: bool = False, ttl: int = 300, extra_headers: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            return []

        # Check Cache
        cache_key = f"{method}:{path}:{json.dumps(body) if body else ''}"
        if use_cache and method.upper() == "GET":
            cached_val = cache.get(cache_key)
            if cached_val is not None:
                return cached_val

        # Handle path encoding
        if '?' in path:
            parts = path.split('?', 1)
            base = parts[0]
            query = parts[1]
            encoded_query = urllib.parse.quote(query, safe='=&(),.!')
            path = f"{base}?{encoded_query}"

        url = f"{self.base_url}/{path}"
        headers = self.headers.copy()
        if extra_headers:
            headers.update(extra_headers)
        
        try:
            client = self._get_async_client()
            if method.upper() == "GET":
                response = await client.get(url, headers=headers)
            elif method.upper() == "POST":
                response = await client.post(url, headers=headers, json=body)
                cache.clear() # Clear cache on write
            elif method.upper() == "PATCH":
                response = await client.patch(url, headers=headers, json=body)
                cache.clear()
            elif method.upper() == "DELETE":
                response = await client.delete(url, headers=headers)
                cache.clear()
            else:
                response = await client.request(method.upper(), url, headers=headers, json=body)
            
            response.raise_for_status()
            result = response.json() if response.content else []
            
            # Save to Cache
            if use_cache and method.upper() == "GET":
                cache.set(cache_key, result, ttl)
                
            return result
        except Exception as e:
            print(f"=> Supabase Request Failure [{method} {path}]: {e}")
            return []

    async def get(self, table: str, query: str = "", use_cache: bool = False, ttl: int = 300) -> List[Dict[str, Any]]:
        path = f"{table}?{query}" if query else table
        return await self.request("GET", path, use_cache=use_cache, ttl=ttl)

    async def post(self, table: str, body: Dict[str, Any]) -> List[Dict[str, Any]]:
        return await self.request("POST", table, body)

    async def upsert(self, table: str, body: Dict[str, Any], on_conflict: str = "id") -> List[Dict[str, Any]]:
        path = f"{table}?on_conflict={on_conflict}"
        extra = {"Prefer": "resolution=merge-duplicates,return=representation"}
        return await self.request("POST", path, body, extra_headers=extra)

    async def patch(self, table: str, query: str, body: Dict[str, Any]) -> List[Dict[str, Any]]:
        path = f"{table}?{query}"
        return await self.request("PATCH", path, body)

# Global singleton
supabase = SupabaseClient()
