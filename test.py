from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from tracker import BehavioralTracker
import asyncio
import cv2
import numpy as np
import uvicorn
import json

app = FastAPI()

# السماح للـ HTML بالاتصال من أي origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ai_engine = BehavioralTracker()


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):  return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.ndarray):  return obj.tolist()
        if isinstance(obj, np.bool_):    return bool(obj)
        return super().default(obj)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive()

            if "text" in message:
                continue

            raw = message.get("bytes")
            if not raw:
                continue

            nparr = np.frombuffer(raw, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                continue

            # FIX 2: نقل التحليل الثقيل لـ thread pool
            # بدلاً من تجميد event loop بـ solvePnP و MediaPipe
            result = await asyncio.to_thread(ai_engine.analyze, frame)

            await websocket.send_text(json.dumps(result, cls=NumpyEncoder))

    except Exception as e:
        print(f"Connection closed: {e}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


if __name__ == "__main__":
    # FIX 1: البورت 8001 لعدم التعارض مع السيرفر الرئيسي
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="warning")