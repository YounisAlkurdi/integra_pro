"""
Agent Routes — Integra
LLM Chat endpoint معتمد على llm/langchain_setup.py
لا علاقة له بـ TTS — هذا للتحليل النصي فقط
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from auth import get_current_user
from llm.langchain_setup import get_analysis_chain, get_llm

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
        chain = get_analysis_chain(req.config)
        result = await chain.ainvoke({"text": req.prompt})
        
        # AIMessage.content أو string
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
