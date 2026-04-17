import httpx
import json
import urllib.parse
from typing import Any, Dict, List, Optional
from utils import get_env_safe

SUPABASE_URL = get_env_safe("SUPABASE_URL")
SUPABASE_SERVICE_KEY = get_env_safe("SUPABASE_SERVICE_ROLE_KEY")

class SupabaseClient:
    """
    Unified Async Supabase Client for Integra.
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
            self._async_client = httpx.AsyncClient(timeout=30.0, limits=httpx.Limits(max_connections=100, max_keepalive_connections=20))
        return self._async_client

    async def request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            print("=> Supabase Client Error: Missing credentials in .env")
            return []

        # Handle path encoding for complex filters
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
            return response.json() if response.content else []
        except Exception as e:
            print(f"=> Supabase Request Failure [{method} {path}]: {e}")
            return []

    def request_sync(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Synchronous version of request for legacy integrations."""
        import requests
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            return []

        if '?' in path:
            base, query = path.split('?', 1)
            encoded_query = urllib.parse.quote(query, safe='=&(),.!')
            path = f"{base}?{encoded_query}"

        url = f"{self.base_url}/{path}"
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers, timeout=30)
            else:
                response = requests.request(method.upper(), url, headers=self.headers, json=body, timeout=30)
            
            response.raise_for_status()
            return response.json() if response.content else []
        except Exception as e:
            print(f"=> Supabase Sync Request Failure [{method} {path}]: {e}")
            return []

    async def get(self, table: str, query: str = "") -> List[Dict[str, Any]]:
        path = f"{table}?{query}" if query else table
        return await self.request("GET", path)

    def get_sync(self, table: str, query: str = "") -> List[Dict[str, Any]]:
        path = f"{table}?{query}" if query else table
        return self.request_sync("GET", path)

    async def post(self, table: str, body: Dict[str, Any]) -> List[Dict[str, Any]]:
        return await self.request("POST", table, body)

    async def patch(self, table: str, query: str, body: Dict[str, Any]) -> List[Dict[str, Any]]:
        path = f"{table}?{query}"
        return await self.request("PATCH", path, body)

# Global singleton
supabase = SupabaseClient()
