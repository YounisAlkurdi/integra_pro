"""
Agent Routes — Integra
LLM Chat endpoint معتمد على llm/langchain_setup.py
لا علاقة له بـ TTS — هذا للتحليل النصي فقط
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from auth import get_current_user
from llm.langchain_setup import get_analysis_chain, get_llm
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_react_agent, create_tool_calling_agent, AgentExecutor

router = APIRouter(prefix="/api/agent", tags=["Neural Agent"])


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
        # Check if the model supports tools (like OpenAI, Google, Anthropic, or HF with specific configs)
        # We will attempt to use bind_tools. If we get a NotImplementedError or similar, we fallback.
        try:
            from agent_tools import INTEGRA_TOOLS
            
            # Identity Injection
            user_email = user.get("email", "Unknown")
            user_id = user.get("sub", "")
            
            # --- NEW: Cloud-Linked Settings Fetch ---
            # If the request doesn't have a key, check the DB
            if not req.config.get("apiKey"):
                from nodes import _supabase_request
                try:
                    db_res = _supabase_request("GET", f"user_settings?user_id=eq.{user_id}")
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
            user_id = user.get("sub", "")
            
            # Core Protocol (Mandatory instructions for the Integra Command Engine)
            core_instruction = (
                "## INTEGRA COMMAND ENGINE PROTOCOL\n"
                f"- User Identity: {user_email} (ID: {user_id})\n"
                "- ROLE: You are an autonomous Command Executor. Do NOT engage in conversation when a task is clear.\n"
                "- EXECUTION: When asked to create/send/delete, use 'execute_...' tools IMMEDIATELY.\n"
                "- MANDATORY INPUT: Tools like 'execute_establish_secure_link' REQUIRE a single JSON string as input.\n"
                "  * Example: Action Input: {{\"candidate_name\": \"...\", \"position\": \"...\", \"user_id\": \"YOUR_ID_HERE\"}}\n"
                "- NO QUESTIONS: Do NOT ask for company name or location unless absolutely necessary. Use defaults.\n"
                "- TELEMETRY: For 'stats', use 'get_neural_telemetry'.\n"
                f"- ALWAYS pass user_id='{user_id}' inside your JSON payload.\n"
                "- FINISH: Once the tool returns success, just confirm 'Signal Transmitted' and shut down.\n"
            )

            # Combine with user's custom system prompt if provided
            user_custom_prompt = req.config.get("systemPrompt") or (
                "أنت المساعد الذكي الخاص بنظام Integra للتحكم والمراقبة. "
                "كن ذكياً، مختصراً، وقوياً في إجاباتك بالعربية."
            )
            
            final_system_instruction = f"{core_instruction}\n\n{user_custom_prompt}"
            
            # ReAct Prompt Structure
            template = (
                f"{final_system_instruction}\n\n"
                "TOOLS:\n"
                "------\n"
                "You have access to the following tools:\n"
                "{tools}\n\n"
                "To use a tool, please use the following format:\n"
                "Thought: Do I need to use a tool? Yes\n"
                "Action: the action to take, should be one of [{tool_names}]\n"
                "Action Input: the input to the action\n"
                "Observation: the result of the action\n"
                "... (this Thought/Action/Action Input/Observation can repeat N times)\n"
                "Thought: I now know the final answer\n"
                "Final Answer: the final answer to the original input question\n\n"
                "Begin!\n\n"
                "Question: {input}\n"
                "Thought: {agent_scratchpad}"
            )
            
            prompt_template = PromptTemplate.from_template(template)
            llm = get_llm(req.config)
            
            agent = create_react_agent(llm, INTEGRA_TOOLS, prompt_template)
            agent_executor = AgentExecutor(
                agent=agent, 
                tools=INTEGRA_TOOLS, 
                max_iterations=10, 
                verbose=True,
                handle_parsing_errors=True
            )
            
            result = await agent_executor.ainvoke({"input": req.prompt})
            content = result["output"]
            
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
