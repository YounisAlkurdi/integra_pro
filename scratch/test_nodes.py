import asyncio
import os
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

from backend.nodes import get_active_streams
from backend.services.database_service import db

async def test():
    user_id = "d622853e-93c5-47af-8f84-15717e3f36bd"
    print(f"Testing get_active_streams for user: {user_id}")
    
    # Ensure DB client is initialized
    if not db.client:
        print("DB client not initialized. Check .env")
        return

    nodes = await get_active_streams(user_id)
    print(f"Found {len(nodes)} active nodes")
    for node in nodes:
        print(f" - {node.get('room_id')}: {node.get('candidate_name')} (is_deleted: {node.get('is_deleted')})")

if __name__ == "__main__":
    asyncio.run(test())
