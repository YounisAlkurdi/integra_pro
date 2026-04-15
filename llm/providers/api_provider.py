"""
API Provider — Integra LLM Engine
مأخوذة من D:\Voiser\tts\backend\llm\providers\api_provider.py
معدّلة: حذف import من backend.config واستبداله بمعاملات مباشرة فقط
"""

def get_api_llm(provider_name: str, model: str, api_key: str, temperature: float = 0.1, **kwargs):
    """
    يُرجع LLM مناسب بناءً على اسم الـ provider.
    مدعوم: openai, anthropic, groq, google/gemini
    """
    provider_name = (provider_name or "openai").lower()

    if provider_name == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(model=model, groq_api_key=api_key, temperature=temperature)

    elif provider_name == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, api_key=api_key, temperature=temperature)

    elif provider_name == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, api_key=api_key, temperature=temperature)

    elif provider_name in ("google", "gemini"):
        from langchain_google_genai import ChatGoogleGenerativeAI
        # Stable config for older langchain-google-genai versions
        return ChatGoogleGenerativeAI(
            model=model, 
            google_api_key=api_key, 
            temperature=0.0
        )

    else:
        raise ValueError(f"Unsupported API provider: {provider_name}")
