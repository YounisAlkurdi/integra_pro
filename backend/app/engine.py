"""
Integra Neural Engine — AI Agent Core
Responsible for tool binding, memory management, and execution logic.
"""

import logging
from typing import List, Dict, Any
from langchain.agents import create_react_agent, create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory

from .supabase_client import supabase
from .llm.langchain_setup import get_llm, get_analysis_chain
from .tools.protocol_tools import PROTOCOL_TOOLS
from .tools.matrix_tools import MATRIX_TOOLS
from .tools.sensor_tools import SENSOR_TOOLS

logger = logging.getLogger("neural-engine")

# Combine all tools
ALL_TOOLS = PROTOCOL_TOOLS + MATRIX_TOOLS + SENSOR_TOOLS

async def get_persistent_history(user_id: str, limit: int = 10) -> ChatMessageHistory:
    """Retrieves conversation history from Supabase."""
    history = ChatMessageHistory()
    try:
        res = await supabase.get("agent_memories", f"user_id=eq.{user_id}&order=created_at.desc&limit={limit}")
        for msg in reversed(res):
            if msg['role'] == 'human':
                history.add_user_message(msg['content'])
            else:
                history.add_ai_message(msg['content'])
    except Exception as e:
        logger.error(f"Memory Retrieval Error: {e}")
    return history

async def save_memory(user_id: str, role: str, content: str):
    """Saves a message to Supabase."""
    try:
        await supabase.post("agent_memories", {
            "user_id": user_id,
            "role": role,
            "content": content
        })
    except Exception as e:
        logger.error(f"Memory Storage Error: {e}")

async def run_agent(prompt: str, config: Dict[str, Any], user_context: Dict[str, Any]) -> str:
    """
    Core execution loop for the Integra Agent.
    """
    user_id = user_context.get("user_id")
    user_email = user_context.get("email", "Unknown")
    
    # 1. Initialize LLM
    llm = get_llm(config)
    if not llm:
        return "LLM Configuration Error: Unable to initialize provider."

    # 2. Construct System Prompt
    core_instruction = (
        "## INTEGRA COMMAND ENGINE PROTOCOL\n"
        f"- User Identity: {user_email} (ID: {user_id})\n"
        "- ROLE: You are an autonomous Command Executor & System Manager.\n"
        "- MATRIX NODES: Check linked services via 'get_external_matrix_nodes'.\n"
        "- NEURAL NODES: Use 'execute_establish_secure_link' for interview sessions.\n"
        "- CLARIFICATION: If missing Email/Position/Context, ASK the user.\n"
        "- EXECUTION: ONLY call tools when you have CLEAR data.\n"
    )
    
    user_custom_prompt = config.get("systemPrompt") or "أنت المساعد الذكي الخاص بنظام Integra."
    final_system_instruction = f"{core_instruction}\n\n{user_custom_prompt}"
    
    # 3. Choose Agent Strategy
    provider = config.get("apiProvider", "openai").lower()
    
    if provider == "google":
        # ReAct pattern for models that struggle with native tool calling
        template = (
            final_system_instruction + "\n\n"
            "TOOLS: {tools}\n\n"
            "CHAT HISTORY: {chat_history}\n\n"
            "Question: {input}\n"
            "Thought: {agent_scratchpad}"
        )
        prompt_template = PromptTemplate.from_template(template)
        agent = create_react_agent(llm, ALL_TOOLS, prompt_template)
    else:
        # Native tool calling for OpenAI/Anthropic
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", final_system_instruction),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ])
        agent = create_tool_calling_agent(llm, ALL_TOOLS, prompt_template)

    # 4. Initialize Executor
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=ALL_TOOLS, 
        max_iterations=10, 
        verbose=True,
        handle_parsing_errors=True
    )

    # 5. Execute with History
    history = await get_persistent_history(user_id)
    
    try:
        result = await agent_executor.ainvoke({
            "input": prompt,
            "chat_history": history.messages
        })
        output = result["output"]
        
        # 6. Persist Memory (Fire and forget)
        import asyncio
        asyncio.create_task(save_memory(user_id, 'human', prompt))
        asyncio.create_task(save_memory(user_id, 'ai', output))
        
        return output
    except Exception as e:
        logger.error(f"Agent Execution Failure: {e}")
        return f"CRITICAL SYSTEM ERROR: {str(e)}"
