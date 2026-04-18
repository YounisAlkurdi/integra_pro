"""
LangChain Setup — Integra LLM Engine
مأخوذة من D:\Voiser\tts\backend\llm\langchain_setup.py
معدّلة: متكاملة مع نظام Integra (تحليل مقابلات HR)
"""

from langchain_core.prompts import ChatPromptTemplate


DEFAULT_SYSTEM_PROMPT = (
    "أنت (Integra AI Agent)، النظام الذكي لإدارة مركز التحكم العصبي للمقابلات. "
    "أنت مدمج كلياً في الموقع ولديك صلاحية استخدام 10 أدوات (Tools) متطورة تشمل: "
    "التحكم في الجلسات، إنشاء المقابلات، إرسال الإيميلات، مراقبة الإيرادات والفواتير، وقراءة سجلات الأمان. "
    "استخدم الأدوات دائماً للحصول على بيانات حقيقية. كن دقيقاً، مهنياً، ومباشراً في إجابتك."
)


def get_llm(llm_config: dict):
    """
    يُرجع LLM مناسب بناءً على إعدادات الواجهة.
    llm_config dict يُرسَل من الـ Frontend (localStorage).
    """
    source = llm_config.get("source", "api")
    temperature = float(llm_config.get("temperature", 0.1))

    if source == "local":
        from llm.providers.local_provider import get_local_llm
        return get_local_llm(
            model=llm_config.get("localModel"),
            base_url=llm_config.get("localUrl"),
            temperature=temperature
        )
    elif source == "hf":
        from llm.providers.hf_provider import get_hf_llm
        return get_hf_llm(
            hf_model=llm_config.get("hfModel"),
            hf_token=llm_config.get("hfToken"),
            hf_mode=llm_config.get("hfMode", "inference_api"),
            temperature=temperature
        )
    else:  # api (default)
        from llm.providers.api_provider import get_api_llm
        return get_api_llm(
            provider_name=llm_config.get("apiProvider", "openai"),
            model=llm_config.get("apiModel", "gpt-4o"),
            api_key=llm_config.get("apiKey", ""),
            temperature=temperature,
            system_instruction=llm_config.get("systemPrompt")
        )


def get_analysis_chain(llm_config: dict):
    """
    يُرجع chain جاهز لتحليل نص مقابلة.
    مأخوذ من TTS langchain_setup.py وموسّع لـ Integra.
    """
    llm = get_llm(llm_config)
    system_instruction = llm_config.get("systemPrompt", DEFAULT_SYSTEM_PROMPT)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system_instruction}"),
        ("human", "{text}")
    ])

    # partial يثبّت system_instruction في الـ chain
    chain = prompt.partial(system_instruction=system_instruction) | llm
    return chain
