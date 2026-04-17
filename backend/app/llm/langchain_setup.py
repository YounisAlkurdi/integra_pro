"""
LangChain Setup — Integra LLM Engine (Modular)
"""

from langchain_core.prompts import ChatPromptTemplate

DEFAULT_SYSTEM_PROMPT = (
    "أنت (Integra AI Agent)، النظام الذكي لإدارة مركز التحكم العصبي للمقابلات. "
    "أنت مدمج كلياً في الموقع ولديك صلاحية استخدام أدوات (Tools) متطورة تشمل: "
    "التحكم في الجلسات، إنشاء المقابلات، إرسال الإيميلات، مراقبة الإيرادات والفواتير، وقراءة سجلات الأمان. "
    "استخدم الأدوات دائماً للحصول على بيانات حقيقية. كن دقيقاً، مهنياً، ومباشراً في إجابتك."
)

def get_llm(llm_config: dict):
    """
    Returns an LLM based on config.
    """
    source = llm_config.get("source", "api")
    temperature = float(llm_config.get("temperature", 0.1))

    if source == "api":
        from .providers.api_provider import get_api_llm
        return get_api_llm(
            provider_name=llm_config.get("apiProvider", "openai"),
            model=llm_config.get("apiModel", "gpt-4o"),
            api_key=llm_config.get("apiKey", ""),
            temperature=temperature
        )
    # Fallback/Other sources could be added here
    return None

def get_analysis_chain(llm_config: dict):
    llm = get_llm(llm_config)
    if not llm: return None
    
    system_instruction = llm_config.get("systemPrompt", DEFAULT_SYSTEM_PROMPT)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system_instruction}"),
        ("human", "{text}")
    ])

    chain = prompt.partial(system_instruction=system_instruction) | llm
    return chain
