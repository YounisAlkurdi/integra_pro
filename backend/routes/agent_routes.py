"""
Agent Routes — Integra SaaS
Optimized with memory caching and persistent intelligence.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
import json
import asyncio
from pydantic import BaseModel
from typing import List, Optional
from backend.core.auth import get_current_user
from backend.core.supabase_client import supabase
from backend.core.cache import integra_cache
from llm.langchain_setup import get_analysis_chain, get_llm
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_react_agent, create_tool_calling_agent, AgentExecutor
from langchain_community.chat_message_histories import ChatMessageHistory
from ..services.agent_tools import INTEGRA_TOOLS
from backend.core.rate_limit import strict_limit, standard_limit

from backend.services.audit_logger import capture_event

router = APIRouter(prefix="/agent", tags=["Neural Agent"])

async def get_persistent_history(user_id: str, limit: int = 10) -> ChatMessageHistory:
    """Retrieves conversation history with short-term memory caching."""
    cache_key = f"agent:history:{user_id}"
    cached_history = integra_cache.get(cache_key)
    
    if cached_history:
        history = ChatMessageHistory()
        for msg in cached_history:
            if msg['role'] == 'human':
                history.add_user_message(msg['content'])
            else:
                history.add_ai_message(msg['content'])
        return history

    history = ChatMessageHistory()
    try:
        # Fetch from Supabase
        res = await supabase.get("agent_memories", f"user_id=eq.{user_id}&order=created_at.desc&limit={limit}", cache_ttl=0)
        
        # Save to cache for next request
        integra_cache.set(cache_key, res, ttl=300) # 5 min cache
        
        for msg in reversed(res):
            if msg['role'] == 'human':
                history.add_user_message(msg['content'])
            else:
                history.add_ai_message(msg['content'])
    except Exception as e:
        print(f"=> Memory Retrieval Error: {e}")
    return history

async def save_memory(user_id: str, role: str, content: str):
    """Saves to Supabase and invalidates local history cache."""
    try:
        await supabase.post("agent_memories", {
            "user_id": user_id,
            "role": role,
            "content": content
        })
        # Invalidate cache
        integra_cache.delete(f"agent:history:{user_id}")
    except Exception as e:
        print(f"=> Memory Storage Error: {e}")

class ChatRequest(BaseModel):
    prompt: str
    config: dict = {}

@router.post("/chat", dependencies=[Depends(strict_limit)])
async def agent_chat(req: ChatRequest, request: Request, user: dict = Depends(get_current_user)):
    """
    Neural Chat — SaaS Optimized.
    """
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Empty prompt received")

    user_id = user.get("sub", "")
    user_email = user.get("email", "Unknown")

    # --- SETTINGS CACHING ---
    if not req.config.get("apiKey"):
        cache_key = f"user:settings:{user_id}"
        db_conf = integra_cache.get(cache_key)
        
        if not db_conf:
            db_res = await supabase.get("user_settings", f"user_id=eq.{user_id}", cache_ttl=300)
            if db_res:
                db_conf = db_res[0]
                integra_cache.set(cache_key, db_conf, ttl=300)
        
        if db_conf:
            req.config["apiKey"] = db_conf.get("llm_api_key")
            req.config.setdefault("apiProvider", db_conf.get("llm_provider", "openai"))
            req.config.setdefault("apiModel", db_conf.get("llm_model", "gpt-4o"))

    async def event_generator():
        try:
            llm = get_llm(req.config)
            
            # --- ENHANCED SYSTEM PROTOCOL ---
            core_instruction = (
                "## INTEGRA COMMAND ENGINE PROTOCOL\n"
                f"- User Identity: {user_email} (ID: {user_id})\n"
                "- ROLE: You are an autonomous Command Executor & System Manager. Always think before you act.\n"
                "- MATRIX NODES: Check linked services via 'get_external_matrix_nodes'.\n"
                "- EXTERNAL PROTOCOLS: You are authorized to perform tasks for any linked service discovered. Use 'matrix_gateway'.\n"
                "  * target_service: Exact 'mcp_name' from the node list, operation_goal: 'Tool/Endpoint Name', payload_json: 'JSON_PARAMETERS'.\n"
                "- NEURAL NODES: Use 'execute_establish_secure_link' for interview sessions.\n"
                "- CLARIFICATION: If missing Email/Position/Context, ASK the user. Do not assume.\n"
                "- TELEMETRY: Use 'get_neural_telemetry' for status reports.\n"
                "- EXECUTION: ONLY call tools when you have CLEAR and COMPLETE data.\n"
                "  * ALWAYS pass user_id inside your JSON payloads if required.\n"
                "- FINISH: Confirm execution with terms like 'NEURAL LINK ACTIVE' or 'SIGNAL TRANSMITTED'.\n"
            )

            user_custom_prompt = req.config.get("systemPrompt") or (
                "أنت المساعد الذكي الخاص بنظام Integra للتحكم والمراقبة. "
                "كن ذكياً، مختصراً، وقوياً في إجاباتك بالعربية."
            )
            final_system_instruction = f"{core_instruction}\n\n{user_custom_prompt}"
            
            provider = req.config.get("apiProvider", "openai").lower()
            
            # Note: For simplicity in this session, we stream the final answer.
            # Real tool-streaming requires a more complex astream_events setup.
            
            if provider == "google":
                # Fallback for Google (React Agent) as it doesn't stream as easily as ToolCalling
                template = final_system_instruction + "\n\nQuestion: {input}\nThought: {agent_scratchpad}"
                prompt_template = PromptTemplate.from_template(template)
                agent = create_react_agent(llm, INTEGRA_TOOLS, prompt_template)
            else:
                prompt_template = ChatPromptTemplate.from_messages([
                    ("system", final_system_instruction),
                    MessagesPlaceholder("chat_history", optional=True),
                    ("human", "{input}"),
                    MessagesPlaceholder("agent_scratchpad"),
                ])
                agent = create_tool_calling_agent(llm, INTEGRA_TOOLS, prompt_template)
            
            agent_executor = AgentExecutor(
                agent=agent, 
                tools=INTEGRA_TOOLS, 
                max_iterations=10, 
                verbose=False,
                handle_parsing_errors=True
            )
            
            history = await get_persistent_history(user_id)
            
            full_response = ""
            # Simple streaming implementation
            async for chunk in agent_executor.astream({"input": req.prompt, "chat_history": history.messages}):
                if "output" in chunk:
                    output = chunk["output"]
                    full_response += output
                    yield f"data: {json.dumps({'text': output})}\n\n"
            
            # Save memory at the end
            asyncio.create_task(save_memory(user_id, 'human', req.prompt))
            asyncio.create_task(save_memory(user_id, 'ai', full_response))
            capture_event(user_id, "AGENT_CHAT", "agent", None, {"prompt_length": len(req.prompt)}, ip=request.client.host, ua=request.headers.get("user-agent", "unknown"))
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/status", dependencies=[Depends(standard_limit)])
async def agent_status(user: dict = Depends(get_current_user)):
    """يُرجع حالة الـ LLM engine."""
    return {
        "status": "ONLINE",
        "engine": "LangChain",
        "providers": ["openai", "anthropic", "groq", "google", "local", "hf"]
    }
