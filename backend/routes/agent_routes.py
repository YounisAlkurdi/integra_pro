"""
Agent Routes — Integra
LLM Chat endpoint معتمد على llm/langchain_setup.py
لا علاقة له بـ TTS — هذا للتحليل النصي فقط
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from backend.auth import get_current_user
from backend.llm.langchain_setup import get_analysis_chain, get_llm
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_react_agent, create_tool_calling_agent, AgentExecutor
from typing import Optional

router = APIRouter(prefix="/api/agent", tags=["Neural Agent"])

from backend.services.memory_service import SupabaseChatMessageHistory

# MEMORY_BUFFER is now deprecated in favor of Supabase persistent storage
# Phase 4 Migration Complete


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
            from backend.agent_tools import INTEGRA_TOOLS
            
            # Identity Injection
            user_id = user.get("sub", "")
            
            # --- Cloud-Linked Settings Fetch ---
            # If the frontend didn't send a key, pull it from DB (same config saved by llm-config.js)
            if not req.config.get("apiKey") and not req.config.get("hfTokenCustom"):
                from backend.services.database_service import DatabaseService
                db = DatabaseService()
                try:
                    db_res = await db.select("user_settings", "*", filters={"user_id": user_id})
                    if db_res and len(db_res) > 0:
                        db_conf = db_res[0]
                        saved_provider = db_conf.get("llm_provider", "")
                        saved_model    = db_conf.get("llm_model", "")
                        saved_key      = db_conf.get("llm_api_key", "")

                        # Fill only what's missing — keep frontend values if present
                        if not req.config.get("apiKey"):
                            req.config["apiKey"] = saved_key
                        if not req.config.get("apiProvider"):
                            req.config["apiProvider"] = saved_provider
                        if not req.config.get("apiModel"):
                            req.config["apiModel"] = saved_model

                        # ✅ Infer 'source' from provider so get_llm() routes correctly
                        # (mirrors the logic in llm-config.js syncToCloud)
                        if not req.config.get("source"):
                            hf_providers = {"kie", "nvidia", "hf", "huggingface"}
                            local_providers = {"ollama", "local", "lmstudio"}
                            p = saved_provider.lower()
                            if p in hf_providers:
                                req.config["source"] = "hf"
                                req.config["hfProviderType"] = p
                                req.config["hfModelCustom"]  = saved_model
                                req.config["hfTokenCustom"]  = saved_key
                            elif p in local_providers:
                                req.config["source"] = "local"
                            else:
                                req.config["source"] = "api"  # openai, groq, anthropic, etc.
                except Exception as e:
                    print(f"[Supabase] Failed to fetch cloud settings: {e}")

            # Safety: abort if still no key and not a local provider
            provider_check = (req.config.get("apiProvider") or req.config.get("hfProviderType") or "").lower()
            key_check = req.config.get("apiKey") or req.config.get("hfTokenCustom")
            if not key_check and provider_check not in {"local", "ollama", "lmstudio", ""}:
                return {"response": "⚠️ No LLM API key configured. Please set your key in Settings → AI Engine.", "status": "NO_KEY"}

            llm = get_llm(req.config)
            
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
            
            source = req.config.get("source", "api").lower()
            provider = req.config.get("apiProvider", "openai").lower()
            
            # Use ReAct agent for Google, Local (Ollama), and Neural Matrix (Universal)
            use_react = (provider == "google") or (source == "local") or (source == "hf")
            
            if use_react:
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
            
            agent_executor = AgentExecutor(
                agent=agent, 
                tools=INTEGRA_TOOLS, 
                max_iterations=10, 
                verbose=True,
                handle_parsing_errors=True
            )
            
            # Load history from Supabase
            history = SupabaseChatMessageHistory(user_id)
            await history.aload_messages()
            
            # Format history for ReAct if needed
            if use_react:
                chat_history_data = ""
                for m in history.messages:
                    prefix = "Human" if hasattr(m, "type") and m.type == "human" else "AI"
                    chat_history_data += f"{prefix}: {m.content}\n"
            else:
                chat_history_data = history.messages

            result = await agent_executor.ainvoke({
                "input": req.prompt,
                "chat_history": chat_history_data
            })
            
            content = result["output"]
            
            # Save to history (Persistence)
            from langchain_core.messages import HumanMessage, AIMessage
            await history.aadd_messages([
                HumanMessage(content=req.prompt),
                AIMessage(content=content)
            ])
            
        except Exception as tool_err:
            print(f"[Warning] Tool binding failed, falling back to standard chain: {tool_err}")
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


@router.post("/analyze")
async def agent_analyze(req: ChatRequest, user: dict = Depends(get_current_user)):
    """
    Interview Room Neural Copilot — direct LLM chain, no tools, no agent overhead.
    Used by integra-session.js for real-time insights during live interviews.
    Reads the same LLM config the HR set in the LangChain settings page.
    """
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Empty prompt received")

    try:
        user_id = user.get("sub", "")

        # --- Load config: prefer what frontend sends, fill gaps from DB ---
        config = dict(req.config)

        if not config.get("apiKey") and not config.get("hfTokenCustom"):
            from backend.services.database_service import DatabaseService
            db = DatabaseService()
            try:
                db_res = await db.select("user_settings", "*", filters={"user_id": user_id})
                if db_res and len(db_res) > 0:
                    db_conf = db_res[0]
                    saved_provider = db_conf.get("llm_provider", "")
                    saved_model    = db_conf.get("llm_model", "")
                    saved_key      = db_conf.get("llm_api_key", "")

                    config["apiKey"]      = config.get("apiKey") or saved_key
                    config["apiProvider"] = config.get("apiProvider") or saved_provider
                    config["apiModel"]    = config.get("apiModel") or saved_model

                    # Infer correct source for get_llm() routing
                    if not config.get("source"):
                        hf_providers    = {"kie", "nvidia", "hf", "huggingface"}
                        local_providers = {"ollama", "local", "lmstudio"}
                        p = saved_provider.lower()
                        if p in hf_providers:
                            config["source"]         = "hf"
                            config["hfProviderType"] = p
                            config["hfModelCustom"]  = saved_model
                            config["hfTokenCustom"]  = saved_key
                        elif p in local_providers:
                            config["source"] = "local"
                        else:
                            config["source"] = "api"
            except Exception as e:
                print(f"[Analyze] DB settings fetch failed: {e}")

        # Safety check
        key_check = config.get("apiKey") or config.get("hfTokenCustom")
        provider_check = (config.get("apiProvider") or config.get("hfProviderType") or "").lower()
        if not key_check and provider_check not in {"local", "ollama", "lmstudio", ""}:
            return {"response": "⚠️ No LLM API key configured. Please set your key in Settings → AI Engine.", "status": "NO_KEY"}

        # Direct chain — no tools, no agent, fast
        chain = get_analysis_chain(config)
        result = await chain.ainvoke({"text": req.prompt})
        content = result.content if hasattr(result, "content") else str(result)

        return {"response": content, "status": "OK"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")
