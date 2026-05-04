import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.services.memory_service import SupabaseChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage

async def test_memory():
    user_id = "00000000-0000-0000-0000-000000000000" # Test UUID
    print(f"Testing memory for user: {user_id}")
    
    history = SupabaseChatMessageHistory(user_id)
    
    # 1. Load existing
    messages = await history.aload_messages()
    print(f"Loaded {len(messages)} messages.")
    
    # 2. Add new
    print("Adding test messages...")
    await history.aadd_messages([
        HumanMessage(content="Hello, this is a test."),
        AIMessage(content="I hear you loud and clear.")
    ])
    
    # 3. Verify
    new_messages = await history.aload_messages()
    print(f"After update, loaded {len(new_messages)} messages.")
    
    for m in new_messages[-2:]:
        role = "Human" if isinstance(m, HumanMessage) else "AI"
        print(f"[{role}]: {m.content}")

if __name__ == "__main__":
    asyncio.run(test_memory())
