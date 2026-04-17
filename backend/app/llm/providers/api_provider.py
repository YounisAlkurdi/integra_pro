"""
API Provider — Integra LLM Engine
"""

def get_api_llm(provider_name: str, model: str, api_key: str, temperature: float = 0.1, **kwargs):
    """
    Returns an LLM based on provider name.
    Supported: openai, anthropic, groq, google/gemini
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
        return ChatGoogleGenerativeAI(
            model=model, 
            google_api_key=api_key, 
            temperature=temperature
        )

    else:
        raise ValueError(f"Unsupported API provider: {provider_name}")
