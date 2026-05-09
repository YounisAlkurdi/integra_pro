from typing import List
# pyrefly: ignore [missing-import]
from langchain_core.chat_history import BaseChatMessageHistory
# pyrefly: ignore [missing-import]
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from backend.services.database_service import db

class SupabaseChatMessageHistory(BaseChatMessageHistory):
    """
    Asynchronous Chat Message History backed by Supabase.
    Integrates directly with the Integra DatabaseService.
    """
    
    def __init__(self, user_id: str, limit: int = 50):
        self.user_id = user_id
        self.limit = limit
        self._messages: List[BaseMessage] = []

    async def aload_messages(self) -> List[BaseMessage]:
        """Loads the last N messages from Supabase asynchronously."""
        try:
            res = await db.select(
                table="agent_memories",
                filters={"user_id": self.user_id},
                order="created_at",
                desc=False, # We want chronological order
                limit=self.limit
            )
            
            new_messages = []
            for entry in res:
                role = entry.get("role", "human").lower()
                content = entry.get("content", "")
                if role == "human":
                    new_messages.append(HumanMessage(content=content))
                else:
                    new_messages.append(AIMessage(content=content))
            
            self._messages = new_messages
            return self._messages
        except Exception as e:
            print(f"[MemoryService] Failed to load history: {e}")
            return []

    @property
    def messages(self) -> List[BaseMessage]:
        """Returns the currently cached messages."""
        return self._messages

    async def aadd_messages(self, messages: List[BaseMessage]) -> None:
        """Saves new messages to Supabase asynchronously."""
        for msg in messages:
            role = "human" if isinstance(msg, HumanMessage) else "ai"
            try:
                await db.insert("agent_memories", {
                    "user_id": self.user_id,
                    "role": role,
                    "content": msg.content
                })
                self._messages.append(msg)
            except Exception as e:
                print(f"[MemoryService] Failed to save message: {e}")

    def add_messages(self, messages: List[BaseMessage]) -> None:
        """Synchronous add (fallback). Note: This is blocking and not recommended."""
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we are in an async loop, we schedule it
            loop.create_task(self.aadd_messages(messages))
        else:
            # Fallback for sync contexts
            asyncio.run(self.aadd_messages(messages))

    def clear(self) -> None:
        """Clears memory for this user (not implemented for safety, or implement deletion)."""
        # For now, we don't want to accidentally wipe DB records via LangChain.
        self._messages = []
