import asyncio
import os
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

from backend.nodes import create_neural_node, NodeProtocol
from backend.services.database_service import db

async def test():
    user_id = "d622853e-93c5-47af-8f84-15717e3f36bd"
    print(f"Testing create_neural_node for user: {user_id}")
    
    node = NodeProtocol(
        candidate_name="Test Candidate",
        candidate_email="test@example.com",
        position="Software Engineer",
        questions=["What is Python?"],
        scheduled_at="2026-05-05T12:00:00Z"
    )
    
    result = await create_neural_node(node, user_id)
    print(f"Result: {result}")
    
    # Check if it's in the DB
    if "room_id" in result:
        check = await db.select("nodes", filters={"room_id": result["room_id"]})
        if check:
            print(f"✅ Node verified in DB: {check[0]['room_id']}")
        else:
            print("❌ Node NOT found in DB after 'successful' return!")
    else:
        print("❌ Result does not contain room_id")

if __name__ == "__main__":
    asyncio.run(test())
