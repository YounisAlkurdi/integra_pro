"""
HuggingFace Provider — Integra LLM Engine
مأخوذة من D:\Voiser\tts\backend\llm\providers\hf_provider.py
معدّلة: إزالة dependency على settings
"""

def get_hf_llm(hf_model: str = None, hf_token: str = None, hf_mode: str = "inference_api", temperature: float = 0.1):
    """
    يُرجع HuggingFace LLM.
    hf_mode: 'inference_api' (سحابي مجاني) أو 'local_pipeline' (محلي)
    """
    hf_model = hf_model or "mistralai/Mistral-7B-Instruct-v0.3"

    if hf_mode == "inference_api":
        from langchain_community.llms import HuggingFaceEndpoint
        return HuggingFaceEndpoint(
            endpoint_url=f"https://api-inference.huggingface.co/models/{hf_model}",
            huggingfacehub_api_token=hf_token,
            task="text-generation"
        )
    else:
        # تشغيل محلي — يحتاج torch مثبّت
        from langchain_community.llms import HuggingFacePipeline
        from transformers import pipeline
        pipe = pipeline("text-generation", model=hf_model)
        return HuggingFacePipeline(pipeline=pipe)
