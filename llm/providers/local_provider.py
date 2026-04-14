"""
Local Provider (Ollama) — Integra LLM Engine
مأخوذة من D:\Voiser\tts\backend\llm\providers\local_provider.py
معدّلة: إزالة dependency على settings، استخدام قيم افتراضية مباشرة
"""

def get_local_llm(model: str = None, base_url: str = None, temperature: float = 0.1):
    """يُرجع ChatOllama — آمن 100% بدون إنترنت."""
    from langchain_ollama import ChatOllama
    return ChatOllama(
        model=model or "llama3.2:3b",
        base_url=base_url or "http://localhost:11434",
        temperature=temperature
    )
