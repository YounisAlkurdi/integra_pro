"""
Agent Routes — Integra Neural Engine
Enhanced with Persistent Memory Summarization and Neural Caching for SaaS Scalability.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_react_agent, create_tool_calling_agent, AgentExecutor
from langchain_community.chat_message_histories import ChatMessageHistory
import asyncio
import json

# Absolute imports for the modular structure
try:
    from backend.app.auth import get_current_user
    from backend.app.llm.langchain_setup import get_analysis_chain, get_llm
    from backend.app.supabase_client import supabase
    from backend.app import api_bridge
    from backend.app.agent_tools import INTEGRA_TOOLS
except ImportError:
    # Fallback for localized execution/legacy
    from auth import get_current_user
    from llm.langchain_setup import get_analysis_chain, get_llm
    from supabase_client import supabase
    import api_bridge
    from agent_tools import INTEGRA_TOOLS

router = APIRouter(prefix="/api/agent", tags=["Neural Agent"])

async def get_persistent_history(user_id: str, limit: int = 15) -> ChatMessageHistory:
    """
    Retrieves conversation history from Supabase with intelligent summarization.
    If history is long, it collapses old messages to preserve token budget.
    """
    history = ChatMessageHistory()
    try:
        # Fetch last N messages - No cache for real-time chat
        res = await supabase.get("agent_memories", f"user_id=eq.{user_id}&order=created_at.desc&limit={limit}")
        
        if not res:
            return history

        messages = list(reversed(res))
        
        # --- Memory Summarization Logic ---
        # If we have more than 10 messages, we summarize the first 6 into a single context block
        if len(messages) > 10:
            to_summarize = messages[:-4]
            recent = messages[-4:]
            
            summary_text = "PREVIOUS CONTEXT SUMMARY:\n"
            for m in to_summarize:
                role_label = "User" if m['role'] == 'human' else "Assistant"
                summary_text += f"- {role_label}: {m['content'][:100]}...\n"
            
            history.add_ai_message(f"SYSTEM_MEMORY_COMPRESSION: {summary_text}")
            
            for msg in recent:
                if msg['role'] == 'human':
                    history.add_user_message(msg['content'])
                else:
                    history.add_ai_message(msg['content'])
        else:
            for msg in messages:
                if msg['role'] == 'human':
                    history.add_user_message(msg['content'])
                else:
                    history.add_ai_message(msg['content'])
                    
    except Exception as e:
        print(f"=> Neural Memory Error: {e}")
    return history

async def save_memory(user_id: str, role: str, content: str):
    """Saves a new message to Supabase memories table."""
    try:
        await supabase.post("agent_memories", {
            "user_id": user_id,
            "role": role,
            "content": content
        })
    except Exception as e:
        print(f"=> Memory Persistence Failure: {e}")


class ChatRequest(BaseModel):
    prompt: str
    config: dict = {}


@router.post("/chat")
async def agent_chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    """
    Neural Chat Gateway.
    Uses cloud-linked settings and persistent neural buffers.
    """
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Empty prompt received")

    user_id = user.get("sub", "")
    user_email = user.get("email", "Unknown")

    try:
        # 1. Resolve LLM Configuration (Prioritize cloud settings for SaaS consistency)
        if not req.config.get("apiKey"):
            # Use cached fetch for settings
            db_res = await supabase.get("user_settings", f"user_id=eq.{user_id}", use_cache=True, ttl=600)
            if db_res:
                db_conf = db_res[0]
                req.config["apiKey"] = db_conf.get("llm_api_key")
                req.config["apiProvider"] = req.config.get("apiProvider") or db_conf.get("llm_provider", "openai")
                req.config["apiModel"] = req.config.get("apiModel") or db_conf.get("llm_model", "gpt-4o")

        llm = get_llm(req.config)
        provider = req.config.get("apiProvider", "openai").lower()
        
        # 2. System Instruction Injection (Integra Protocol V2)
        core_instruction = (
            "## INTEGRA NEURAL PROTOCOL V2\n"
            f"- IDENTITY: {user_email} | UID: {user_id}\n"
            "- MISSION: Autonomous Command Execution. You manage the Integra platform.\n"
            "- EXTERNAL MATRIX: Access linked services via 'get_external_matrix_nodes'.\n"
            "- ACTION: Use 'matrix_gateway' for external API operations (Stripe, Slack, etc.).\n"
            "- SENSORS: Use 'analyze_web_link' or 'analyze_image' for data synthesis.\n"
            "- MEMORY: You have access to persistent session history.\n"
            "- CONSTRAINTS: Be precise, technical, and goal-oriented. No fluff.\n"
            "- CONFIRMATION: Use [SIGNAL_LOCKED] when a complex multi-step task is finished.\n"
        )

        user_custom_prompt = req.config.get("systemPrompt") or (
            "أنت الواجهة العصبية لنظام Integra. تفاعل بذكاء وسرعة."
        )
        
        final_system_instruction = f"{core_instruction}\n\n{user_custom_prompt}"
        
        # 3. Agent Construction
        if provider == "google":
            # ReAct pattern for Gemini
            template = (
                final_system_instruction + "\n\n"
                "TOOLS:\n{tools}\n\n"
                "HISTORY:\n{chat_history}\n\n"
                "Thought: {agent_scratchpad}\n"
                "Action: [{tool_names}]\n"
                "Action Input: JSON\n"
                "Observation: Result\n"
                "Final Answer: Your Response\n\n"
                "Input: {input}"
            )
            prompt_template = PromptTemplate.from_template(template)
            agent = create_react_agent(llm, INTEGRA_TOOLS, prompt_template)
        else:
            # Tool Calling pattern for OpenAI/Anthropic
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", final_system_instruction),
                MessagesPlaceholder("chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder("agent_scratchpad"),
            ])
            agent = create_tool_calling_agent(llm, INTEGRA_TOOLS, prompt_template)
        
        # 4. Execution Engine
        agent_executor = AgentExecutor(
            agent=agent, 
            tools=INTEGRA_TOOLS, 
            max_iterations=10, 
            verbose=True,
            handle_parsing_errors=True
        )
        
        # 5. Persistent Memory Link
        history = await get_persistent_history(user_id)
        
        result = await agent_executor.ainvoke({
            "input": req.prompt,
            "chat_history": history.messages
        })
        
        content = result["output"]
        
        # 6. Background Persistence (Don't wait to respond)
        asyncio.create_task(save_memory(user_id, 'human', req.prompt))
        asyncio.create_task(save_memory(user_id, 'ai', content))
        
        return {"response": content, "status": "OK"}

    except Exception as e:
        print(f"!! Neural Link Error: {e}")
        # Robust Fallback to standard chain
        try:
            chain = get_analysis_chain(req.config)
            fallback_res = await chain.ainvoke({"text": req.prompt})
            content = fallback_res.content if hasattr(fallback_res, "content") else str(fallback_res)
            return {"response": content, "status": "FALLBACK_ACTIVE"}
        except Exception as fallback_err:
            raise HTTPException(status_code=500, detail=f"Total Neural Failure: {str(fallback_err)}")


@router.get("/status")
async def agent_status(user: dict = Depends(get_current_user)):
    return {
        "status": "ONLINE",
        "engine": "LangChain/IntegraV2",
        "caching": "ENABLED",
        "memory_summarization": "ACTIVE"
    }

@router.post("/external-mcps/test")
async def test_external_mcp(req: dict, user: dict = Depends(get_current_user)):
    """Test connection to an external matrix service."""
    return await api_bridge.test_connection(req.get("provider"), req.get("mcp_config"))
