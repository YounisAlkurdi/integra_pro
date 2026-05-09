import os
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from supabase.client import AsyncClient, ClientOptions
from backend.utils import get_env_safe

class DatabaseService:
    _instance: Optional['DatabaseService'] = None
    client: AsyncClient = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseService, cls).__new__(cls)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        url = get_env_safe("SUPABASE_URL")
        key = get_env_safe("SUPABASE_SERVICE_ROLE_KEY")
        
        if not url or not key:
            print("⚠️ Database Service: Missing Supabase credentials. Async client disabled.")
            return

        try:
            # Note: supabase-py v2.x create_client supports async if used correctly
            # We use AsyncClient specifically for our service layer
            self.client = AsyncClient(url, key, options=ClientOptions(postgrest_client_timeout=10))
            print("⚡ Database Service: Neural Link (Async) Established.")
        except Exception as e:
            print(f"❌ Database Service: Initialization failed: {e}")

    async def select(self, table: str, columns: str = "*", filters: Dict[str, Any] = None, order: str = None, desc: bool = True, limit: int = None) -> List[Dict[str, Any]]:
        """Generic async select operation."""
        if not self.client: return []
        
        try:
            query = self.client.table(table).select(columns)
            
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            if order:
                query = query.order(order, desc=desc)
            
            if limit:
                query = query.limit(limit)
                
            response = await query.execute()
            return response.data
        except Exception as e:
            print(f"❌ DB Select Error [{table}]: {e}")
            return []

    async def insert(self, table: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generic async insert operation."""
        if not self.client: return None
        
        try:
            response = await self.client.table(table).insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"❌ DB Insert Error [{table}]: {e}")
            return None

    async def update(self, table: str, data: Dict[str, Any], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generic async update operation."""
        if not self.client: return []
        
        try:
            query = self.client.table(table).update(data)
            for key, value in filters.items():
                query = query.eq(key, value)
            
            response = await query.execute()
            return response.data
        except Exception as e:
            print(f"❌ DB Update Error [{table}]: {e}")
            return []

    async def upsert(self, table: str, data: Dict[str, Any], on_conflict: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Generic async upsert operation."""
        if not self.client: return None
        
        try:
            query = self.client.table(table).upsert(data, on_conflict=on_conflict)
            response = await query.execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"❌ DB Upsert Error [{table}]: {e}")
            return None

# Global Singleton Instance
db = DatabaseService()
