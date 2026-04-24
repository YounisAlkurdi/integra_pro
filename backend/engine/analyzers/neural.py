import asyncio
from concurrent.futures import ThreadPoolExecutor

class NeuralDetector:
    """Neural AI Detection using Transformer models (SOTA Research)."""
    
    def __init__(self):
        self.model_name = "roberta-base-openai-detector"
        self.executor = ThreadPoolExecutor(max_workers=2)
        try:
            from transformers import pipeline
            import torch
            # Check for GPU
            device = 0 if torch.cuda.is_available() else -1
            self.pipe = pipeline("text-classification", model=self.model_name, device=device)
            self.online = True
            print("Neural Engine: ONLINE")
        except Exception as e:
            print(f"Neural model load failed: {e}. Using Statistical Forensics only.")
            self.online = False

    def _sync_predict(self, text):
        if not self.online: return {"label": "Human", "score": 0.5}
        try:
            results = self.pipe(text[:1500]) 
            return results[0]
        except:
            return {"label": "Human", "score": 0.5}

    async def predict_async(self, text):
        """Runs heavy neural inference in a separate thread."""
        if not self.online: return {"ai_label": "Untested", "confidence": 0.5}
        
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(self.executor, self._sync_predict, text)
            return {
                "ai_label": result["label"],
                "confidence": round(result["score"], 4)
            }
        except:
            return {"ai_label": "Error", "confidence": 0.5}
