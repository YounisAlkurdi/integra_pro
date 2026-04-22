from fastapi import FastAPI, WebSocket
from tracker import BehavioralTracker
import cv2
import numpy as np
import uvicorn
import json

app = FastAPI()
ai_engine = BehavioralTracker()

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive()

            # Ignore text/ping messages (e.g. "start", keepalives)
            if "text" in message:
                continue

            raw = message.get("bytes")
            if not raw:
                continue

            nparr = np.frombuffer(raw, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is not None:
                result = ai_engine.analyze(frame)
                await websocket.send_text(json.dumps(result, cls=NumpyEncoder))
    except Exception as e:
        print(f"Connection error: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)