"""
Universal Neural Matrix Provider — Integra LLM Engine
يدعم (Kie.ai, NVIDIA, Hugging Face) عبر واجهة متوافقة مع OpenAI.
"""

def get_universal_llm(provider_type: str, model: str, api_key: str, temperature: float = 0.1):
    """
    يُرجع LLM متوافق مع OpenAI بناءً على نوع المزود (Neural Matrix).
    """
    from langchain_openai import ChatOpenAI
    
    # خريطة الـ Base URLs للمزودين المختلفين (Neural Matrix Hub)
    BASE_URLS = {
        "kie": "https://api.kie.ai/v1",
        "nvidia": "https://integrate.api.nvidia.com/v1",
        "hf": "https://api-inference.huggingface.co/v1" # بروتوكول HF الجديد المتوافق مع OpenAI
    }
    
    # اختيار الـ URL المناسب، الافتراضي هو Hugging Face
    p_type = provider_type.lower() if provider_type else "hf"
    base_url = BASE_URLS.get(p_type, BASE_URLS["hf"])
    
    # Special Handling for Kie.ai (Gemini Flash optimization)
    if p_type == "kie" and not model:
        model = "google/gemini-2.0-flash"
    
    return ChatOpenAI(
        model=model or "meta-llama/Llama-3.1-8B-Instruct", # Default for HF if none provided
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=temperature
    )
