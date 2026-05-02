from fastapi import APIRouter, WebSocket
from tracker import BehavioralTracker
import asyncio
import cv2
import numpy as np
import json

router = APIRouter(tags=["Behavioral Analysis"])

# Initialize the tracker at startup
print("👁️ Behavioral Node: Initializing Gaze & Emotion Tracker...")
ai_engine = BehavioralTracker()

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):  return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.ndarray):  return obj.tolist()
        if isinstance(obj, np.bool_):    return bool(obj)
        return super().default(obj)

@router.websocket("/ws/behavioral")
async def behavioral_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time gaze and behavioral tracking.
    This replaces the standalone test.py server.
    """
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive()

            if "text" in message:
                continue

            raw = message.get("bytes")
            if not raw:
                continue

            # Process frame
            nparr = np.frombuffer(raw, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                continue

            # Heavy AI processing in a separate thread to keep WS responsive
            result = await asyncio.to_thread(ai_engine.analyze, frame)

            await websocket.send_text(json.dumps(result, cls=NumpyEncoder))

    except Exception as e:
        print(f"📡 Behavioral WS: Connection closed or error: {e}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
