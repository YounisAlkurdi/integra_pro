"""
Agent Routes — Integra
LLM Chat endpoint معتمد على llm/langchain_setup.py
لا علاقة له بـ TTS — هذا للتحليل النصي فقط
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_react_agent, create_tool_calling_agent, AgentExecutor
from langchain_community.chat_message_histories import ChatMessageHistory
import asyncio

# Absolute imports for the new structure
try:
    from backend.auth import get_current_user
    from backend.llm.langchain_setup import get_analysis_chain, get_llm
    from backend.supabase_client import supabase
    from backend import api_bridge
except ImportError:
    # Fallback for direct execution
    from auth import get_current_user
    from llm.langchain_setup import get_analysis_chain, get_llm
    from supabase_client import supabase
    import api_bridge

router = APIRouter(prefix="/api/agent", tags=["Neural Agent"])

async def get_persistent_history(user_id: str, limit: int = 10) -> ChatMessageHistory:
    """Retrieves conversation history from Supabase memories table."""
    history = ChatMessageHistory()
    try:
        # Fetch last N messages for context
        res = await supabase.get("agent_memories", f"user_id=eq.{user_id}&order=created_at.desc&limit={limit}")
        # Reverse to get chronological order
        if res:
            for msg in reversed(res):
                if msg['role'] == 'human':
                    history.add_user_message(msg['content'])
                else:
                    history.add_ai_message(msg['content'])
    except Exception as e:
        print(f"=> Memory Retrieval Error: {e}")
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
        print(f"=> Memory Storage Error: {e}")


class ChatRequest(BaseModel):
    prompt: str
    config: dict = {}


class SimpleChat(BaseModel):
    """Chat بسيط بدون config — يستخدم الإعدادات الافتراضية."""
    message: str
    config: dict = {}


@router.post("/chat")
async def agent_chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    """
    Neural Chat — يحلل النص باستخدام LLM المحدد في إعدادات الواجهة.
    الـ config يُرسَل من localStorage في الواجهة.
    """
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Empty prompt received")

    try:
        # Check if the model supports tools
        try:
            try:
                from backend.agent_tools import INTEGRA_TOOLS
                from backend.nodes import _supabase_request
            except ImportError:
                from agent_tools import INTEGRA_TOOLS
                from nodes import _supabase_request
            
            # Identity Injection
            user_id = user.get("sub", "")
            
            # --- NEW: Cloud-Linked Settings Fetch ---
            if not req.config.get("apiKey"):
                try:
                    db_res = await _supabase_request("GET", f"user_settings?user_id=eq.{user_id}")
                    if db_res and len(db_res) > 0:
                        db_conf = db_res[0]
                        req.config["apiKey"] = db_conf.get("llm_api_key")
                        if not req.config.get("apiProvider"):
                            req.config["apiProvider"] = db_conf.get("llm_provider", "openai")
                        if not req.config.get("apiModel"):
                            req.config["apiModel"] = db_conf.get("llm_model", "gpt-4o")
                except Exception as e:
                    print(f"[Supabase] Failed to fetch cloud settings: {e}")

            llm = get_llm(req.config)
            
            # IDENTITY INJECTION: Tell the agent exactly who it's talking to
            user_email = user.get("email", "Unknown")
            
            # Core Protocol (Mandatory instructions for the Integra Command Engine)
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
            
            if provider == "google":
                template = (
                    final_system_instruction + "\n\n"
                    "TOOLS:\n"
                    "------\n"
                    "You have access to the following tools:\n"
                    "{tools}\n\n"
                    "CHAT HISTORY:\n"
                    "-------------\n"
                    "{chat_history}\n\n"
                    "To use a tool, please use the following format:\n"
                    "Thought: Do I need to use a tool? Yes\n"
                    "Action: the action to take, should be one of [{tool_names}]\n"
                    "Action Input: the input to the action (must be JSON)\n"
                    "Observation: the result of the action\n"
                    "... (this Thought/Action/Action Input/Observation can repeat N times)\n"
                    "Thought: I now know the final answer\n"
                    "Final Answer: the final answer to the original input question\n\n"
                    "Begin!\n\n"
                    "Question: {input}\n"
                    "Thought: {agent_scratchpad}"
                )
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
            
            # --- AGENT ENGINE INITIALIZATION ---
            agent_executor = AgentExecutor(
                agent=agent, 
                tools=INTEGRA_TOOLS, 
                max_iterations=10, 
                verbose=True,
                handle_parsing_errors=True
            )
            
            # Retrieve Persistent History from Supabase
            history = await get_persistent_history(user_id)
            
            result = await agent_executor.ainvoke({
                "input": req.prompt,
                "chat_history": history.messages
            })
            
            content = result["output"]
            
            # Persist the interaction to Supabase memory
            asyncio.create_task(save_memory(user_id, 'human', req.prompt))
            asyncio.create_task(save_memory(user_id, 'ai', content))
            
        except Exception as tool_err:
            print(f"[Warning] Tool binding failed, falling back to standard chain: {tool_err}")
            # Fallback to standard chain if the LLM doesn't support tools properly
            chain = get_analysis_chain(req.config)
            result = await chain.ainvoke({"text": req.prompt})
            content = result.content if hasattr(result, "content") else str(result)
            
        return {"response": content, "status": "OK"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")


@router.get("/status")
async def agent_status(user: dict = Depends(get_current_user)):
    """يُرجع حالة الـ LLM engine."""
    return {
        "status": "ONLINE",
        "engine": "LangChain",
        "providers": ["openai", "anthropic", "groq", "google", "local", "hf"]
    }


class ExternalMCPTest(BaseModel):
    provider: str
    mcp_config: dict


@router.post("/external-mcps/test")
async def test_external_mcp(req: ExternalMCPTest, user: dict = Depends(get_current_user)):
    """Test connection to an external matrix service."""
    return await api_bridge.test_connection(req.provider, req.mcp_config)
